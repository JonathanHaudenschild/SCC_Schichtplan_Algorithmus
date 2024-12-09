import random
import time
import copy
from logger import logging
from utilities import showInitProgressIndicator
from error_handling import (
    raise_capacity_error,
    raise_invalid_assignment_error,
    raise_schedule_creation_error,
    InvalidAssignmentError,
)

from hard_constraints import is_valid_assignment


DEFAULT_MIN_AMOUNT_SHIFT = 4
DEFAULT_MAX_AMOUNT_SHIFT = 5


def calculate_total_capacities(data, key):
    """Calculate total minimum and maximum capacities for the given data."""
    total_min = sum(capacity[0] for capacity in data[key].values())
    total_max = sum(capacity[1] for capacity in data[key].values())
    return total_min, total_max


def check_shift_type_capacity(people_data, shifts_data):
    """Check individual shift type capacities and log the status."""
    for shift_type, capacity in people_data["total_capacity"].items():
        max_shift_capacity = shifts_data["total_capacity"][shift_type][1]
        min_required_capacity = capacity[0]

        if max_shift_capacity < min_required_capacity:
            raise_capacity_error(
                f"Insufficient capacity for shift type '{shift_type}': "
                f"Maximum capacity available is {max_shift_capacity}, but at least {min_required_capacity} slots are required."
            )

        logging.info(
            f"Shift type '{shift_type}' still has {max_shift_capacity - min_required_capacity} slots available."
        )


def check_total_capacity(people_data, shifts_data):
    """Check total shift and person capacities and log the status."""
    total_min_shift_capacity, total_max_shift_capacity = calculate_total_capacities(
        shifts_data, "total_capacity"
    )
    total_min_person_capacity, total_max_person_capacity = calculate_total_capacities(
        people_data, "person_capacity_dict"
    )

    if total_max_shift_capacity < total_min_person_capacity:
        raise_capacity_error(
            f"Insufficient total shift capacity: "
            f"Maximum shift capacity ({total_max_shift_capacity}) is less than the minimum required person capacity ({total_min_person_capacity})."
        )
    logging.info(
        f"Total shift capacity left: {total_max_shift_capacity - total_min_person_capacity}"
    )

    if total_min_shift_capacity > total_max_person_capacity:
        raise_capacity_error(
            f"Insufficient total shift capacity: "
            f"Minimum shift capacity ({total_min_shift_capacity}) exceeds the maximum person capacity ({total_max_person_capacity})."
        )
    logging.info(
        f"Minimum required shift capacity is satisfied. Surplus person capacity: {total_max_person_capacity - total_min_shift_capacity}"
    )


def generate_initial_solution(shifts_data, people_data):
    """
    Generate an initial solution for the schedule by assigning shifts to people.

    Args:
    - shifts_data (dict): Data about shifts including capacities and priorities.
    - people_data (dict): Data about people including their preferences and capacities.

    Returns:
    - dict: The final schedule after attempting to assign shifts to all people, or None if unsuccessful.
    """
    try:
        # Get the start time
        st = time.time()

        # Initialize the schedule with empty lists for each shift
        schedule = {shift_id: [] for shift_id in shifts_data["shift_time_dict"]}

        # Create the schedule by assigning shifts to people
        schedule, assigned_shifts = create_schedule(
            schedule,
            people_data,
            shifts_data,
        )

        logging.info(
            f"{len(assigned_shifts)} out of {len(people_data['name_dict'])} people have assigned shifts"
        )

        # Check if a valid schedule was generated
        if schedule:
            logging.info(f"Solution generated successfully: {schedule}")
            logging.info(f"Assigned shifts: {assigned_shifts}")
        else:
            logging.error("Failed to generate a valid initial solution...")

        # Get the end time
        et = time.time()
        # Calculate the execution time
        elapsed_time = et - st
        logging.info(f"(Creating init Schedule) Execution time: {elapsed_time} seconds")
        return schedule, assigned_shifts
    except Exception as e:
        logging.error(f"Error in generating initial solution: {e}")
        return None, None


# Helper function to check if the shift's capacity is within limits
def is_within_shift_capacity(shift_id, schedule, shift_capacity_dict):
    current_capacity = len(schedule[shift_id])
    max_capacity = shift_capacity_dict[shift_id][1]
    return current_capacity < max_capacity or max_capacity == 0


# Helper function to check if the person has not exceeded their allowable capacity for the shift type
def is_within_person_capacity(
    shift_id, shift_type_dict, assigned_shift_types, person_shift_types
):
    shift_type = shift_type_dict[shift_id]
    assigned_count = assigned_shift_types.get(shift_type, 0)
    max_allowable = person_shift_types.get(shift_type, [0, 0, 0])[2]
    return assigned_count < max_allowable or max_allowable == 0


# Helper function to check if the person is already assigned to the shift
def is_not_already_assigned(shift_id, schedule, person_id):
    return person_id not in schedule[shift_id]


