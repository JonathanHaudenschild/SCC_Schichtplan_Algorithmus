import random
import math
import numpy as np
import csv
import openpyxl
from openpyxl.styles import PatternFill, Font
from colorhash import ColorHash
import statistics
import time
import concurrent.futures
from functools import partial
from threading import Lock
import pandas as pd


# Costs Factor
# Adjust to increase or decrease a cost factor's influence on the total cost.
INEXPERIENCE_FACTOR = 10
ONE_SIDED_GENDER_FACTOR = 5
SHIFT_CATEGORY_FACTOR = 5
OFF_DAY_FACTOR = 5
SHIFT_RANKING_FACTOR = 1

############################################################################################################## 
# start - crewliste.xlsx: index_name_list & person_capacity_list & preferred_shift_category_list
##############################################################################################################

# Creating a list of tuples, where each tuple contains an index and a name.
# The purpose of this list is to link a unique index with a specific name,
# which can be used for instance, to identify users in a system, 
# or to keep track of the order of elements in a dataset.


def excel_to_array(file_path, name_col, nickname_col):
    # Excel-Datei einlesen
    df = pd.read_excel(file_path)

    # Array aus Namen und Spitznamen erstellen
    data = []
    for i, (name, nickname) in enumerate(zip(df[name_col], df[nickname_col])):
        if pd.isna(nickname):
            data.append((i, name))
        else:
            data.append((i, nickname))

    return data

name = excel_to_array('crewliste.xlsx', 'Namen', 'Spitznamen')
index_name_list = []

for i, n in name:
    index_name_list.append((i, n))


NUM_OF_SHIFTS_PER_PERSON = 5  # default number of shifts per person

# Global variables to store the data from the Excel file
name_data = []
capacity_data = []
checkinpref_data = []

def excel_to_array(file_path, name_col, nickname_col):
    global name_data
    # Only read the Excel file if the global variable is empty
    if not name_data:
        # Excel-Datei einlesen
        df = pd.read_excel(file_path)

        # Array aus Namen und Spitznamen erstellen
        data = []
        for i, (name, nickname) in enumerate(zip(df[name_col], df[nickname_col])):
            if pd.isna(nickname):
                data.append((i, name))
            else:
                data.append((i, nickname))

        name_data = data

    return name_data

def excel_to_person_capacity_list(file_path, capacity_col):
    global capacity_data
    # Only read the Excel file if the global variable is empty
    if not capacity_data:
        # Excel-Datei einlesen
        df = pd.read_excel(file_path)

        # Array aus Kapazitäten erstellen
        cdata = []
        for i, capacity in df[capacity_col].items():
            if pd.isnull(capacity):
                capacity = NUM_OF_SHIFTS_PER_PERSON
            else:
                capacity = int(capacity)
            cdata.append((i, capacity))

        capacity_data = cdata

    return capacity_data

# Creating a list of tuples, where each tuple contains an index and a name.
# The purpose of this list is to link a unique index with a specific name,
# which can be used for instance, to identify users in a system, 
# or to keep track of the order of elements in a dataset.
name = excel_to_array('crewliste.xlsx', 'Namen', 'Spitznamen')
index_name_list = []

for i, n in name:
    index_name_list.append((i, n))

# This list specifies the capacity for each person.
# Each tuple represents a person's index and the number of shifts that the person can work.
# For example, (0, 4) means that person 0 can work 4 shifts.
# NUM_OF_SHIFTS_PER_PERSON is the default number of shifts per person. Each tuple will override this default value.
person_capacity = excel_to_person_capacity_list('crewliste.xlsx', 'Schichtanzahl')
person_capacity_list = []
for i, pc in person_capacity:
    person_capacity_list.append((i, pc))
    
    

def excel_to_checkinshift_array(file_path, nummer_col, check_in_col):
    # Excel-Datei einlesen
    df = pd.read_excel(file_path)

    # Array aus Check-in-Werten erstellen
    checkinpref_data = []
    for i, (nummer, check_in) in df[[nummer_col, check_in_col]].iterrows():
        if check_in == "CHECK_IN":
            checkinpref_data.append((nummer, check_in))

    return checkinpref_data



############################################################################################################## 
# end - crewliste.xlsx: index_name_list & person_capacity_list & preferred_shift_category_list
##############################################################################################################

