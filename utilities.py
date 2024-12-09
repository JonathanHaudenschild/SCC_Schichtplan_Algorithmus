import time


def replace_numbers_with_names(schedule, name_dict):
    name_solution = {shift: [] for shift in schedule}
    for shift in schedule:
        name_group = set()
        for number in schedule.get(shift, []):
            name = name_dict.get(number, None)
            if name is not None:
                name_group.add(name)
        name_solution[shift] = name_group
    return name_solution


def showProgressIndicator(
    current_iteration, total_iterations, start_time, new_cost, init_cost
):
    progress = current_iteration / total_iterations
    elapsed_time = time.time() - start_time
    remaining_time = (
        (elapsed_time / (progress - elapsed_time))
        if (progress - elapsed_time) != 0
        else 0
    )

    hours, remainder = divmod(remaining_time, 3600)
    minutes, seconds = divmod(remainder, 60)

    print(
        f"Progress: {progress * 100:.2f}% | Estimated time remaining: {hours:.0f}h {minutes:.0f}m {seconds:.0f}s | Cost Improvement: {round(((init_cost - new_cost) / init_cost) * 100)}%  | Current Cost: {new_cost:.1f}",
        flush=True,
        end="\r",
        # Ensures output is flushed immediately
    )


def showInitProgressIndicator(
    current_iteration, total_iterations, start_time, prev_iteration_time=None
):
    """
    Displays progress and estimated remaining time.

    Args:
        current_iteration (int): Current iteration number.
        total_iterations (int): Total number of iterations.
        start_time (float): The start time of the process.
        prev_iteration_time (float): Time taken for the previous iteration.
    """
    # Calculate overall progress
    progress = 1 - (current_iteration / total_iterations)
    elapsed_time = time.time() - start_time

    # Estimate the remaining time considering elapsed and progress
    time_per_iteration = (
        elapsed_time / current_iteration if current_iteration > 0 else 0
    )
    remaining_time = time_per_iteration * (total_iterations - current_iteration)

    # Time passed during the current iteration
    if prev_iteration_time is not None:
        time_diff = time.time() - prev_iteration_time
    else:
        time_diff = elapsed_time / current_iteration if current_iteration > 0 else 0

    # Convert remaining time to hours, minutes, and seconds
    hours, remainder = divmod(remaining_time, 3600)
    minutes, seconds = divmod(remainder, 60)

    # Print the progress and time estimate
    print(
        f"Progress: {progress * 100:.2f}% | "
        f"Estimated time remaining: {hours:.0f}h {minutes:.0f}m {seconds:.0f}s | "
        f"Current Iteration: {current_iteration} | "
        f"Time for this iteration: {time_diff:.2f}s",
        flush=True,
        end="\r",  # Ensures the output is flushed immediately
    )

