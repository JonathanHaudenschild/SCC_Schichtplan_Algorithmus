from io import StringIO
from datetime import time
from data_transformation import time_to_seconds_since_midnight
from logger import logging
from error_handling import raise_not_found_error
import time as t
import numpy as np
from concurrent.futures import ThreadPoolExecutor

EXPERIENCE_FACTOR = 1000
GENDER_DISTRIBUTION_FACTOR = 1000
SHIFT_CATEGORY_FACTOR = 1
SHIFT_TYPE_FACTOR = 4000
OFF_DAY_FACTOR = 1000
SHIFT_RANKING_FACTOR = 1
CONSECUTIVE_SHIFT_FACTOR = 5
FRIEND_FACTOR = 400
ENEMY_FACTOR = 200000


DEFAULT_MIN_AMOUNT_SHIFT = 4
DEFAULT_MAX_AMOUNT_SHIFT = 5


def calculate_statistics(values):
    values = np.array(values)
    total_sum = np.sum(values)  # Calculate the sum
    mean = np.mean(values)  # Calculate the mean
    deviation = np.std(values)  # Calculate the standard deviation
    return total_sum, mean, deviation


def cost_function(
    schedule, assigned_shifts, people_data, shifts_data, print_costs=False
):
    """
    Calculate the total cost of the schedule based on individual costs, experience costs

    Args:
    - schedule (dict): The schedule to evaluate
    - assigned_shifts (dict): The shifts assigned to each person
    - people_data (dict): The people data
    - shifts_data (dict): The shifts data
    - print_costs (bool): Whether to print the costs to the console

    Returns:
    - int: The total cost of the schedule
    - dict: The total cost breakdown for each person
    - str: The cost details
    """

    # Calculate individual costs
    individual_costs, total_cost_breakdown = total_individual_cost(
        schedule, assigned_shifts, people_data, shifts_data
    )

    # Calculate the mean and standard deviation of individual costs
    total_sum_individual_cost, mean_individual_cost, deviation_individual_cost = (
        calculate_statistics(list(individual_costs.values()))
    )

    # # Introduce a balance factor to penalize high deviation
    balance_factor = 50  # Adjust this factor as needed
    individual_balance_cost = deviation_individual_cost * balance_factor

    # Calculate mixed experience and gender costs
    gender_cost = mixed_gender_dist_cost(schedule, people_data, shifts_data)
    experience_cost = mixed_experience_cost(schedule, people_data, shifts_data)

    # priority_cost = shift_priority_cost(schedule, shifts_data)

    # Total cost combines individual costs, experience cost, gender cost, and balance cost
    total_cost = (
        +total_sum_individual_cost
        # + priority_cost
        + individual_balance_cost
        + gender_cost
        + experience_cost
    )

    # Calculate the top n people with the highest costs
    n = len(people_data["name_dict"]) // 100
    n = max(n, 1)
    # Get the top n people and their costs
    top_n_people = sorted(
        individual_costs.items(), key=lambda item: item[1], reverse=True
    )[:n]

    bias = top_n_people

    # if print_costs:
    #     for person in people_data["name_dict"]:
    #         logging.info(f"{person}: {individual_costs[person]}")
    #         logging.info(f"Cost Breakdown: {total_cost_breakdown[person]}")
    #     logging.info(f"Total Cost: {total_cost}")
    #     logging.info(f"Genders cost: {gender_cost}")
    #     logging.info(f"Sum of Individual Costs: {sum(individual_costs.values())}")
    #     logging.info(f"Mean Individual Cost: {mean_individual_cost}")
    #     logging.info(f"Deviation Individual Cost: {deviation_individual_cost}")

    # output_buffer.write(f"    Preference Cost: {pref_costs[person]}\n")
    # output_buffer.write(f"    Off-Day Cost: {off_day_costs[person]}\n")
    # output_buffer.write(f"    Shift Ranking Cost: {rank_costs[person]}\n")
    # output_buffer.write(f"Experience cost: {experience_cost}\n")
    # output_buffer.write(f"Sum of Off-Day Costs: {sum(off_day_costs)}\n")
    # output_buffer.write(
    #     f"No. of people having no off days: {off_day_costs.count(OFF_DAY_FACTOR)}\n"
    # )
    # output_buffer.write(f"Sum of Preference Costs: {sum(pref_costs)}\n")
    # output_buffer.write(f"Sum of Shift Ranking Costs: {sum(rank_costs)}\n")
    # output_buffer.write(
    # f"Sum of Shift Type Experience Costs: {sum(shift_type_experience_costs)}\n"
    # )

    return total_cost, total_cost_breakdown, bias


