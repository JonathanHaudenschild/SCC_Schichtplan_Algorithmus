import random
import statistics
from io import StringIO
from datetime import time
import math
from data_transformation import time_to_seconds_since_midnight


EXPERIENCE_FACTOR = 1000
GENDER_DISTRIBUTION_FACTOR = 1000
SHIFT_CATEGORY_FACTOR = 1
SHIFT_TYPE_FACTOR = 1000
OFF_DAY_FACTOR = 1000
SHIFT_RANKING_FACTOR = 1
CONSECUTIVE_SHIFT_FACTOR = 5
FRIEND_FACTOR = 1000
ENEMY_FACTOR = 20000
NIGHT_SHIFT_FACTOR = 200


DEFAULT_MIN_AMOUNT_SHIFT = 4
DEFAULT_MAX_AMOUNT_SHIFT = 5


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

    if not schedule:
        return 0, {}, ""

    # Calculate individual costs
    individual_costs, total_cost_breakdown = total_individual_cost(
        schedule, assigned_shifts, people_data, shifts_data
    )

    # Calculate the mean and standard deviation of individual costs
    mean_individual_cost = statistics.mean(individual_costs.values())
    deviation_individual_cost = (
        statistics.stdev(individual_costs.values()) if len(individual_costs) > 1 else 0
    )

    # # Introduce a balance factor to penalize high deviation
    balance_factor = 2 # Adjust this factor as needed
    individual_balance_cost = deviation_individual_cost ** balance_factor

    # Calculate mixed experience and gender costs
    gender_cost = mixed_gender_dist_cost(schedule, people_data, shifts_data)
    # experience_cost = mixed_experience_cost(schedule, people_data, shifts_data)

    priority_cost = shift_priority_cost(schedule, shifts_data)

    # Total cost combines individual costs, experience cost, gender cost, and balance cost
    total_cost = (
        +sum(individual_costs.values())
        + priority_cost
        + individual_balance_cost
        + gender_cost
        # + experience_cost
    )

    output_buffer = StringIO()
    if print_costs:
        for person in people_data["name_dict"]:
            output_buffer.write(f"Person {person}\n")
            output_buffer.write(f"    Total Cost: {individual_costs[person]}\n")
            # output_buffer.write(f"    Preference Cost: {pref_costs[person]}\n")
            # output_buffer.write(f"    Off-Day Cost: {off_day_costs[person]}\n")
            # output_buffer.write(f"    Shift Ranking Cost: {rank_costs[person]}\n")
            output_buffer.write(f" Cost Breakdown: {total_cost_breakdown[person]}\n")
        output_buffer.write(f"Total Cost: {total_cost}\n")
        # output_buffer.write(f"Experience cost: {experience_cost}\n")
        output_buffer.write(f"Genders cost: {gender_cost}\n")
        output_buffer.write(
            f"Sum of Individual Costs: {sum(individual_costs.values())}\n"
        )
        output_buffer.write(f"Mean Individual Cost: {mean_individual_cost}\n")
        output_buffer.write(f"Deviation Individual Cost: {deviation_individual_cost}\n")
        # output_buffer.write(f"Sum of Off-Day Costs: {sum(off_day_costs)}\n")
        # output_buffer.write(
        #     f"No. of people having no off days: {off_day_costs.count(OFF_DAY_FACTOR)}\n"
        # )
        # output_buffer.write(f"Sum of Preference Costs: {sum(pref_costs)}\n")
        # output_buffer.write(f"Sum of Shift Ranking Costs: {sum(rank_costs)}\n")
        # output_buffer.write(
        # f"Sum of Shift Type Experience Costs: {sum(shift_type_experience_costs)}\n"
        # )

        print(output_buffer.getvalue())

    return total_cost, total_cost_breakdown, output_buffer.getvalue()


