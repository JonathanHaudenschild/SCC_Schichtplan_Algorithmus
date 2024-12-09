import random
import math
import time
import statistics
from functools import partial
import concurrent.futures
from excel_processing import create_file, load_excel_and_create_solution

from cost_calculation import cost_function, individual_cost
from utilities import showProgressIndicator

from hard_constraints import get_neighbor

from logger import logging

from create_init import generate_initial_solution


def run_parallel_simulated_annealing(
    num_instances,
    people_data,
    shifts_data,
    initial_temperature,
    cooling_rate,
    max_iterations_without_improvement,
    *args,
    **kwargs,
):
    best_solutions = []
    with concurrent.futures.ProcessPoolExecutor() as executor:
        seeds = [random.randint(0, 1000000) for _ in range(num_instances)]
        annealing_function = partial(
            simulated_annealing,
            people_data,
            shifts_data,
            initial_temperature,
            cooling_rate,
            max_iterations_without_improvement,
        )

        futures = {executor.submit(annealing_function, seed): seed for seed in seeds}

        for future in concurrent.futures.as_completed(futures):
            seed = futures[future]
            try:
                result = future.result()
                best_solutions.append(result)
            except Exception as e:
                print(f"An error occurred with seed {seed}: {e}")

    if best_solutions:
        best_solutions.sort(key=lambda x: x[2])
        return (
            best_solutions[0][0],
            best_solutions[0][1],
            best_solutions[0][2],
            best_solutions[0][3],
        )
    else:
        print("No valid solutions found.")
        return None, None, None, None


def simulated_annealing(
    people_data,
    shifts_data,
    initial_temperature,
    cooling_rate,
    max_iterations_without_improvement,
    seed=None,
):
    if seed is not None:
        random.seed(seed)

    current_schedule, current_assigned_shifts = generate_initial_solution(
        shifts_data, people_data
    )


    current_cost, total_cost_breakdown, cost_details = cost_function(
        current_schedule, current_assigned_shifts, people_data, shifts_data
    )


    create_file(
        current_schedule,
        total_cost_breakdown,
        people_data,
        shifts_data,
        cost_details,
    )
    
    init_cost = current_cost
    temperature = initial_temperature
    iterations_without_improvement = 0

    total_iterations = math.ceil(
        math.log(1 / initial_temperature) / math.log(cooling_rate)
    )
    start_time = time.time()
    last_progress_time = start_time
    current_iteration = 0
    
    while (
        temperature > 1
        and iterations_without_improvement < max_iterations_without_improvement
    ):

        new_schedule, new_assigned_shifts = get_neighbor(
            current_schedule,
            current_assigned_shifts,
            shifts_data,
            people_data,
        )
        new_cost, new_cost_breakdown, cost_details = cost_function(
            new_schedule, new_assigned_shifts, people_data, shifts_data
        )

        if (
            acceptance_probability(
                current_cost,
                new_cost,
                temperature,
            )
            > random.random()
        ):
            current_schedule = new_schedule
            current_assigned_shifts = new_assigned_shifts
            current_cost = new_cost
            iterations_without_improvement = 0
        else:
            iterations_without_improvement += 1

        temperature *= cooling_rate
        current_iteration += 1
        # Check if 5 seconds have passed since the last progress indicator
        current_time = time.time()
        if current_time - last_progress_time >= 5:
            showProgressIndicator(
                current_iteration, total_iterations, start_time, new_cost, init_cost
            )
            
        if current_time - last_progress_time >= 30:
            logging.info(
                f"Progress: {current_iteration / total_iterations * 100:.2f}% | Current Cost: {new_cost:.1f}"
            )
        

    return current_schedule, current_assigned_shifts, current_cost, init_cost


def acceptance_probability(old_cost, new_cost, temperature):
    if new_cost < old_cost:
        return 1
    else:
        return math.exp(-(abs(new_cost - old_cost) / temperature))