# Creating a list of tuples to represent different work shifts.
# Each tuple contains an index and a corresponding shift time.
shift_name_list = [
    (0, '13:00 - 19:00'),
    (1, '19:00 - 01:00'),
    (2, '01:00 - 07:00'),
    (3, '07:00 - 13:00'),
    # Adjust the shift times and amount here to match your schedule
]

# Creating a list of tuples to represent shift rankings.
# Each tuple contains a ranking and a corresponding tuple of shift indices.
# This assigns a priority or preference order to different shifts
shift_ranking_list = [
    (1, (0, 1, 2, 3)), # The shifts at indices 0, 1, 2, and 3 are assigned a ranking of 1
    (3, (4, 5, 6, 7, 20, 21, 22, 23 )), # The shifts at indices 4, 5, 6, 7, 20, 21, 22, and 23 are assigned a ranking of 3
    (6, (8, 9, 10, 11)), # The shifts at indices 8, 9, 10, and 11 are assigned a ranking of 6
    (9, (12, 13, 14, 15, 16, 17, 18, 19)), # The shifts at indices 12, 13, 14, 15, 16, 17, 18, and 19 are assigned a ranking of 9
    # Add more shift rankings here
]

# Creating a list of tuples to represent rankings for different shift types.
# Each tuple contains a ranking and a corresponding tuple of shift type indices.
# This assigns a priority  or preference order to different shift types,
shift_type_ranking_list = [
    (1, (2,)), # The shift type at index 2 is assigned a ranking of 1
    (3, (1, 3)), # The shift types at indices 1 and 3 are assigned a ranking of 3
    (9, (0,)), # The shift type at index 0 is assigned a ranking of 9
    # Add more shift type rankings here
]

# These are constants representing different levels of preference for or against working with certain partners.
# Negative values are used for preferred partners (friends), with a larger absolute value indicating a stronger preference.
# Positive values are used for non-preferred partners (enemies), with a larger value indicating a stronger preference against.
ONE_FRIEND = -5
TWO_FRIENDS = -3
THREE_FRIENDS = -2
FOUR_FRIENDS = -1
ONE_ENEMY = 15
TWO_ENEMIES = 12
THREE_ENEMIES = 9
FOUR_ENEMIES = 6

# This list defines the preference of employees to work together.
# Each tuple consists of two persons indices and a preference constant.
# A negative preference constant (e.g., ONE_FRIEND) indicates a preference to work together.
# A positive preference constant (e.g., ONE_ENEMY) indicates a preference to avoid working together.

preference_list = [
    (3, 17, ONE_FRIEND),  # Person 0 and person 1 have a preference of 5 to work together
    (45, 50, ONE_FRIEND),
    (36, 28, ONE_FRIEND),
    (6, 11, TWO_FRIENDS),
    (6, 46, TWO_FRIENDS),
    (11, 46, TWO_FRIENDS),
# Add more preferences here
]

# These are constants representing different categories of shifts.
NORMAL = 0  # Normal shift
CHECK_IN = 1  # Check-in shift

# This list defines the preferred shift categories of the people.
# Each tuple consists of a persons index and a shift category constant.
# For example, a tuple (4, CHECK_IN) means that the person with index 4 prefers to work check-in shifts.


preferred_shift_category_list = [
    (4, "CHECK_IN"),  # Person with index 4 prefers to work check-in shifts
    (34, "CHECK_IN")  # Person with index 34 also prefers to work check-in shifts
    # Add more preferred shift categories here
]


# This list defines the categories of each shift.
# Each tuple consists of a shift index and a shift category constant.
# For example, a tuple (0, CHECK_IN) means that the shift with index 0 is a check-in shift.
shift_category_list= [
    (0, CHECK_IN),  # Shift 0 is a check-in shift
    (1, CHECK_IN),  # Shift 1 is a check-in shift
    (2, CHECK_IN),  # Shift 2 is a check-in shift
    (3, CHECK_IN),  # Shift 3 is a check-in shift
    (4, CHECK_IN),  # Shift 4 is a check-in shift
    (5, CHECK_IN),  # Shift 4 is a check-in shift
    (6, CHECK_IN),  # Shift 4 is a check-in shift
    (7, CHECK_IN),  # Shift 4 is a check-in shift
    (8, CHECK_IN),  # Shift 4 is a check-in shift
    (9, CHECK_IN),  # Shift 4 is a check-in shift
    # Add more shift categories here
]

