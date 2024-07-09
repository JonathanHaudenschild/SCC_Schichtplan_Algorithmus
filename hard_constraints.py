import random


def is_valid_assignment(
    person_shift_type_capacity_arrays,
    shift_type_capacity_matrices,
    minimum_array,
    unavailability_matrix,
    preference_matrix,
    solution,
    shift_index,
    person,
    shift_type,
    assigned_shifts,
):
    person_capacity_array = person_shift_type_capacity_arrays[shift_type]
    return (
        len(solution[shift_index][shift_type])
        < shift_type_capacity_matrices[shift_type][1][shift_index][1]
        and shift_index not in assigned_shifts
        and (
            len(solution[shift_index][shift_type])
            < shift_type_capacity_matrices[shift_type][0][shift_index][1]
            or random.random() < 0.30
        )
        and not consecutive_shifts(solution, shift_index, person, minimum_array)
        and unavailability(shift_index, unavailability_matrix, person) == 0
        and not isEnemy(
            person,
            solution[shift_index][shift_type],
            preference_matrix,
            shift_index,
            shift_type,
        )
        and not any(
            person in solution[shift_index][other_shift_type]
            for other_shift_type in range(len(shift_type_capacity_matrices))
            if other_shift_type != shift_type
        )
        and sum(person in solution[shift][shift_type] for shift in range(len(solution)))
        < person_capacity_array[
            person
        ]  # Ensure person does not exceed their capacity for this shift type
    )


def generate_initial_solution(
    x,
    y,
    shift_type_capacity_matrices,  # List of capacity matrices for each shift type
    person_shift_type_capacity_arrays,  # List of capacity arrays for each shift type per person
    unavailability_matrix,
    minimum_array,
    preference_matrix,
    max_attempts=10000,
    max_retries=10000,
):
    def reset_solution():
        return [
            {
                shift_type: set()
                for shift_type in range(len(shift_type_capacity_matrices))
            }
            for _ in range(x)
        ]

    retries = 0
    solution = reset_solution()

    while retries < max_retries:
        success = True
        attempts = 0
        for person in range(y):
            assigned_shifts = set()
            total_capacity = sum(
                person_shift_type_capacity_arrays[shift_type][person]
                for shift_type in range(len(person_shift_type_capacity_arrays))
            )
            while len(assigned_shifts) < total_capacity and attempts < max_attempts:
                shift_index = random.randint(0, x - 1)
                for shift_type in range(len(person_shift_type_capacity_arrays)):
                    if is_valid_assignment(
                        person_shift_type_capacity_arrays,
                        shift_type_capacity_matrices,
                        minimum_array,
                        unavailability_matrix,
                        preference_matrix,
                        solution,
                        shift_index,
                        person,
                        shift_type,
                        assigned_shifts,
                    ):
                        solution[shift_index][shift_type].add(person)
                        assigned_shifts.add(shift_index)

                    attempts += 1

                if attempts >= max_attempts:
                    success = False
                    break

            if not success:
                break

        if success:
            print("solution generated successfully", solution)
            return solution

        retries += 1
        solution = reset_solution()

    raise ValueError(
        f"Failed to generate a valid initial solution after {max_retries} retries."
    )


def get_neighbor(
    solution,
    unavailability_matrix,
    shift_type_capacity_matrices,
    person_shift_type_capacity_arrays,
    minimum_array,
    preference_matrix,
    max_attempts=10000,
):
    attempts = 0
    shift_types = list(range(len(shift_type_capacity_matrices)))  # List of shift types

    while attempts < max_attempts:
        shift_type = random.choice(shift_types)

        index1 = random.randint(0, len(solution) - 1)
        index2 = random.randint(0, len(solution) - 1)

        shift1 = solution[index1][shift_type].copy()
        shift2 = solution[index2][shift_type].copy()

        capacity_matrix = shift_type_capacity_matrices[shift_type]
        person_capacity_array = person_shift_type_capacity_arrays[shift_type]

        if len(shift1) > capacity_matrix[0][index1][1] and (
            len(shift2) < capacity_matrix[0][index2][1]
            or (len(shift2) < capacity_matrix[1][index2][1] and random.random() < 0.33)
        ):
            person_to_move = get_random_element(shift1)

            if (
                person_to_move not in shift2
                and not any(
                    person_to_move in solution[index2][t] for t in shift_types
                )  # Ensure person is not in any shift type at index2
                and not consecutive_shifts(
                    solution, index2, person_to_move, minimum_array
                )
                and unavailability(index2, unavailability_matrix, person_to_move) == 0
                and not any(
                    isEnemy(
                        person_to_move,
                        solution[index2][t],
                        preference_matrix,
                        index2,
                        t,
                    )
                    for t in shift_types
                )
            ):
                shift1.remove(person_to_move)
                shift2.add(person_to_move)
                new_solution = [sh.copy() for sh in solution]
                new_solution[index1][shift_type] = shift1
                new_solution[index2][shift_type] = shift2
                return new_solution  # The neighbor solution satisfies both hard constraints
        else:
            # Swap people between the shifts if possible
            person1 = get_random_element(shift1)
            person2 = get_random_element(shift2)
            if (
                person1 not in shift2
                and person2 not in shift1
                and not any(
                    person1 in solution[index2][t] for t in shift_types
                )  # Ensure person1 is not in any shift type at index2
                and not any(
                    person2 in solution[index1][t] for t in shift_types
                )  # Ensure person2 is not in any shift type at index1
                and not consecutive_shifts(solution, index2, person1, minimum_array)
                and not consecutive_shifts(solution, index1, person2, minimum_array)
                and unavailability(index2, unavailability_matrix, person1) == 0
                and unavailability(index1, unavailability_matrix, person2) == 0
                and not any(
                    isEnemy(person1, solution[index2][t], preference_matrix, index2, t)
                    for t in shift_types
                )
                and not any(
                    isEnemy(person2, solution[index1][t], preference_matrix, index1, t)
                    for t in shift_types
                )
            ):
                shift1.remove(person1)
                shift1.add(person2)
                shift2.remove(person2)
                shift2.add(person1)
                new_solution = [sh.copy() for sh in solution]
                new_solution[index1][shift_type] = shift1
                new_solution[index2][shift_type] = shift2
                return new_solution  # The neighbor solution satisfies both hard constraints

        attempts += 1
    # Return the original solution if no valid neighbor is found after max_attempts
    print("No valid neighbor found after", max_attempts, "attempts")
    return solution


def get_random_element(s):
    if len(s) == 0:
        return None
    return random.choice(list(s))


def get_random_element(s):
    if len(s) == 0:
        return None
    return random.choice(list(s))


def isEnemy(person, shift, preference_matrix, shift_index, shift_type):
    if shift_index < 10 and shift_type == 0:
        return False
    for other_person in shift:
        if preference_matrix[person][other_person] > 0:
            return True
    return False


def unavailability(shift_index, unavailability_matrix, person):
    return unavailability_matrix[person][shift_index]


def consecutive_shifts(solution, shift_index, person, minimum_array):
    for i in range(1, minimum_array[person] + 1):
        if shift_index - i >= 0:
            for shift_type in solution[shift_index - i]:
                if person in solution[shift_index - i][shift_type]:
                    return True
        if shift_index + i < len(solution):
            for shift_type in solution[shift_index + i]:
                if person in solution[shift_index + i][shift_type]:
                    return True
    return False
