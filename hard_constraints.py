import random
import time
import copy


DEFAULT_MIN_AMOUNT_SHIFT = 4
DEFAULT_MAX_AMOUNT_SHIFT = 5


def get_random_element(d, weights=None):
    if isinstance(d, dict):
        items = list(d.items())
        if weights:
            return random.choices(items, weights=weights, k=1)[0][0]
        return random.choice(items)[0]
    elif isinstance(d, list):
        if weights:
            return random.choices(d, weights=weights, k=1)[0]
        return random.choice(d)
    elif isinstance(d, set):
        items = list(d)
        if weights:
            return random.choices(items, weights=weights, k=1)[0]
        return random.choice(items)
    else:
        raise TypeError("Input must be a list, dictionary, or set")


def choose_shift(schedule, person_id, assigned_shifts, people_data, shifts_data):
    """
    Choose a shift for a person based on their preferences and the current schedule.

    Args:
    - schedule (dict): The current state of the schedule.
    - person_id (int/float): The ID of the person to assign a shift to.
    - assigned_shifts (list): List of shifts already assigned to the person.
    - people_data (dict): Data about people including their preferences and capacities.
    - shifts_data (dict): Data about shifts including capacities and priorities.

    Returns:
    - str: The ID of the chosen shift.
    """

    def calculate_assigned_shift_types(assigned_shifts, shift_type_dict):
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
            if assigned_shift_type in assigned_shift_types:
                assigned_shift_types[assigned_shift_type] += 1
            else:
                assigned_shift_types[assigned_shift_type] = 1
        return assigned_shift_types

    # Get the preferred shift types for the person
    person_shift_types = people_data["people_shift_types_dict"].get(person_id, {})

    # Calculate the number of each shift type already assigned to the person
    assigned_shift_types = calculate_assigned_shift_types(
        assigned_shifts, shifts_data["shift_type_dict"]
    )

    # Filter out shifts exceeding their maximum capacity, unless capacity is unlimited and filter out shifts that exceed the person's maximum capacity for that shift type and filter out shifts that the person is already assigned to
    valid_shifts = {
        shift_id: shifts_data["shift_type_dict"][shift_id]
        for shift_id in schedule
        if (
            len(schedule[shift_id]) < shifts_data["shift_capacity_dict"][shift_id][1]
            or shifts_data["shift_capacity_dict"][shift_id][1] == 0
        )
        and (
            assigned_shift_types.get(shifts_data["shift_type_dict"][shift_id], 0)
            < person_shift_types.get(
                shifts_data["shift_type_dict"][shift_id], [0, 0, 0]
            )[2]
            or person_shift_types.get(
                shifts_data["shift_type_dict"][shift_id], [0, 0, 0]
            )[2]
            == 0
        )
        and person_id not in schedule[shift_id]
    }

    def calculate_individual_shift_score(shift_id):
        """
        Calculate the score for a shift based on different criteria.

        Args:
        - shift_id (str): The ID of the shift to score.

        Returns:
        - int: The calculated score for the shift.
        """
        shift_type = shifts_data["shift_type_dict"][shift_id]
        score = 0

        # Criteria 1: Restriction
        if (
            shifts_data["restrict_shift_type_dict"].get(shift_id)
            and assigned_shift_types.get(shift_type, 0)
            < person_shift_types.get(shift_type, [0, 0, 0])[2]
        ):
            score += 100  # Higher score for restricted shifts

        # Criteria 2: Minimum capacity of person
        if (
            shift_type in person_shift_types
            and assigned_shift_types.get(shift_type, 0)
            < person_shift_types[shift_type][1]
        ):
            score += 5  # Higher score if below minimum capacity of person

        # Criteria 3: Shift priority
        score += shifts_data["shift_priority_dict"].get(shift_id, 0)

        # Criteria 4: Below minimum capacity of shift
        if (
            len(schedule.get(shift_id, []))
            < shifts_data["shift_capacity_dict"][shift_id][0]
        ):
            score += 2  # Higher score if below minimum capacity of shift

        return score

    # Calculate the score for each valid shift
    shift_scores = {
        shift_id: calculate_individual_shift_score(shift_id)
        for shift_id in valid_shifts
    }

    # Sort shifts based on their score
    ranked_shifts = sorted(shift_scores.items(), key=lambda item: item[1], reverse=True)

    # Extract shift IDs and their corresponding scores
    shift_ids = [shift_id for shift_id, score in ranked_shifts]
    scores = [score for shift_id, score in ranked_shifts]

    # Use scores as weights to randomly choose a shift
    chosen_shift = random.choices(shift_ids, weights=scores, k=1)[0]
    return chosen_shift