# These constants represent different levels of preference for shifts.
FIRST_PREFERENCE = 3  # Highest preference
SECOND_PREFERENCE = 2
THIRD_PREFERENCE = 1
FOURTH_PREFERENCE = 0  # Lowest preference

# This list defines the shift preferences of each person.
# Each tuple consists of a person index and a tuple of preferences for each shift.
# The preferences are ordered by shift time. For example, the shift times is ordered as '13:00 - 19:00', '19:00 - 01:00', '01:00 - 07:00', '07:00 - 13:00', etc.
# A preference tuple like (FIRST_PREFERENCE, SECOND_PREFERENCE, THIRD_PREFERENCE, FOURTH_PREFERENCE) means that the person prefers the first shift time most, the second shift time next, etc.
preferred_shift_list = [
    (0, (FIRST_PREFERENCE, SECOND_PREFERENCE, THIRD_PREFERENCE, FOURTH_PREFERENCE)),  # Person 0's shift preferences
    (1, (FOURTH_PREFERENCE, FIRST_PREFERENCE, SECOND_PREFERENCE, FOURTH_PREFERENCE)),
    (2, (SECOND_PREFERENCE, FIRST_PREFERENCE, THIRD_PREFERENCE, FOURTH_PREFERENCE)),
    (3, (THIRD_PREFERENCE, FOURTH_PREFERENCE, FIRST_PREFERENCE, SECOND_PREFERENCE)),
    (4, (FOURTH_PREFERENCE, SECOND_PREFERENCE, FIRST_PREFERENCE, THIRD_PREFERENCE)),
    # Add more shift preferences here
]

# These constants represent different levels of experience.
NEW = 0  # Represents a person with less than one year of experience
ONE_YEAR = 1  # Represents a person with exactly one year of experience
MORE_THAN_ONE_YEAR = 2  # Represents a person with more than one year of experience

# This list defines the experience level of each person.
# Each tuple consists of a person index and a experience level.
# For example, a tuple (0, MORE_THAN_ONE_YEAR) means that the person with index 0 has more than one year of experience.
experience_list = [
    (0, MORE_THAN_ONE_YEAR),  # Person 0 has more than one year of experience
    (1, MORE_THAN_ONE_YEAR),  # Person 1 has more than one year of experience
    # Add more experience levels here
]

# These constants represent different gender categories.
MALE = 0  # Represents male gender
FEMALE = 1  # Represents female gender
OTHER = 2  # Represents other gender identities

# This list defines the gender of each person.
# Each tuple consists of a person index and a gender category.
# For example, a tuple (0, FEMALE) means that the person with index 0 identifies as female.
gender_list = [
    (0, FEMALE), # Person 0 identifies as female
    (1, MALE),
    (2, MALE),
    # Add gender data here
]

# This list specifies periods during which each person is unavailable for shifts.
# Each tuple represents a person's index and the indices of the shifts during which they are unavailable.
# For example, (0, (2, 3)) means that person 0 is unavailable for shifts 2 and 3.
unavailability_list = [
    (0, (2, 3)),  # Person 0 is unavailable for shifts 2 and 3
    (4, (2, 3)),  # Person 4 is unavailable for shifts 2 and 3
    (1, (2, 3)),  # Person 1 is unavailable for shifts 2 and 3
    (16, (0, 1, 2, 3, 4, 5, 6, 7, 8)),  # Person 16 is unavailable for shifts 0 through 8
    # Add more unavailability data here
]

