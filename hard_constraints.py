import random

def generate_initial_solution(
    x,
    y,
    shift_capacity_matrix,
    person_capacity_array,
    unavailability_matrix,
    minimum_array,
    preference_matrix,
    max_attempts=25000,
    max_retries=1000,
):
    def reset_solution():
        return [set() for _ in range(x)]

    def is_valid_assignment(solution, shift, person):
        return (
            len(solution[shift]) < shift_capacity_matrix[1][shift][1]
            and shift not in assigned_shifts
            and (
                len(solution[shift]) < shift_capacity_matrix[0][shift][1]
                or random.random() < 0.30
            )
            and consecutive_shifts(solution, shift, person, minimum_array) == 0
            and unavailability(shift, unavailability_matrix, person) == 0
            and not isEnemy(person, solution[shift], preference_matrix)
        )

    retries = 0
    solution = reset_solution()

    while retries < max_retries:
        success = True
        attempts = 0
        for person in range(y):
            assigned_shifts = set()

            while len(assigned_shifts) < person_capacity_array[person] and attempts < max_attempts:
                shift = random.randint(0, x - 1)

                if is_valid_assignment(solution, shift, person):
                    solution[shift].add(person)
                    assigned_shifts.add(shift)
                
                attempts += 1

                if attempts >= max_attempts:
                    success = False
                    break

            if not success:
                break

        if success:
            return solution

        print(
            f"Warning: Failed to generate a valid initial solution after {max_attempts} attempts. Retrying..."
        )
        retries += 1
        solution = reset_solution()

    raise ValueError(f"Failed to generate a valid initial solution after {max_retries} retries.")



def get_neighbor(
    solution,
    unavailability_matrix,
    shift_capacity_matrix,
    minimum_array,
    preference_matrix,
    max_attempts=10000,
):
    attempts = 0
    while attempts < max_attempts:
        index1 = random.randint(0, len(solution) - 1)
        index2 = random.randint(0, len(solution) - 1)
        shift1 = solution[index1].copy()
        shift2 = solution[index2].copy()

        if len(shift1) > shift_capacity_matrix[0][index1][1] and (
            len(shift2) < shift_capacity_matrix[0][index2][1]
            or (
                len(shift2) < shift_capacity_matrix[1][index2][1]
                and random.random() < 0.33
            )
        ):

            person_to_move = get_random_element(shift1)

            if (
                person_to_move not in shift2
                and consecutive_shifts(solution, index2, person_to_move, minimum_array)
                == 0
                and unavailability(index2, unavailability_matrix, person_to_move) == 0
                and not isEnemy(person_to_move, shift2, preference_matrix)
            ):
                shift1.remove(person_to_move)
                shift2.add(person_to_move)
                new_solution = solution.copy()
                new_solution[index1] = shift1
                new_solution[index2] = shift2
                return new_solution  # The neighbor solution satisfies both hard constraints
        else:
            # Swap people between the shifts if possible
            person1 = get_random_element(shift1)
            person2 = get_random_element(shift2)

            if (
                person1 not in shift2
                and person2 not in shift1
                and consecutive_shifts(solution, index2, person1, minimum_array) == 0
                and consecutive_shifts(solution, index1, person2, minimum_array) == 0
                and unavailability(index2, unavailability_matrix, person1) == 0
                and unavailability(index1, unavailability_matrix, person2) == 0
                and not isEnemy(person1, shift2, preference_matrix)
                and not isEnemy(person2, shift1, preference_matrix)
            ):
                shift1.remove(person1)
                shift1.add(person2)
                shift2.remove(person2)
                shift2.add(person1)
                new_solution = solution.copy()
                new_solution[index1] = shift1
                new_solution[index2] = shift2
                return new_solution  # The neighbor solution satisfies both hard constraints

        attempts += 1
    # Return the original solution if no valid neighbor is found after max_attempts
    print("No valid neighbor found after", max_attempts, "attempts")
    return solution


def get_random_element(s):
    if len(s) == 0:
        return None
    return random.choice(list(s))


def isEnemy(person1, shift, preference_matrix):
    for person2 in shift:
        if preference_matrix[person1][person2] > 0:
            return True
    return False


def unavailability(shift_index, unavailability_matrix, person):
    if unavailability_matrix[person][shift_index]:
        return 1
    return 0


def consecutive_shifts(solution, shift_index, person, minimum_array):
    # Check previous and next shifts within the specified range
    for i in range(1, minimum_array[person] + 1):
        if (shift_index - i >= 0 and person in solution[shift_index - i]) or (
            shift_index + i < len(solution) and person in solution[shift_index + i]
        ):
            return 1

    return 0
