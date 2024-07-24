import random
import statistics
from io import StringIO

from data_transformation import time_to_seconds_since_midnight


EXPERIENCE_FACTOR = 1000
GENDER_DISTRIBUTION_FACTOR = 1000
SHIFT_CATEGORY_FACTOR = 1
OFF_DAY_FACTOR = 1000
SHIFT_RANKING_FACTOR = 10
CONSECUTIVE_SHIFT_FACTOR = 5
FRIEND_FACTOR = 1000
ENEMY_FACTOR = 20000


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
    balance_factor = 50  # Adjust this factor as needed
    individual_balance_cost = deviation_individual_cost * balance_factor
    
    # Calculate mixed experience and gender costs
    gender_cost = mixed_gender_dist_cost(schedule, people_data, shifts_data)
    experience_cost = mixed_experience_cost(schedule, people_data, shifts_data)

    # Total cost combines individual costs, experience cost, gender cost, and balance cost
    total_cost = (
        +sum(individual_costs.values())
        # + rank_balance_cost
        + individual_balance_cost
        + gender_cost
        + experience_cost
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
        output_buffer.write(f"Experience cost: {experience_cost}\n")
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

    rank_costs = shift_ranking_cost(
        schedule, person_id, assigned_shifts_person, people_data, shifts_data
    )

    individual_costs += rank_costs
    cost_breakdown["shift_ranking_cost"] = rank_costs

    return individual_costs, cost_breakdown


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


def shift_ranking_cost(
    schedule,
    person_id,
    assigned_shifts_person,
    people_data,
    shifts_data,
    ranking_factor=SHIFT_RANKING_FACTOR,
):
    shift_ranking_cost = 0

    # General shift costs from shifts_data
    shift_costs = shifts_data["shift_cost_dict"]
    
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
                    if shift_start_sec >= time_to_seconds_since_midnight("01:00:00") or shift_end_sec <= time_to_seconds_since_midnight("07:00:00"):
                        night_shift_count += 1
                    preference_cost = cost
                    break

        # Add the squared preference cost multiplied by the general shift cost
        shift_ranking_cost += (shift_costs.get(shift_id, 0) + (shift_costs.get(shift_id, 0) * (preference_cost**2))) * ranking_factor

    return shift_ranking_cost


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

    for shift_id, shift in schedule.items():
        shift_gender_dist = 0
        for person_id in shift:
            shift_gender_dist += people_data["gender_dict"][person_id]
        shift_gender_dist /= len(shift)
        total_gender_dist_cost.append(shift_gender_dist)

    gender_dist_deviation = statistics.stdev(total_gender_dist_cost)

    gender_dist_cost = gender_dist_deviation * gender_dist_factor
    return gender_dist_cost