# This list specifies the off-shifts for each person. 
# Each tuple represents a person's index and the indices of the shifts during which they are off.
# For example, (0, (0, 1, 2, 3)) means that person 0 has off-shifts 0, 1, 2, and 3.
offShift_list= [
    (0, (0, 1, 2, 3)), # Person 0 has off-shifts 0, 1, 2, and 3
    (1, (4, 5, 6, 7)),
    (3, (4, 5, 6, 7)),
    (4, (4, 5, 6, 7)),
    (5, (4, 5, 6, 7)),
    (6, (4, 5, 6, 7)),
    (7, (4, 5, 6, 7)),
    (8, (8, 9, 10, 11)),
    (9, (8, 9, 10, 11)),
    (10, (8, 9, 10, 11)),
    (11, (8, 9, 10, 11)),
    (12, (8, 9, 10, 11)),
    (13, (8, 9, 10, 11)),
    (14, (8, 9, 10, 11)),
    (15, (8, 9, 10, 11)),
    (16, (8, 9, 10, 11)),
    (17, (12,13, 14,15)),
    (18, (12,13, 14,15)),
    (19, (12,13, 14,15)),
    (20, (12,13, 14,15)),
    (21, (12,13, 14,15)),
    (22, (12,13, 14,15)),
    (23, (12,13, 14,15)),
    (24, (12,13, 14,15)),
    (25, (12,13, 14,15)),
    (26, (12,13, 14,15)),
    (27, (16, 17, 18, 19)),
    (28, (16, 17, 18, 19)),
    (29, (16, 17, 18, 19)),
    (30, (16, 17, 18, 19)),
    (31, (16, 17, 18, 19)),
    (32, (16, 17, 18, 19)),
    (33, (16, 17, 18, 19)),
    (34, (16, 17, 18, 19)),
    (35, (16, 17, 18, 19)),
    (36, (16, 17, 18, 19)),
    (37, (16, 17, 18, 19)),
    (38, (16, 17, 18, 19)),
    (39, (16, 17, 18, 19)),
    (40, (16, 17, 18, 19)),
    (41, (16, 17, 18, 19)),
    (42, (16, 17, 18, 19)),
    (43, (16, 17, 18, 19)),
    (44, (16, 17, 18, 19)),
    (45, (16, 17, 18, 19)),
    (46, (16, 17, 18, 19)),
    (47, (16, 17, 18, 19)),
    (48, (16, 17, 18, 19)),
    (49, (16, 17, 18, 19)),
    (50, (16, 17, 18, 19)),
    (51, (16, 17, 18, 19)),
    (52, (20, 21, 22, 23)),
    (53, (20, 21, 22, 23)),
    (54, (20, 21, 22, 23)),
    (55, (20, 21, 22, 23)),
    (56, (20, 21, 22, 23)),
    (57, (20, 21, 22, 23)),
    (58, (20, 21, 22, 23)),
    (59, (20, 21, 22, 23)),
    (60, (20, 21, 22, 23)),
    (61, (20, 21, 22, 23)),
    # Add more off-shift data here
]

# This list specifies the dates for which the schedule is being generated.
# Each tuple represents a date's index, the date in string format, and the indices of the shifts on that date.
dates_list = [
    (0, '27.06.2023 Tuesday', (0, 1)),
    (2, '28.06.2023 Wednesday', (2, 3, 4, 5)),
    (6, '29.06.2023 Thursday', (6, 7, 8, 9)),
    (10, '30.06.2023 Friday', (10, 11, 12, 13)),
    (14, '01.07.2023 Saturday', (14, 15, 16, 17)),
    (18, '02.07.2023 Sunday', (18, 19, 20, 21)),
    (22, '03.07.2023 Monday', (22, 23)),
]

# This list specifies the capacity for each shift.
# Each tuple represents a shift's index and the minimum and maximum number of persons that can work during this shift.
shift_capacity_list= [
    # For example, (0, (12, 13)) means that shift 0 requires between 12 and 13 persons.
    # Dates are mentioned in comments for better understanding
    # 27.06.2023 Tuesday
    (0, (12, 14)), 
    (1, (17, 18)),  
    # 28.06.2023 Wednesday
    (2, (17, 18)),  
    (3, (18, 19)), 
    (4, (17, 18)),  
    (5, (16, 17)), 
    # 29.06.2023 Thursday
    (6, (12, 13)),  
    (7, (15, 16)), 
    (8, (15, 16)),  
    (9, (14, 15)),  
    # 30.06.2023 Friday
    (10, (10, 11)),  
    (11, (13, 14)),  
    (12, (13, 14)), 
    (13, (12, 13)), 
    # 01.07.2023 Saturday
    (14, (8, 10)), 
    (15, (11, 12)), 
    (16, (11, 12)), 
    (17, (11, 12)),  
    # 02.07.2023 Sunday     
    (18, (8, 9)),
    (19, (12, 13)),
    (20, (12, 13)), 
    (21, (11, 12)), 
    # 03.07.2023 Monday
    (22, (6, 7)),
    (23, (7, 8)),   
    # Add more shift capacity data here
]