def total_individual_cost(schedule, assigned_shifts, people_data, shifts_data):
    total_individual_costs = {person: 0 for person in people_data["name_dict"]}
    total_cost_breakdown = {person: {} for person in people_data["name_dict"]}
    for person_id in people_data["name_dict"]:
        individual_costs, cost_breakdown = individual_cost(
            schedule, person_id, assigned_shifts[person_id], people_data, shifts_data
        )
        total_individual_costs[person_id] = individual_costs
        total_cost_breakdown[person_id] = cost_breakdown

    return total_individual_costs, total_cost_breakdown


def individual_cost(
    schedule, person_id, assigned_shifts_person, people_data, shifts_data
):
    individual_costs = 0
    cost_breakdown = {}

    pref_costs = preference_cost(
        schedule, person_id, assigned_shifts_person, people_data, shifts_data
    )
    individual_costs += pref_costs
    cost_breakdown["preference_cost"] = pref_costs

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

    return individual_costs, cost_breakdown



def shift_priority_cost(schedule, shifts_data):
    cost = 0
    for shift_id, shift in schedule.items():
        shift_priority = shifts_data["shift_priority_dict"].get(shift_id, 1)
        if len(shift) < shifts_data["shift_capacity_dict"][shift_id][0]:
            cost += shift_priority**2
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
            assigned_shift_types[assigned_shift_type] = assigned_shift_types.get(assigned_shift_type, 0) + 1
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
    for person_shift_type, (_, min_required,  max_allowed) in person_shift_types.items():
        assigned_count = assigned_shift_types.get(person_shift_type, 0)

        # Penalty if the assigned shifts are less than the minimum required
        if min_required > 0 and assigned_count < min_required:
            cost += SHIFT_TYPE_FACTOR

        # Penalty if the assigned shifts exceed the maximum allowed
        if max_allowed > 0 and assigned_count > max_allowed:
            cost += SHIFT_TYPE_FACTOR
            
        
        if min_required == 0 and max_allowed == 0:
            if person_shift_type not in assigned_shift_types:
                cost += SHIFT_TYPE_FACTOR * 2

    return cost


