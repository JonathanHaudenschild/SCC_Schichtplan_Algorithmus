# schedule_compliance_analyzer.py

import numpy as np
from datetime import time, datetime
from collections import defaultdict

# Assuming these functions are in data_transformation.py or accessible
# If not, you'll need to define/import them.
# For simplicity, I'll redefine a basic version here if needed.
try:
    from data_transformation import time_to_seconds_since_midnight
except ImportError:
    def time_to_seconds_since_midnight(t_obj):
        if isinstance(t_obj, str): # Assuming "HH:MM:SS" or "HH:MM"
            parts = list(map(int, t_obj.split(':')))
            if len(parts) == 2:
                t_obj = time(parts[0], parts[1], 0)
            elif len(parts) == 3:
                t_obj = time(parts[0], parts[1], parts[2])
            else:
                raise ValueError("Invalid time string format")
        elif not isinstance(t_obj, time):
            raise TypeError("Input must be a datetime.time object or string 'HH:MM[:SS]'")
        return t_obj.hour * 3600 + t_obj.minute * 60 + t_obj.second

# Constants (can be adjusted)
NIGHT_SHIFT_START_TIME = time(1, 0, 0)
NIGHT_SHIFT_END_TIME = time(7, 0, 0)
SECONDS_IN_A_DAY = 24 * 60 * 60


def _is_overlap(start1, end1, start2, end2):
    """Checks if two time intervals overlap."""
    # Ensure datetime objects for comparison if they are not already
    # This basic version assumes they are comparable (e.g., all datetime.time or all seconds)
    return max(start1, start2) < min(end1, end2)


def get_assigned_shifts_for_people(schedule, people_ids):
    """
    Helper function to create a dictionary of person_id -> list of assigned_shift_ids.
    """
    assigned_shifts_per_person = {person_id: [] for person_id in people_ids}
    for shift_id, assigned_person_ids in schedule.items():
        for person_id in assigned_person_ids:
            if person_id in assigned_shifts_per_person:
                assigned_shifts_per_person[person_id].append(shift_id)
    return assigned_shifts_per_person


def analyze_off_day_violations(person_id, assigned_shifts_person, people_data, shifts_data):
    """
    Analyzes how many assigned shifts conflict with a person's off-day requests.
    """
    violations_count = 0
    violated_shift_ids = []
    
    person_off_periods = people_data.get("off_shifts_dict", {}).get(person_id, [])
    if not person_off_periods:
        return 0, []

    for shift_id in assigned_shifts_person:
        shift_start, shift_end = shifts_data.get("shift_time_dict", {}).get(shift_id, (None, None))
        if shift_start is None or shift_end is None:
            continue

        for off_start, off_end in person_off_periods:
            # Assuming shift_start/end and off_start/end are comparable (e.g., datetime objects or seconds)
            # For simplicity, direct comparison. Convert to seconds if they are time objects.
            # This check needs to be robust based on how your times are stored.
            # If they are datetime.datetime, direct comparison works.
            # If datetime.time, convert to seconds for proper range check, especially across midnight.
            
            # Simple overlap check (more robust logic might be needed for specific time formats)
             if _is_overlap(shift_start, shift_end, off_start, off_end):
                violations_count += 1
                violated_shift_ids.append(shift_id)
                break # One violation per shift is enough
    return violations_count, list(set(violated_shift_ids))


def analyze_collaboration_preferences(person_id, assigned_shifts_person, schedule, people_data, shifts_data):
    """
    Analyzes collaboration preferences:
    - Shifts worked with enemies.
    - Friends worked with (and on which shifts).
    - Friends requested but not worked with at all.
    """
    shifts_with_enemies = []
    friends_worked_with_details = defaultdict(list) # friend_id: [shift_ids]
    
    preferences = people_data.get("collaboration_preferences_dict", {}).get(person_id, [])
    friend_ids = {pref[0] for pref in preferences if pref[1] < 0} # Negative score for friends
    enemy_ids = {pref[0] for pref in preferences if pref[1] > 0}  # Positive score for enemies

    for shift_id in assigned_shifts_person:
        colleagues_on_shift = set(schedule.get(shift_id, [])) - {person_id}
        
        # Check for enemies
        enemies_on_this_shift = colleagues_on_shift.intersection(enemy_ids)
        if enemies_on_this_shift:
            shifts_with_enemies.append({
                "shift_id": shift_id,
                "enemies_present": list(enemies_on_this_shift)
            })
            
        # Check for friends
        friends_on_this_shift = colleagues_on_shift.intersection(friend_ids)
        for friend_id in friends_on_this_shift:
            friends_worked_with_details[friend_id].append(shift_id)
            
    friends_not_worked_with_at_all = list(friend_ids - set(friends_worked_with_details.keys()))

    return {
        "shifts_with_enemies_count": len(shifts_with_enemies),
        "shifts_with_enemies_details": shifts_with_enemies,
        "friends_worked_with_count": len(friends_worked_with_details),
        "friends_worked_with_details": dict(friends_worked_with_details),
        "friends_not_worked_with_at_all": friends_not_worked_with_at_all
    }


