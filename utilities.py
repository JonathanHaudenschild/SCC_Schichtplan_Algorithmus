import time


def replace_numbers_with_names(solution, index_name_list):
    name_solution = []
    for shift in solution:
        name_shift = {}
        for shift_type, shift_group in shift.items():
            name_group = set()
            for number in shift_group:
                name = next(name for index, name in index_name_list if index == number)
                name_group.add(name)
            name_shift[shift_type] = name_group
        name_solution.append(name_shift)
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
        end="\r",
    )

