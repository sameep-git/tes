"""
Two-phase solver core.

Phase 1 allocates professor/course section counts, including timeless sections.
Phase 2 places timed sections into timeslots and rooms.
"""
import traceback
from collections import Counter
from typing import Any, Dict, List, Tuple

from ortools.sat.python import cp_model


def _log(msg: str):
    """Print with immediate flush so Lambda CloudWatch captures every line."""
    print(msg, flush=True)


def _course_key(course: dict) -> str:
    return f"{course['code']} | {course['name']}"


def _time_to_min(t_str: str) -> int:
    parts = t_str.split(":")
    return int(parts[0]) * 60 + int(parts[1])


def _timeslots_overlap(t1: dict, t2: dict) -> bool:
    days1 = set(t1["days"])
    days2 = set(t2["days"])
    if not days1 & days2:
        return False
    s1, e1 = _time_to_min(t1["start_time"]), _time_to_min(t1["end_time"])
    s2, e2 = _time_to_min(t2["start_time"]), _time_to_min(t2["end_time"])
    return s1 < e2 and s2 < e1


def _build_conflict_pairs(timeslots: List[dict]) -> set:
    conflict_pairs = set()
    for i, t1 in enumerate(timeslots):
        for t2 in timeslots[i:]:
            if _timeslots_overlap(t1, t2):
                conflict_pairs.add((t1["id"], t2["id"]))
    return conflict_pairs


def _build_course_lookup(courses: List[dict]) -> Dict[str, str]:
    lookup: Dict[str, str] = {}
    code_to_keys: Dict[str, set] = {}
    for course in courses:
        key = _course_key(course)
        lookup[key] = key
        code_to_keys.setdefault(course["code"], set()).add(key)

    for code, keys in code_to_keys.items():
        if len(keys) == 1:
            lookup[code] = next(iter(keys))

    return lookup


def _normalize_preferences(
    professors: List[dict],
    courses: List[dict],
    preferences: Dict[str, dict],
    semester: str,
) -> Dict[int, dict]:
    course_lookup = _build_course_lookup(courses)

    normalized: Dict[int, dict] = {}
    for professor in professors:
        pref = preferences.get(str(professor["id"]), {}) or {}
        assignments = pref.get("course_assignments", []) or []
        preferred_courses_legacy = pref.get("preferred_courses", []) or []

        requested_course_counts: Counter = Counter()
        requested_course_timeslot_counts: Counter = Counter()

        if assignments:
            for entry in assignments:
                course_name = entry.get("course", "") if isinstance(entry, dict) else str(entry)
                canonical_course = course_lookup.get(course_name)
                if not canonical_course:
                    continue

                requested_course_counts[canonical_course] += 1

                timeslot_label = entry.get("timeslot") if isinstance(entry, dict) else None
                if timeslot_label:
                    requested_course_timeslot_counts[(canonical_course, timeslot_label)] += 1
        else:
            for course_name in preferred_courses_legacy:
                canonical_course = course_lookup.get(course_name)
                if canonical_course:
                    requested_course_counts[canonical_course] += 1

        avoid_courses = set()
        for course_name in pref.get("avoid_courses", []) or []:
            canonical_course = course_lookup.get(course_name)
            if canonical_course:
                avoid_courses.add(canonical_course)

        db_limit = professor["fall_count"] if semester.lower() == "fall" else professor["spring_count"]
        max_load = pref.get("max_load")
        hard_cap = min(db_limit, max_load) if max_load is not None else db_limit
        hard_cap = max(0, int(hard_cap))

        requested_load = pref.get("requested_load")
        requested_sections_total = sum(requested_course_counts.values())

        if requested_load is not None:
            target_load = max(0, min(int(requested_load), hard_cap))
        elif requested_sections_total > 0:
            target_load = min(requested_sections_total, hard_cap)
        else:
            target_load = hard_cap

        normalized[professor["id"]] = {
            "on_leave": bool(pref.get("on_leave", False)),
            "hard_cap": hard_cap,
            "target_load": target_load,
            "requested_sections_total": requested_sections_total,
            "requested_course_counts": requested_course_counts,
            "requested_course_timeslot_counts": requested_course_timeslot_counts,
            "avoid_courses": avoid_courses,
            "preferred_levels": set(pref.get("preferred_levels", []) or []),
            "avoid_timeslots": set(pref.get("avoid_timeslots", []) or []),
            "avoid_days": set(pref.get("avoid_days", []) or []),
            "preferred_timeslots_legacy": set(pref.get("preferred_timeslots", []) or []),
        }

    return normalized


