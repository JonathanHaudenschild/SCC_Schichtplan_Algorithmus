import random

DEFAULT_MIN_AMOUNT_SHIFT = 4
DEFAULT_MAX_AMOUNT_SHIFT = 5


def get_random_element(d, weights=None):
    items = list(d.items())
    if weights:
        return random.choices(items, weights=weights, k=1)[0][0]
    return random.choice(items)[0]


def create_ranked_shifts(schedule, shifts_data):
    ranked_shifts = {shift_id: 0 for shift_id in schedule}
    priority_dict = shifts_data.get("shift_priority_dict", {})

    for shift_id, people_in_shift in schedule.items():
        min_capacity, max_capacity = shifts_data["shift_capacity_dict"].get(
            shift_id, (0, 0)
        )
        current_capacity = len(people_in_shift)

        # Calculate rank based on capacity
        if current_capacity < min_capacity:
            capacity_rank = (min_capacity - current_capacity) / min_capacity * 100
        else:
            capacity_rank = 0

        # Add priority factor to the rank
        priority_rank = priority_dict.get(shift_id, 0)

        # Combine both rankings
        rank = capacity_rank + priority_rank

        ranked_shifts[shift_id] = rank

    # Normalize rankings to make them suitable for weighted random selection
    total_ranking = sum(ranked_shifts.values())
    if total_ranking > 0:
        for shift_id in ranked_shifts:
            ranked_shifts[shift_id] /= total_ranking

    return ranked_shifts


def get_random_element_from_list(s):
    if len(s) == 0:
        return None
    return random.choice(list(s))


def filter_shift_type(shift, shift_id, people_data, shifts_data):
    shift_type = shifts_data["shift_type_dict"].get(shift_id)
    return {
        person: people_data["people_shift_types_dict"][person]
        for person in shift
        if shift_type in people_data["people_shift_types_dict"][person]
    }


def filter_shifts_for_person(
    schedule, person_id, assigned_shifts, people_data, shifts_data
):
    # Helper function to calculate the number of allocated shift types for a person
    def calculate_allocated_shift_types(assigned_shifts, shift_type_dict):
        allocated_shift_types = {}
        for assigned_shift in assigned_shifts:
            assigned_shift_type = shift_type_dict.get(assigned_shift, 0)
            if assigned_shift_type in allocated_shift_types:
                allocated_shift_types[assigned_shift_type] += 1
            else:
                allocated_shift_types[assigned_shift_type] = 1
        return allocated_shift_types

    # Get the preferred shift types for the person
    person_shift_types = people_data["people_shift_types_dict"].get(person_id, {})
    # Calculate the number of each shift type already assigned to the person
    allocated_shift_types = calculate_allocated_shift_types(
        assigned_shifts, shifts_data["shift_type_dict"]
    )

    # Filter out shifts exceeding their maximum capacity, unless capacity is unlimited
    valid_shifts = {
        shift_id: shifts_data["shift_type_dict"][shift_id]
        for shift_id in schedule
        if len(schedule[shift_id]) < shifts_data["shift_capacity_dict"][shift_id][1]
        or shifts_data["shift_capacity_dict"][shift_id][1] == 0
    }

    # Function to calculate the score for a shift based on different criteria
    def calculate_shift_score(shift_id):
        shift_type = shifts_data["shift_type_dict"][shift_id]
        score = 0

        # Criteria 1: Restriction
        if shifts_data["restrict_shift_type_dict"].get(shift_id) and allocated_shift_types.get(shift_type, 0) < person_shift_types.get(shift_type, [0, 0, 0])[2]:
            score += 10  # Higher score for restricted shifts

        # Criteria 2: Minimum capacity of person
        if shift_type in person_shift_types and allocated_shift_types.get(shift_type, 0) < person_shift_types[shift_type][1]:
            score += 5  # Higher score if below minimum capacity of person

        # Criteria 3: Shift priority
        score += shifts_data["shift_priority_dict"].get(shift_id, 0)

        # Criteria 4: Below minimum capacity of shift
        if len(schedule.get(shift_id, [])) < shifts_data["shift_capacity_dict"][shift_id][0]:
            score += 2  # Higher score if below minimum capacity of shift

        # Criteria 5: Maximum capacity
        if len(schedule.get(shift_id, [])) < shifts_data["shift_capacity_dict"][shift_id][1] or shifts_data["shift_capacity_dict"][shift_id][1] == 0:
            score += 1  # Higher score if below maximum capacity of shift

        return score

    # Calculate the score for each valid shift
    shift_scores = {
        shift_id: calculate_shift_score(shift_id) for shift_id in valid_shifts
    }

    # Sort shifts based on their score
    ranked_shifts = sorted(shift_scores.items(), key=lambda item: item[1], reverse=True)

    # Extract shift IDs and their corresponding scores
    shift_ids = [shift_id for shift_id, score in ranked_shifts]
    scores = [score for shift_id, score in ranked_shifts]

    # Use scores as weights to randomly choose a shift
    chosen_shift = random.choices(shift_ids, weights=scores, k=1)[0]
    print("ranked_shifts", ranked_shifts)
    print("chosen_shift", chosen_shift)
    return chosen_shift


