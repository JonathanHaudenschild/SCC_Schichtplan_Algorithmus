import random
import statistics
from io import StringIO

from data_transformation import time_to_seconds_since_midnight


EXPERIENCE_FACTOR = 1000
ONE_SIDED_GENDER_FACTOR = 1000
SHIFT_CATEGORY_FACTOR = 1
OFF_DAY_FACTOR = 1000
SHIFT_RANKING_FACTOR = 100
CONSECUTIVE_SHIFT_FACTOR = 5
FRIEND_FACTOR = 1000
ENEMY_FACTOR = 20000


DEFAULT_MIN_AMOUNT_SHIFT = 4
DEFAULT_MAX_AMOUNT_SHIFT = 5


def cost_function(
    schedule, assigned_shifts, people_data, shifts_data, print_costs=False
):
    if not schedule:
        return 0, {}, ""


    # Calculate individual costs
    individual_costs = total_individual_cost(
        schedule, assigned_shifts, people_data, shifts_data
    )

    # Calculate the mean and standard deviation of individual costs
    mean_individual_cost = statistics.mean(individual_costs.values())
    deviation_individual_cost = (
        statistics.stdev(individual_costs.values()) if len(individual_costs) > 1 else 0
    )

    # # Introduce a balance factor to penalize high deviation
    balance_factor = 50  # Adjust this factor as needed

    # mean_rank_costs = statistics.mean(rank_costs)
    # deviation_rank_costs = statistics.stdev(rank_costs)
    # rank_balance_cost = deviation_rank_costs * 5

    # Calculate mixed experience and gender costs
    # exp_cost = mixedExperience_cost(
    #     schedule,
    #     people_data["experience_dict"],
    #     num_of_shifts,
    #     EXPERIENCE_FACTOR,
    # )
    # gender_cost = mixedGender_cost(
    #     schedule, people_data["gender_dict"], num_of_shifts, ONE_SIDED_GENDER_FACTOR
    # )

    individual_balance_cost = deviation_individual_cost * balance_factor

    # Total cost combines individual costs, experience cost, gender cost, and balance cost
    total_cost = (
        +sum(individual_costs.values())
        # + rank_balance_cost
        + individual_balance_cost
        # + gender_cost
        # + exp_cost
    )

    output_buffer = StringIO()
    if print_costs:
        for person in people_data["name_dict"]:
            output_buffer.write(f"Person {person}\n")
            output_buffer.write(f"    Total Cost: {individual_costs[person]}\n")
            # output_buffer.write(f"    Preference Cost: {pref_costs[person]}\n")
            # output_buffer.write(f"    Off-Day Cost: {off_day_costs[person]}\n")
            # output_buffer.write(f"    Shift Ranking Cost: {rank_costs[person]}\n")
        output_buffer.write(f"Total Cost: {total_cost}\n")
        # output_buffer.write(f"Experience cost: {exp_cost}\n")
        # output_buffer.write(f"Genders cost: {gender_cost}\n")
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

    return total_cost, individual_costs, output_buffer.getvalue()


def total_individual_cost(schedule, assigned_shifts, people_data, shifts_data):
    total_individual_costs = {person: 0 for person in people_data["name_dict"]}
    for person_id in people_data["name_dict"]:
        total_individual_costs[person_id] = individual_cost(
            schedule, person_id, assigned_shifts[person_id], people_data, shifts_data
        )
        
    return total_individual_costs


def individual_cost(
    schedule, person_id, assigned_shifts_person, people_data, shifts_data
):
    individual_costs = 0

    pref_costs = preference_cost(
        schedule, person_id, assigned_shifts_person, people_data, shifts_data
    )
    individual_costs += pref_costs

    off_day_costs = off_day_cost(
        schedule, person_id, assigned_shifts_person, people_data, shifts_data
    )

    individual_costs += off_day_costs

    rank_costs = shift_ranking_cost(
        schedule, person_id, assigned_shifts_person, people_data, shifts_data
    )
    
    individual_costs += rank_costs

    # shift_type_experience_costs = shift_type_experience_cost(
    #     schedule, num_people, people_data["sv_experience_array"]
    # )

    # for person, cost in enumerate(shift_type_experience_costs):
    #     individual_costs[person] += cost

    return individual_costs