def total_individual_cost(schedule, assigned_shifts, people_data, shifts_data):

    if schedule is None or assigned_shifts is None:
        raise_not_found_error("Schedule or assigned shifts not found")

    person_ids = list(people_data["name_dict"].keys())
    results = calculate_individual_costs_concurrent(
        person_ids,
        schedule,
        assigned_shifts,
        people_data,
        shifts_data,
    )
    # Map results to person_ids
    individual_costs = {
        person_id: result[0] for person_id, result in zip(person_ids, results)
    }
    total_cost_breakdown = {
        person_id: result[1] for person_id, result in zip(person_ids, results)
    }

    return individual_costs, total_cost_breakdown


def calculate_individual_costs_concurrent(
    people, schedule, assigned_shifts, people_data, shifts_data
):

    with ThreadPoolExecutor(max_workers=8) as executor:
        results = executor.map(
            lambda person: individual_cost(
                schedule, person, assigned_shifts[person], people_data, shifts_data
            ),
            people,
        )
    return list(results)


def individual_cost(
    schedule, person_id, assigned_shifts_person, people_data, shifts_data
):
    individual_costs = 0
    cost_breakdown = {}
    
    pref_costs = collaboration_preferences_cost(
        schedule, person_id, assigned_shifts_person, people_data, shifts_data
    )
    individual_costs += pref_costs

    off_day_costs = off_day_cost(
        schedule, person_id, assigned_shifts_person, people_data, shifts_data
    )

    individual_costs += off_day_costs
    cost_breakdown["off_day_cost"] = off_day_costs
    

    time_frame_costs = time_frame_cost(
        schedule, person_id, assigned_shifts_person, people_data, shifts_data
    )

    individual_costs += time_frame_costs
    cost_breakdown["time_frame_costs"] = time_frame_costs

    
    shift_type_costs = shift_type_cost(
        schedule, person_id, assigned_shifts_person, people_data, shifts_data
    )

    individual_costs += shift_type_costs
    cost_breakdown["shift_type_cost"] = shift_type_costs


    mandatory_costs = check_mandatory(
        assigned_shifts_person, person_id, people_data, shifts_data
    )

    individual_costs += mandatory_costs
    cost_breakdown["mandatory_costs"] = mandatory_costs

    
    return individual_costs, cost_breakdown


def check_occurance():

    return


def check_mandatory(assigned_shifts_person, person_id, people_data, shifts_data):
    mandatory_periods = people_data["mandatory_coverage_periods_dict"].get(
        person_id, []
    )

    # Set to keep track of mandatory periods that have been satisfied
    satisfied_periods = set()

    for shift_id in assigned_shifts_person:
        shift_start, shift_end = shifts_data["shift_time_dict"].get(
            shift_id, (None, None)
        )
        if shift_start is None or shift_end is None:
            continue  # Skip if shift times are not found

        for mandatory_start, mandatory_end in mandatory_periods:
            if shift_start >= mandatory_start and shift_end <= mandatory_end:
                satisfied_periods.add((mandatory_start, mandatory_end))

    # If all mandatory periods are satisfied, return True
    if len(satisfied_periods) >= len(mandatory_periods):
        return 0

    return 5000000


def shift_priority_cost(schedule, shifts_data):
    cost = 0
    for shift_id, shift in schedule.items():
        shift_priority = shifts_data["shift_priority_dict"].get(shift_id, 1)
        if len(shift) < shifts_data["shift_capacity_dict"][shift_id][0]:
            cost += shift_priority
    return cost


def shift_type_cost(
    schedule, person_id, assigned_shifts_person, people_data, shifts_data
):
    def retrieve_shift_types(assigned_shifts, shift_type_dict):
        """
        Calculate the number of assigned shift types for a person.

        Args:
        - assigned_shifts (list): List of shifts already assigned to the person.
        - shift_type_dict (dict): Mapping from shift ID to shift type.

        Returns:
        - dict: A dictionary with the count of each shift type assigned to the person.
        """
        assigned_shift_types = {}
        for assigned_shift in assigned_shifts:
            assigned_shift_type = shift_type_dict.get(assigned_shift, 0)
            assigned_shift_types[assigned_shift_type] = (
                assigned_shift_types.get(assigned_shift_type, 0) + 1
            )
        return assigned_shift_types

    # If person_shift_types is empty, act as a "joker" and don't apply any penalties
    person_shift_types = people_data["people_shift_types_dict"].get(person_id, {})
    if not person_shift_types:
        return 0  # No cost since all shift types are acceptable

    cost = 0

    # Calculate the number of each shift type already assigned to the person
    assigned_shift_types = retrieve_shift_types(
        assigned_shifts_person, shifts_data["shift_type_dict"]
    )

    # Apply penalties based on shift type preferences
    for person_shift_type, (_, min_required, max_allowed) in person_shift_types.items():
        assigned_count = assigned_shift_types.get(person_shift_type, 0)

        # Penalty if the assigned shifts are less than the minimum required
        if min_required > 0 and assigned_count < min_required:
            cost += SHIFT_TYPE_FACTOR * 3

        # Penalty if the assigned shifts exceed the maximum allowed
        if max_allowed > 0 and assigned_count > max_allowed:
            cost += SHIFT_TYPE_FACTOR

        if min_required == 0 and max_allowed == 0:
            if person_shift_type not in assigned_shift_types:
                cost += SHIFT_TYPE_FACTOR * 2

    return cost