def _build_room_options(courses: List[dict], rooms: List[dict]) -> Tuple[Dict[int, List[dict]], List[dict]]:
    max_rooms_per_course = 8
    rooms_sorted = sorted(rooms, key=lambda r: r["capacity"])
    course_rooms: Dict[int, List[dict]] = {}
    no_room_courses: List[dict] = []

    for course in courses:
        if course.get("is_timeless"):
            continue

        eligible = [room for room in rooms_sorted if room["capacity"] >= course["capacity"]]
        if eligible:
            course_rooms[course["id"]] = eligible[:max_rooms_per_course]
        else:
            no_room_courses.append(course)

    return course_rooms, no_room_courses


def _solve_allocation_phase(
    semester: str,
    professors: List[dict],
    courses: List[dict],
    normalized_prefs: Dict[int, dict],
) -> Dict[str, Any]:
    active_professors = [p for p in professors if not normalized_prefs[p["id"]]["on_leave"]]
    if not active_professors:
        return {"status": "error", "message": "All professors are on leave. No one available to teach."}

    model = cp_model.CpModel()
    course_list = list(courses)

    assign_count: Dict[Tuple[int, int], Any] = {}
    load_vars: Dict[int, Any] = {}
    objective_terms = []

    weight_match = 1000
    weight_unmet = -1200
    weight_extra = -175
    weight_unrequested = -25
    weight_avoid_course = -500
    weight_preferred_level = 40
    weight_under_target = -325
    weight_over_target = -80

    for professor in active_professors:
        p_id = professor["id"]
        hard_cap = normalized_prefs[p_id]["hard_cap"]
        requested_course_counts: Counter = normalized_prefs[p_id]["requested_course_counts"]
        for course in course_list:
            if course.get("is_timeless"):
                max_count = requested_course_counts.get(_course_key(course), 0)
            else:
                max_count = min(hard_cap, course["max_sections"])
            assign_count[(p_id, course["id"])] = model.NewIntVar(
                0,
                max_count,
                f"alloc_p{p_id}_c{course['id']}",
            )

    for course in course_list:
        course_vars = [assign_count[(p["id"], course["id"])] for p in active_professors]
        model.Add(sum(course_vars) >= course["min_sections"])
        model.Add(sum(course_vars) <= course["max_sections"])

    for professor in active_professors:
        p_id = professor["id"]
        hard_cap = normalized_prefs[p_id]["hard_cap"]
        vars_p = [assign_count[(p_id, course["id"])] for course in course_list]

        load_var = model.NewIntVar(0, hard_cap, f"load_p{p_id}")
        model.Add(load_var == sum(vars_p))
        model.Add(load_var <= hard_cap)
        load_vars[p_id] = load_var

        target_load = normalized_prefs[p_id]["target_load"]
        if target_load > 0:
            under_target = model.NewIntVar(0, target_load, f"under_target_p{p_id}")
            over_target = model.NewIntVar(0, hard_cap, f"over_target_p{p_id}")
            model.Add(under_target >= target_load - load_var)
            model.Add(over_target >= load_var - target_load)
            objective_terms.append(under_target * weight_under_target)
            objective_terms.append(over_target * weight_over_target)

    for professor in active_professors:
        p_id = professor["id"]
        pref = normalized_prefs[p_id]
        requested_course_counts: Counter = pref["requested_course_counts"]
        has_explicit_course_requests = pref["requested_sections_total"] > 0

        for course in course_list:
            key = _course_key(course)
            course_var = assign_count[(p_id, course["id"])]
            requested_count = requested_course_counts.get(key, 0)

            if requested_count > 0:
                matched = model.NewIntVar(0, requested_count, f"match_p{p_id}_c{course['id']}")
                unmet = model.NewIntVar(0, requested_count, f"unmet_p{p_id}_c{course['id']}")
                extra = model.NewIntVar(0, course["max_sections"], f"extra_p{p_id}_c{course['id']}")

                model.Add(matched <= course_var)
                model.Add(matched <= requested_count)
                model.Add(unmet == requested_count - matched)
                model.Add(extra >= course_var - requested_count)

                objective_terms.append(matched * weight_match)
                objective_terms.append(unmet * weight_unmet)
                objective_terms.append(extra * weight_extra)
            elif has_explicit_course_requests:
                objective_terms.append(course_var * weight_unrequested)

            if key in pref["avoid_courses"]:
                objective_terms.append(course_var * weight_avoid_course)

            if course["level"] in pref["preferred_levels"]:
                objective_terms.append(course_var * weight_preferred_level)

    if objective_terms:
        model.Maximize(sum(objective_terms))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 180.0
    solver.parameters.num_search_workers = 2

    status = solver.Solve(model)
    _log(
        f"[SOLVER][ALLOC] Status: {solver.StatusName(status)}, wall time: {solver.WallTime():.1f}s"
    )

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return {
            "status": "infeasible",
            "message": "The allocation phase could not find a feasible professor-course assignment.",
            "solver_status": solver.StatusName(status),
        }

    allocation_counts: Dict[Tuple[int, int], int] = {}
    assignments: List[dict] = []
    timed_shells: List[dict] = []
    timeless_sections = 0
    section_seq = 0

    for professor in active_professors:
        p_id = professor["id"]
        for course in course_list:
            c_id = course["id"]
            count = solver.Value(assign_count[(p_id, c_id)])
            if count <= 0:
                continue

            allocation_counts[(p_id, c_id)] = count
            for _ in range(count):
                if course.get("is_timeless"):
                    assignments.append(
                        {
                            "professor_id": p_id,
                            "course_id": c_id,
                            "timeslot_id": None,
                            "room_id": None,
                        }
                    )
                    timeless_sections += 1
                else:
                    section_seq += 1
                    timed_shells.append(
                        {
                            "section_id": section_seq,
                            "professor_id": p_id,
                            "course_id": c_id,
                        }
                    )

    return {
        "status": "success",
        "solver_status": solver.StatusName(status),
        "score": solver.ObjectiveValue(),
        "wall_time": solver.WallTime(),
        "assignments": assignments,
        "timed_shells": timed_shells,
        "allocation_counts": allocation_counts,
        "timeless_sections": timeless_sections,
        "load_by_professor": {p["id"]: solver.Value(load_vars[p["id"]]) for p in active_professors},
    }


