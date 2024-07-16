from excel_processing import process_excel, create_file, load_excel_and_create_solution
from data_transformation import transform_people_data, transform_shifts_data
from simulated_annealing import run_parallel_simulated_annealing, simulated_annealing
from cost_calculation import (
    cost_function,
)
from utilities import replace_numbers_with_names

# Parameters for the simulated annealing algorithm
initial_temperature = 1000
cooling_rate = 0.9999
activate_parallelization = False
num_of_parallel_threads = 14
max_iterations_without_improvement = 1000
excel_file_path = "SCC_SCHICHTPLAN_FINAL.xlsx"
input_solution_path = "SCC_SCHICHTPLAN_2024_B.xlsx"


def run_simulation():
    people_data, shifts_data = process_excel(excel_file_path)

    # print ("Shifts data: ", shifts_data)
    shifts_transformed_data = transform_shifts_data(shifts_data)
    people_transformed_data = transform_people_data(people_data)
    
    # print("Shifts shifts_transformed_data: ", shifts_transformed_data)

    print("People people_transformed_data: ", people_transformed_data)
    # return

    # shift_time_list = shifts_transformed_data["shift_time_array"]
    # name_list = people_transformed_data["name_array"]
    # dates_list = shifts_transformed_data["shift_date_array"]

    print("Starting simulated annealing")

    if activate_parallelization:
        best_solution, best_cost, init_cost = run_parallel_simulated_annealing(
            num_of_parallel_threads,
            people_transformed_data,
            shifts_transformed_data,
            initial_temperature,
            cooling_rate,
            max_iterations_without_improvement,
        )
    else:
        best_solution, best_cost, init_cost = simulated_annealing(
            people_transformed_data,
            shifts_transformed_data,
            initial_temperature,
            cooling_rate,
            max_iterations_without_improvement,
        )

    if best_solution is None:
        print("No valid solution found")
        exit()

    # Check the cost of each person
    total_cost, individual_costs, cost_details = cost_function(
        best_solution, people_transformed_data, shifts_transformed_data, True
    )
    name_list = people_transformed_data["name_dict"]
    best_solution_with_names = replace_numbers_with_names(best_solution, name_list)
    print(f"Best solution with names: {best_solution_with_names}")
    print(f"Initial cost: {init_cost}")
    print(f"Best cost: {best_cost}")

    create_file(
        best_solution,
        individual_costs,
        people_transformed_data,
        shifts_transformed_data,
        cost_details,
    )


def calculate_cost_from_excel():
    people_data, shifts_data = process_excel(excel_file_path)
    people_transformed_data, shifts_transformed_data = transform_data(
        people_data, shifts_data
    )

    input_path = input_solution_path
    dates_list = shifts_transformed_data["shift_date_array"]

    name_list = people_transformed_data["name_dict"]
    shift_types = [0, 1]
    solution = load_excel_and_create_solution(
        input_path, dates_list, name_list, shift_types
    )
    cost_function(solution, people_transformed_data, shifts_transformed_data, True)


if __name__ == "__main__":

    # for i in range(7):
    run_simulation()