def collaboration_preferences_cost(
    schedule,
    person_id,
    assigned_shifts_person,
    people_data,
    shifts_data,
    same_shift_friend_factor=1,
    same_shift_enemy_factor=1,
    same_time_friend_factor=0.75,
    same_time_enemy_factor=0.75,
    friend_factor=FRIEND_FACTOR,
    enemy_factor=ENEMY_FACTOR,
):
    friends_count = 0
    enemies_count = 0
    collaboration_preferences_cost = 0

    preferences = people_data["collaboration_preferences_dict"].get(person_id, [])
    shift_times = shifts_data["shift_time_dict"]
    friend_set = {preference[0] for preference in preferences if preference[1] < 0}
    enemy_set = {preference[0] for preference in preferences if preference[1] > 0}

    # Convert assigned shifts to a set of start times
    assigned_times = {shift_times[shift][0] for shift in assigned_shifts_person}

    total_possible_matches = len(friend_set) * len(assigned_shifts_person)

    # Iterate through assigned shifts
    for shift_id, colleagues in schedule.items():
        shift_start_time = shift_times[shift_id][0]
        colleagues_set = set(colleagues) - {person_id}  # Exclude self

        # Calculate friend overlaps (same shift or same start time)
        friend_overlap = colleagues_set & friend_set
        if shift_id in assigned_shifts_person:
            # Same shift overlap
            friends_count += len(friend_overlap) * same_shift_friend_factor
        elif friend_overlap:
            # Check if friends have the same start time
            if shift_start_time in assigned_times:
                friends_count += len(friend_overlap) * same_time_friend_factor

        # Calculate enemy overlaps (same shift or same start time)
        enemy_overlap = colleagues_set & enemy_set
        if shift_id in assigned_shifts_person:
            # Same shift overlap
            enemies_count += len(enemy_overlap) * same_shift_enemy_factor
        elif enemy_overlap:
            # Check if enemies have the same start time
            if shift_start_time in assigned_times:
                enemies_count += len(enemy_overlap) * same_time_enemy_factor

    # Calculate the cost for each potential deviation from the preference
    difference = max(total_possible_matches - friends_count, 0)
    collaboration_preferences_cost += difference * friend_factor
    collaboration_preferences_cost += enemies_count * enemy_factor

    return collaboration_preferences_cost


def off_day_cost(
    schedule,
    person_id,
    assigned_shifts_person,
    people_data,
    shifts_data,
    off_day_factor=OFF_DAY_FACTOR,
):
    unavailability_periods = people_data["off_shifts_dict"].get(person_id, [])
    shift_times = [
        shifts_data["shift_time_dict"].get(shift_id, (None, None))
        for shift_id in assigned_shifts_person
    ]

    # Vectorized overlap check
    off_day_mask = np.array(
        [
            any(
                start <= unavailability_start < end
                or start < unavailability_end <= end
                or (unavailability_start <= start and unavailability_end >= end)
                for unavailability_start, unavailability_end in unavailability_periods
            )
            for start, end in shift_times
            if start and end
        ]
    )

    return np.sum(off_day_mask) * off_day_factor


def overlap_mask(
    shift_start_times, shift_end_times, lower_bound, upper_bound
):

    S = shift_start_times      # array of ints in [0..86399]
    E = shift_end_times        # array of ints in [0..86399]
    L = lower_bound           # single int in [0..86399]
    U = upper_bound           # single int in [0..86399]

    shift_overnight  = (S > E)
    window_overnight = (L > U)

    # 2) Build each of the four sub‐masks:

    # A) shift & window both “same‐day” (no wrap)
    case_A = (~shift_overnight & ~window_overnight) & ( (S < U) & (E > L) )

    # B) shift same‐day, window wraps
    case_B = (~shift_overnight & window_overnight) & ( (E > L) | (S < U) )

    # C) shift wraps, window same‐day
    case_C = (shift_overnight & ~window_overnight) & ( (S < U) | (E > L) )

    # D) shift wraps, window wraps → always overlap
    case_D = (shift_overnight & window_overnight)   # no extra test needed

    # 3) Final mask: any of the four cases is enough
    overlap_mask = case_A | case_B | case_C | case_D
    return overlap_mask

