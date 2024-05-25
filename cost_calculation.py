import random
import statistics
import math

from utilities import convert_to_solution_matrix, split_shift_data

EXPERIENCE_FACTOR = 1
ONE_SIDED_GENDER_FACTOR = 1
SHIFT_CATEGORY_FACTOR = 1
OFF_DAY_FACTOR = 200
SHIFT_RANKING_FACTOR = 1
CONSECUTIVE_SHIFT_FACTOR = 3
FRIEND_FACTOR = 100
ENEMY_FACTOR = 5000


def cost_function(solution, people_data, shifts_data):
    combine_solution = convert_to_solution_matrix(solution)

    num_of_shifts = len(shifts_data["shift_date_array"])

    # Calculate individual costs
    individual_costs, rank_costs, pref_costs, off_day_costs = individual_cost(
        solution, people_data, shifts_data
    )

    # Calculate the mean and standard deviation of individual costs
    mean_individual_cost = statistics.mean(individual_costs.values())
    deviation_individual_cost = (
        statistics.stdev(individual_costs.values()) if len(individual_costs) > 1 else 0
    )

    # Introduce a balance factor to penalize high deviation
    balance_factor = 5  # Adjust this factor as needed

    mean_rank_costs = statistics.mean(rank_costs)
    deviation_rank_costs = statistics.stdev(rank_costs)
    rank_balance_cost = deviation_rank_costs * balance_factor

    normal_solution, sv_solution = split_shift_data(solution)

    # Calculate mixed experience and gender costs
    exp_cost = mixedExperience_cost(
        normal_solution,
        people_data["experience_array"],
        num_of_shifts,
        EXPERIENCE_FACTOR,
    )
    gender_cost = mixedGender_cost(
        normal_solution, people_data["gender_array"], num_of_shifts, 1
    )

    sv_exp_cost = mixedExperience_cost(
        sv_solution,
        people_data["sv_experience_array"],
        num_of_shifts,
        10,
    )

    sv_gender_cost = mixedGender_cost(
        sv_solution, people_data["gender_array"], num_of_shifts, 10
    )

    individual_balance_cost = deviation_individual_cost * balance_factor * 5
    # Total cost combines individual costs, experience cost, gender cost, and balance cost
    total_cost = (
        mean_individual_cost
        + individual_balance_cost
        + mean_rank_costs
        + rank_balance_cost
        + gender_cost
        + exp_cost
        + sv_exp_cost
        + sv_gender_cost
    )

    return total_cost


def individual_cost(solution, people_data, shifts_data):
    combine_solution = convert_to_solution_matrix(solution)
    num_people = len(people_data["name_array"])
    individual_costs = {person: 0 for person in range(num_people)}

    pref_costs = preference_cost(
        combine_solution,
        people_data["preference_matrix"],
        people_data["total_friends"],
        people_data["person_capacity_array"],
    )
    for person, cost in enumerate(pref_costs):
        individual_costs[person] += cost

    off_day_costs = offDay_cost(combine_solution, people_data["off_shifts_matrix"])
    for person, cost in enumerate(off_day_costs):
        individual_costs[person] += cost

    rank_costs = shift_ranking_cost(
        combine_solution,
        shifts_data["ranking_array"],
        people_data["preferred_shift_matrix"],
        people_data["off_shifts_matrix"],
        people_data["minimum_array"],
        num_people,
        len(shifts_data["shift_time_array"]),
        shifts_data["shift_type_array"],
    )

    for person, cost in enumerate(rank_costs):
        individual_costs[person] += cost

    return individual_costs, rank_costs, pref_costs, off_day_costs


