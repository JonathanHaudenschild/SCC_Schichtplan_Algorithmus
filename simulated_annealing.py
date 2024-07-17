import random
import math
import time
import statistics
from functools import partial
import concurrent.futures
from excel_processing import process_excel, create_file, load_excel_and_create_solution

from cost_calculation import cost_function, individual_cost
from utilities import showProgressIndicator

from hard_constraints import get_neighbor, generate_initial_solution



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
        for result in executor.map(annealing_function, seeds):
            best_solutions.append(result)

    best_solutions.sort(key=lambda x: x[1])
    return best_solutions[0][0], best_solutions[0][1], best_solutions[0][2]


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

    current_schedule, current_assigned_shifts = generate_initial_solution(shifts_data, people_data)
    # Check the cost of each person
    total_cost, individual_costs, cost_details = cost_function(
        current_schedule, current_assigned_shifts, people_data, shifts_data, True
    )
    create_file(
        current_schedule,
        individual_costs,
        people_data,
        shifts_data,
        cost_details,
    )
    

    current_cost, individual_costs, cost_details = cost_function(
        current_schedule, current_assigned_shifts, people_data, shifts_data
    )
    deviation_individual_cost = statistics.stdev(individual_costs.values())
    


    init_cost = current_cost
    temperature = initial_temperature
    iterations_without_improvement = 0

    total_iterations = math.ceil(
        math.log(1 / initial_temperature) / math.log(cooling_rate)
    )
    start_time = time.time()
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
        new_cost, new_individual_costs, cost_details  = cost_function(
            new_schedule, new_assigned_shifts,  people_data, shifts_data
        )
        new_deviation_individual_cost = statistics.stdev(new_individual_costs.values())

        if (
            acceptance_probability(
                current_cost,
                new_cost,
                temperature,
                deviation_individual_cost,
                new_deviation_individual_cost,
            )
            > random.random()
        ):
            current_solution = new_schedule
            current_cost = new_cost
            deviation_individual_cost = new_deviation_individual_cost
            iterations_without_improvement = 0
        else:
            iterations_without_improvement += 1

        temperature *= cooling_rate
        current_iteration += 1
        if current_iteration % 333 == 0:
            showProgressIndicator(
                current_iteration, total_iterations, start_time, new_cost, init_cost
            )

        if current_iteration % 50000 == 0:
            cost_function(current_solution, people_data, shifts_data, True)
    return current_solution, current_cost, init_cost


def acceptance_probability(
    old_cost, new_cost, temperature, deviation_old, deviation_new
):
    if new_cost < old_cost or deviation_new < deviation_old:
        return 1
    else:
        return math.exp(-(abs(new_cost - old_cost) / temperature))