def analyze_shift_types(person_id, assigned_shifts_person, people_data, shifts_data):
    """
    Analyzes assigned shift types against person's preferences (min/max).
    - If min_req=0 and max_allow=0 for a type in preferences, it means no quantity restriction for that type.
    """
    person_shift_type_prefs = people_data.get("people_shift_types_dict", {}).get(person_id, {})
    shift_type_map = shifts_data.get("shift_type_dict", {})
    
    assigned_counts = defaultdict(int)
    for shift_id in assigned_shifts_person:
        s_type = shift_type_map.get(shift_id)
        if s_type is not None: # Ensure shift has a type
            assigned_counts[s_type] += 1
            
    violations = {
        "below_min": [],        # list of {"type": s_type, "assigned": count, "min_required": min_req}
        "above_max": [],        # list of {"type": s_type, "assigned": count, "max_allowed": max_allow}
        "assigned_type_not_in_preferences": [] # New category for types assigned but not in explicit prefs (if prefs exist)
    }
    
    # If person_shift_types is empty for this person, they are a "joker" and accept all types without violation.
    if not person_shift_type_prefs:
        return {
            "assigned_type_counts": dict(assigned_counts),
            "violations": violations, # Will be empty as expected for a joker
            "is_joker": True
        }

    # Iterate through the person's explicit shift type preferences
    for pref_s_type, pref_details in person_shift_type_prefs.items():
        # Unpack preference details, ensure it's a tuple of 3 (exp, min, max)
        if not (isinstance(pref_details, tuple) and len(pref_details) == 3):
            # print(f"Warning: Invalid preference format for person {person_id}, type {pref_s_type}: {pref_details}")
            continue # Skip malformed preference
        
        _experience, min_req, max_allow = pref_details # _experience is not used in this analyzer
        
        current_assigned_count = assigned_counts.get(pref_s_type, 0)

        # Check for "below minimum" violation
        # Only if min_req is positive. If min_req is 0, it's not possible to be "below minimum".
        if min_req > 0 and current_assigned_count < min_req:
            violations["below_min"].append({
                "type": pref_s_type,
                "assigned": current_assigned_count,
                "min_required": min_req
            })
            
        # Check for "above maximum" violation
        # Only if max_allow is positive. If max_allow is 0, it means no upper limit FOR THIS PREFERENCE ENTRY.
        # (This aligns with your cost function's `if max_allowed > 0 and assigned_count > max_allowed`)
        if max_allow > 0 and current_assigned_count > max_allow:
            violations["above_max"].append({
                "type": pref_s_type,
                "assigned": current_assigned_count,
                "max_allowed": max_allow
            })
        
        # If min_req == 0 and max_allow == 0 (for a type *in preferences*):
        # This means "no restrictions for this specific type". So, no violation is possible
        # for being below min or above max (as min_req > 0 and max_allow > 0 conditions handle that).
        # The previous "assigned_unwanted" logic for this case was incorrect and is now removed.

    # Optional: Check for assigned types that are NOT in the person's explicit preferences.
    # This assumes that if preferences are listed, they are exhaustive for what is "actively preferred or restricted".
    # Any other assigned type could be considered "neutral" or "implicitly allowed" or "unmentioned".
    # If you want to flag these as a specific category (e.g., "assigned_type_not_in_preferences"):
    for assigned_s_type, count in assigned_counts.items():
        if assigned_s_type not in person_shift_type_prefs:
            violations["assigned_type_not_in_preferences"].append({
                "type": assigned_s_type,
                "assigned": count,
                "note": "This shift type was assigned but not found in the person's explicit preferences."
            })

    return {
        "assigned_type_counts": dict(assigned_counts),
        "violations": violations,
        "is_joker": False
    }

