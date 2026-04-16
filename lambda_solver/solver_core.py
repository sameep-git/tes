"""
Pure solver logic — no database access, no ORM imports.

Receives a plain dict payload, runs OR-Tools CP-SAT, and returns a plain dict result.
This module is deployed to AWS Lambda inside the tes-solver container image.
"""
import traceback
from typing import Any, Dict, List

from ortools.sat.python import cp_model


def _log(msg: str):
    """Print with immediate flush so Lambda CloudWatch captures every line."""
    print(msg, flush=True)


def solve(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run the CP-SAT solver against the provided data payload.

    Expected payload keys:
        semester        str
        year            int
        professors      list[{id, name, fall_count, spring_count}]
        courses         list[{id, code, name, level, capacity, min_sections, max_sections}]
        timeslots       list[{id, label, days, start_time, end_time, max_classes}]
        rooms           list[{id, capacity}]
        preferences     dict[str(prof_id), {on_leave, max_load, preferred_courses,
                                            avoid_courses, preferred_levels,
                                            preferred_timeslots, avoid_timeslots, avoid_days}]
        constraints     {prime_time?: {start_time, end_time, max_percentage},
                         blocked_timeslots?: {labels: [str]}}

    Returns on success:
        {status: "success", solver_status: str, score: float, wall_time: float,
         assignments: [{professor_id, course_id, timeslot_id, room_id}]}
    Returns on infeasible:
        {status: "infeasible", message: str, bottlenecks?: [str]}
    Returns on error:
        {status: "error", message: str}
    """
    try:
        semester: str = payload["semester"]
        professors: List[dict] = payload["professors"]
        courses: List[dict] = payload["courses"]
        timeslots: List[dict] = payload["timeslots"]
        rooms: List[dict] = payload["rooms"]
        preferences: Dict[str, dict] = payload.get("preferences", {})
        constraints_cfg: dict = payload.get("constraints", {})

        _log(f"[SOLVER] Input: {len(professors)} professors, {len(courses)} courses, "
             f"{len(timeslots)} timeslots, {len(rooms)} rooms")

        if not professors or not courses or not timeslots or not rooms:
            return {"status": "error", "message": "Missing basic data (professors, courses, timeslots, or rooms)."}

        # ── 0. Pre-filter professors: skip those on leave ─────────────────────
        active_professors = []
        on_leave_names = []
        for p in professors:
            pref = preferences.get(str(p["id"]), {})
            if pref.get("on_leave", False):
                on_leave_names.append(p["name"])
            else:
                active_professors.append(p)

        if on_leave_names:
            _log(f"[SOLVER] Professors on leave (excluded): {', '.join(on_leave_names)}")
        _log(f"[SOLVER] Active professors for scheduling: {len(active_professors)}")

        if not active_professors:
            return {"status": "error", "message": "All professors are on leave. No one available to teach."}

        # ── 0.5 Pre-compute eligible rooms per course ─────────────────────────
        # Use up to MAX_ROOMS_PER_COURSE smallest eligible rooms to keep the
        # variable space manageable while giving the solver flexibility for
        # courses of similar sizes.
        MAX_ROOMS_PER_COURSE = 8
        rooms_sorted = sorted(rooms, key=lambda r: r["capacity"])
        course_rooms: Dict[int, List[dict]] = {}   # course_id → list of eligible rooms
        skipped_no_room: List[dict] = []

        for c in courses:
            eligible = [r for r in rooms_sorted if r["capacity"] >= c["capacity"]]
            if eligible:
                course_rooms[c["id"]] = eligible[:MAX_ROOMS_PER_COURSE]
            else:
                skipped_no_room.append(c)

        if skipped_no_room:
            max_room = max(r["capacity"] for r in rooms)
            _log(f"[SOLVER] WARNING: {len(skipped_no_room)} courses have no room with enough capacity:")
            for s in skipped_no_room:
                _log(f"  - {s['code']} ({s['name']}): needs {s['capacity']}, max room is {max_room}")

        schedulable_courses = [c for c in courses if c["id"] in course_rooms]
        _log(f"[SOLVER] Schedulable courses: {len(schedulable_courses)}")

        # ── 1. Build model ────────────────────────────────────────────────────
        model = cp_model.CpModel()

        # ── 2. Decision variables: assign[prof_id, course_id, timeslot_id, room_id]
        assign: Dict[tuple, Any] = {}
        for p in active_professors:
            for c in schedulable_courses:
                for t in timeslots:
                    for r in course_rooms[c["id"]]:
                        assign[(p["id"], c["id"], t["id"], r["id"])] = model.NewBoolVar(
                            f"a_p{p['id']}_c{c['id']}_t{t['id']}_r{r['id']}"
                        )

        _log(f"[SOLVER] Created {len(assign)} decision variables "
             f"(down from ~{len(professors)*len(courses)*len(timeslots)*len(rooms)} with all rooms)")

        if len(assign) == 0:
            return {
                "status": "error",
                "message": "No valid assignment variables could be created. "
                           "Check that room capacities are >= course capacities.",
            }

        assumptions_map: Dict[int, str] = {}

        # ── 3. HARD CONSTRAINTS ───────────────────────────────────────────────

        # ── Pre-compute overlapping timeslot pairs ────────────────────────────
        # Two timeslots conflict if they share at least one day AND their time
        # ranges overlap (start1 < end2 AND start2 < end1).
        def _time_to_min(t_str: str) -> int:
            """Convert 'HH:MM' to minutes since midnight."""
            parts = t_str.split(":")
            return int(parts[0]) * 60 + int(parts[1])

        def _timeslots_overlap(t1: dict, t2: dict) -> bool:
            """Return True if two timeslots share a day and their times intersect."""
            days1 = set(t1["days"])
            days2 = set(t2["days"])
            if not days1 & days2:
                return False
            s1, e1 = _time_to_min(t1["start_time"]), _time_to_min(t1["end_time"])
            s2, e2 = _time_to_min(t2["start_time"]), _time_to_min(t2["end_time"])
            return s1 < e2 and s2 < e1

        # Build a set of conflicting timeslot ID pairs (includes self-pairs)
        conflict_pairs: set = set()
        for i, t1 in enumerate(timeslots):
            for t2 in timeslots[i:]:
                if _timeslots_overlap(t1, t2):
                    conflict_pairs.add((t1["id"], t2["id"]))

        _log(f"[SOLVER] Computed {len(conflict_pairs)} overlapping timeslot pairs "
             f"(out of {len(timeslots)} timeslots)")

        # A. A professor cannot teach two courses at overlapping times
        b_physics = model.NewBoolVar("assump_A_physics")
        for p in active_professors:
            for (tid1, tid2) in conflict_pairs:
                if tid1 == tid2:
                    # Same timeslot — original logic
                    vars_pt = [assign[k] for k in assign if k[0] == p["id"] and k[2] == tid1]
                else:
                    # Different but overlapping timeslots
                    vars_pt = [assign[k] for k in assign
                               if k[0] == p["id"] and k[2] in (tid1, tid2)]
                if vars_pt:
                    model.Add(sum(vars_pt) <= 1).OnlyEnforceIf(b_physics)
        model.AddAssumption(b_physics)
        assumptions_map[b_physics.Index()] = "A professor cannot teach multiple courses at overlapping times."

        # A2. A room cannot have more than one course at overlapping times
        b_room_double = model.NewBoolVar("assump_A2_room_double")
        all_room_ids = set()
        for room_list in course_rooms.values():
            for r in room_list:
                all_room_ids.add(r["id"])

        for rid in all_room_ids:
            for (tid1, tid2) in conflict_pairs:
                if tid1 == tid2:
                    vars_rt = [assign[k] for k in assign if k[2] == tid1 and k[3] == rid]
                else:
                    vars_rt = [assign[k] for k in assign
                               if k[2] in (tid1, tid2) and k[3] == rid]
                if vars_rt:
                    model.Add(sum(vars_rt) <= 1).OnlyEnforceIf(b_room_double)
        model.AddAssumption(b_room_double)
        assumptions_map[b_room_double.Index()] = "A room cannot be double-booked at overlapping times."
        _log(f"[SOLVER] Room pool: {len(all_room_ids)} unique rooms in use")

        # B. Minimum/Maximum course sections
        for c in schedulable_courses:
            vars_c = [assign[k] for k in assign if k[1] == c["id"]]

            if not vars_c:
                _log(f"[SOLVER] WARNING: Course {c['code']} has 0 assignment vars. Skipping.")
                continue

            b_min = model.NewBoolVar(f"assump_B_min_c{c['id']}")
            model.Add(sum(vars_c) >= c["min_sections"]).OnlyEnforceIf(b_min)
            model.AddAssumption(b_min)
            assumptions_map[b_min.Index()] = (
                f"Course {c['code']} ({c['name']}) requires a minimum of {c['min_sections']} sections."
            )

            b_max = model.NewBoolVar(f"assump_B_max_c{c['id']}")
            model.Add(sum(vars_c) <= c["max_sections"]).OnlyEnforceIf(b_max)
            model.AddAssumption(b_max)
            assumptions_map[b_max.Index()] = (
                f"Course {c['code']} ({c['name']}) is capped at a maximum of {c['max_sections']} sections."
            )

        # C. Professor load limits
        for p in active_professors:
            pref = preferences.get(str(p["id"]), {})
            vars_p = [assign[k] for k in assign if k[0] == p["id"]]

            db_limit = p["fall_count"] if semester.lower() == "fall" else p["spring_count"]
            email_limit = pref.get("max_load")
            limit = min(db_limit, email_limit) if email_limit is not None else db_limit

            if limit <= 0:
                _log(f"[SOLVER] WARNING: Professor {p['name']} has load limit {limit} "
                     f"(db={db_limit}, email={email_limit})")

            b = model.NewBoolVar(f"assump_C_load_p{p['id']}")
            model.Add(sum(vars_p) <= limit).OnlyEnforceIf(b)
            model.AddAssumption(b)
            assumptions_map[b.Index()] = f"Professor {p['name']} cannot teach more than {limit} sections."

        # E. Timeslot capacity
        for t in timeslots:
            vars_t = [assign[k] for k in assign if k[2] == t["id"]]
            if not vars_t:
                continue
            b = model.NewBoolVar(f"assump_E_cap_t{t['id']}")
            model.Add(sum(vars_t) <= t["max_classes"]).OnlyEnforceIf(b)
            model.AddAssumption(b)
            assumptions_map[b.Index()] = (
                f"Timeslot {t['label']} cannot exceed its capacity of {t['max_classes']} concurrent classes."
            )

        # F. Prime-time cap — use intermediate IntVars to avoid a single massive
        #    linear expression with hundreds of thousands of terms.
        prime_cfg = constraints_cfg.get("prime_time")
        if prime_cfg:
            pt_start = prime_cfg.get("start_time", "09:00")
            pt_end = prime_cfg.get("end_time", "14:00")
            max_pct = prime_cfg.get("max_percentage", 60)

            prime_slot_ids = {t["id"] for t in timeslots if pt_start <= t["start_time"] < pt_end}
            if prime_slot_ids:
                n_vars = len(assign)
                prime_vars = [assign[k] for k in assign if k[2] in prime_slot_ids]

                if prime_vars and n_vars > 0:
                    # Create intermediate counting variables
                    total_sections = model.NewIntVar(0, n_vars, "total_sections")
                    prime_sections = model.NewIntVar(0, len(prime_vars), "prime_sections")
                    model.Add(total_sections == sum(assign.values()))
                    model.Add(prime_sections == sum(prime_vars))

                    b = model.NewBoolVar("assump_F_prime")
                    model.Add(prime_sections * 100 <= max_pct * total_sections).OnlyEnforceIf(b)
                    model.AddAssumption(b)
                    assumptions_map[b.Index()] = (
                        f"Prime-time cap exceeded: max {max_pct}% of sections allowed "
                        f"between {pt_start} and {pt_end}."
                    )
                    _log(f"[SOLVER] Prime-time constraint: {len(prime_vars)} prime vars, "
                         f"{n_vars} total vars, max {max_pct}%")

        # G. Blocked timeslots
        blocked_cfg = constraints_cfg.get("blocked_timeslots")
        if blocked_cfg:
            blocked_labels = set(blocked_cfg.get("labels", []))
            blocked_ids = {t["id"]: t["label"] for t in timeslots if t["label"] in blocked_labels}
            for tid, label in blocked_ids.items():
                b = model.NewBoolVar(f"assump_G_blk_t{tid}")
                vars_blocked = [assign[k] for k in assign if k[2] == tid]
                for var in vars_blocked:
                    model.Add(var == 0).OnlyEnforceIf(b)
                model.AddAssumption(b)
                assumptions_map[b.Index()] = f"Timeslot {label} is marked as blocked by administration."

        _log(f"[SOLVER] All constraints added. Assumptions: {len(assumptions_map)}")

        # ── 4. SOFT CONSTRAINTS (Objective) ──────────────────────────────────
        #
        # Weight guide:
        #   +500  preferred course           — prof should teach what they asked for
        #   +200  timeslot match (bonus)      — exactly the timeslot they paired with a course
        #   +100  preferred level             — level preference beyond specific courses
        #   -1000 avoid course                — strong: do NOT assign this
        #   -200  avoid timeslot / avoid day  — scheduling avoidance
        #   -20   non-preferred course        — mild nudge away from unrequested courses
        #
        WEIGHT_PREFERRED_COURSE = 500
        WEIGHT_TIMESLOT_MATCH = 200
        WEIGHT_PREFERRED_LEVEL = 100
        WEIGHT_AVOID_COURSE = -1000
        WEIGHT_AVOID_TIMESLOT = -200
        WEIGHT_AVOID_DAY = -200
        WEIGHT_NON_PREFERRED_COURSE = -20

        objective_terms = []

        course_dict = {c["id"]: c for c in schedulable_courses}
        timeslot_dict = {t["id"]: t for t in timeslots}

        for p in active_professors:
            pref = preferences.get(str(p["id"]), {})

            avoid_courses = pref.get("avoid_courses", [])
            preferred_levels = pref.get("preferred_levels", [])
            avoid_timeslots = pref.get("avoid_timeslots", [])
            avoid_days = pref.get("avoid_days", [])

            # ── Determine source format ───────────────────────────────────────
            course_assignments = pref.get("course_assignments", [])  # new format
            preferred_courses_legacy = pref.get("preferred_courses", [])  # old format

            using_new_format = bool(course_assignments)

            if using_new_format:
                # Build lookup: course_key -> list of desired timeslot labels (may be null)
                # Multiple entries for same course = multiple desired sections
                wanted_course_keys = [a.get("course", "") for a in course_assignments]
                # For timeslot bonus: map course_key -> set of desired timeslots
                wanted_timeslots_by_course: Dict[str, set] = {}
                for a in course_assignments:
                    ck = a.get("course", "")
                    ts = a.get("timeslot")
                    if ck and ts:
                        wanted_timeslots_by_course.setdefault(ck, set()).add(ts)

                if pref and (course_assignments or avoid_courses or preferred_levels):
                    _log(f"[SOLVER] Prefs for {p['name']} (new format): "
                         f"want={wanted_course_keys}, avoid={avoid_courses}, "
                         f"levels={preferred_levels}, avoid_days={avoid_days}")
            else:
                # Legacy format: flat preferred_courses list
                wanted_course_keys = preferred_courses_legacy
                wanted_timeslots_by_course = {}
                preferred_timeslots_legacy = pref.get("preferred_timeslots", [])

                if pref and (preferred_courses_legacy or avoid_courses or preferred_levels):
                    _log(f"[SOLVER] Prefs for {p['name']} (legacy): "
                         f"want={preferred_courses_legacy}, avoid={avoid_courses}, "
                         f"levels={preferred_levels}, avoid_days={avoid_days}")

            p_keys = [k for k in assign if k[0] == p["id"]]

            for k in p_keys:
                var = assign[k]
                c = course_dict.get(k[1])
                t = timeslot_dict.get(k[2])

                if not c or not t:
                    continue

                course_key = f"{c['code']} | {c['name']}"
                is_preferred = (c["code"] in wanted_course_keys or
                                course_key in wanted_course_keys)
                is_avoided = (c["code"] in avoid_courses or
                              course_key in avoid_courses)

                # Course preference
                if is_preferred:
                    objective_terms.append(var * WEIGHT_PREFERRED_COURSE)
                    # Bonus: timeslot matches what prof paired with this course
                    desired_slots = wanted_timeslots_by_course.get(course_key, set())
                    if t["label"] in desired_slots:
                        objective_terms.append(var * WEIGHT_TIMESLOT_MATCH)
                elif is_avoided:
                    objective_terms.append(var * WEIGHT_AVOID_COURSE)
                elif wanted_course_keys:
                    # Prof has expressed preferences but this course isn't one of them
                    objective_terms.append(var * WEIGHT_NON_PREFERRED_COURSE)

                # Level preference
                if c["level"] in preferred_levels:
                    objective_terms.append(var * WEIGHT_PREFERRED_LEVEL)

                # Timeslot avoidance
                if t["label"] in avoid_timeslots:
                    objective_terms.append(var * WEIGHT_AVOID_TIMESLOT)

                # Legacy: timeslot preference (old format only)
                if not using_new_format:
                    if t["label"] in preferred_timeslots_legacy:
                        objective_terms.append(var * 50)

                # Day avoidance
                for day in avoid_days:
                    if day in t["days"]:
                        objective_terms.append(var * WEIGHT_AVOID_DAY)

        _log(f"[SOLVER] Objective terms: {len(objective_terms)}")
        if objective_terms:
            model.Maximize(sum(objective_terms))

        # ── 4.5 Validate model before solving ────────────────────────────────
        _log("[SOLVER] Validating model...")
        validation_error = model.Validate()
        if validation_error:
            _log(f"[SOLVER] MODEL VALIDATION FAILED: {validation_error}")
            return {
                "status": "error",
                "message": f"The CP-SAT model is invalid: {validation_error}",
            }

        _log(f"[SOLVER] Model validated OK. Starting solver...")

        # ── 5. Solve ──────────────────────────────────────────────────────────
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = 540.0  # 540s gives 60s buffer before Lambda's 10-min timeout
        solver.parameters.num_search_workers = 2       # Lambda with 3GB RAM gets ~2 vCPUs

        status = solver.Solve(model)
        _log(f"[SOLVER] Solve complete. Status: {solver.StatusName(status)}, "
             f"Wall time: {solver.WallTime():.1f}s")

        if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            assignments = []
            for k, var in assign.items():
                if solver.Value(var) == 1:
                    p_id, c_id, t_id, r_id = k
                    assignments.append({
                        "professor_id": p_id,
                        "course_id": c_id,
                        "timeslot_id": t_id,
                        "room_id": r_id,
                    })
            _log(f"[SOLVER] SUCCESS: {len(assignments)} assignments, score={solver.ObjectiveValue()}")
            return {
                "status": "success",
                "solver_status": solver.StatusName(status),
                "score": solver.ObjectiveValue(),
                "wall_time": solver.WallTime(),
                "assignments": assignments,
            }

        elif status == cp_model.INFEASIBLE:
            conflict_indices = solver.SufficientAssumptionsForInfeasibility()
            if conflict_indices:
                bottlenecks = [assumptions_map[idx] for idx in conflict_indices if idx in assumptions_map]
                unique_bottlenecks = list(dict.fromkeys(bottlenecks))
                _log(f"[SOLVER] INFEASIBLE. Bottlenecks: {unique_bottlenecks}")
                return {
                    "status": "infeasible",
                    "message": "The solver failed because the following constraints conflict with each other:",
                    "bottlenecks": unique_bottlenecks,
                }
            else:
                _log("[SOLVER] INFEASIBLE. No unsatisfiable core identified.")
                return {
                    "status": "infeasible",
                    "message": (
                        "The solver could not find any possible schedule that satisfies all hard constraints, "
                        "and it could not identify a specific unsatisfiable core to explain the infeasibility."
                    ),
                }
        else:
            response_info = solver.ResponseStats()
            _log(f"[SOLVER] Non-success status: {solver.StatusName(status)}")
            _log(f"[SOLVER] Response stats: {response_info}")
            return {
                "status": "infeasible",
                "solver_status": solver.StatusName(status),
                "message": f"Solver stopped with status: {solver.StatusName(status)}. {response_info}",
            }

    except Exception as e:
        tb = traceback.format_exc()
        _log(f"[SOLVER] EXCEPTION: {tb}")
        return {"status": "error", "message": str(e)}