def is_valid_assignment(
    schedule, new_shift_id, person_id, assigned_shifts_person, people_data, shifts_data
):
    # Ensure schedule entry exists
    # if new_shift_id not in schedule:
    #     schedule[new_shift_id] = []

    # Check constraints
    if (
        len(schedule[new_shift_id])
        > shifts_data["shift_capacity_dict"][new_shift_id][1]
    ):
        return False
    if not check_min_break(assigned_shifts_person, person_id, people_data, shifts_data):
        return False
    # if not check_unavailability(
    #     shifts_data["shift_time_dict"],
    #     new_shift_id,
    #     people_data["unavailability_dict"],
    #     person,
    # ):
    #     return False
    # if not check_shift_restriction(
    #     person,
    #     people_data["people_shift_types_dict"],
    #     new_shift_id,
    #     shifts_data["shift_type_dict"],
    #     shifts_data["restrict_shift_type_dict"],
    # ):
    #     return False
    # if isEnemy(person, schedule[new_shift_id], people_data["preference_dict"]):
    #     return False
    # if exceed_person_shift_type_capacity(
    #     schedule,
    #     person,
    #     people_data["people_shift_types_dict"],
    #     people_data["person_capacity_dict"],
    #     shifts_data["shift_type_dict"],
    # ):
    #     return False

    return True


def allocate_shifts_for_all_persons(
    schedule,
    people_data,
    shifts_data,
):

    people = list(people_data["name_dict"].keys())
    attempts = 0
    max_attempts = 1000
    assigned_shifts_history = {}

    while people != [] and attempts < max_attempts:
        person_id = people.pop()
        new_schedule, shifts_history_of_person, success = allocate_shifts_for_person(
            assigned_shifts_history.get(person_id, []).copy(),
            schedule.copy(),
            person_id,
            people_data,
            shifts_data,
            shifts_data["shift_time_dict"].copy(),
        )

        if success:
            schedule = new_schedule
            assigned_shifts_history[person_id] = shifts_history_of_person
            attempts = 0
            print(
                "Person",
                person_id,
                "assigned shifts",
                assigned_shifts_history,
                "successfully",
            )
        else:
            people.append(person_id)
            for shift_id in schedule:
                if person_id in schedule[shift_id]:
                    schedule[shift_id].remove(person_id)
                    
                    if shift_id in assigned_shifts_history:
                        assigned_shifts_history.remove(shift_id)
            attempts += 1
            print("Failed to assign shifts to person", person_id)
            
    return schedule


def allocate_shifts_for_person(
    assigned_shifts_history,
    schedule,
    person_id,
    people_data,
    shifts_data,
    filtered_shifts,
):
    person_capacity = people_data["person_capacity_dict"].get(
        person_id, (DEFAULT_MIN_AMOUNT_SHIFT, DEFAULT_MAX_AMOUNT_SHIFT)
    )[1]

    if len(assigned_shifts_history) >= person_capacity:
        return schedule, assigned_shifts_history, True

    shift_id  = filter_shifts_for_person(
        schedule, person_id, assigned_shifts_history, people_data, shifts_data
    )

    if not shift_id:
        return schedule, assigned_shifts_history, False


    is_person_in_shift = person_id in (schedule.get(shift_id, []))
    

    if not is_person_in_shift:
        
        schedule[shift_id].append(person_id)
        assigned_shifts_history.append(shift_id)
        
        if is_valid_assignment(
            schedule.copy(),
            shift_id,
            person_id,
            assigned_shifts_history.copy(),
            people_data,
            shifts_data,
        ):

            filtered_shifts.pop(shift_id)
            if person_id == '33.0' or person_id == 51.0:
                print("filtered_shifts", filtered_shifts)
                print("schedule", schedule)

            return allocate_shifts_for_person(
                assigned_shifts_history.copy(),
                schedule.copy(),
                person_id,
                people_data,
                shifts_data,
                filtered_shifts.copy(),
            )
            
        else:
            schedule[shift_id].remove(person_id)
            assigned_shifts_history.pop()

    return schedule, assigned_shifts_history, False