def analyze_time_frame_preferences(person_id, assigned_shifts_person, people_data, shifts_data):
    """
    Counts shifts falling into dis-preferred time slots.
    A dis-preferred slot is one with a positive cost in time_preferences_dict.
    """
    dispreferred_shifts_count = 0
    dispreferred_shifts_details = [] # list of (shift_id, matched_dispreference_cost)

    person_time_prefs = people_data.get("time_preferences_dict", {}).get(person_id, [])
    if not person_time_prefs:
        return 0, []

    shift_time_dict = shifts_data.get("shift_time_dict", {})

    # Helper function to format time values robustly for display
    def _format_pref_time_value(value):
        if isinstance(value, int): # Assuming it's seconds since midnight
            # Ensure value is within a day's seconds for H, M conversion
            val_seconds = value % SECONDS_IN_A_DAY 
            h = val_seconds // 3600
            m = (val_seconds % 3600) // 60
            return f"{h:02d}:{m:02d}"
        elif hasattr(value, 'strftime'): # Covers datetime.time and datetime.datetime
            return value.strftime('%H:%M')
        return str(value) # Fallback if it's neither

    for shift_id in assigned_shifts_person:
        s_start_obj, s_end_obj = shift_time_dict.get(shift_id, (None, None))
        if s_start_obj is None or s_end_obj is None:
            continue

        # s_start_obj and s_end_obj are expected to be datetime.datetime objects
        # so s_start_obj.strftime will work.
        shift_display_time = "N/A"
        if hasattr(s_start_obj, 'strftime') and hasattr(s_end_obj, 'strftime'):
             shift_display_time = f"{s_start_obj.strftime('%H:%M')}-{s_end_obj.strftime('%H:%M')}"


        s_start_sec = time_to_seconds_since_midnight(s_start_obj)
        s_end_sec = time_to_seconds_since_midnight(s_end_obj)
        
        if s_end_sec < s_start_sec: # overnight shift
            s_end_sec_adj = s_end_sec + SECONDS_IN_A_DAY
        else:
            s_end_sec_adj = s_end_sec
            
        max_penalty_for_this_shift = 0
        # This will store the info of the preference that caused the highest penalty for the current shift
        matched_pref_details_for_shift = None 

        for pref_tuples_list, cost_factor in person_time_prefs:
            if cost_factor <= 0: 
                continue
            
            for current_pref_start_obj, current_pref_end_obj in pref_tuples_list:
                # current_pref_start_obj, current_pref_end_obj are the items from the data,
                # which might be int or time objects.
                p_start_sec = time_to_seconds_since_midnight(current_pref_start_obj)
                p_end_sec = time_to_seconds_since_midnight(current_pref_end_obj)

                overlap = False
                if p_start_sec <= p_end_sec: 
                    if max(s_start_sec, p_start_sec) < min(s_end_sec_adj, p_end_sec):
                        overlap = True
                else: 
                    if max(s_start_sec, p_start_sec) < min(s_end_sec_adj, SECONDS_IN_A_DAY) or \
                       max(s_start_sec, 0) < min(s_end_sec_adj, p_end_sec):
                        # This simplified check for wrapped preferences might need more nuance
                        # depending on how wrapped shifts interact with wrapped preferences.
                        # The original logic from cost_function.py was more detailed here.
                        # For the purpose of this error, we focus on the formatting.
                        # A simple way:
                        is_shift_overnight = s_end_sec < s_start_sec
                        # Pref part 1: [p_start_sec, DAY_END_SEC), Pref part 2: [DAY_START_SEC, p_end_sec)
                        # Shift part 1 (if overnight): [s_start_sec, DAY_END_SEC), Shift part 2: [DAY_START_SEC, s_end_sec)
                        
                        # Overlap with preference's first part (e.g., 22:00-23:59)
                        if not is_shift_overnight: # Shift is same-day
                            if max(s_start_sec, p_start_sec) < min(s_end_sec, SECONDS_IN_A_DAY): overlap = True
                        else: # Shift is overnight
                            # Shift's first part vs Pref's first part
                            if max(s_start_sec, p_start_sec) < min(SECONDS_IN_A_DAY, SECONDS_IN_A_DAY): overlap = True
                            # Shift's second part vs Pref's first part
                            if max(0, p_start_sec) < min(s_end_sec, SECONDS_IN_A_DAY) : overlap = True
                        
                        # Overlap with preference's second part (e.g., 00:00-02:00)
                        if not overlap: # Only check if not already overlapping
                            if not is_shift_overnight: # Shift is same-day
                                if max(s_start_sec, 0) < min(s_end_sec, p_end_sec): overlap = True
                            else: # Shift is overnight
                                # Shift's first part vs Pref's second part
                                if max(s_start_sec, 0) < min(SECONDS_IN_A_DAY, p_end_sec): overlap = True
                                # Shift's second part vs Pref's second part
                                if max(0,0) < min(s_end_sec, p_end_sec): overlap = True
                
                if overlap:
                    if cost_factor > max_penalty_for_this_shift: 
                        max_penalty_for_this_shift = cost_factor
                        # Apply robust formatting when capturing the preference info
                        formatted_start = _format_pref_time_value(current_pref_start_obj)
                        formatted_end = _format_pref_time_value(current_pref_end_obj)
                        matched_pref_details_for_shift = {
                            "pref_time": f"{formatted_start}-{formatted_end}",
                            "penalty_factor": cost_factor
                        }
        
        if max_penalty_for_this_shift > 0 and matched_pref_details_for_shift is not None:
            dispreferred_shifts_count += 1
            dispreferred_shifts_details.append({
                "shift_id": shift_id,
                "shift_time": shift_display_time,
                "violated_preference": matched_pref_details_for_shift 
            })
            
    return dispreferred_shifts_count, dispreferred_shifts_details

