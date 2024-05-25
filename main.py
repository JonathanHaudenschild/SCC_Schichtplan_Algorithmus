from functools import partial

from excel_processing import process_excel
from data_transformation import transform_data
from simulated_annealing import run_parallel_simulated_annealing, simulated_annealing
from cost_calculation import (
    EXPERIENCE_FACTOR,
    check_person_costs,
    cost_function,
    individual_cost,
    mixedExperience_cost,
    mixedGender_cost,
)
from utilities import replace_numbers_with_names, createFile, split_shift_data

# Parameters for the simulated annealing algorithm
initial_temperature = 1000
cooling_rate = 0.99997
activate_parallelization = True
num_of_parallel_threads = 6

if __name__ == "__main__":
    people_data, shifts_data = process_excel("SCC_SCHICHTPLAN_FINAL.xlsx")
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
            num_of_parallel_threads, people_transformed_data, shifts_transformed_data
        )
    else:
        best_solution, best_cost, init_cost = simulated_annealing(
            people_transformed_data,
            shifts_transformed_data,
            initial_temperature,
            cooling_rate,
            max_iterations_without_improvement=100000,
        )

    # Check the cost of each person
    individual_costs = check_person_costs(
        best_solution, people_transformed_data, shifts_transformed_data
    )

    normal_solution, sv_solution = split_shift_data(best_solution)
    # Calculate mixed experience and gender costs
    exp_cost = mixedExperience_cost(
        normal_solution,
        people_transformed_data["experience_array"],
        num_of_shifts,
        EXPERIENCE_FACTOR,
    )
    gender_cost = mixedGender_cost(
        normal_solution, people_transformed_data["gender_array"], num_of_shifts, 1
    )

    sv_exp_cost = mixedExperience_cost(
        sv_solution,
        people_transformed_data["sv_experience_array"],
        num_of_shifts,
        10,
    )
    sv_gender_cost = mixedGender_cost(
        sv_solution, people_transformed_data["gender_array"], num_of_shifts, 10
    )

    print(
        f"Experience cost: {exp_cost}",
        f"Genders cost: {gender_cost}",
        f"SV Experience cost: {sv_exp_cost}",
        f"SV gender cost: {sv_gender_cost}",
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