def choose_shift(
    schedule, person_id, assigned_shifts, people_data, shifts_data, factor=1
):
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

    # Validate inputs
    if person_id not in people_data["people_shift_types_dict"]:
        raise ValueError(f"Person ID {person_id} not found in people data.")

    if not isinstance(assigned_shifts, list):
        raise TypeError("assigned_shifts should be a list.")

    if not isinstance(schedule, dict) or not isinstance(shifts_data, dict):
        raise TypeError("schedule and shifts_data should be dictionaries.")

    # Get the preferred shift types for the person
    person_shift_types = people_data["people_shift_types_dict"].get(person_id, {})

    # Calculate the number of each shift type already assigned to the person
    assigned_shift_types = calculate_assigned_shift_types(
        assigned_shifts, shifts_data["shift_type_dict"]
    )

    # Filter shifts based on the following criteria:
    # 1. Exclude shifts that exceed their maximum capacity, unless the capacity is unlimited.
    # 2. Exclude shifts that surpass the person's maximum allowable capacity for that shift type.
    # 3. Exclude shifts to which the person is already assigned.
    # Filter valid shifts
    valid_shifts = {
        shift_id: shifts_data["shift_type_dict"][shift_id]
        for shift_id in schedule
        if is_within_shift_capacity(
            shift_id, schedule, shifts_data["shift_capacity_dict"]
        )
        and is_within_person_capacity(
            shift_id,
            shifts_data["shift_type_dict"],
            assigned_shift_types,
            person_shift_types,
        )
        and is_not_already_assigned(shift_id, schedule, person_id)
    }

    # Handle case where no valid shifts are found
    if not valid_shifts:
        return None

    def calculate_individual_shift_score(shift_id):
        """
        Calculate the score for a shift based on different criteria.

        Args:
        - shift_id (str): The ID of the shift to score.

        Returns:
        - int: The calculated score for the shift.
        """
        # Extract relevant data once to avoid redundant lookups
        shift_type = shifts_data["shift_type_dict"][shift_id]
        restrict_shift = shifts_data["restrict_shift_type_dict"].get(shift_id, False)
        assigned_count = assigned_shift_types.get(shift_type, 0)
        person_limits = person_shift_types.get(shift_type, [0, 0, 0])
        min_shift_capacity = shifts_data["shift_capacity_dict"][shift_id][0]
        current_shift_capacity = len(schedule.get(shift_id, []))
        shift_priority = shifts_data["shift_priority_dict"].get(shift_id, 0)

        # Define weights for criteria
        weights = {
            "restricted_shift": 100,
            "below_person_min_capacity": 15,
            "shift_priority": 10,
            "below_shift_min_capacity": 15,
        }
        average_weight = sum(weights.values()) / len(weights)
        score = 0

        # Add a random bonus to avoid local optima
        if random.random() < (0.23 + factor * 0.10):
            score += random.randint(1, average_weight * factor)
            return score  # Early return if random bonus is applied

        # Criterion 1: Restriction
        if restrict_shift and assigned_count < person_limits[2]:
            score += weights["restricted_shift"]

        # Criterion 2: Below person's minimum capacity
        if shift_type in person_shift_types and assigned_count < person_limits[1]:
            score += weights["below_person_min_capacity"]

        # Criterion 3: Shift priority
        score += shift_priority * weights["shift_priority"]

        # Criterion 4: Below shift's minimum capacity
        if current_shift_capacity < min_shift_capacity:
            score += weights["below_shift_min_capacity"]

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

    if sum(scores) == 0:
        return random.choice(shift_ids)

    # Use scores as weights to randomly choose a shift
    chosen_shift = random.choices(shift_ids, weights=scores, k=1)[0]
    return chosen_shift


