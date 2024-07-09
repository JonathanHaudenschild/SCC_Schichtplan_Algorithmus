
from excel_processing import process_excel, createFile, load_excel_and_create_solution
from data_transformation import transform_data
from simulated_annealing import run_parallel_simulated_annealing, simulated_annealing
from cost_calculation import (
    cost_function,
)
from utilities import replace_numbers_with_names

# Parameters for the simulated annealing algorithm
initial_temperature = 1000
cooling_rate = 0.999997
activate_parallelization = True
num_of_parallel_threads = 14
max_iterations_without_improvement = 1000
excel_file_path = "SCC_SCHICHTPLAN_FINAL.xlsx"
input_solution_path = "SCC_SCHICHTPLAN_2024_B.xlsx"


def run_simulation():
    people_data, shifts_data = process_excel(excel_file_path )
    people_transformed_data, shifts_transformed_data = transform_data(
        people_data, shifts_data
    )

    shift_time_list = shifts_transformed_data["shift_time_array"]
    name_list = people_transformed_data["name_array"]
    dates_list = shifts_transformed_data["shift_date_array"]

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
            dates_list,
        )
    else:
        best_solution, best_cost, init_cost = simulated_annealing(
            people_transformed_data,
            shifts_transformed_data,
            initial_temperature,
            cooling_rate,
            max_iterations_without_improvement,
            shift_time_list,
            dates_list,
        )

    if best_solution is None:
        print("No valid solution found")
        exit()

    # Check the cost of each person
    total_cost, individual_costs, cost_details = cost_function(
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
        cost_details,
    )


def calculate_cost_from_excel():
    people_data, shifts_data = process_excel(excel_file_path )
    people_transformed_data, shifts_transformed_data = transform_data(
        people_data, shifts_data
    )
    
    input_path = input_solution_path
    dates_list = shifts_transformed_data["shift_date_array"]

    name_list = people_transformed_data["name_array"]
    shift_types = [0, 1] 
    solution = load_excel_and_create_solution(input_path, dates_list, name_list, shift_types)
    cost_function(solution, people_transformed_data, shifts_transformed_data, True)


if __name__ == "__main__":
    
    for i in range(7):
        run_simulation()