def time_frame_cost(
    schedule,
    person_id,
    assigned_shifts_person,
    people_data,
    shifts_data,
    ranking_factor=SHIFT_RANKING_FACTOR,
):
    time_frame_cost = 0

    # General shift costs from shifts_data
    shift_costs = shifts_data["shift_cost_dict"]
    time_frame_cost = np.sum(
        [
            (shift_costs.get(shift_id, 0)) * SHIFT_RANKING_FACTOR
            for shift_id in assigned_shifts_person
        ]
    )
    
    night_shift_count = 0
    shift_times = [
        shifts_data["shift_time_dict"][shift_id] for shift_id in assigned_shifts_person
    ]

    shift_start_times = np.array(
        [time_to_seconds_since_midnight(start) for start, _ in shift_times]
    )
    shift_end_times = np.array(
        [time_to_seconds_since_midnight(end) for _, end in shift_times]
    )

    lower_bound = time_to_seconds_since_midnight(time(1, 0, 0))
    upper_bound = time_to_seconds_since_midnight(time(7, 0, 0))

    night_shift_mask = overlap_mask(
        shift_start_times, shift_end_times, lower_bound, upper_bound
    )

    night_shift_count = np.sum(night_shift_mask)

    if night_shift_count > 2:
        ratio = (
          night_shift_count /  len(assigned_shifts_person) 
        )
        
        time_frame_cost += np.exp((ratio))** 5


    time_preferences = people_data["time_preferences_dict"].get(person_id, [])

    # Iterate through preferences and calculate costs
    for pref_times, cost in time_preferences:
        for pref_start, pref_end in pref_times:
            overlap_mask_result = overlap_mask(
                shift_start_times,
                shift_end_times,
                time_to_seconds_since_midnight(pref_start),
                time_to_seconds_since_midnight(pref_end),
            )
            time_frame_cost += np.sum(overlap_mask_result) * cost ** 2


    return time_frame_cost


def mixed_experience_cost(
    schedule, people_data, shifts_data, experience_factor=EXPERIENCE_FACTOR
):
    """
    For each shift‐type t (no matter how many there are):
      1) Find all shifts with shifts_data['shift_type_dict'][shift_key] == t.
      2) Compute avg_experience for each such shift.
      3) Compute stddev of those per‐shift averages (within type t).
    Return (sum of stddevs over all types) * experience_factor.
    """

    # Alias for quicker lookups
    psd = people_data.get("people_shift_types_dict", {})
    shift_type_dict = shifts_data.get("shift_type_dict", {})

    if not psd:
        return 0.0

    # We'll build dictionaries on the fly:
    #   S1[t] = sum of all per‐shift means for type t
    #   S2[t] = sum of (per‐shift mean)^2 for type t
    #   M[t]  = number of shifts of type t that had ≥1 valid person
    S1 = {}
    S2 = {}
    M  = {}

    for shift_key, person_list in schedule.items():
        # Lookup this shift's numeric type
        t = shift_type_dict.get(shift_key, 0)

        # If it's the first time we see t, initialize
        if t not in S1:
            S1[t] = 0.0
            S2[t] = 0.0
            M[t]  = 0

        # Compute sum/count for this shift
        total_exp = 0.0
        cnt = 0

        for pid in person_list:
            person_experiences = psd.get(pid)
            if not person_experiences:
                continue

            tup = person_experiences.get(t)
            if tup:
                total_exp += tup[0]
                cnt += 1

        if cnt > 0:
            mean_i = total_exp / cnt
            S1[t] += mean_i
            S2[t] += mean_i * mean_i
            M[t]  += 1
        # If cnt == 0, skip this shift entirely (no contribution to S1/S2/M)

    total_std = 0.0
    for t, count_shifts in M.items():
        if count_shifts == 0:
            continue
        mean_of_means = S1[t] / count_shifts
        var_of_means = (S2[t] / count_shifts) - (mean_of_means * mean_of_means)
        # Guard against tiny negative due to FP rounding
        if var_of_means < 0 and var_of_means > -1e-12:
            var_of_means = 0.0
        std_of_means = np.sqrt(var_of_means)
        total_std += std_of_means

    return total_std * experience_factor

def mixed_gender_dist_cost(
    schedule, people_data, shifts_data, gender_dist_factor=GENDER_DISTRIBUTION_FACTOR
):
    if not people_data["gender_dict"]:
        return 0

    # Vectorized computation of gender distribution per shift
    shift_genders = [
        [people_data["gender_dict"].get(person_id, 0) for person_id in shift]
        for shift in schedule.values()
    ]

    shift_gender_means = np.array(
        [np.mean(genders) if genders else 0 for genders in shift_genders]
    )

    # Calculate standard deviation of gender distributions
    gender_dist_deviation = np.std(shift_gender_means)

    return gender_dist_deviation * gender_dist_factor