def assign_shifts_person(
    assigned_shifts_history, schedule, person_id, people_data, shifts_data, attempt
):
    """
    Recursively assign shifts to a person based on their preferences and capacities.

    Args:
        assigned_shifts_history (list): List of shifts already assigned to the person.
        schedule (dict): The current state of the schedule.
        person_id (int/float): The ID of the person to assign shifts to.
        people_data (dict): Data about people including their preferences and capacities.
        shifts_data (dict): Data about shifts including capacities and priorities.

    Returns:
        tuple: Updated schedule, updated assigned shifts history.
    """
    # Get the maximum capacity of shifts for the person
    person_capacity = people_data["person_capacity_dict"].get(
        person_id, (DEFAULT_MIN_AMOUNT_SHIFT, DEFAULT_MAX_AMOUNT_SHIFT)
    )[1]

    max_iterations = 20  # Maximum iterations allowed
    assigned_shifts_history.clear()  # Clear previously assigned shifts for retries

    iteration = 1  # Reset iteration counter for each attempt

    # Assign shifts until the person reaches their maximum capacity
    while (
        len(assigned_shifts_history) < person_capacity and iteration <= max_iterations
    ):
        # Choose a shift for the person
        shift_id = choose_shift(
            schedule,
            person_id,
            assigned_shifts_history,
            people_data,
            shifts_data,
            iteration,
        )

        # If no valid shift is found, break and retry
        if not shift_id:
            logging.warning(
                f"No valid shift found for person {person_id} on iteration {iteration} (attempt {attempt})."
            )
            break

        # Temporarily assign the person to the shift
        schedule[shift_id].append(person_id)
        assigned_shifts_history.append(shift_id)

        # Validate the assignment
        if not is_valid_assignment(
            schedule,
            shift_id,
            person_id,
            assigned_shifts_history,
            people_data,
            shifts_data,
        ):
            schedule[shift_id].remove(person_id)
            assigned_shifts_history.remove(shift_id)

        iteration += 1  # Always increment iteration

    if len(assigned_shifts_history) < person_capacity:
        for shift_id in assigned_shifts_history:
            schedule[shift_id].remove(person_id)
        # If both attempts fail, raise an error
        raise_invalid_assignment_error(
            f"Person {person_id} could not be assigned all required shifts after {iteration - 1} iterations. (attempt {attempt}) "
            f"(assigned {len(assigned_shifts_history)}/{person_capacity})."
        )

    # Check if the person was successfully assigned all required shifts
    if len(assigned_shifts_history) >= person_capacity:
        logging.info(
            f"Person {person_id} successfully assigned all {person_capacity} required shifts after {iteration - 1} iterations. (attempt {attempt}) Assigned shifts: {assigned_shifts_history}"
        )
        return schedule, assigned_shifts_history


def create_schedule(schedule, people_data, shifts_data, max_backtracks=200):
    """
    Create a schedule by assigning shifts to people based on provided data.

    Args:
    - schedule (dict): The initial empty or partially filled schedule.
    - people_data (dict): Data about people including their preferences and capacities.
    - shifts_data (dict): Data about shifts including capacities and priorities.

    Returns:
    - dict: The final schedule after attempting to assign shifts to all people.
    - dict: The dictionary tracking assigned shifts for each person.
    """
    people = list(people_data["name_dict"].keys())
    random.shuffle(people)
    no_of_people = len(people)
    change_stack = []  # Stack to track incremental changes
    assigned_shifts = {}  # Dictionary to track shifts assigned to each person

    backtrack_depth = {}  # Tracks the depth of backtracking for each person

    # Perform initial capacity checks
    check_shift_type_capacity(people_data, shifts_data)
    check_total_capacity(people_data, shifts_data)

    start_time = time.time()
    attempts = 20  # Allow two attempts to assign shifts
    prev_iteration_time = start_time

    while people:
        prev_iteration_time = showInitProgressIndicator(
            len(people), no_of_people, start_time, prev_iteration_time
        )

        # Select the next person to assign shifts
        person_id = people.pop()

        success = False
        shift_assignments = []

        for attempt in range(attempts):
            try:
                # Attempt to assign shifts to the current person
                schedule, shift_assignments = assign_shifts_person(
                    assigned_shifts.get(person_id, []).copy(),
                    schedule,
                    person_id,
                    people_data,
                    shifts_data,
                    attempt,
                )
                success = True
                break  # Break if successful

            except InvalidAssignmentError as e:
                continue  # Retry if assignment is invalid

        if success:
            # Save the current state before updating
            change_stack.append((person_id, shift_assignments))
            assigned_shifts[person_id] = shift_assignments

            # Reset backtrack depth for the person on success
            backtrack_depth[person_id] = 0
        else:
               # Retry logic
            current_depth = backtrack_depth.get(person_id, 0) + 1

            if len(change_stack) >= current_depth:
                backtrack_depth[person_id] = current_depth  # Update backtrack depth

                
                # Undo the last `current_depth` assignments
                for _ in range(current_depth):
                    last_person, last_assignments = change_stack.pop()
                    for shift_id in last_assignments:
                        schedule[shift_id].remove(last_person)
                    del assigned_shifts[last_person]
                    people.append(last_person)  # Re-add last person to the queue
             
                # Retry the current person
                people.append(person_id)
                logging.warning(
                    f"Backtracked {current_depth} steps to {last_person} to resolve conflict for person {person_id}."
                )
            else:
                schedule = {shift_id: [] for shift_id in schedule}
                assigned_shifts = {}
                people = list(people_data["name_dict"].keys())
                random.shuffle(people)
                backtrack_depth.clear()
                change_stack.clear()
                logging.error(
                    f"Exceeded maximum backtracks. Resetting schedule and assigned shifts."
                )

    # If people list is empty, scheduling is complete
    if not people:
        logging.info("Schedule created successfully.")
    else:
        raise_schedule_creation_error("Failed to assign shifts to all people.")

    return schedule, assigned_shifts
