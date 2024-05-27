from functools import partial

from excel_processing import process_excel
from data_transformation import transform_data
from simulated_annealing import run_parallel_simulated_annealing, simulated_annealing
from cost_calculation import (
    EXPERIENCE_FACTOR,
    cost_function,
    individual_cost,
    mixedExperience_cost,
    mixedGender_cost,
)
from utilities import replace_numbers_with_names, createFile

# Parameters for the simulated annealing algorithm
initial_temperature = 1000
cooling_rate = 0.99997
activate_parallelization = False
num_of_parallel_threads = 8
max_iterations_without_improvement = 1000

if __name__ == "__main__":
    people_data, shifts_data = process_excel("SCC_SCHICHTPLAN_FINAL_SV.xlsx")
    people_transformed_data, shifts_transformed_data = transform_data(
        people_data, shifts_data
    )

    shift_time_list = shifts_transformed_data["shift_time_array"]
    name_list = people_transformed_data["name_array"]
    dates_list = shifts_transformed_data["shift_date_array"]
    num_of_shifts = len(dates_list)

    print("Starting simulated annealing")

    if activate_parallelization:
        best_solution, best_cost, init_cost = run_parallel_simulated_annealing(
            num_of_parallel_threads,
            people_transformed_data,
            shifts_transformed_data,
            initial_temperature,
            cooling_rate,
            max_iterations_without_improvement,
            shift_time_list,
            dates_list
        )
    else:
        best_solution, best_cost, init_cost = simulated_annealing(
            people_transformed_data,
            shifts_transformed_data,
            initial_temperature,
            cooling_rate,
            max_iterations_without_improvement,
            shift_time_list,
            dates_list
        )
        
    if best_solution is None:
        print("No valid solution found")
        exit()

    # Check the cost of each person
    total_cost, individual_costs = cost_function(
        best_solution, people_transformed_data, shifts_transformed_data, True
    )

    best_solution_with_names = replace_numbers_with_names(best_solution, name_list)
    print(f"Best solution with names: {best_solution_with_names}")
    print(f"Initial cost: {init_cost}")
    print(f"Best cost: {best_cost}")

    createFile(
        best_solution,
        name_list,
        individual_costs,
        shift_time_list,
        dates_list,
    )