def generate_initial_solution(
    shifts_data, people_data, max_attempts=1000, max_retries=1000
):

    schedule = {shift_id: [] for shift_id in shifts_data["shift_time_dict"]}

    schedule = allocate_shifts_for_all_persons(
        schedule,
        people_data,
        shifts_data,
    )
    if schedule:
        print("Solution generated successfully", schedule)

    else:
        print(
            "Failed to generate a valid initial solution after", max_retries, "retries."
        )
    return schedule

    # def reset_schedule():
    #     return {shift_id: [] for shift_id in shifts_data["shift_time_dict"]}

    # def backtrack(assigned_shifts_history, schedule, person):
    #     if assigned_shifts_history[person]:
    #         last_assigned_shift = assigned_shifts_history[person].pop()
    #         schedule[last_assigned_shift].remove(person)
    #         return True
    #     return False

    # def generate_weights(items):
    #     return [(len(items) - i) for i in range(len(items))]

    # retries = 0
    # schedule = reset_schedule()

    # while retries < max_retries:
    #     success = True
    #     assigned_shifts_history = {person: [] for person in people_data["name_dict"]}

    #     list_of_people = list(people_data["name_dict"].items())
    #     random.shuffle(list_of_people)
    #     list_of_people_shuffled = dict(list_of_people)

    #     for person_id in list_of_people_shuffled:

    #         ## get the person capacity
    #         person_capacity = people_data["person_capacity_dict"].get(
    #             person_id, (DEFAULT_MIN_AMOUNT_SHIFT, DEFAULT_MAX_AMOUNT_SHIFT)
    #         )[1]

    #         attempts = 0

    #         ## while the person has not reached the capacity and the number of attempts is less than the max attempts allowed
    #         ## keep trying to assign shifts to the person
    #         while (
    #             len(assigned_shifts_history[person_id])
    #             < person_capacity
    #             # and attempts < max_attempts
    #         ):

    #             filtered_shifts = filter_shifts_for_person(
    #                 person_id,
    #                 assigned_shifts_history[person_id],
    #                 people_data,
    #                 schedule,
    #                 shifts_data,
    #             )
    #             items = list(filtered_shifts.items())
    #             weights = generate_weights(items)
    #             if filtered_shifts == {}:  # If no shifts are available
    #                 break

    #             new_shift_id = get_random_element(filtered_shifts, weights)
    #             schedule[new_shift_id].append(person_id)

    #             if is_valid_assignment(
    #                 shifts_data,
    #                 people_data,
    #                 schedule,
    #                 new_shift_id,
    #                 person_id,
    #                 assigned_shifts_history[person_id],
    #             ):
    #                 assigned_shifts_history[person_id].append(new_shift_id)
    #             else:
    #                 schedule[new_shift_id].remove(person_id)
    #                 if attempts >= max_attempts:
    #                     attempts = 0
    #                     if not backtrack(assigned_shifts_history, schedule, person_id):
    #                         break
    #             attempts += 1

    #         if len(assigned_shifts_history[person_id]) < person_capacity:
    #             success = False
    #             break

    #     if success:
    #         print("Solution generated successfully", schedule)
    #         return schedule

    #     retries += 1
    #     schedule = reset_schedule()

    # raise ValueError(
    #     f"Failed to generate a valid initial solution after {max_retries} retries."
    # )


def get_neighbor(
    schedule,
    shifts_data,
    people_data,
    max_attempts=10000,
):
    attempts = 0

    while attempts < max_attempts:
        ranked_shifts = create_ranked_shifts(schedule, shifts_data)
        random_id1 = get_random_element(shifts_data["shift_time_dict"])
        random_id2 = get_random_element(ranked_shifts, list(ranked_shifts.values()))

        shift1 = schedule.get(random_id1).copy()
        shift2 = schedule.get(random_id2).copy()

        shift_capacity_dict = shifts_data["shift_capacity_dict"]

        if len(shift1) > shift_capacity_dict.get(random_id1)[0] and (
            len(shift2) < shift_capacity_dict.get(random_id2)[0]
            or (
                len(shift2) < shift_capacity_dict.get(random_id2)[1]
                and random.random() < 0.33
            )
        ):

            filtered_shift = filter_shift_type(
                shift1, random_id2, people_data, shifts_data
            )
            person_to_move = get_random_element_from_list(filtered_shift)
            if person_to_move == None:
                continue
            if (
                person_to_move not in shift2
                and check_min_break(
                    schedule, random_id2, person_to_move, people_data, shifts_data
                )
                and check_unavailability(
                    shifts_data["shift_time_dict"],
                    random_id2,
                    people_data["unavailability_dict"],
                    person_to_move,
                )
                and not isEnemy(
                    person_to_move,
                    schedule.get(random_id2),
                    people_data["preference_dict"],
                )
            ):
                shift1.remove(person_to_move)
                shift2.append(person_to_move)
                new_schedule = schedule.copy()
                new_schedule[random_id1] = shift1
                new_schedule[random_id2] = shift2
                return new_schedule  # The neighbor solution satisfies both hard constraints
        else:
            # Swap people between the shifts if possible

            filtered_shift1 = filter_shift_type(
                shift1, random_id2, people_data, shifts_data
            )

            filtered_shift2 = filter_shift_type(
                shift2, random_id1, people_data, shifts_data
            )

            person1 = get_random_element_from_list(filtered_shift1)
            person2 = get_random_element_from_list(filtered_shift2)

            if person1 == None or person2 == None:
                continue

            if (
                person1 not in shift2
                and person2 not in shift1
                and check_min_break(
                    schedule, random_id2, person1, people_data, shifts_data
                )
                and check_min_break(
                    schedule, random_id1, person2, people_data, shifts_data
                )
                and check_unavailability(
                    shifts_data["shift_time_dict"],
                    random_id1,
                    people_data["unavailability_dict"],
                    person2,
                )
                and check_unavailability(
                    shifts_data["shift_time_dict"],
                    random_id2,
                    people_data["unavailability_dict"],
                    person1,
                )
                and not isEnemy(
                    person1,
                    schedule.get(random_id1),
                    people_data["preference_dict"],
                )
                and not isEnemy(
                    person2,
                    schedule.get(random_id2),
                    people_data["preference_dict"],
                )
            ):

                shift1.remove(person1)
                shift1.append(person2)
                shift2.remove(person2)
                shift2.append(person1)
                new_schedule = schedule.copy()
                new_schedule[random_id1] = shift1
                new_schedule[random_id2] = shift2
                return new_schedule  # The neighbor solution satisfies both hard constraints

        attempts += 1
    # Return the original solution if no valid neighbor is found after max_attempts
    print("No valid neighbor found after", max_attempts, "attempts")
    return schedule