def _solve_placement_phase(
    timed_shells: List[dict],
    courses: List[dict],
    timeslots: List[dict],
    rooms: List[dict],
    course_rooms: Dict[int, List[dict]],
    normalized_prefs: Dict[int, dict],
    constraints_cfg: dict,
) -> Dict[str, Any]:
    if not timed_shells:
        return {
            "status": "success",
            "solver_status": "NO_TIMED_SECTIONS",
            "score": 0.0,
            "wall_time": 0.0,
            "assignments": [],
        }

    course_dict = {course["id"]: course for course in courses}
    timeslot_dict = {timeslot["id"]: timeslot for timeslot in timeslots}
    conflict_pairs = _build_conflict_pairs(timeslots)
    blocked_labels = set((constraints_cfg.get("blocked_timeslots") or {}).get("labels", []))
    blocked_ids = {t["id"] for t in timeslots if t["label"] in blocked_labels}

    model = cp_model.CpModel()
    place: Dict[Tuple[int, int, int], Any] = {}
    shell_ids_by_prof: Dict[int, List[int]] = {}
    shell_ids_by_prof_course: Dict[Tuple[int, int], List[int]] = {}

    for shell in timed_shells:
        shell_ids_by_prof.setdefault(shell["professor_id"], []).append(shell["section_id"])
        shell_ids_by_prof_course.setdefault((shell["professor_id"], shell["course_id"]), []).append(
            shell["section_id"]
        )

    for shell in timed_shells:
        course = course_dict[shell["course_id"]]
        options = []
        for timeslot in timeslots:
            if timeslot["id"] in blocked_ids:
                continue
            for room in course_rooms.get(course["id"], []):
                var = model.NewBoolVar(
                    f"place_s{shell['section_id']}_t{timeslot['id']}_r{room['id']}"
                )
                place[(shell["section_id"], timeslot["id"], room["id"])] = var
                options.append(var)

        if not options:
            return {
                "status": "infeasible",
                "message": (
                    f"The placement phase has no feasible timeslot/room options for "
                    f"{course['code']} ({course['name']})."
                ),
            }
        model.AddExactlyOne(options)

    for p_id, shell_ids in shell_ids_by_prof.items():
        for tid1, tid2 in conflict_pairs:
            relevant_tids = {tid1} if tid1 == tid2 else {tid1, tid2}
            vars_pt = [
                var for (sid, tid, _rid), var in place.items()
                if sid in shell_ids and tid in relevant_tids
            ]
            if vars_pt:
                model.Add(sum(vars_pt) <= 1)

    room_ids = {room["id"] for room in rooms}
    for room_id in room_ids:
        for tid1, tid2 in conflict_pairs:
            vars_rt = []
            if tid1 == tid2:
                vars_rt.extend(
                    var for (_sid, tid, rid), var in place.items()
                    if tid == tid1 and rid == room_id
                )
            else:
                vars_rt.extend(
                    var for (_sid, tid, rid), var in place.items()
                    if tid in (tid1, tid2) and rid == room_id
                )
            if vars_rt:
                model.Add(sum(vars_rt) <= 1)

    for timeslot in timeslots:
        vars_t = [var for (_sid, tid, _rid), var in place.items() if tid == timeslot["id"]]
        if vars_t:
            model.Add(sum(vars_t) <= timeslot["max_classes"])

    prime_cfg = constraints_cfg.get("prime_time")
    if prime_cfg:
        pt_start = prime_cfg.get("start_time", "09:00")
        pt_end = prime_cfg.get("end_time", "14:00")
        max_pct = prime_cfg.get("max_percentage", 60)
        prime_slot_ids = {t["id"] for t in timeslots if pt_start <= t["start_time"] < pt_end}
        if prime_slot_ids and timed_shells:
            prime_sections = model.NewIntVar(0, len(timed_shells), "prime_sections")
            model.Add(
                prime_sections
                == sum(var for (_sid, tid, _rid), var in place.items() if tid in prime_slot_ids)
            )
            model.Add(prime_sections * 100 <= max_pct * len(timed_shells))

    objective_terms = []
    weight_timeslot_match = 220
    weight_avoid_timeslot = -220
    weight_avoid_day = -180
    weight_legacy_preferred_timeslot = 40

    for shell in timed_shells:
        p_id = shell["professor_id"]
        course = course_dict[shell["course_id"]]
        course_key = _course_key(course)
        pref = normalized_prefs[p_id]

        for (sid, tid, rid), var in place.items():
            if sid != shell["section_id"]:
                continue

            timeslot = timeslot_dict[tid]
            if timeslot["label"] in pref["avoid_timeslots"]:
                objective_terms.append(var * weight_avoid_timeslot)

            if timeslot["label"] in pref["preferred_timeslots_legacy"]:
                objective_terms.append(var * weight_legacy_preferred_timeslot)

            for day in pref["avoid_days"]:
                if day in timeslot["days"]:
                    objective_terms.append(var * weight_avoid_day)

        requested_pair_count = pref["requested_course_timeslot_counts"]
        for timeslot in timeslots:
            requested_count = requested_pair_count.get((course_key, timeslot["label"]), 0)
            if requested_count <= 0:
                continue

            shell_ids = shell_ids_by_prof_course.get((p_id, course["id"]), [])

            placed_here = model.NewIntVar(
                0,
                len(shell_ids),
                f"placed_pair_p{p_id}_c{course['id']}_t{timeslot['id']}",
            )
            matched_here = model.NewIntVar(
                0,
                requested_count,
                f"matched_pair_p{p_id}_c{course['id']}_t{timeslot['id']}",
            )
            vars_here = [
                var for (sid, tid, _rid), var in place.items()
                if tid == timeslot["id"]
                and sid in shell_ids
            ]
            model.Add(placed_here == sum(vars_here))
            model.Add(matched_here <= placed_here)
            model.Add(matched_here <= requested_count)
            objective_terms.append(matched_here * weight_timeslot_match)

    if objective_terms:
        model.Maximize(sum(objective_terms))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 300.0
    solver.parameters.num_search_workers = 2

    status = solver.Solve(model)
    _log(
        f"[SOLVER][PLACE] Status: {solver.StatusName(status)}, wall time: {solver.WallTime():.1f}s"
    )

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return {
            "status": "infeasible",
            "message": "The placement phase could not fit the allocated timed sections into timeslots and rooms.",
            "solver_status": solver.StatusName(status),
        }

    assignments = []
    for shell in timed_shells:
        for (sid, tid, rid), var in place.items():
            if sid == shell["section_id"] and solver.Value(var) == 1:
                assignments.append(
                    {
                        "professor_id": shell["professor_id"],
                        "course_id": shell["course_id"],
                        "timeslot_id": tid,
                        "room_id": rid,
                    }
                )
                break

    return {
        "status": "success",
        "solver_status": solver.StatusName(status),
        "score": solver.ObjectiveValue(),
        "wall_time": solver.WallTime(),
        "assignments": assignments,
    }