def preference_cost(
    solution,
    preference_matrix,
    total_friends,
    person_capacity_array,
    friend_factor=FRIEND_FACTOR,
    enemy_factor=ENEMY_FACTOR,
):
    num_people = len(preference_matrix)
    individual_costs = [0] * num_people
    friend_shift_count = [
        0
    ] * num_people  # Track how often each person works with their friends

    # Count the number of times each person works with their friends
    for shift in solution:
        for person1 in shift:
            for person2 in shift:
                if person1 != person2 and preference_matrix[person1][person2] < 0:
                    friend_shift_count[person1] += 1

    # Calculate the preference cost
    for shift in solution:
        for person1 in shift:
            has_friend_in_shift = False
            for person2 in shift:
                if person1 != person2:
                    if preference_matrix[person1][person2] < 0:
                        has_friend_in_shift = True
                        friend_shift_count[person2] -= 1  # Decrement friend shift count

                    if preference_matrix[person1][person2] > 0:
                        individual_costs[person1] += (
                            preference_matrix[person1][person2] * enemy_factor
                        )

            # Penalize if person1 has friends but none in the shift, and the friend still has shift capacity left
            if total_friends[person1] > 0 and not has_friend_in_shift:
                # Check if any friend still has shift capacity left
                for friend, capacity in enumerate(person_capacity_array):
                    if (
                        preference_matrix[person1][friend] < 0
                        and capacity > friend_shift_count[friend]
                    ):
                        individual_costs[person1] += friend_factor
                        break  # Only penalize once per shift if any friend has capacity left

    return individual_costs


def offDay_cost(solution, unavailability_matrix, off_day_factor=OFF_DAY_FACTOR):
    individual_costs = [0] * len(unavailability_matrix)
    for shift_index, shift in enumerate(solution):
        for person in shift:
            if unavailability_matrix[person][shift_index]:
                individual_costs[person] = off_day_factor
    return individual_costs


def shift_ranking_cost(
    solution,
    ranking_array,
    personal_pref_matrix,
    unavailability_matrix,
    minimum_array,
    num_people,
    num_of_shift_types,
    ranking_type_array,
):
    individual_costs = [0] * num_people
    last_shift_index = [-1] * num_people
    conc_shifts = [0] * num_people

    for shift_index, shift in enumerate(solution):
        shift_type = shift_index % num_of_shift_types
        shift_cost = ranking_array[shift_index]
        for person in shift:
            persons_cost = 0
            personal_preference_cost = personal_pref_matrix[person][shift_type]
            persons_cost += shift_cost * personal_preference_cost

            if last_shift_index[person] != -1:
                shift_diff = shift_index - last_shift_index[person]

                if conc_shifts[person] > 1:
                    persons_cost += CONSECUTIVE_SHIFT_FACTOR * conc_shifts[person]

                if shift_diff > (minimum_array[person] + random.randint(0, 1)):
                    conc_shifts[person] = 0
                else:
                    conc_shifts[person] += 1

            last_shift_index[person] = shift_index
            individual_costs[person] += persons_cost

    return individual_costs


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
        if len(shift) > 0:
            mean_experience = sum(experience_array[person] for person in shift) / len(
                shift
            )
            shift_experience[shift_index] = mean_experience
        else:
            shift_experience[shift_index] = 0

    for shift in shift_experience:
        total_cost += abs(shift - statistics.mean(experience_array)) * experience_factor
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
        if len(shift) > 0:
            gender_mix = sum(gender_array[person] for person in shift) / len(shift)
            shift_gender[shift_index] = gender_mix
        else:
            shift_gender[shift_index] = 0

    for shift in shift_gender:
        total_cost += abs(shift - statistics.mean(gender_array)) * one_sided_gender_factor
    return total_cost


def check_person_costs(solution, people_data, shifts_data):
    individual_costs, rank_costs, pref_costs, off_day_costs = individual_cost(
        solution, people_data, shifts_data
    )

    for person in range(len(people_data["name_array"])):
        print(f"Person {person}: Total Cost = {individual_costs[person]}")
        print(f"    Preference Cost: {pref_costs[person]}")
        print(f"    Off-Day Cost: {off_day_costs[person]}")
        print(f"    Shift Ranking Cost: {rank_costs[person]}")
    
    # Calculate the mean and standard deviation of individual costs
    mean_individual_cost = statistics.mean(individual_costs.values())
    deviation_individual_cost = (
        statistics.stdev(individual_costs.values()) if len(individual_costs) > 1 else 0
    )
    print(f"Total Cost: {sum(individual_costs)}")
    print(f"Mean Individual Cost: {mean_individual_cost}")
    print(f"Deviation Individual Cost: {deviation_individual_cost}")

    return individual_costs


def minimum_sv_experience_costs(shift, sv_experience_array):
    total_experience = 0
    for person in shift:
        total_experience += sv_experience_array[person]

    return total_experience > 0 or random.random() < 0.50
