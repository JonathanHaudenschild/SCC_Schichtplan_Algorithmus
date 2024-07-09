import random
import statistics
from io import StringIO


EXPERIENCE_FACTOR = 1000
ONE_SIDED_GENDER_FACTOR = 1000
SHIFT_CATEGORY_FACTOR = 1
OFF_DAY_FACTOR = 1000
SHIFT_RANKING_FACTOR = 100
CONSECUTIVE_SHIFT_FACTOR = 5
FRIEND_FACTOR = 1000
ENEMY_FACTOR = 20000


def cost_function(solution, people_data, shifts_data, print_costs=False):
    num_of_shifts = len(shifts_data["shift_date_array"])

    experience_array = people_data["experience_array"]
    sv_experience_array = people_data["sv_experience_array"]

    # Calculate individual costs
    (
        individual_costs,
        rank_costs,
        pref_costs,
        off_day_costs,
        pref_and_off_day_costs,
        shift_type_experience_costs,
    ) = individual_cost(solution, people_data, shifts_data)

    # Calculate the mean and standard deviation of individual costs
    mean_individual_cost = statistics.mean(individual_costs.values())
    deviation_individual_cost = (
        statistics.stdev(individual_costs.values()) if len(individual_costs) > 1 else 0
    )

    # Introduce a balance factor to penalize high deviation
    balance_factor = 50  # Adjust this factor as needed

    mean_rank_costs = statistics.mean(rank_costs)
    deviation_rank_costs = statistics.stdev(rank_costs)
    rank_balance_cost = deviation_rank_costs * 5

    # Calculate mixed experience and gender costs
    exp_cost = mixedExperience_cost(
        solution,
        people_data["experience_array"],
        num_of_shifts,
        EXPERIENCE_FACTOR,
    )
    gender_cost = mixedGender_cost(
        solution, people_data["gender_array"], num_of_shifts, ONE_SIDED_GENDER_FACTOR
    )

    individual_balance_cost = deviation_individual_cost * balance_factor

    # Total cost combines individual costs, experience cost, gender cost, and balance cost
    total_cost = (
        +sum(individual_costs.values())
        + rank_balance_cost
        + individual_balance_cost
        + gender_cost
        + exp_cost
    )

    output_buffer = StringIO()
    if print_costs:
        for person in range(len(people_data["name_array"])):
            output_buffer.write(f"Person {person}\n")
            output_buffer.write(f"    Total Cost: {individual_costs[person]}\n")
            output_buffer.write(f"    Preference Cost: {pref_costs[person]}\n")
            output_buffer.write(f"    Off-Day Cost: {off_day_costs[person]}\n")
            output_buffer.write(f"    Shift Ranking Cost: {rank_costs[person]}\n")
        output_buffer.write(f"Total Cost: {total_cost}\n")
        output_buffer.write(f"Experience cost: {exp_cost}\n")
        output_buffer.write(f"Genders cost: {gender_cost}\n")
        output_buffer.write(
            f"Sum of Individual Costs: {sum(individual_costs.values())}\n"
        )
        output_buffer.write(f"Mean Individual Cost: {mean_individual_cost}\n")
        output_buffer.write(f"Deviation Individual Cost: {deviation_individual_cost}\n")
        output_buffer.write(f"Sum of Off-Day Costs: {sum(off_day_costs)}\n")
        output_buffer.write(
            f"No. of people having no off days: {off_day_costs.count(OFF_DAY_FACTOR)}\n"
        )
        output_buffer.write(f"Sum of Preference Costs: {sum(pref_costs)}\n")
        output_buffer.write(f"Sum of Shift Ranking Costs: {sum(rank_costs)}\n")
        output_buffer.write(
            f"Sum of Shift Type Experience Costs: {sum(shift_type_experience_costs)}\n"
        )

        print(output_buffer.getvalue())

    return total_cost, individual_costs, output_buffer.getvalue()