def is_valid_assignment(
    schedule, new_shift_id, person_id, assigned_shifts_person, people_data, shifts_data
):
    """
    Check if assigning a person to a new shift is valid based on various criteria.

    Args:
    - schedule (dict): The current state of the schedule.
    - new_shift_id (str): The ID of the new shift to assign.
    - person_id (int/float): The ID of the person to assign the shift to.
    - assigned_shifts_person (list): List of shifts already assigned to the person.
    - people_data (dict): Data about people including their preferences and capacities.
    - shifts_data (dict): Data about shifts including capacities and priorities.

    Returns:
    - bool: True if the assignment is valid, False otherwise.
    """

    # Helper function to calculate the number of assigned shift types for a person
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
            if assigned_shift_type in assigned_shift_types:
                assigned_shift_types[assigned_shift_type] += 1
            else:
                assigned_shift_types[assigned_shift_type] = 1
        return assigned_shift_types

    # Calculate the number of each shift type already assigned to the person
    assigned_shift_types = retrieve_shift_types(
        assigned_shifts_person, shifts_data["shift_type_dict"]
    )

    # Get the preferred shift types for the person
    person_shift_types = people_data["people_shift_types_dict"].get(person_id, {})

    # Check if the shift exceeds its maximum capacity (unless capacity is unlimited)
    if (
        len(schedule[new_shift_id])
        > shifts_data["shift_capacity_dict"][new_shift_id][1]
        and shifts_data["shift_capacity_dict"][new_shift_id][1] != 0
    ):
        return False

    # Check if the person exceeds their maximum capacity for this shift type
    if (
        assigned_shift_types.get(shifts_data["shift_type_dict"][new_shift_id], 0)
        > person_shift_types.get(
            shifts_data["shift_type_dict"][new_shift_id], [0, 0, 0]
        )[2]
        and person_shift_types.get(
            shifts_data["shift_type_dict"][new_shift_id], [0, 0, 0]
        )[2]
        != 0
    ):
        return False

    # Check if the shift is restricted and the person is not allowed to work on it
    if not check_shift_restriction(
        person_id,
        people_data["people_shift_types_dict"],
        new_shift_id,
        shifts_data["shift_type_dict"],
        shifts_data["restrict_shift_type_dict"],
    ):
        return False

    # Check if the minimum break requirements are met
    if not check_min_break(assigned_shifts_person, person_id, people_data, shifts_data):
        return False

    # Check if the person is unavailable for the new shift
    if not check_unavailability(
        shifts_data["shift_time_dict"],
        new_shift_id,
        people_data["unavailability_dict"],
        person_id,
    ):
        return False

    if not check_mandatory(assigned_shifts_person, person_id, people_data, shifts_data):
        return False

    # Check if the person should not be scheduled with someone they have a conflict with
    if isEnemy(person_id, schedule[new_shift_id], people_data["preference_dict"]):
        return False

    # If all checks pass, the assignment is valid
    return True


def create_schedule(schedule, people_data, shifts_data):
    """
    Create a schedule by assigning shifts to people based on provided data.

    Args:
    - schedule (dict): The initial empty or partially filled schedule.
    - people_data (dict): Data about people including their preferences and capacities.
    - shifts_data (dict): Data about shifts including capacities and priorities.

    Returns:
    - dict: The final schedule after attempting to assign shifts to all people.
    """

    # List of all people to be assigned shifts
    people = list(people_data["name_dict"].keys())
    attempts = 0
    max_attempts = 100000  # Maximum number of attempts to avoid infinite loops
    assigned_shifts = {}  # Dictionary to track shifts assigned to each person

    while people and attempts < max_attempts:
        person_id = people.pop()

        # Attempt to assign shifts to the current person
        new_schedule, shifts_of_person, success = assign_shifts_person(
            assigned_shifts.get(person_id, []).copy(),
            schedule.copy(),
            person_id,
            people_data,
            shifts_data,
            shifts_data["shift_time_dict"].copy(),
        )

        if success:
            # Update schedule and history if assignment was successful
            schedule = new_schedule
            assigned_shifts[person_id] = shifts_of_person
            attempts = 0  # Reset attempts after a successful assignment
        else:
            # Add person back to the list for another attempt
            people.append(person_id)

            # Remove the person from all shifts they were assigned to in this attempt
            for shift_id in schedule:
                if person_id in schedule[shift_id]:
                    schedule[shift_id].remove(person_id)

            attempts += 1  # Increment attempt counter

    if attempts >= max_attempts:
        print("Failed to assign shifts to all people after", max_attempts, "attempts")
        return None, None

    return schedule, assigned_shifts