# Parameters for the simulated annealing algorithm
initial_temperature = 1000  # initial temperature
cooling_rate = 0.9999  # cooling rate
activate_parallelization = True  # activate parallelization
num_of_parallel_threads = 8  # number of parallel threads

############################################################################################################## 
# DO NOT CHANGE ANYTHING BELOW THIS LINE
##############################################################################################################
num_of_shifts = len(shift_capacity_list)  # total number of shifts
num_people = len(index_name_list)   # total number of people
num_of_shift_types = len(shift_name_list)  # total number of shift types


def generate_initial_solution(x, y):
    solution = [set() for _ in range(x)]
    for person in range(y):
        assigned_shifts = set()
        while len(assigned_shifts) < create_persons_capacity_array(person_capacity_list)[person]:
            shift = random.randint(0, x - 1)
            if len(solution[shift]) < create_shift_capacity_matrix(shift_capacity_list)[1][shift] and shift not in assigned_shifts:
                # Higher probability of adding a person if the shift has less than the minimum people
                if len(solution[shift]) < create_shift_capacity_matrix(shift_capacity_list)[0][shift] or random.random() < 0.30:
                    solution[shift].add(person)
                    assigned_shifts.add(shift)
    return solution


def get_neighbor(solution, unavailability_matrix, max_attempts=10000):
    attempts = 0
    while attempts < max_attempts:
        index1 = random.randint(0, len(solution) - 1)
        index2 = random.randint(0, len(solution) - 1)
        shift1 = solution[index1].copy()
        shift2 = solution[index2].copy()

        if len(shift1) > create_shift_capacity_matrix(shift_capacity_list)[0][index1] and len(shift2) < create_shift_capacity_matrix(shift_capacity_list)[0][index2] :
          
            person_to_move = get_random_element(shift1)

            if person_to_move not in shift2 and consecutive_shifts(solution, index2, person_to_move) == 0 and unavailability(index2, unavailability_matrix, person_to_move) == 0:
                shift1.remove(person_to_move)
                shift2.add(person_to_move)
                new_solution = solution.copy()
                new_solution[index1] = shift1
                new_solution[index2] = shift2
                return new_solution  # The neighbor solution satisfies both hard constraints
        else:
            # Swap people between the shifts if possible
            person1 = get_random_element(shift1)
            person2 = get_random_element(shift2)

            if person1 not in shift2 and person2 not in shift1 and consecutive_shifts(solution, index2, person1) == 0 and consecutive_shifts(solution, index1, person2) == 0 and unavailability(index2, unavailability_matrix, person1) == 0 and unavailability(index1, unavailability_matrix, person2) == 0:
                shift1.remove(person1)
                shift1.add(person2)
                shift2.remove(person2)
                shift2.add(person1)
                new_solution = solution.copy()
                new_solution[index1] = shift1
                new_solution[index2] = shift2
                return new_solution  # The neighbor solution satisfies both hard constraints

        attempts += 1
    # Return the original solution if no valid neighbor is found after max_attempts
    print("No valid neighbor found after", max_attempts, "attempts")
    return solution

def get_random_element(s):
    return random.choice(list(s))

def adaptive_cooling_rate(initial_temperature, min_temperature, cooling_factor):
    return max(min_temperature, initial_temperature * cooling_factor)

def acceptance_probability(old_cost, new_cost, temperature):
    if new_cost < old_cost:
        return 1
    else:
        return math.exp(-(abs(new_cost - old_cost) / temperature))

def run_parallel_simulated_annealing(num_instances, *args, **kwargs):
    best_solutions = []

    # Use a ProcessPoolExecutor to run the simulated annealing function concurrently
    with concurrent.futures.ProcessPoolExecutor() as executor:
        # Call the function with different seeds or initial solutions
        seeds = [random.randint(0, 1000000) for _ in range(num_instances)]
        annealing_function = partial(simulated_annealing, num_of_shifts, num_people, initial_temperature, cooling_rate)
        all_args = [num_of_shifts, num_people, initial_temperature, cooling_rate, 1000]
        for result in executor.map(annealing_function, all_args, seeds):
            best_solutions.append(result)
        
    best_solutions.sort(key=lambda x: x[1])
    return best_solutions[0][0], best_solutions[0][1], best_solutions[0][2]