def solve(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run a two-phase solve:
      1. Allocate professor/course section counts, including timeless sections.
      2. Place timed sections into timeslots and rooms.
    """
    try:
        semester: str = payload["semester"]
        professors: List[dict] = payload["professors"]
        courses: List[dict] = payload["courses"]
        timeslots: List[dict] = payload["timeslots"]
        rooms: List[dict] = payload["rooms"]
        preferences: Dict[str, dict] = payload.get("preferences", {})
        constraints_cfg: dict = payload.get("constraints", {})

        _log(
            f"[SOLVER] Input: {len(professors)} professors, {len(courses)} courses, "
            f"{len(timeslots)} timeslots, {len(rooms)} rooms"
        )

        if not professors or not courses:
            return {"status": "error", "message": "Missing basic data (professors or courses)."}

        normalized_prefs = _normalize_preferences(professors, courses, preferences, semester)
        active_professors = [p for p in professors if not normalized_prefs[p["id"]]["on_leave"]]
        on_leave_names = [p["name"] for p in professors if normalized_prefs[p["id"]]["on_leave"]]

        if on_leave_names:
            _log(f"[SOLVER] Professors on leave (excluded): {', '.join(on_leave_names)}")
        _log(f"[SOLVER] Active professors for scheduling: {len(active_professors)}")

        timed_courses = [course for course in courses if not course.get("is_timeless")]
        if timed_courses and (not timeslots or not rooms):
            return {
                "status": "error",
                "message": "Timed courses exist, but timeslots or rooms are missing.",
            }

        course_rooms, no_room_courses = _build_room_options(courses, rooms)
        if no_room_courses:
            details = ", ".join(f"{course['code']} ({course['name']})" for course in no_room_courses)
            return {
                "status": "error",
                "message": f"The following timed courses have no eligible room: {details}",
            }

        allocation_result = _solve_allocation_phase(
            semester=semester,
            professors=professors,
            courses=courses,
            normalized_prefs=normalized_prefs,
        )
        if allocation_result.get("status") != "success":
            return allocation_result

        placement_result = _solve_placement_phase(
            timed_shells=allocation_result["timed_shells"],
            courses=courses,
            timeslots=timeslots,
            rooms=rooms,
            course_rooms=course_rooms,
            normalized_prefs=normalized_prefs,
            constraints_cfg=constraints_cfg,
        )
        if placement_result.get("status") != "success":
            return placement_result

        assignments = allocation_result["assignments"] + placement_result["assignments"]
        total_score = allocation_result["score"] + placement_result["score"]
        total_wall_time = allocation_result["wall_time"] + placement_result["wall_time"]

        _log(
            f"[SOLVER] SUCCESS: {len(assignments)} assignments "
            f"({allocation_result['timeless_sections']} timeless), score={total_score}"
        )
        return {
            "status": "success",
            "solver_status": f"ALLOC={allocation_result['solver_status']}; PLACE={placement_result['solver_status']}",
            "score": total_score,
            "wall_time": total_wall_time,
            "assignments": assignments,
            "timeless_sections": allocation_result["timeless_sections"],
        }

    except Exception as e:
        tb = traceback.format_exc()
        _log(f"[SOLVER] EXCEPTION: {tb}")
        return {"status": "error", "message": str(e)}