def assign_shifts_person(
    assigned_shifts_history,
    schedule,
    person_id,
    people_data,
    shifts_data,
    filtered_shifts,
):
    """
    Recursively assign shifts to a person based on their preferences and capacities.

    Args:
    - assigned_shifts_history (list): List of shifts already assigned to the person.
    - schedule (dict): The current state of the schedule.
    - person_id (int/float): The ID of the person to assign shifts to.
    - people_data (dict): Data about people including their preferences and capacities.
    - shifts_data (dict): Data about shifts including capacities and priorities.
    - filtered_shifts (dict): Shifts filtered by time.

    Returns:
    - tuple: Updated schedule, updated assigned shifts history, and success flag.
    """

    # Get the maximum capacity of shifts for the person
    person_capacity = people_data["person_capacity_dict"].get(
        person_id, (DEFAULT_MIN_AMOUNT_SHIFT, DEFAULT_MAX_AMOUNT_SHIFT)
    )[1]

    # If the person has reached or exceeded their capacity, return success
    if len(assigned_shifts_history) >= person_capacity:
        return schedule, assigned_shifts_history, True

    # Choose a shift for the person to be assigned to
    shift_id = choose_shift(
        schedule,  # Pass the current schedule
        person_id,  # Pass the person ID
        assigned_shifts_history,  # Pass the current shift history for the person
        people_data,  # Pass the people data
        shifts_data,  # Pass the shifts data
    )

    # If no valid shift is found, return failure
    if not shift_id:
        return schedule, assigned_shifts_history, False

        # Temporarily assign the person to the shift
    schedule[shift_id].append(person_id)
    assigned_shifts_history.append(shift_id)

    # Check if the assignment is valid
    if is_valid_assignment(
        schedule,  # Pass the updated schedule
        shift_id,  # Pass the shift ID
        person_id,  # Pass the person ID
        assigned_shifts_history,  # Pass the updated shift history
        people_data,  # Pass the people data
        shifts_data,  # Pass the shifts data
    ):
        # Remove the assigned shift from the filtered shifts
        filtered_shifts.pop(shift_id, None)

        # Recursively assign remaining shifts
        return assign_shifts_person(
            assigned_shifts_history,  # Pass the updated shift history
            schedule,  # Pass the updated schedule
            person_id,  # Pass the person ID
            people_data,  # Pass the people data
            shifts_data,  # Pass the shifts data
            filtered_shifts,  # Pass the updated filtered shifts
        )
    else:
        # If the assignment is not valid, rollback the changes
        schedule[shift_id].remove(person_id)
        assigned_shifts_history.pop()

    return schedule, assigned_shifts_history, False


def generate_initial_solution(shifts_data, people_data):
    """
    Generate an initial solution for the schedule by assigning shifts to people.

    Args:
    - shifts_data (dict): Data about shifts including capacities and priorities.
    - people_data (dict): Data about people including their preferences and capacities.

    Returns:
    - dict: The final schedule after attempting to assign shifts to all people, or None if unsuccessful.
    """

    # get the start time
    st = time.time()

    # Initialize the schedule with empty lists for each shift
    schedule = {shift_id: [] for shift_id in shifts_data["shift_time_dict"]}

    # Create the schedule by assigning shifts to people
    schedule, assigned_shifts = create_schedule(
        schedule,
        people_data,
        shifts_data,
    )

    # Check if a valid schedule was generated
    if schedule:
        print("Solution generated successfully", schedule)
    else:
        print("Failed to generate a valid initial solution...")
    # get the end time
    et = time.time()
    # get the execution time
    elapsed_time = et - st
    print("(Creating init Schedule) Execution time:", elapsed_time, "seconds")
    return schedule, assigned_shifts


