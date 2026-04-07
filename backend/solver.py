import json
from collections import defaultdict
from typing import Dict, Any

from ortools.sat.python import cp_model

from .database import SessionLocal
from .models import Professor, Course, TimeSlot, Schedule, Section, Preference, Room


def run_solver(semester: str, year: int) -> Dict[str, Any]:
    """
    Executes the OR-Tools CP-SAT solver to assign professors to courses, timeslots, and rooms.
    """
    db = SessionLocal()

    try:
        # 1. Fetch all data
        professors = db.query(Professor).filter(Professor.active == True).all()
        courses = db.query(Course).filter(Course.semester == semester, Course.year == year).all()
        timeslots = db.query(TimeSlot).filter(TimeSlot.active == True).all()
        rooms = db.query(Room).all()

        preferences = {}
        for p in professors:
            pref = db.query(Preference).filter(
                Preference.professor_id == p.id,
                Preference.semester == semester,
                Preference.year == year
            ).first()
            if pref and pref.parsed_json:
                preferences[p.id] = pref.parsed_json
            else:
                preferences[p.id] = {}

        if not professors or not courses or not timeslots or not rooms:
            return {"status": "error", "message": "Missing basic data (professors, courses, timeslots, or rooms)."}

        # 2. Initialize Model
        model = cp_model.CpModel()

        # 3. Create Decision Variables (Sparsified)
        # We only create variables if the room's capacity can actually hold the course.
        # This dramatically reduces the search space and prevents memory explosion.
        assign = {}
        for p in professors:
            for c in courses:
                for t in timeslots:
                    for r in rooms:
                        if r.capacity >= c.capacity:
                            assign[(p.id, c.id, t.id, r.id)] = model.NewBoolVar(f"assign_p{p.id}_c{c.id}_t{t.id}_r{r.id}")

        assumptions_map = {}

        # Helper to safely yield variables that actually exist in the dict
        def get_vars(*args, **kwargs):
            return [assign[k] for k in assign.keys() if all(k[i] == v for i, v in kwargs.items())]

        # 4. HARD CONSTRAINTS
        
        # A. A professor cannot teach more than one course at the exact same time
        b_physics = model.NewBoolVar("assump_A_physics")
        for p in professors:
            for t in timeslots:
                # Get all variables for this professor at this timeslot
                vars_pt = [assign[k] for k in assign if k[0] == p.id and k[2] == t.id]
                model.AddAtMostOne(vars_pt).OnlyEnforceIf(b_physics)
        model.AddAssumption(b_physics)
        assumptions_map[b_physics.Index()] = "A professor cannot teach multiple courses at the exact same time."

        # A2. A room cannot have more than one course at the exact same time
        b_room_double = model.NewBoolVar("assump_A2_room_double")
        for r in rooms:
            for t in timeslots:
                # Get all variables for this room at this timeslot
                vars_rt = [assign[k] for k in assign if k[2] == t.id and k[3] == r.id]
                model.AddAtMostOne(vars_rt).OnlyEnforceIf(b_room_double)
        model.AddAssumption(b_room_double)
        assumptions_map[b_room_double.Index()] = "A room cannot be double-booked at the exact same time."

        # A3. Room capacity must meet or exceed course capacity (HANDLED AT CREATION)
        # Variables where c.capacity > r.capacity simply do not exist in the `assign` dict anymore.
        # This implicitly enforces A3 and dramatically speeds up the solver.

        # B. Minimum/Maximum Course Sections
        for c in courses:
            vars_c = [assign[k] for k in assign if k[1] == c.id]
            
            b_min = model.NewBoolVar(f"assump_B_min_c{c.id}")
            model.Add(sum(vars_c) >= c.min_sections).OnlyEnforceIf(b_min)
            model.AddAssumption(b_min)
            assumptions_map[b_min.Index()] = f"Course {c.code} requires a minimum of {c.min_sections} sections."
            
            b_max = model.NewBoolVar(f"assump_B_max_c{c.id}")
            model.Add(sum(vars_c) <= c.max_sections).OnlyEnforceIf(b_max)
            model.AddAssumption(b_max)
            assumptions_map[b_max.Index()] = f"Course {c.code} is capped at a maximum of {c.max_sections} sections."

        # C. Professor Load Limits & Sabbatical
        for p in professors:
            pref = preferences.get(p.id, {})
            on_leave = pref.get("on_leave", False)
            
            vars_p = [assign[k] for k in assign if k[0] == p.id]

            if on_leave:
                b = model.NewBoolVar(f"assump_C_leave_p{p.id}")
                model.Add(sum(vars_p) == 0).OnlyEnforceIf(b)
                model.AddAssumption(b)
                assumptions_map[b.Index()] = f"Professor {p.name} is on leave and must teach 0 sections."
            else:
                db_limit = p.fall_count if semester.lower() == "fall" else p.spring_count
                email_limit = pref.get("max_load")
                limit = min(db_limit, email_limit) if email_limit is not None else db_limit
                    
                b = model.NewBoolVar(f"assump_C_load_p{p.id}")
                model.Add(sum(vars_p) <= limit).OnlyEnforceIf(b)
                model.AddAssumption(b)
                assumptions_map[b.Index()] = f"Professor {p.name} cannot teach more than {limit} sections."

        # D. Core Requirements Constraint
        ssc_sections = [assign[k] for k in assign for c in courses if k[1] == c.id and c.core_ssc]
        ht_sections = [assign[k] for k in assign for c in courses if k[1] == c.id and c.core_ht]
        ga_sections = [assign[k] for k in assign for c in courses if k[1] == c.id and c.core_ga]
        wem_sections = [assign[k] for k in assign for c in courses if k[1] == c.id and c.core_wem]
        
        if ssc_sections: 
            b = model.NewBoolVar("assump_D_ssc")
            model.Add(sum(ssc_sections) >= 1).OnlyEnforceIf(b)
            model.AddAssumption(b)
            assumptions_map[b.Index()] = "At least one Social Science Core (SSC) course must be scheduled."
            
        if ht_sections: 
            b = model.NewBoolVar("assump_D_ht")
            model.Add(sum(ht_sections) >= 1).OnlyEnforceIf(b)
            model.AddAssumption(b)
            assumptions_map[b.Index()] = "At least one Historical Traditions (HT) core course must be scheduled."
            
        if ga_sections: 
            b = model.NewBoolVar("assump_D_ga")
            model.Add(sum(ga_sections) >= 1).OnlyEnforceIf(b)
            model.AddAssumption(b)
            assumptions_map[b.Index()] = "At least one Global Awareness (GA) core course must be scheduled."
            
        if wem_sections: 
            b = model.NewBoolVar("assump_D_wem")
            model.Add(sum(wem_sections) >= 1).OnlyEnforceIf(b)
            model.AddAssumption(b)
            assumptions_map[b.Index()] = "At least one Written Expression (WEM) core course must be scheduled."

        # E. Timeslot Capacity
        for t in timeslots:
            vars_t = [assign[k] for k in assign if k[2] == t.id]
            b = model.NewBoolVar(f"assump_E_cap_t{t.id}")
            model.Add(sum(vars_t) <= t.max_classes).OnlyEnforceIf(b)
            model.AddAssumption(b)
            assumptions_map[b.Index()] = f"Timeslot {t.label} cannot exceed its capacity of {t.max_classes} concurrent classes."

        # F. Prime-Time Cap
        from .models import Constraint
        prime_row = db.query(Constraint).filter(
            Constraint.name == "prime_time", Constraint.active == True
        ).first()
        if prime_row and prime_row.value_json:
            cfg = prime_row.value_json
            pt_start = cfg.get("start_time", "09:00")
            pt_end = cfg.get("end_time", "14:00")
            max_pct = cfg.get("max_percentage", 60)

            prime_slot_ids = {t.id for t in timeslots if pt_start <= t.start_time < pt_end}
            if prime_slot_ids:
                prime_vars = [assign[k] for k in assign if k[2] in prime_slot_ids]
                all_vars = list(assign.values())
                
                b = model.NewBoolVar("assump_F_prime")
                model.Add(sum(prime_vars) * 100 <= max_pct * sum(all_vars)).OnlyEnforceIf(b)
                model.AddAssumption(b)
                assumptions_map[b.Index()] = f"Prime-time cap exceeded: max {max_pct}% of sections allowed between {pt_start} and {pt_end}."

        # G. Blocked Timeslots
        blocked_row = db.query(Constraint).filter(
            Constraint.name == "blocked_timeslots", Constraint.active == True
        ).first()
        if blocked_row and blocked_row.value_json:
            blocked_labels = set(blocked_row.value_json.get("labels", []))
            blocked_ids = {t.id for t in timeslots if t.label in blocked_labels}
            for tid in blocked_ids:
                b = model.NewBoolVar(f"assump_G_blk_t{tid}")
                vars_blocked = [assign[k] for k in assign if k[2] == tid]
                for var in vars_blocked:
                    model.Add(var == 0).OnlyEnforceIf(b)
                model.AddAssumption(b)
                assumptions_map[b.Index()] = f"A timeslot is marked as blocked by administration."

        # 5. SOFT CONSTRAINTS (Objective Function)
        objective_terms = []

        for p in professors:
            pref = preferences.get(p.id, {})
            
            preferred_courses = pref.get("preferred_courses", [])
            avoid_courses = pref.get("avoid_courses", [])
            preferred_levels = pref.get("preferred_levels", [])
            preferred_timeslots = pref.get("preferred_timeslots", [])
            avoid_timeslots = pref.get("avoid_timeslots", [])
            avoid_days = pref.get("avoid_days", [])

            # Filter assign keys for just this professor to loop much faster
            p_keys = [k for k in assign if k[0] == p.id]

            for k in p_keys:
                var = assign[k]
                c_id = k[1]
                t_id = k[2]
                
                c = next((course for course in courses if course.id == c_id), None)
                t = next((timeslot for timeslot in timeslots if timeslot.id == t_id), None)
                
                if c and t:
                    course_key = f"{c.code} | {c.name}"

                    if c.code in preferred_courses or course_key in preferred_courses:
                        objective_terms.append(var * 10)
                    if c.code in avoid_courses or course_key in avoid_courses:
                        objective_terms.append(var * -100)
                    if c.level in preferred_levels:
                        objective_terms.append(var * 5)
                    if t.label in preferred_timeslots:
                        objective_terms.append(var * 5)
                    if t.label in avoid_timeslots:
                        objective_terms.append(var * -50)
                    for day in avoid_days:
                        if day in t.days:
                            objective_terms.append(var * -50)

        model.Maximize(sum(objective_terms))

        # 6. Run the Solver
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = 30.0 
        
        status = solver.Solve(model)

        if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
            new_schedule = Schedule(
                semester=semester,
                year=year,
                status="Draft",
                solver_log=f"Status: {solver.StatusName(status)}\nScore: {solver.ObjectiveValue()}\nTime: {solver.WallTime()}s"
            )
            db.add(new_schedule)
            db.commit() 
            
            sections_created = 0
            for k, var in assign.items():
                if solver.Value(var) == 1:
                    p_id, c_id, t_id, r_id = k
                    new_sec = Section(
                        course_id=c_id,
                        professor_id=p_id,
                        timeslot_id=t_id,
                        room_id=r_id,
                        schedule_id=new_schedule.id,
                        status="Assigned"
                    )
                    db.add(new_sec)
                    sections_created += 1
            
            db.commit()
            
            return {
                "status": "success", 
                "solution_type": solver.StatusName(status),
                "schedule_id": new_schedule.id,
                "sections_created": sections_created,
                "score": solver.ObjectiveValue()
            }
        elif status == cp_model.INFEASIBLE:
            conflict_indices = solver.SufficientAssumptionsForInfeasibility()
            
            if conflict_indices:
                bottlenecks = [assumptions_map[idx] for idx in conflict_indices]
                unique_bottlenecks = list(dict.fromkeys(bottlenecks))
                
                return {
                    "status": "infeasible",
                    "message": "The solver failed because the following constraints conflict with each other:",
                    "bottlenecks": unique_bottlenecks
                }
            else:
                return {
                    "status": "infeasible",
                    "message": "The solver could not find any possible schedule that satisfies all hard constraints, and it could not identify a specific unsatisfiable core (conflicting set of constraints) to explain the infeasibility."
                }
        else:
            return {
                "status": "infeasible",
                "solver_status": solver.StatusName(status),
                "message": f"Solver stopped with status: {solver.StatusName(status)}"
            }

    except Exception as e:
        db.rollback()
        return {"status": "error", "message": str(e)}
    finally:
        db.close()
