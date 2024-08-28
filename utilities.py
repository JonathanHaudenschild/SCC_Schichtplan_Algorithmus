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
    remaining_time = elapsed_time / progress - elapsed_time

    hours, remainder = divmod(remaining_time, 3600)
    minutes, seconds = divmod(remainder, 60)

    print(
        f"Progress: {progress * 100:.2f}% | Estimated time remaining: {hours:.0f}h {minutes:.0f}m {seconds:.0f}s | Cost Improvement: {round(((init_cost - new_cost) / init_cost) * 100)}%  | Current Cost: {new_cost:.1f}",
        flush=True,  # Ensures output is flushed immediately
    )