def isEnemy(person, shift, preference_dict):
    if person not in preference_dict:
        return False

    for other_person in shift:
        if other_person in preference_dict[person]:
            return True
    return False


# shifttype: (shifttype, (experience, min_capacity, max_capacity))
def exceed_person_shift_type_capacity(
    schedule, person, people_shift_types_dict, person_capacity_dict, shift_type_dict
):

    # Initialize the counts dictionary
    current_shift_types_counts = {
        p: {st: 0 for st in people_shift_types_dict[p]} for p in people_shift_types_dict
    }

    # Iterate through each shift in the schedule
    for shift_id, shift in schedule.items():
        shift_type = shift_type_dict[shift_id]
        for p in shift:
            if (
                p in current_shift_types_counts
                and shift_type in current_shift_types_counts[p]
            ):
                current_shift_types_counts[p][shift_type] += 1

    # Check if the given person exceeds any shift type capacity
    for shift_type, count in current_shift_types_counts[person].items():
        exp, min_capacity, max_capacity = people_shift_types_dict[person].get(
            shift_type, (0, 0, 0)
        )
        if (min_capacity == 0 and max_capacity == 0) or (min_capacity > max_capacity):
            return False
        if count > max_capacity:
            print(
                f"Person {person} has exceeded the maximum capacity for shift type {shift_type}."
            )
            return True

    # Add up all shift counts regardless of shift type
    total_shift_count = sum(current_shift_types_counts[person].values())

    if person in person_capacity_dict:
        if total_shift_count > person_capacity_dict[person][1]:
            print(
                f"Person {person} has exceeded the maximum total shift capacity of {person_capacity_dict[person][1]}."
            )
            return True

    # If no capacity is exceeded for any shift type, return False
    return False


def check_shift_restriction(
    person, people_shift_types_dict, shift_id, shift_type_dict, restrict_shift_type_dict
):
    shift_type = shift_type_dict.get(shift_id)
    if restrict_shift_type_dict.get(shift_id):
        return shift_type in people_shift_types_dict.get(person, [])
    return True


def check_unavailability(shift_time_dict, shift_id, unavailability_dict, person):
    shift_start, shift_end = shift_time_dict.get(shift_id)
    unavailability_periods = unavailability_dict.get(person, [])

    for unavailability_start, unavailability_end in unavailability_periods:
        if not (shift_end <= unavailability_start or shift_start >= unavailability_end):
            return False
    return True


def check_min_break(person_shifts, person, people_data, shifts_data):

    shift_time_dict = shifts_data["shift_time_dict"].copy()
    if not person_shifts:
        return True
    # for shift in person_shifts:
    #     if shift not in shifts_data["shift_time_dict"]:
    #         return False
    person_shifts = [
        (
            shift_time_dict[shift][0],
           shift_time_dict[shift][1],
        )
        for shift in person_shifts
    ]

    person_shifts.sort()

    min_break = people_data["minimum_break_dict"].get(person, 0)
    for i in range(1, len(person_shifts)):
        if person_shifts[i][0] - person_shifts[i - 1][1] < min_break:
            return False
    return True
