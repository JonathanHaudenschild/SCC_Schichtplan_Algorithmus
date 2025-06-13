from excel_processing import process_people_data, process_shifts_data, create_file, load_excel_and_create_solution
from data_transformation import transform_people_data, transform_shifts_data
from simulated_annealing import run_parallel_simulated_annealing, simulated_annealing
from cost_calculation import (
    cost_function,
)
from utilities import replace_numbers_with_names
from sql_processing import process_supporter_data, process_supporter_shifts_data, write_to_db
import sqlite3
import os
import mysql.connector
from dotenv import load_dotenv
import sys
from prevent_sleep import PreventSleep
from analyze_preferences import analyze_schedule_compliance


PROJECT_ID = 17
PERIODS = ['pre1', 'pre2']
STATES = ['CONFIRMED', 'CHECKED_IN', 'CHECKED_OUT']
SHIFTS_START = '2025-06-11 10:00:00'
SHIFTS_END = '2025-06-30 23:59:59'
# SHIFTS_START = '2024-09-05 00:00:00'
# SHIFTS_END = '2024-09-11 23:59:59'


# Parameters for the simulated annealing algorithm
initial_temperature = 10000
cooling_rate = 0.9
use_db = True
use_excel = False
activate_parallelization = False
num_of_parallel_threads = 14
max_iterations_without_improvement = 1000
excel_file_path = "2025_FUSION_SCHICHTPLAN.xlsx"
input_solution_path = "SCC_SCHICHTPLAN_2024_B.xlsx"

def get_dict_memory_usage(d):
    """
    Calculate the memory usage of a dictionary, including its keys and values.
    """
    total_size = sys.getsizeof(d)  # Size of the dictionary object itself
    for key, value in d.items():
        total_size += sys.getsizeof(key)  # Memory size of each key
        total_size += sys.getsizeof(value)  # Memory size of each value
    return total_size

def create_db_connection():
    # Load environment variables from .env file
    load_dotenv(override=True)

    # Retrieve database connection details from environment variables
    db_host = os.getenv("DB_HOST")
    db_port = os.getenv("DB_PORT")
    db_user = os.getenv("DB_USER")
    db_password = os.getenv("DB_PASSWORD")
    db_name = os.getenv("DB_NAME")
        
    # Establish the database connection
    connection = None
    try:
        connection = mysql.connector.connect(
            host=db_host,
            port=db_port,  # Add this line
            user=db_user,
            password=db_password,
            database=db_name # Replace with your actual database name
        )
        print("Connection to the database established successfully")
    except mysql.connector.Error as err:
        print(f"Error: '{err}'")

    return connection

def run_simulation():
    
    db_connection = None
    # Example usage:
    if use_db:
        db_connection = create_db_connection()
    
    if db_connection and use_db:
        print("Processing data", db_connection)
        people_data = process_supporter_data(db_connection, PROJECT_ID, STATES, PERIODS)
        shifts_data = process_supporter_shifts_data(db_connection, PROJECT_ID, SHIFTS_START, SHIFTS_END)
        db_connection.close()

    if use_excel:
        people_data = process_people_data(excel_file_path)
        shifts_data = process_shifts_data(excel_file_path)
        
    if not use_db and not use_excel:
        print("Please specify whether to use the database or the excel file")
        exit()
    
    memory_usage_shifts_transformed_data = get_dict_memory_usage(shifts_data)
    print("Memory usage of shifts_transformed_data: ", memory_usage_shifts_transformed_data)
    
    memory_usage_people_transformed_data = get_dict_memory_usage(people_data)
    print("Memory usage of people_transformed_data: ", memory_usage_people_transformed_data)

    shifts_transformed_data = transform_shifts_data(shifts_data)
    people_transformed_data = transform_people_data(people_data)
    memory_usage_shifts_transformed_data = get_dict_memory_usage(shifts_transformed_data)
    print("Memory usage of shifts_transformed_data: ", memory_usage_shifts_transformed_data)
    
    memory_usage_people_transformed_data = get_dict_memory_usage(people_transformed_data)
    print("Memory usage of people_transformed_data: ", memory_usage_people_transformed_data)
    print("Starting simulated annealing")

    if activate_parallelization:
        best_schedule, best_assigned_shifts, best_cost, init_cost = run_parallel_simulated_annealing(
            num_of_parallel_threads,
            people_transformed_data,
            shifts_transformed_data,
            initial_temperature,
            cooling_rate,
            max_iterations_without_improvement,
        )
    else:
        best_schedule, best_assigned_shifts, best_cost, init_cost = simulated_annealing(
            people_transformed_data,
            shifts_transformed_data,
            initial_temperature,
            cooling_rate,
            max_iterations_without_improvement,
        )

    if best_schedule is None:
        print("No valid solution found")
        exit()

    name_list = people_transformed_data["name_dict"]
    best_solution_with_names = replace_numbers_with_names(best_schedule, name_list)
    print(f"Best solution with names: {best_solution_with_names}")
    print(f"Initial cost: {init_cost}")
    print(f"Best cost: {best_cost}")
    
    if use_db:
        db_connection = create_db_connection()
    if db_connection and use_db:
        write_to_db(db_connection, PROJECT_ID, best_schedule)
        db_connection.close() 

    full_analysis = analyze_schedule_compliance(best_schedule, people_transformed_data, shifts_transformed_data)
    
    create_file(
        best_schedule,
        people_transformed_data,
        shifts_transformed_data,
        full_analysis,
        'final'
    )


# def calculate_cost_from_excel():
#     people_data, shifts_data = process_excel(excel_file_path)
#     people_transformed_data, shifts_transformed_data = transform_data(
#         people_data, shifts_data
#     )

#     input_path = input_solution_path
#     dates_list = shifts_transformed_data["shift_date_array"]

#     name_list = people_transformed_data["name_dict"]
#     shift_types = [0, 1]
#     solution = load_excel_and_create_solution(
#         input_path, dates_list, name_list, shift_types
#     )
#     cost_function(solution, assigned_shifts,  people_transformed_data, shifts_transformed_data, True)


if __name__ == "__main__":

    # for i in range(7):
    prevent_sleep = PreventSleep()
    try:
        print("Preventing the system from sleeping...")
        prevent_sleep.start()
        run_simulation()
    except KeyboardInterrupt:
        print("Exiting and allowing the system to sleep.")
    finally:
        prevent_sleep.stop()