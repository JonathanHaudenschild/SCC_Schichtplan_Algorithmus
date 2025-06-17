import random
import time
import copy
import numpy as np
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
        if shift_type not in shifts_data["total_capacity"]:
            continue
        
        max_shift_capacity = shifts_data["total_capacity"][shift_type][1]
        min_required_capacity = capacity[1]

        if max_shift_capacity < min_required_capacity and max_shift_capacity != 0:
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
        person_limits = person_shift_types.get(shift_type)
        min_shift_capacity = shifts_data["shift_capacity_dict"][shift_id][0]
        max_shift_capacity = shifts_data["shift_capacity_dict"][shift_id][1]
        current_shift_capacity = len(schedule.get(shift_id, []))
        shift_priority = shifts_data["shift_priority_dict"].get(shift_id, 0)

        # Define weights for criteria
        weights = {
            "restricted_shift": 1,
            "below_person_min_capacity": 0,
            "shift_priority": 0,
            "below_shift_min_capacity": 0
        }
        average_weight = sum(weights.values()) / len(weights)
        score = 0

        # Add a random bonus to avoid local optima
        # if  random.uniform(0, 5) < 1:  # Randomly apply a bonus
        #     score += random.uniform(0, 5) * average_weight
        #     return score  # Early return if random bonus is applied

        # Criterion 1: Restriction
        # 20% chance to apply the restricted shift bonus
        if person_limits is not None and restrict_shift and random.randint(1, 4) == 1 and assigned_count < person_limits[1] and current_shift_capacity < max_shift_capacity and max_shift_capacity > 0:
            score += weights["restricted_shift"] 

        # Criterion 2: Below person's minimum capacity
        if person_limits is not None and assigned_count < person_limits[1] and person_limits[1] > 0:
            score += weights["below_person_min_capacity"]  * random.uniform(0, 5)

        # Criterion 3: Shift priority
        score += shift_priority * weights["shift_priority"]

        # Criterion 4: Below shift's minimum capacity
        if current_shift_capacity < min_shift_capacity:
            score += weights["below_shift_min_capacity"] * (min_shift_capacity - current_shift_capacity) * random.uniform(0, 5)

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

    max_iterations = 50  # Maximum iterations allowed
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

def sort_people_by_shift_type_capacity(people, people_data, shifts_data):
    """
    Sort people by their shift type capacity.

    Args:
    - people_data (dict): Data about people including their preferences and capacities.
    - shifts_data (dict): Data about shifts including capacities and priorities.

    Returns:
    - list: Sorted list of people based on their shift type capacity.
    """
    sorted_people = sorted(
        people,
        key=lambda person_id: 
            sum(
                values[1] for values in people_data["people_shift_types_dict"][person_id].values() if values[1] > 0
            ),
        reverse=True
    )
    return sorted_people


def raise_schedule_creation_error(message):
    logging.error(message)
    raise Exception(message)