def simulated_annealing(x, y, initial_temperature, cooling_rate, max_iterations_without_improvement, seed=None):
   # If a seed is provided, use it to initialize the random module
    if seed is not None:
        random.seed(seed)
  
    current_solution = generate_initial_solution(x, y)
    current_cost = cost_function(current_solution)
    init_cost = current_cost
    # print(f"Current solution: {current_solution}")
    # print(f"Current cost: {current_cost}")
    temperature = initial_temperature
    iterations_without_improvement = 0

    total_iterations = math.ceil(math.log(1 / initial_temperature) / math.log(cooling_rate))
    start_time = time.time()
    current_iteration = 0

    while temperature > 1 and iterations_without_improvement < max_iterations_without_improvement:

        new_solution = get_neighbor(current_solution, create_unavailability_matrix(unavailability_list))
        new_cost = cost_function(new_solution)   

        if acceptance_probability(current_cost, new_cost, temperature) > random.random():
            current_solution = new_solution
            current_cost = new_cost
            iterations_without_improvement = 0  # Reset the counter when an improvement is found
        else:
            iterations_without_improvement += 1

        temperature *= cooling_rate
        current_iteration += 1
        if(current_iteration % 333 == 0):
            showProgressIndicator(current_iteration, total_iterations, start_time, new_cost, init_cost)

    return current_solution, current_cost, init_cost

def create_ranking_array(shift_ranking_list, shift_type_ranking_list):
    cost_array = [0] * num_of_shifts

    for cost, shifts in shift_ranking_list:
        for shift_index in shifts:
            # Check if this shift_index matches a shift type
            for type_cost, shifts in shift_type_ranking_list:
                for shift in shifts:
                    if shift_index % num_of_shift_types == shift:  # Assuming there are 4 shift types
                        cost_array[shift_index] = type_cost * cost

    return cost_array

def create_preference_matrix(preference_list):
    preference_matrix = [[0 for _ in range(num_people)] for _ in range(num_people)]
    for person1, person2, preference in preference_list:
        preference_matrix[person1][person2] = preference
        preference_matrix[person2][person1] = preference
    return preference_matrix

def create_persons_capacity_array(capacity_list):
    capacity_array = [NUM_OF_SHIFTS_PER_PERSON] * num_people
    for capacity in capacity_list:
        capacity_array[capacity[0]] = capacity[1]
    return capacity_array

def create_preferred_shift_category_array(pref_shift_category_list):
    pref_shift_category_array = [0] * num_people
    for pref_shift_category in pref_shift_category_list:
        pref_shift_category_array[pref_shift_category[0]] = pref_shift_category[1]
    return pref_shift_category_array

def create_experience_array(experience_list):
    experience_array = [1] * num_people
    for experience in experience_list:
        experience_array[experience[0]] = experience[1]
    return experience_array

def create_gender_array(gender_list):
    gender_array = [0] * num_people
    for gender in gender_list:
        gender_array[gender[0]] = gender[1]
    return gender_array

def create_shift_category_array(shift_category_list):
    shift_category_array = [0] * num_of_shifts
    for shift_category in shift_category_list:
        shift_category_array[shift_category[0]] = shift_category[1]
    return shift_category_array


def create_preferred_shift_matrix(pref_shift_list):
    matrix = [[1] * num_of_shift_types for _ in range(num_people)]
    for _, (person, shift_values) in enumerate(pref_shift_list):
        matrix[person] = list(shift_values)
    return matrix

def create_unavailability_matrix(unavailability_list):
    unavailability_matrix = [[0 for _ in range(num_of_shifts)] for _ in range(num_people)]
    for person, shifts in unavailability_list:
        for shift in shifts:
            unavailability_matrix[person][shift] = 1
    return unavailability_matrix

def create_shift_capacity_matrix(shift_capacity_list):
    shift_capacity_matrix = [[0 for _ in range(num_of_shifts)] for _ in range(2)]
    for shift, capacity in shift_capacity_list:
        shift_capacity_matrix[0][shift] = capacity[0]
        shift_capacity_matrix[1][shift] = capacity[1]
    return shift_capacity_matrix