def preference_cost(
    schedule,
    person_id,
    assigned_shifts_person,
    people_data,
    shifts_data,
    same_shift_friend_factor=1,
    same_shift_enemy_factor=0.75,
    same_time_friend_factor=1,
    same_time_enemy_factor=1,
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
):
    shift_ranking_cost = 0

    # General shift costs from shifts_data
    shift_costs = shifts_data["shift_cost_dict"]

    for shift_id in assigned_shifts_person:
        # Add general shift cost to shift_ranking_cost
        shift_ranking_cost += shift_costs.get(shift_id, 0)

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
                    preference_cost = cost
                    break

        # Add the squared preference cost multiplied by the general shift cost
        shift_ranking_cost += shift_costs.get(shift_id, 0) * (preference_cost**2)

    return shift_ranking_cost


def shift_type_experience_cost(solution, num_people, sv_experience_array):
    individual_costs = [0] * num_people

    # Track the last shift type assigned to each person
    first_shift_type_assigned = [-1] * num_people

    for shift_index, shift in enumerate(solution):
        for shift_type in sorted(shift.keys()):  # Iterate through shift types in order
            total_experience = 0
            for person in shift[shift_type]:
                # Check if the person has been assigned to a higher shift type before a lower one
                if (
                    first_shift_type_assigned[person] > shift_type
                    and sv_experience_array[person] == 0
                ):
                    individual_costs[person] += 10000

                if shift_type == 1:
                    total_experience += sv_experience_array[person]

                if first_shift_type_assigned[person] == -1:
                    first_shift_type_assigned[person] = shift_type
            if total_experience == 0 and shift_type == 1:
                individual_costs[person] += 20000

    return individual_costs


def shift_type_weighted_cost(
    person,
    person_shift_type_capacity_arrays,
    shift_type,
    shift_index,
    shift_type_experience_array,
):
    cost = 0

    if person_shift_type_capacity_arrays[1][person] > 0:
        if shift_type == 1:
            if shift_type_experience_array[1] == 0:
                if shift_index > 10:
                    cost += 100

        if shift_type == 0:
            if shift_index <= 10:
                cost -= 100

    return cost


def shift_category_com_cost(
    solution,
    shift_category_array,
    pref_shift_category_array,
    shift_category_factor=SHIFT_CATEGORY_FACTOR,
):
    num_people = len(pref_shift_category_array)
    individual_costs = [0] * num_people

    mismatches = [0] * num_people
    for shift_index, shift in enumerate(solution):
        for person in shift:
            if shift_category_array[shift_index] != pref_shift_category_array[person]:
                if shift_category_array[shift_index] > 0:
                    mismatches[person] += 1

    for person in range(num_people):
        if mismatches[person] > 0:
            individual_costs[person] = shift_category_factor * (
                2 ** (mismatches[person] - 1)
            )  # Exponential increase

    return individual_costs


def mixedExperience_cost(
    solution,
    experience_array,
    num_of_shifts,
    experience_factor=EXPERIENCE_FACTOR,
):
    total_cost = 0
    shift_experience = [0] * num_of_shifts

    for shift_index, shift in enumerate(solution):
        for shift_type in shift:
            shift_experience[shift_index] += sum(
                experience_array[person] for person in shift[shift_type]
            ) / len(shift[shift_type])

    experience_deviation = statistics.stdev(shift_experience)

    total_cost = experience_deviation * experience_factor
    return total_cost


def mixedGender_cost(
    solution,
    gender_array,
    num_of_shifts,
    one_sided_gender_factor=ONE_SIDED_GENDER_FACTOR,
):
    total_cost = 0
    shift_gender = [0] * num_of_shifts

    for shift_index, shift in enumerate(solution):
        for shift_type in shift:
            shift_gender[shift_index] += sum(
                gender_array[person] for person in shift[shift_type]
            ) / len(shift[shift_type])

    gender_deviation = statistics.stdev(shift_gender)
    total_cost = gender_deviation * one_sided_gender_factor
    return total_cost


def minimum_sv_experience_costs(shift, sv_experience_array):
    total_experience = 0
    for person in shift:
        total_experience += sv_experience_array[person]

    return total_experience > 0 or random.random() < 0.50