def preference_cost(
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
    preference_cost = 0

    preferences = people_data["preference_dict"].get(person_id, [])
    shift_times = shifts_data["shift_time_dict"]
    friend_set = {preference[0] for preference in preferences if preference[1] < 0}
    enemy_set = {preference[0] for preference in preferences if preference[1] > 0}

    # Convert assigned shifts to a set of start times
    assigned_times = {shift_times[shift][0] for shift in assigned_shifts_person}

    total_possible_matches = len(friend_set) * len(assigned_shifts_person)

    # Iterate through assigned shifts
    for shift_id, colleagues in schedule.items():
        shift_start_time = shift_times[shift_id][0]
        for colleague_id in colleagues:
            if person_id != colleague_id:
                if colleague_id in friend_set:
                    if shift_id in assigned_shifts_person:
                        friends_count += same_shift_friend_factor
                    elif shift_start_time in assigned_times:
                        friends_count += same_time_friend_factor
                if colleague_id in enemy_set:
                    if shift_id in assigned_shifts_person:
                        enemies_count += same_shift_enemy_factor
                    elif shift_start_time in assigned_times:
                        enemies_count += same_time_enemy_factor

    # Calculate the cost for each potential deviation from the preference
    difference = max(total_possible_matches - friends_count, 0)
    preference_cost += difference * friend_factor
    preference_cost += enemies_count * enemy_factor

    return preference_cost


def off_day_cost(
    schedule,
    person_id,
    assigned_shifts_person,
    people_data,
    shifts_data,
    off_day_factor=OFF_DAY_FACTOR,
):
    off_day_cost = 0
    unavailability_periods = people_data["off_shifts_dict"].get(person_id, [])
    shift_times = shifts_data["shift_time_dict"]

    for shift_id in assigned_shifts_person:
        start, end = shift_times.get(shift_id, (None, None))
        if start is None or end is None:
            continue  # Skip if shift times are not found

        for unavailability_start, unavailability_end in unavailability_periods:
            if (
                start
                <= unavailability_start
                < end  # Unavailability starts during the shift
                or start
                < unavailability_end
                <= end  # Unavailability ends during the shift
                or (
                    unavailability_start <= start and unavailability_end >= end
                )  # Unavailability spans the entire shift
            ):
                off_day_cost += off_day_factor
                break  # Break to avoid multiple increments for the same shift

    return off_day_cost


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

    avg_shift_cost = 0

    if len(shift_costs) > 0:
        ## calc avg shift cost for all shifts
        avg_shift_cost = sum(shift_costs.values()) / len(shift_costs)

    ## expected cost for a person with 4 shifts
    expected_cost = avg_shift_cost * DEFAULT_MIN_AMOUNT_SHIFT

    night_shift_count = 0

    for shift_id in assigned_shifts_person:

        # Retrieve personal shift preferences for the person
        personal_shift_preference = people_data["shift_preference_dict"].get(
            person_id, []
        )

        # Get shift start and end times
        shift_start, shift_end = shifts_data["shift_time_dict"].get(
            shift_id, (None, None)
        )

        # Convert shift start and end times to seconds since midnight
        shift_start_sec = time_to_seconds_since_midnight(shift_start)
        shift_end_sec = time_to_seconds_since_midnight(shift_end)

        # Initialize preference cost for the shift
        preference_cost = 0

        # Find the preference cost for the shift
        for pref_times, cost in personal_shift_preference:
            for pref_start, pref_end in pref_times:
                if (shift_start_sec >= pref_start and shift_end_sec <= pref_end) or (
                    shift_start_sec <= pref_start and shift_end_sec >= pref_end
                ):
                    # check if the shift is a night shift
                    if shift_start_sec >= time_to_seconds_since_midnight(
                        time(23, 0, 0)
                    ) or shift_end_sec <= time_to_seconds_since_midnight(time(7, 0, 0)):
                        night_shift_count += 1
                    preference_cost = cost
                    break

        # Add the squared preference cost multiplied by the general shift cost
        time_frame_cost += (
            shift_costs.get(shift_id, 0) + (preference_cost**2)
        ) * ranking_factor
        
    
    if night_shift_count > 1:
        time_frame_cost += (len(assigned_shifts_person) / night_shift_count) * NIGHT_SHIFT_FACTOR

    return time_frame_cost


def mixed_experience_cost(
    schedule,
    people_data,
    shifts_data,
    experience_factor=EXPERIENCE_FACTOR,
):
    total_experience_cost = []

    for shift_id, shift in schedule.items():
        shift_experience = 0
        for person_id in shift:
            shift_experience += people_data["experience_dict"][person_id]
        shift_experience /= len(shift)
        total_experience_cost.append(shift_experience)

    experience_deviation = statistics.stdev(total_experience_cost)

    mixed_experience_cost = experience_deviation * experience_factor
    return mixed_experience_cost


def mixed_gender_dist_cost(
    schedule,
    people_data,
    shifts_data,
    gender_dist_factor=GENDER_DISTRIBUTION_FACTOR,
):
    total_gender_dist_cost = []

    if people_data["gender_dict"] is None or people_data["gender_dict"] == {}:
        return 0

    for shift_id, shift in schedule.items():
        shift_gender_dist = 0
        for person_id in shift:
            if people_data["gender_dict"][person_id] is not None:
                shift_gender_dist += people_data["gender_dict"][person_id]
        if len(shift) > 0:
            shift_gender_dist /= len(shift)
            total_gender_dist_cost.append(shift_gender_dist)

    gender_dist_deviation = statistics.stdev(total_gender_dist_cost)

    gender_dist_cost = gender_dist_deviation * gender_dist_factor
    return gender_dist_cost