def swap_or_move_shift(
    schedule,
    assigned_shifts,
    people_data,
    shifts_data,
):
    person_a_id = get_random_element(assigned_shifts)  # get a random person

    person_a_shift_id = get_random_element(
        assigned_shifts[person_a_id]
    )  # get a random shift of the person

    person_b_id = get_random_element(assigned_shifts)  # get a random person

    person_b_shift_id = get_random_element(
        assigned_shifts[person_b_id]
    )  # get a random shift of the person

    if person_a_shift_id == person_b_shift_id or person_a_id == person_b_id:
        return schedule, assigned_shifts

    shift_a = schedule[person_a_shift_id]
    shift_b = schedule[person_b_shift_id]

    new_schedule = copy.deepcopy(schedule)
    new_assigned_shifts = copy.deepcopy(assigned_shifts)

    shift_capacity_dict = shifts_data["shift_capacity_dict"]

    if len(shift_a) > shift_capacity_dict.get(person_a_shift_id)[0] and (
        len(shift_b) < shift_capacity_dict.get(person_b_shift_id)[0]
        or (
            len(shift_b) < shift_capacity_dict.get(person_b_shift_id)[1]
            and random.random() < 0.66
        )
    ):
        # Temporarily assign the person to the shift
        new_schedule[person_a_shift_id].remove(person_a_id)
        new_schedule[person_b_shift_id].append(person_a_id)
        new_assigned_shifts[person_a_id].remove(person_a_shift_id)
        new_assigned_shifts[person_a_id].append(person_b_shift_id)

        if is_valid_assignment(
            new_schedule.copy(),
            person_b_shift_id,
            person_a_id,
            new_assigned_shifts.copy()[person_a_id],
            people_data,
            shifts_data,
        ):
            return (
                new_schedule,
                new_assigned_shifts,
            )  # The neighbor solution satisfies both hard constraints
        else:
            return None, None

    else:  # Swap people between the shifts if possible

        new_schedule[person_a_shift_id].remove(person_a_id)
        new_schedule[person_b_shift_id].append(person_a_id)
        new_assigned_shifts[person_a_id].remove(person_a_shift_id)
        new_assigned_shifts[person_a_id].append(person_b_shift_id)

        new_schedule[person_b_shift_id].remove(person_b_id)
        new_schedule[person_a_shift_id].append(person_b_id)
        new_assigned_shifts[person_b_id].remove(person_b_shift_id)
        new_assigned_shifts[person_b_id].append(person_a_shift_id)

        if is_valid_assignment(
            new_schedule.copy(),
            person_b_shift_id,
            person_a_id,
            new_assigned_shifts.copy()[person_a_id],
            people_data,
            shifts_data,
        ) and is_valid_assignment(
            new_schedule.copy(),
            person_a_shift_id,
            person_b_id,
            new_assigned_shifts.copy()[person_b_id],
            people_data,
            shifts_data,
        ):
            return (
                new_schedule,
                new_assigned_shifts,
            )  # The neighbor solution satisfies both hard constraints
        else:
            return None, None


def get_neighbor(
    schedule,
    assigned_shifts,
    shifts_data,
    people_data,
    max_attempts=10000,
):
    attempts = 0

    while attempts < max_attempts:
        new_schedule, new_assigned_shifts = swap_or_move_shift(
            schedule.copy(),
            assigned_shifts.copy(),
            people_data,
            shifts_data,
        )
        if new_schedule and new_assigned_shifts:
            return new_schedule, new_assigned_shifts
        else:
            attempts += 1

    # Return the original solution if no valid neighbor is found after max_attempts
    print("No valid neighbor found after", max_attempts, "attempts")
    return None, None


def isEnemy(person, shift, preference_dict):
    if person not in preference_dict:
        return False

    # Create a set of enemies for the person
    enemies = {p[0] for p in preference_dict[person] if p[1] == 1}

    # Check if any person in the shift is an enemy
    return any(other_person in enemies for other_person in shift)


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


def check_mandatory(assigned_shifts_person, person_id, people_data, shifts_data):
    mandatory_periods = people_data["mandatory_dict"].get(person_id, [])
    
    # Set to keep track of mandatory periods that have been satisfied
    satisfied_periods = set()

    for shift_id in assigned_shifts_person:
        shift_start, shift_end = shifts_data["shift_time_dict"].get(shift_id, (None, None))
        if shift_start is None or shift_end is None:
            continue  # Skip if shift times are not found

        for mandatory_start, mandatory_end in mandatory_periods:
            if shift_start >= mandatory_start and shift_end <= mandatory_end:
                satisfied_periods.add((mandatory_start, mandatory_end))
                
    # If all mandatory periods are satisfied, return True
    if len(satisfied_periods) >= len(mandatory_periods):
        return True

    return False


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
