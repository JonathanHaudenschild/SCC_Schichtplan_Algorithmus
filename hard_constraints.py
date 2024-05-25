import random


def generate_initial_solution(
    x,
    y,
    shift_capacity_matrix,
    shift_sv_capacity_matrix,
    person_capacity_array,
    sv_capacity_array,
    max_attempts=100000,
):
    solution = [dict(normal=set(), sv=set()) for _ in range(x)]
    attempts = 0

    for person in range(y):
        assigned_normal_shifts = set()
        assigned_sv_shifts = set()
        while (
            (len(assigned_normal_shifts) < person_capacity_array[person])
            or (len(assigned_sv_shifts) < sv_capacity_array[person])
        ) and (attempts < max_attempts):
            shift = random.randint(0, x - 1)
            if len(assigned_normal_shifts) < person_capacity_array[person]:
                if (
                    len(solution[shift]["normal"]) < shift_capacity_matrix[1][shift][1]
                    and person not in solution[shift]["sv"]
                    and shift not in assigned_normal_shifts
                ):
                    if (
                        len(solution[shift]["normal"])
                        < shift_capacity_matrix[0][shift][1]
                        or random.random() < 0.30
                    ):
                        solution[shift]["normal"].add(person)
                        assigned_normal_shifts.add(shift)

            if len(assigned_sv_shifts) < sv_capacity_array[person]:
                if (
                    len(solution[shift]["sv"]) < shift_sv_capacity_matrix[1][shift][1]
                    and person not in solution[shift]["normal"]
                    and shift not in assigned_sv_shifts
                ):
                    if (
                        len(solution[shift]["sv"])
                        < shift_sv_capacity_matrix[0][shift][1]
                        or random.random() < 0.30
                    ):
                        solution[shift]["sv"].add(person)
                        assigned_sv_shifts.add(shift)

            attempts += 1

        if attempts >= max_attempts:
            print(
                "Warning: Failed to generate a valid initial solution after "
                + str(max_attempts)
                + " attempts."
            )
            break

    return solution


def get_neighbor(
    solution,
    unavailability_matrix,
    shift_capacity_matrix,
    sv_shift_capacity_matrix,
    minimum_array,
    preference_matrix,
    sv_experience_array,
    max_attempts=15000,
):
    # Calculate total slots for normal and sv
    total_normal_slots = sum(len(shift["normal"]) for shift in solution)
    total_sv_slots = sum(len(shift["sv"]) for shift in solution)

    # Calculate weights
    total_slots = total_normal_slots + total_sv_slots
    normal_weight = total_normal_slots / total_slots
    sv_weight = total_sv_slots / total_slots

    attempts = 0
    while attempts < max_attempts:
        shift_type = random.choices(
            ["normal", "sv"], weights=[normal_weight, sv_weight], k=1
        )[0]

        index1 = random.randint(0, len(solution) - 1)
        index2 = random.randint(0, len(solution) - 1)

        shift1 = solution[index1][shift_type].copy()
        shift2 = solution[index2][shift_type].copy()

        if shift_type == "normal":
            capacity_matrix = shift_capacity_matrix
        else:
            capacity_matrix = sv_shift_capacity_matrix

        if len(shift1) > 0 and len(shift2) < capacity_matrix[0][index2][1]:
            person_to_move = get_random_element(shift1)
            if (
                person_to_move not in shift2
                and person_to_move
                not in solution[index2]["normal" if shift_type == "sv" else "sv"]
                and consecutive_shifts(solution, index2, person_to_move, minimum_array)
                == 0
                and unavailability(index2, unavailability_matrix, person_to_move) == 0
                and not isEnemy(person_to_move, shift2, preference_matrix)
            ):
                shift1.remove(person_to_move)
                shift2.add(person_to_move)
                new_solution = solution.copy()
                new_solution[index1][shift_type] = shift1
                new_solution[index2][shift_type] = shift2
                return new_solution
        elif len(shift1) > 0 and len(shift2) > 0:
            person1 = get_random_element(shift1)
            person2 = get_random_element(shift2)
            if (
                person1 not in shift2
                and person2 not in shift1
                and person1
                not in solution[index2]["normal" if shift_type == "sv" else "sv"]
                and person2
                not in solution[index1]["normal" if shift_type == "sv" else "sv"]
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
                new_solution[index1][shift_type] = shift1
                new_solution[index2][shift_type] = shift2
                return new_solution

        attempts += 1
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
    return unavailability_matrix[person][shift_index]


def consecutive_shifts(solution, shift_index, person, minimum_array):
    # Check previous and next shifts within the specified range
    for i in range(1, minimum_array[person] + 1):
        if (shift_index - i >= 0 and person in solution[shift_index - i]["normal"]) or (
            shift_index + i < len(solution)
            and person in solution[shift_index + i]["normal"]
        ):
            return 1
        if (shift_index - i >= 0 and person in solution[shift_index - i]["sv"]) or (
            shift_index + i < len(solution)
            and person in solution[shift_index + i]["sv"]
        ):
            return 1
    return 0
