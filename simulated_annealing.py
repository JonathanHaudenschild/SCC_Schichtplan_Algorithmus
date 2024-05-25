import random
import math
import time
import statistics
from functools import partial
import concurrent.futures

from cost_calculation import cost_function, individual_cost
from utilities import showProgressIndicator, convert_to_solution_matrix

from hard_constraints import get_neighbor, generate_initial_solution


# Parameters for the simulated annealing algorithm
initial_temperature = 1000
cooling_rate = 0.99997
activate_parallelization = True
num_of_parallel_threads = 8


def run_parallel_simulated_annealing(
    num_instances, people_data, shifts_data, *args, **kwargs
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
            100000,
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

    name_list = people_data["name_array"]
    person_capacity_array = people_data["person_capacity_array"]
    sv_capacity_array = people_data["sv_capacity_array"]
    sv_experience_array = people_data["sv_experience_array"]
    unavailability_matrix = people_data["unavailability_matrix"]
    minimum_array = people_data["minimum_array"]
    shift_capacity_matrix = shifts_data["shift_capacity_matrix"]
    shift_sv_capacity_matrix = shifts_data["shift_sv_capacity_matrix"]
    preference_matrix = people_data["preference_matrix"]
    

    num_of_shifts = len(shifts_data["shift_date_array"])
    num_people = len(name_list)
    current_solution = generate_initial_solution(
        num_of_shifts,
        num_people,
        shift_capacity_matrix,
        shift_sv_capacity_matrix,
        person_capacity_array,
        sv_capacity_array,
    )
    current_cost = cost_function(current_solution, people_data, shifts_data)
    individual_costs, rank_costs, pref_costs, off_day_costs = individual_cost(
        current_solution, people_data, shifts_data
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
        new_solution = get_neighbor(
            current_solution,
            unavailability_matrix,
            shift_capacity_matrix,
            shift_sv_capacity_matrix,
            minimum_array,
            preference_matrix,
            sv_experience_array
        )
        new_cost = cost_function(new_solution, people_data, shifts_data)
        new_individual_costs, rank_costs, pref_costs, off_day_costs = individual_cost(
            new_solution, people_data, shifts_data
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
            current_solution = new_solution
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

    return current_solution, current_cost, init_cost




def acceptance_probability(
    old_cost, new_cost, temperature, deviation_old, deviation_new
):
    if new_cost < old_cost or deviation_new < deviation_old:
        return 1
    else:
        return math.exp(-(abs(new_cost - old_cost) / temperature))
