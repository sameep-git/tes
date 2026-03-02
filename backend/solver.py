import json
from collections import defaultdict
from typing import Dict, Any

from ortools.sat.python import cp_model

from .database import SessionLocal
from .models import Professor, Course, TimeSlot, Schedule, Section, Preference


def run_solver(semester: str, year: int) -> Dict[str, Any]:
    """
    Executes the OR-Tools CP-SAT solver to assign professors to courses and timeslots.
    """
    db = SessionLocal()

    try:
        # 1. Fetch all data
        professors = db.query(Professor).filter(Professor.active == True).all()
        courses = db.query(Course).all()
        timeslots = db.query(TimeSlot).filter(TimeSlot.active == True).all()

        # Build a dictionary of professor preferences for quick lookup
        # If they haven't replied, they won't have a preference object.
        preferences = {}
        for p in professors:
            pref = db.query(Preference).filter(
                Preference.professor_id == p.id,
                Preference.semester == semester,
                Preference.year == year
            ).first()
            if pref and pref.parsed_json:
                # parsed_json is stored as a dict if we used model_dump()
                preferences[p.id] = pref.parsed_json
            else:
                preferences[p.id] = {}

        if not professors or not courses or not timeslots:
            return {"status": "error", "message": "Missing basic data (professors, courses, or timeslots)."}

        # 2. Initialize Model
        model = cp_model.CpModel()

        # 3. Create Decision Variables
        # assign[p, c, t] = 1 if Professor p teaches Course c at TimeSlot t
        assign = {}
        for p in professors:
            for c in courses:
                for t in timeslots:
                    assign[(p.id, c.id, t.id)] = model.NewBoolVar(f"assign_p{p.id}_c{c.id}_t{t.id}")

        # 4. HARD CONSTRAINTS
        
        # A. A professor cannot teach more than one course at the exact same time
        for p in professors:
            for t in timeslots:
                model.AddAtMostOne(assign[(p.id, c.id, t.id)] for c in courses)

        # B. Minimum/Maximum Course Sections
        for c in courses:
            total_sections = []
            for p in professors:
                for t in timeslots:
                    total_sections.append(assign[(p.id, c.id, t.id)])
            model.Add(sum(total_sections) >= c.min_sections)
            model.Add(sum(total_sections) <= c.max_sections)

        # C. Professor Load Limits & Sabbatical
        for p in professors:
            pref = preferences.get(p.id, {})
            on_leave = pref.get("on_leave", False)
            
            total_classes = []
            for c in courses:
                for t in timeslots:
                    total_classes.append(assign[(p.id, c.id, t.id)])

            if on_leave:
                # Professor is on sabbatical, assign 0 classes
                model.Add(sum(total_classes) == 0)
            else:
                # Get the strictest limit: max_sections from DB, or max_load from preference email
                db_limit = p.max_sections
                email_limit = pref.get("max_load")
                
                # If they explicitly requested a max_load, use the smaller of the two to be safe
                if email_limit is not None:
                    limit = min(db_limit, email_limit)
                else:
                    limit = db_limit
                    
                model.Add(sum(total_classes) <= limit)

        # D. Core Requirements Constraint
        # At least one section of each required core tag must be scheduled
        ssc_sections = []
        ht_sections = []
        ga_sections = []
        wem_sections = []
        
        for c in courses:
            for p in professors:
                for t in timeslots:
                    var = assign[(p.id, c.id, t.id)]
                    if c.core_ssc: ssc_sections.append(var)
                    if c.core_ht: ht_sections.append(var)
                    if c.core_ga: ga_sections.append(var)
                    if c.core_wem: wem_sections.append(var)
        
        if ssc_sections: model.Add(sum(ssc_sections) >= 1)
        if ht_sections: model.Add(sum(ht_sections) >= 1)
        if ga_sections: model.Add(sum(ga_sections) >= 1)
        if wem_sections: model.Add(sum(wem_sections) >= 1)


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

            for c in courses:
                for t in timeslots:
                    var = assign[(p.id, c.id, t.id)]

                    # Points for Course match
                    if c.code in preferred_courses:
                        objective_terms.append(var * 10)
                    
                    if c.code in avoid_courses:
                        objective_terms.append(var * -100)
                    
                    # Points for Course Level match
                    if c.level in preferred_levels:
                        objective_terms.append(var * 5)
                    
                    # Points for Timeslot match
                    if t.label in preferred_timeslots:
                        objective_terms.append(var * 5)
                    
                    if t.label in avoid_timeslots:
                        objective_terms.append(var * -50)
                    
                    # Points for Avoid Days
                    # E.g., if avoid_days=["F"] and t.days="MWF", we penalize
                    for day in avoid_days:
                        if day in t.days:
                            objective_terms.append(var * -50)

        model.Maximize(sum(objective_terms))

        # 6. Run the Solver
        solver = cp_model.CpSolver()
        # Set a 30 second time limit so the API doesn't hang forever
        solver.parameters.max_time_in_seconds = 30.0 
        
        status = solver.Solve(model)

        if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
            # 7. Save the Resulting Schedule
            new_schedule = Schedule(
                semester=semester,
                year=year,
                status="Draft",
                solver_log=f"Status: {solver.StatusName(status)}\nScore: {solver.ObjectiveValue()}\nTime: {solver.WallTime()}s"
            )
            db.add(new_schedule)
            db.commit() # Commit to get the schedule ID
            
            sections_created = 0
            for p in professors:
                for c in courses:
                    for t in timeslots:
                        if solver.Value(assign[(p.id, c.id, t.id)]) == 1:
                            new_sec = Section(
                                course_id=c.id,
                                professor_id=p.id,
                                timeslot_id=t.id,
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
        else:
            return {
                "status": "infeasible",
                "message": "The solver could not find any possible schedule that satisfies all hard constraints."
            }

    except Exception as e:
        db.rollback()
        return {"status": "error", "message": str(e)}
    finally:
        db.close()