# --- Main Function ---
def create_schedule(
    initial_schedule_template: dict,
    people_data: dict, # This is your main people_data dictionary
    shifts_data: dict, # This is your main shifts_data dictionary
    max_attempts_per_person: int = 10,
    max_total_backtracks: int = 200,
    max_full_resets: int = 5
):
    """
    Create a schedule by assigning shifts to people based on provided data.

    Args:
    - initial_schedule_template (dict): An empty schedule template (shift_id: []).
    - people_data (dict): Your main data structure for people, expected to contain "name_dict"
                          among other keys for preferences, capacities etc.
    - shifts_data (dict): Your main data structure for shifts.
    - max_attempts_per_person (int): Attempts for one person before backtracking.
    - max_total_backtracks (int): Max backtrack operations before a full reset.
    - max_full_resets (int): Max full resets before giving up.

    Returns:
    - dict: The final schedule.
    - dict: Dictionary tracking assigned shifts for each person.
    """
    
    current_schedule = {k: list(v) for k, v in initial_schedule_template.items()}
    all_shift_ids_for_reset = list(initial_schedule_template.keys())

    if "name_dict" not in people_data:
        raise ValueError("The 'people_data' dictionary must contain a 'name_dict' key with person_ids.")
    
    # Get the initial list of person_ids
    base_person_id_list = list(people_data["name_dict"].keys())
    if not base_person_id_list:
        logging.warning("No people found in people_data['name_dict']. Returning empty schedule.")
        return current_schedule, {}

    # Initial checks (passing the full data structures)
    # check_shift_type_capacity(people_data, shifts_data)
    # TODO Handle when shift_type_capacity is not defined
    # check_total_capacity(people_data, shifts_data)

    # Prepare the initial processing queue
    # A copy of the base list to be shuffled and sorted
    initial_people_to_process = list(base_person_id_list)
    random.shuffle(initial_people_to_process)
    # sort_people_by_shift_type_capacity receives the list of IDs, and full data dicts
    processing_queue = sort_people_by_shift_type_capacity(initial_people_to_process, people_data, shifts_data)
    
    num_total_people = len(processing_queue) 
    
    change_stack = []  # Stores (person_id, list_of_shifts_assigned_to_them_in_that_step)
    assigned_shifts_per_person = {}

    num_actual_backtrack_ops = 0
    current_backtrack_undo_depth = 1
    num_full_resets_done = 0

    start_time = time.time()
    prev_iteration_time = start_time
    
    logging.info(f"Starting schedule creation for {num_total_people} people.")

    while processing_queue: # Continues as long as there are people to process
        # Progress indicator uses len(processing_queue) and num_total_people
        prev_iteration_time = showInitProgressIndicator(
            len(processing_queue), num_total_people, start_time, prev_iteration_time
        )

        person_id_to_schedule = processing_queue.pop(0) # Get person from front of queue

        successful_assignment_for_person = False
        shifts_assigned_this_round = [] # Shifts confirmed for this person in this round

        for attempt_num in range(max_attempts_per_person):
            try:
                # Get shifts already assigned to this person for incremental assignment
                shifts_already_with_person = assigned_shifts_per_person.get(person_id_to_schedule, [])
                
                # Create a copy of the current_schedule for assign_shifts_person to work on,
                # to avoid partial updates if it fails.
                schedule_copy_for_attempt = {k: list(v) for k, v in current_schedule.items()}

                updated_schedule_state, shifts_assigned_this_round = assign_shifts_person(
                    list(shifts_already_with_person), # Pass a copy of current assignments
                    schedule_copy_for_attempt,    # Pass the schedule copy
                    person_id_to_schedule,
                    people_data,      # Pass the full people_data
                    shifts_data,      # Pass the full shifts_data
                    attempt_num,
                )
                # If assign_shifts_person succeeds:
                current_schedule = updated_schedule_state # Commit the changes from the copy
                successful_assignment_for_person = True
                break 

            except InvalidAssignmentError as e:
                logging.debug(f"Attempt {attempt_num+1}/{max_attempts_per_person} for {person_id_to_schedule} failed: {e}")
                if attempt_num == max_attempts_per_person - 1:
                    logging.warning(
                        f"All {max_attempts_per_person} assignment attempts failed for {person_id_to_schedule}."
                    )
                # Continue to next attempt or fail out of loop

        if successful_assignment_for_person:
            # Record the successful state
            # The change_stack should store what was decided for this person in this step
            change_stack.append((person_id_to_schedule, list(shifts_assigned_this_round)))
            assigned_shifts_per_person[person_id_to_schedule] = list(shifts_assigned_this_round)

            current_backtrack_undo_depth = 1 # Reset progressive backtrack on success
            logging.debug(f"Successfully processed {person_id_to_schedule}. Assigned: {shifts_assigned_this_round}. Resetting backtrack_undo_depth to 1.")
        
        else: # Failed to assign to person_id_to_schedule after all attempts
            num_actual_backtrack_ops += 1
            logging.warning(
                f"Failed assignment for {person_id_to_schedule}. Backtrack op #{num_actual_backtrack_ops}. "
                f"Will try to undo up to {current_backtrack_undo_depth} assignments."
            )

            if num_actual_backtrack_ops > max_total_backtracks or not change_stack:
                if not change_stack and num_full_resets_done <= max_full_resets : # Cannot backtrack if stack is empty
                     logging.warning("Change stack empty, cannot backtrack normally. Attempting full reset.")
                
                num_full_resets_done += 1
                if num_full_resets_done > max_full_resets:
                    raise_schedule_creation_error(
                        f"Exceeded maximum full resets ({max_full_resets}). Cannot create schedule."
                    )
                
                logging.error(
                    f"Exceeded max_total_backtracks or stack empty. Full schedule reset #{num_full_resets_done}."
                )
                # FULL RESET
                current_schedule = {shift_id: [] for shift_id in all_shift_ids_for_reset}
                assigned_shifts_per_person.clear()
                change_stack.clear()
                
                people_for_reset = list(base_person_id_list) # Get fresh list of all people
                random.shuffle(people_for_reset)
                processing_queue = sort_people_by_shift_type_capacity(people_for_reset, people_data, shifts_data)
                num_total_people = len(processing_queue) # Update for progress indicator
                
                num_actual_backtrack_ops = 0 # Reset for this new attempt
                current_backtrack_undo_depth = 1
                # start_time = time.time() # Optionally reset timer for this new full attempt
                prev_iteration_time = time.time() # Reset iteration timer
                logging.info("Schedule fully reset. Restarting assignment process.")
                # Re-add the person who just failed to the new queue so they are tried again
                if person_id_to_schedule not in processing_queue: # Should be there from sort
                    processing_queue.append(person_id_to_schedule) # Ensure they are there
                    random.shuffle(processing_queue) # Re-shuffle if adding manually

                continue # Restart the while loop

            # Actual backtracking if not a full reset
            actual_steps_to_undo = min(current_backtrack_undo_depth, len(change_stack))
            logging.info(f"Backtracking: Undoing {actual_steps_to_undo} assignment steps.")

            people_to_re_process_after_undo = []
            for _ in range(actual_steps_to_undo):
                if not change_stack: break 
                
                last_person_id, shifts_they_had = change_stack.pop()
                
                # Undo their assignments in the main schedule
                for shift_id_to_clear in shifts_they_had:
                    if shift_id_to_clear in current_schedule and last_person_id in current_schedule[shift_id_to_clear]:
                        current_schedule[shift_id_to_clear].remove(last_person_id)
                
                if last_person_id in assigned_shifts_per_person:
                    del assigned_shifts_per_person[last_person_id]
                
                people_to_re_process_after_undo.append(last_person_id)
                logging.debug(f"Undid assignments for {last_person_id}: {shifts_they_had}")

            # Add the current failing person to be re-processed
            # processing_queue.insert(0, person_id_to_schedule) # Try failing person first
            
            # Add all undone people and the failing person to the front of the queue
            # Order can matter: failing person first, then those whose assignments were undone
            re_add_to_queue = [person_id_to_schedule] + list(reversed(people_to_re_process_after_undo))
            # Ensure no duplicates if person_id_to_schedule was among people_to_re_process_after_undo
            # (should not happen if logic is correct as person_id_to_schedule failed, so not on stack top)
            
            current_queue_set = set(processing_queue)
            new_front_queue = []
            for p_id in re_add_to_queue:
                if p_id not in current_queue_set and p_id not in new_front_queue:
                    new_front_queue.append(p_id)
            
            processing_queue = new_front_queue + processing_queue
            
            # Re-sort potentially, or just rely on the order.
            # processing_queue = sort_people_by_shift_type_capacity(processing_queue, people_data, shifts_data) # Optional re-sort

            current_backtrack_undo_depth += 1 # Increase for next potential backtrack
            logging.info(f"Next backtrack (if needed before a success) will attempt to undo {current_backtrack_undo_depth} assignments.")
            
    # Loop finished
    if not processing_queue: # If queue is empty, all people were processed
        logging.info(f"Schedule created successfully in {time.time() - start_time:.2f} seconds.")
        logging.info(f"Total backtrack operations (undo steps): {num_actual_backtrack_ops}")
        logging.info(f"Total full resets: {num_full_resets_done}")
    else: # Should be caught by max_full_resets or other logic
        raise_schedule_creation_error(
             f"Failed to assign shifts to all people. {len(processing_queue)} people remaining in queue."
        )

    return current_schedule, assigned_shifts_per_person