# Create the cost arrays and matrices
preference_matrix = create_preference_matrix(preference_list)
experience_array = create_experience_array(experience_list)
unavailability_matrix = create_unavailability_matrix(offShift_list)
ranking_array = create_ranking_array(shift_ranking_list, shift_type_ranking_list)
preferred_shift_matrix = create_preferred_shift_matrix(preferred_shift_list)
shift_category_array = create_shift_category_array(shift_category_list)
preferred_shift_category_array = create_preferred_shift_category_array(preferred_shift_category_list)
gender_array = create_gender_array(gender_list)

def cost_function(solution):
    # Calculate preference-based cost
    pref_cost = preference_cost(solution,preference_matrix)
    exp_cost = mixedExperience_cost(solution, experience_array)
    oday_cost = offDay_cost(solution, unavailability_matrix)
    rank_cost = shift_ranking_cost(solution,ranking_array, preferred_shift_matrix, unavailability_matrix)
    shift_category_cost = shift_category_com_cost(solution,shift_category_array, preferred_shift_category_array)
    gender_cost = mixedGender_cost(solution, gender_array)
    # Add other cost components if necessary
    total_cost = pref_cost + exp_cost + shift_category_cost + rank_cost + oday_cost + gender_cost
    return total_cost 

def preference_cost(solution, preference_matrix):
    total_cost = 0
    for shift in solution:
        for person1 in shift:
            for person2 in shift:
                if person1 != person2:
                    total_cost += preference_matrix[person1][person2]
    return total_cost

def shift_ranking_cost(solution, ranking_array, personal_pref_matrix, unavailability_matrix):
    shift_costs = [0] * num_people
    shift_types = [[1] * num_of_shift_types for _ in range(num_people)]

    for shift_index, shift in enumerate(solution):
        for person in shift:
            shift_type = shift_index % num_of_shift_types
            persons_cost = 0
            shift_cost = ranking_array[shift_index]
            duplicate_factor = shift_types[person][shift_type]
            if unavailability_matrix[person][shift_index]:
                persons_cost += OFF_DAY_FACTOR * math.sqrt(shift_cost) * NUM_OF_SHIFTS_PER_PERSON

            persons_cost += (shift_cost / (math.log(personal_pref_matrix[person][shift_type] + 1) + 1)) * duplicate_factor

            shift_costs[person] += persons_cost
            shift_types[person][shift_type] += 1

    deviation = statistics.stdev(shift_costs)
    mean = statistics.mean(shift_costs)
    return deviation * mean * SHIFT_RANKING_FACTOR

def shift_category_com_cost(solution, shift_category_array, pref_shift_category_array):
    total_cost = 0
    for shift_index, shift in enumerate(solution):
        for person in shift:
            if shift_category_array[shift_index] != pref_shift_category_array[person]:
                total_cost += SHIFT_CATEGORY_FACTOR 
    return total_cost

def mixedExperience_cost(solution, experience_array):
    total_cost = 0
    shift_experience = [0] * num_of_shifts
    for shift_index, shift in enumerate(solution):
        total_experience = 0
        for person in shift:
            total_experience += experience_array[person]
        shift_experience[shift_index] = total_experience
    
    deviation = statistics.stdev(shift_experience)
    mean = statistics.mean(shift_experience)
    decay = math.pow(0.9, mean)
    total_cost = deviation * decay * INEXPERIENCE_FACTOR
    return total_cost 

def mixedGender_cost(solution, gender_array):
    total_cost = 0
    shift_gender = [0] * num_of_shifts
    for shift_index, shift in enumerate(solution):
        gender_mix = 0
        for person in shift:
            gender_mix += gender_array[person]
        shift_gender[shift_index] = gender_mix

    deviation = statistics.stdev(shift_gender) 
    total_cost = deviation * ONE_SIDED_GENDER_FACTOR       
    return total_cost 

def offDay_cost(solution, unavailability_matrix):
    total_cost = 0
    for shift_index, shift in enumerate(solution):
        for person in shift:
            if unavailability_matrix[person][shift_index]:
                total_cost += OFF_DAY_FACTOR   # Penalize the cases when a person is assigned to an unavailable shift
    return total_cost

def unavailability(shift_index, unavailability_matrix, person):
        if unavailability_matrix[person][shift_index]:
            return 1 
        return 0