def individual_cost(solution, people_data, shifts_data):
    num_people = len(people_data["name_array"])
    individual_costs = {person: 0 for person in range(num_people)}
    pref_and_off_day_costs = {person: 0 for person in range(num_people)}

    pref_costs = preference_cost(
        solution,
        people_data["preference_matrix"],
        people_data["total_friends"],
        people_data["person_capacity_array"],
    )
    for person, cost in enumerate(pref_costs):
        individual_costs[person] += cost

    off_day_costs = offDay_cost(solution, people_data["off_shifts_matrix"])
    for person, cost in enumerate(off_day_costs):
        adjustment_factor = 1 + (
            individual_costs[person] ** (1 / 10)
        )  # Adding 1 to avoid division by zero
        individual_costs[person] += cost * adjustment_factor

    rank_costs = shift_ranking_cost(
        solution,
        shifts_data["ranking_array"],
        people_data["preferred_shift_matrix"],
        num_people,
        len(shifts_data["shift_time_array"]),
        people_data,
    )
    for person, cost in enumerate(rank_costs):
        individual_costs[person] += cost

    shift_type_experience_costs = shift_type_experience_cost(
        solution, num_people, people_data["sv_experience_array"]
    )

    for person, cost in enumerate(shift_type_experience_costs):
        individual_costs[person] += cost

    return (
        individual_costs,
        rank_costs,
        pref_costs,
        off_day_costs,
        pref_and_off_day_costs,
        shift_type_experience_costs,
    )


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
    shifts_without_friend = [
        0
    ] * num_people  # Track how many shifts each person has without a friend

    for shift in solution:
        combined_shift = set().union(*shift.values())
        for person1 in combined_shift:
            for person2 in combined_shift:
                if person1 != person2 and preference_matrix[person1][person2] < 0:
                    friend_shift_count[person1] += 1

    for shift_index, shift in enumerate(solution):
        combined_shift = set().union(
            *shift.values()
        )  # Combine all shift types into one set

        for person1 in combined_shift:
            has_friend_in_shift = False
            for person2 in combined_shift:
                if person1 != person2:
                    if preference_matrix[person1][person2] < 0:
                        has_friend_in_shift = True
                        friend_shift_count[person2] -= 1  # Decrement friend shift count

                    if preference_matrix[person1][person2] > 0 and shift_index > 9:
                        individual_costs[person1] += (
                            preference_matrix[person1][person2] * enemy_factor
                        )

            if total_friends[person1] > 0 and not has_friend_in_shift:
                any_friend_has_capacity = False
                for friend, capacity in enumerate(person_capacity_array):
                    if (
                        preference_matrix[person1][friend] < 0
                        and capacity > friend_shift_count[friend]
                    ):
                        any_friend_has_capacity = True
                        break

                if any_friend_has_capacity:
                    shifts_without_friend[person1] += 1
                    penalty = friend_factor * (
                        2 ** (shifts_without_friend[person1] - 1)
                    )
                    individual_costs[person1] += penalty
            else:
                shifts_without_friend[person1] = 0

    return individual_costs


def offDay_cost(solution, unavailability_matrix, off_day_factor=OFF_DAY_FACTOR):
    individual_costs = [0] * len(unavailability_matrix)
    for shift_index, shift in enumerate(solution):
        for shift_type in shift:
            for person in shift[shift_type]:
                if unavailability_matrix[person][shift_index]:
                    individual_costs[person] = off_day_factor
    return individual_costs


def shift_ranking_cost(
    solution,
    ranking_array,
    personal_pref_matrix,
    num_people,
    num_of_shift_seq,
    people_data,
):
    individual_costs = [0] * num_people
    last_shift_index = [-1] * num_people
    shift_accumulation = [[0] * num_of_shift_seq for _ in range(num_people)]
    conc_shifts = [0] * num_people

    for shift_index, shift in enumerate(solution):
        shift_seq = shift_index % num_of_shift_seq
        for shift_type, shift_group in shift.items():
            shift_cost = ranking_array[shift_index]
            for person in shift_group:
                persons_cost = 0
                personal_preference_cost = personal_pref_matrix[person][shift_seq]
                persons_cost += shift_cost * (personal_preference_cost**2)

                if last_shift_index[person] != -1:
                    shift_diff = shift_index - last_shift_index[person]
                    last_shift__seq = last_shift_index[person] % num_of_shift_seq

                    if last_shift__seq == shift_seq:
                        persons_cost += (
                            (personal_preference_cost + 1)
                            * SHIFT_RANKING_FACTOR
                            * shift_accumulation[person][shift_seq]
                        )
                        shift_accumulation[person][shift_seq] += 1

                    if conc_shifts[person] > 1:
                        persons_cost += CONSECUTIVE_SHIFT_FACTOR * conc_shifts[person]

                    if shift_diff < 4:
                        conc_shifts[person] += 1
                    else:
                        conc_shifts[person] = 0

                last_shift_index[person] = shift_index

                # individual_costs[person] += shift_type_weighted_cost(
                #     person, [people_data["person_capacity_array"],people_data["sv_capacity_array"]],
                #     shift_type, shift_index, people_data["sv_experience_array"]
                # )

                individual_costs[person] += persons_cost

    return individual_costs


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