def analyze_night_shifts(assigned_shifts_person, shifts_data, 
                         night_start_time=NIGHT_SHIFT_START_TIME, 
                         night_end_time=NIGHT_SHIFT_END_TIME):
    """
    Counts shifts that fall (even partially) into the defined night period (e.g., 01:00-07:00).
    """
    night_shifts_count = 0
    night_shift_ids = []
    
    night_start_sec = time_to_seconds_since_midnight(night_start_time)
    night_end_sec = time_to_seconds_since_midnight(night_end_time)

    shift_time_dict = shifts_data.get("shift_time_dict", {})

    for shift_id in assigned_shifts_person:
        s_start_obj, s_end_obj = shift_time_dict.get(shift_id, (None, None))
        if s_start_obj is None or s_end_obj is None:
            continue

        s_start_sec = time_to_seconds_since_midnight(s_start_obj)
        s_end_sec = time_to_seconds_since_midnight(s_end_obj)

        # Check for overlap with the night period [night_start_sec, night_end_sec)
        # This basic check assumes night period does not span midnight (e.g. 01:00-07:00 is fine, 22:00-06:00 needs more logic)
        # For 01:00-07:00, night_start_sec < night_end_sec, so simple overlap is:
        # max(shift_start, night_start) < min(shift_end, night_end)
        
        is_night_shift = False
        # Case 1: Shift is entirely within the day (no wrap around midnight)
        if s_start_sec <= s_end_sec:
            if max(s_start_sec, night_start_sec) < min(s_end_sec, night_end_sec):
                is_night_shift = True
        # Case 2: Shift wraps around midnight (e.g., 22:00 - 06:00)
        else: 
            # Check overlap with night period:
            # Part 1 of shift: [s_start_sec, SECONDS_IN_A_DAY)
            # Part 2 of shift: [0, s_end_sec)
            # If night period itself (e.g. 01:00-07:00) does not span midnight:
            if (max(s_start_sec, night_start_sec) < min(SECONDS_IN_A_DAY, night_end_sec)) or \
               (max(0, night_start_sec) < min(s_end_sec, night_end_sec)):
                is_night_shift = True
        
        if is_night_shift:
            night_shifts_count += 1
            night_shift_ids.append(shift_id)
            
    return night_shifts_count, night_shift_ids