def consecutive_shifts(solution, shift_index, person):
    # Check previous shifts
    for i in range(1, 3):
        if shift_index - i >= 0:
            previous_shift = solution[shift_index - i]
            if person in previous_shift:
                return 1 

    # Check next shifts
    for i in range(1, 3):
        if shift_index + i < len(solution):
            next_shift = solution[shift_index + i]
            if person in next_shift:
                return 1 

    return 0  # No constraint violations were found

def replace_numbers_with_names(solution, index_name_list):
    name_solution = []
    for shift in solution:
        name_shift = set()
        for number in shift:
            name = next(name for index, name in index_name_list if index == number)
            name_shift.add(name)
        name_solution.append(name_shift)
    return name_solution

def showProgressIndicator(current_iteration, total_iterations, start_time, new_cost, init_cost):
    progress = current_iteration / total_iterations
    elapsed_time = time.time() - start_time
    remaining_time = elapsed_time / progress - elapsed_time

    # Convert remaining_time to hours, minutes, and seconds
    hours, remainder = divmod(remaining_time, 3600)
    minutes, seconds = divmod(remainder, 60)

    print(f"Progress: {progress * 100:.2f}% | Estimated time remaining: {hours:.0f}h {minutes:.0f}m {seconds:.0f}s | Cost Improvement: {round(((init_cost-new_cost)/init_cost)*100,0)}%  ", end='\r' )

def createFile(solution, shift_name_list):
     # Create a new Excel workbook and select the active worksheet
    workbook = openpyxl.Workbook()
    worksheet = workbook.active

    # Write shift names as headers
    for col_index, _ in enumerate(solution):
        shift_name = shift_name_list[col_index % len(shift_name_list)][1]

        cell = worksheet.cell(row=1, column=col_index + 2)
        cell.value = col_index
        for dates in dates_list:
            if dates[0] == col_index:
                day_name = dates[1]
                cell1 = worksheet.cell(row=2, column=col_index + 2)
                cell1.value = day_name
        cell2 = worksheet.cell(row=3, column=col_index + 2)
        cell2.value = shift_name



        # Write the data to the worksheet and apply a unique color to each name
    name_colors = {}
    white_font = Font(color='FFFFFF')  # Set font color to white
    dark_font = Font(color='000000')  # Set font color to black
    for row_index, shift in enumerate(solution, start=4):
        cell = worksheet.cell(row=row_index, column=1)
        cell.value = row_index - 3
        cell.font = dark_font
    for col_index, shift in enumerate(solution, start=1):

         
        for row_index, name in enumerate(shift, start=4):
            cell = worksheet.cell(row=row_index, column=col_index+1)
            cell.value = name

            # Generate a unique color for each name if not already generated
            if name not in name_colors:
                color = ColorHash(name).hex
                color = 'FF' + color[1:]  # Add alpha channel to the hex color
                name_colors[name] = PatternFill(start_color=color, end_color=color, fill_type='solid')

            # Apply the unique color to the cell
            cell.fill = name_colors[name]
            cell.font = white_font

    # Save the workbook as an Excel file
    workbook.save('shifts_with_unique_colors.xlsx')



#Main Funktion
if __name__ == "__main__":
    
    # Namen aus Excel Liste auslesen
    name = excel_to_array('crewliste.xlsx', 'Namen', 'Spitznamen')
    # Namen aus Excel Liste auslesen - TEST
    print(name)
    
    # Person Capacity aus Excel Liste auslesen
    person_capacity_list = excel_to_person_capacity_list('crewliste.xlsx', 'Schichtanzahl')

    # Gib die Liste aus - TEST
    print(person_capacity_list)
    
    preferred_shift_category_list = excel_to_checkinshift_array('crewliste.xlsx', 'Nummer' , 'check_in')
    print(preferred_shift_category_list)
    
    
    
    
    if activate_parallelization:
        best_solution, best_cost, init_cost = run_parallel_simulated_annealing(num_of_parallel_threads)
    else:
        best_solution, best_cost, init_cost = simulated_annealing(num_of_shifts, num_people, initial_temperature, cooling_rate, max_iterations_without_improvement=1000)
   
    # Print the best solution and its cost
    best_solution_with_names = replace_numbers_with_names(best_solution, index_name_list) 
    print(f"Best solution with names: {best_solution_with_names}")
    print(f"Initial cost: {init_cost}")
    print(f"Best cost: {best_cost}")
    createFile(best_solution_with_names, shift_name_list)
   