def analyze_mandatory_coverage(person_id, assigned_shifts_person, people_data, shifts_data):
    """
    Checks if all mandatory coverage periods for the person are met.
    """
    unfulfilled_mandatory_periods = []
    mandatory_periods = people_data.get("mandatory_coverage_periods_dict", {}).get(person_id, [])
    
    if not mandatory_periods:
        return []

    shift_time_dict = shifts_data.get("shift_time_dict", {})
    
    assigned_shift_times_sec = []
    for shift_id in assigned_shifts_person:
        s_start_obj, s_end_obj = shift_time_dict.get(shift_id, (None, None))
        if s_start_obj and s_end_obj:
            assigned_shift_times_sec.append(
                (time_to_seconds_since_midnight(s_start_obj), time_to_seconds_since_midnight(s_end_obj))
            )

    for mand_start_obj, mand_end_obj in mandatory_periods:
        mand_start_sec = time_to_seconds_since_midnight(mand_start_obj)
        mand_end_sec = time_to_seconds_since_midnight(mand_end_obj)
        
        is_covered = False
        for s_start_sec, s_end_sec in assigned_shift_times_sec:
            # Check if assigned shift [s_start_sec, s_end_sec) covers mandatory [mand_start_sec, mand_end_sec)
            # This means s_start_sec <= mand_start_sec AND s_end_sec >= mand_end_sec
            # Handle wrap-around for shifts/mandatory periods if necessary (more complex)
            # Assuming no wrap-around for simplicity here or times are adjusted.
            if s_start_sec <= mand_start_sec and s_end_sec >= mand_end_sec:
                is_covered = True
                break
        
        if not is_covered:
            unfulfilled_mandatory_periods.append(
                (mand_start_obj, mand_end_obj)
            )
            
    return unfulfilled_mandatory_periods


def get_assigned_shift_details_for_person(assigned_shifts_person, shifts_data):
    """
    Returns a list of details for assigned shifts.
    """
    details = []
    shift_time_dict = shifts_data.get("shift_time_dict", {})
    shift_type_dict = shifts_data.get("shift_type_dict", {})

    for shift_id in assigned_shifts_person:
        s_start, s_end = shift_time_dict.get(shift_id, (None, None))
        s_type = shift_type_dict.get(shift_id, "N/A")
        details.append({
            "shift_id": shift_id,
            "start_time": s_start if s_start else "N/A",
            "end_time": s_end if s_end else "N/A",
            "type": s_type
        })
    return details


def analyze_schedule_compliance(schedule, people_data, shifts_data):
    """
    Main function to analyze schedule compliance against individual preferences.
    """
    analysis_results = {}
    all_person_ids = list(people_data.get("name_dict", {}).keys())
    
    assigned_shifts_map = get_assigned_shifts_for_people(schedule, all_person_ids)

    for person_id in all_person_ids:
        person_name = people_data.get("name_dict", {}).get(person_id, f"Person_{person_id}")
        assigned_shifts_person = assigned_shifts_map.get(person_id, [])
        
        person_analysis = {
            "person_id": person_id,
            "person_name": person_name,
            "total_assigned_shifts": len(assigned_shifts_person)
        }
        
        # 1. Off-day violations
        off_day_violations_count, violated_off_day_shifts = analyze_off_day_violations(
            person_id, assigned_shifts_person, people_data, shifts_data
        )
        person_analysis["off_day_violations"] = {
            "count": off_day_violations_count,
            "violated_shift_ids": violated_off_day_shifts
        }
        
        # 2. Collaboration preferences
        collab_analysis = analyze_collaboration_preferences(
            person_id, assigned_shifts_person, schedule, people_data, shifts_data
        )
        person_analysis["collaboration_analysis"] = collab_analysis
        
        # 3. Shift type analysis
        type_analysis = analyze_shift_types(
            person_id, assigned_shifts_person, people_data, shifts_data
        )
        person_analysis["shift_type_analysis"] = type_analysis
        
        # 4. Time frame preferences (dis-preferred times)
        dispreferred_time_count, dispreferred_time_details = analyze_time_frame_preferences(
            person_id, assigned_shifts_person, people_data, shifts_data
        )
        person_analysis["dispreferred_time_slots"] = {
            "count": dispreferred_time_count,
            "details": dispreferred_time_details
        }

        # 5. Night shifts (01:00-07:00)
        # Using default night hours, can be parameterized
        night_shift_count, night_shift_ids = analyze_night_shifts(
            assigned_shifts_person, shifts_data 
        )
        person_analysis["night_shifts_01_to_07"] = {
            "count": night_shift_count,
            "shift_ids": night_shift_ids
        }

        # 6. Mandatory coverage
        unfulfilled_mandatory = analyze_mandatory_coverage(
            person_id, assigned_shifts_person, people_data, shifts_data
        )
        person_analysis["mandatory_coverage"] = {
            "unfulfilled_periods_count": len(unfulfilled_mandatory),
            "unfulfilled_periods_details": unfulfilled_mandatory
        }

        # 7. List of assigned shifts
        assigned_details = get_assigned_shift_details_for_person(assigned_shifts_person, shifts_data)
        person_analysis["assigned_shifts_details"] = assigned_details
        
        analysis_results[person_id] = person_analysis
        
    return analysis_results


