import openpyxl
from datetime import datetime
from openpyxl.styles import PatternFill, Font
from colorhash import ColorHash


def process_excel(file_path):
    people_column_names = [
        "Namen",
        "Spitznamen",
        "Schichtanzahl",
        "Schichtart",
        "Schichtpräferenz",
        "Freunde",
        "Feinde",
        "Freie Schichten",
        "Nicht Verfügbar",
        "Geschlecht",
        "Erfahrung",
        "Minimum",
        "SV",
        "SV-Erfahrung",
        "SV-Schichtanzahl",
    ]
    shifts_column_names = [
        "date",
        "time",
        "min",
        "max",
        "Schichtart",
        "SV-min",
        "SV-max",
    ]
    # Read excel file
    workbook = openpyxl.load_workbook(file_path, data_only=True)
    # Get the first sheet of the workbook
    people_ws = workbook["Personen"]
    # Get the second sheet of the workbook
    shifts_ws = workbook["Schichten"]

    # Initialize an empty dictionary to hold column data
    people_raw_data = {}

    # Iterate through each column
    for column in people_ws.iter_cols(min_row=1, values_only=True):
        # Get the column name
        column_name = column[0]
        # Get the column data as a list
        column_values = [cell for cell in column[1:]]
        # Add the column data to the dictionary
        people_raw_data[column_name] = column_values

    name_data = [
        (
            (int(index), nickname)
            if nickname is not None and nickname != ""
            else (int(index), name)
        )
        for index, name, nickname in zip(
            people_raw_data["index"],
            people_raw_data[people_column_names[0]],
            people_raw_data[people_column_names[1]],
        )
        if name is not None and name != ""
    ]
    capacity_data = [
        (int(index), int(capacity))
        for index, capacity in zip(
            people_raw_data["index"], people_raw_data[people_column_names[2]]
        )
        if capacity is not None
    ]

    # This list defines the preferred shift categories of the people.
    # Each tuple consists of a persons index and a shift category constant.
    # For example, a tuple (4, CHECK_IN) means that the person with index 4 prefers to work check-in shifts.
    # check_in_pref_peopleData, shiftsData = [(i, CHECK_IN) for i, check_in in df[shift_category_col].items() if (check_in == "CHECK_IN") or (check_in == 1)]
    preferred_shift_category_list = [
        (int(index), 1 if shift_category == "CHECK_IN" else shift_category)
        for index, shift_category in zip(
            people_raw_data["index"], people_raw_data[people_column_names[3]]
        )
        if shift_category is not None and str(shift_category) != ""
    ]

    # This list defines the shift rankings of the people.
    # Each tuple consists of a person's index and a shift ranking.
    # A shift ranking is a number that indicates the priority of a shift.
    # A shift ranking of 3 is the highest priority, a shift ranking of 2 is the second highest priority, and so on.
    # A shift ranking of 0 means that the person has no preference for any shift.
    shift_preference_data = [
        (int(index), tuple(int(j) for j in shift_ranking.split(",")))
        for index, shift_ranking in zip(
            people_raw_data["index"], people_raw_data[people_column_names[4]]
        )
        if shift_ranking is not None and str(shift_ranking) != ""
    ]

    # This list defines the preference of people to work together.
    # Each tuple consists of two persons indices and a preference constant.
    friends_data = [
        (int(index), int(float(j)), -1)
        for index, friends in zip(
            people_raw_data["index"], people_raw_data[people_column_names[5]]
        )
        if friends is not None
        for j in str(friends).split(",")
        if j.strip() != ""
    ]
    enemies_data = [
        (int(index), int(float(j)), 1)
        for index, enemies in zip(
            people_raw_data["index"], people_raw_data[people_column_names[6]]
        )
        if enemies is not None
        for j in str(enemies).split(",")
        if j.strip() != ""
    ]
    preference_data = friends_data + enemies_data

    # Process off shifts
    # This list defines the off shifts of the people.
    # Each tuple consists of a person's index and a shift index.
    off_shifts_data = [
        (int(index), tuple(int(val) for val in str(off_day).split(",")))
        for index, off_day in zip(
            people_raw_data["index"], people_raw_data[people_column_names[7]]
        )
        if off_day is not None and str(off_day) != ""
    ]
    # Process unavailable shifts
    # This list defines the unavailable shifts of the people.
    # Each tuple consists of a person's index and a shift index.
    unavailability_data = [
        (int(index), tuple(int(val) for val in str(unavailable).split(",")))
        for index, unavailable in zip(
            people_raw_data["index"], people_raw_data[people_column_names[8]]
        )
        if unavailable is not None and str(unavailable) != ""
    ]
    # This list defines the gender of each person.
    # Each tuple consists of a person index and a gender category.
    gender_data = [
        (int(index), int(gender))
        for index, gender in zip(
            people_raw_data["index"], people_raw_data[people_column_names[9]]
        )
        if gender is not None
    ]
    # This list defines the experience level of each person.
    # Each tuple consists of a person index and a experience level.
    experience_data = [
        (int(index), int(experience))
        for index, experience in zip(
            people_raw_data["index"], people_raw_data[people_column_names[10]]
        )
        if experience is not None
    ]

    # This list defines the minimum number of shifts that are between their shifts
    # Each tuple consists of a person index and a minimum number of shifts
    minimum_data = [
        (int(index), int(minimum))
        for index, minimum in zip(
            people_raw_data["index"], people_raw_data[people_column_names[11]]
        )
        if minimum is not None
    ]

    sv_data = [
        (int(index), int(sv))
        for index, sv in zip(
            people_raw_data["index"], people_raw_data[people_column_names[12]]
        )
        if sv is not None
    ]

    sv_experience_data = [
        (int(index), int(sv_experience))
        for index, sv_experience in zip(
            people_raw_data["index"], people_raw_data[people_column_names[13]]
        )
        if sv_experience is not None
    ]

    sv_capacity_data = [
        (int(index), int(sv_capacity))
        for index, sv_capacity in zip(
            people_raw_data["index"], people_raw_data[people_column_names[14]]
        )
        if sv_capacity is not None
    ]

    people_data = {
        "name_data": name_data,
        "capacity_data": capacity_data,
        "preferred_shift_category_data": preferred_shift_category_list,
        "preference_data": preference_data,
        "off_shifts_data": off_shifts_data,
        "unavailability_data": unavailability_data,
        "shift_preference_data": shift_preference_data,
        "gender_data": gender_data,
        "experience_data": experience_data,
        "minimum_data": minimum_data,
        "sv_data": sv_data,
        "sv_experience_data": sv_experience_data,
        "sv_capacity_data": sv_capacity_data,
    }

    # Initialize an empty dictionary to hold column data
    shifts_raw_data = {}

    # Iterate through each column
    for column in shifts_ws.iter_cols(min_row=1, values_only=True):
        # Get the column name
        column_name = column[0]
        # Get the column data as a list
        column_values = [cell for cell in column[1:]]
        # Add the column data to the dictionary
        shifts_raw_data[column_name] = column_values

    # This list specifies the dates for which the schedule is being generated.
    # Each tuple represents a date's index, the date in string format, and the indices of the shifts on that date.

    shift_date_data = [
        (int(index), shift_name)
        for index, shift_name in zip(
            shifts_raw_data["index"], shifts_raw_data[shifts_column_names[0]]
        )
        if index is not None and shift_name is not None and shift_name != ""
    ]

    # Creating a list of tuples to represent different work shifts.
    # Each tuple contains an index and a corresponding shift time.
    shift_time_data = []
    seen_shift_times = set()
    for index, shift_time in zip(
        shifts_raw_data["index"], shifts_raw_data[shifts_column_names[1]]
    ):
        if (
            shift_time is not None
            and shift_time != ""
            and shift_time not in seen_shift_times
        ):
            shift_time_data.append((int(index), shift_time))
            seen_shift_times.add(shift_time)

    shift_min_data = [
        (int(index), int(shift_min))
        for index, shift_min in zip(
            shifts_raw_data["index"], shifts_raw_data[shifts_column_names[2]]
        )
        if shift_min is not None
    ]

    shift_max_data = [
        (int(index), int(shift_max))
        for index, shift_max in zip(
            shifts_raw_data["index"], shifts_raw_data[shifts_column_names[3]]
        )
        if shift_max is not None
    ]

    shift_capacity_data = [
        (int(index), (min_capacity, max_capacity))
        for (index, min_capacity, max_capacity) in zip(
            shifts_raw_data["index"], shift_min_data, shift_max_data
        )
    ]

    shift_category_data = [
        (int(index), int(shift_category))
        for index, shift_category in zip(
            shifts_raw_data["index"], shifts_raw_data[shifts_column_names[4]]
        )
        if shift_category is not None and shift_category != ""
    ]

    sv_shift_min_data = [
        (int(index), int(shift_min))
        for index, shift_min in zip(
            shifts_raw_data["index"], shifts_raw_data[shifts_column_names[5]]
        )
        if shift_min is not None
    ]

    sv_shift_max_data = [
        (int(index), int(shift_max))
        for index, shift_max in zip(
            shifts_raw_data["index"], shifts_raw_data[shifts_column_names[6]]
        )
        if shift_max is not None
    ]

    sv_shift_capacity_data = [
        (int(index), (min_capacity, max_capacity))
        for (index, min_capacity, max_capacity) in zip(
            shifts_raw_data["index"], sv_shift_min_data, sv_shift_max_data
        )
    ]

    # Creating a list of tuples to represent shift rankings.
    # Each tuple contains a ranking and a corresponding tuple of shift indices.
    # This assigns a priority or preference order to different shifts
    shift_ranking_list = [
        (
            1,
            (0, 1, 2, 3),
        ),  # The shifts at indices 0, 1, 2, and 3 are assigned a ranking of 1
        (
            2,
            (4, 5, 6, 7),
        ),  # The shifts at indices 4, 5, 6, 7, 20, 21, 22, and 23 are assigned a ranking of 2
        (
            3,
            (8, 9, 10, 11, 22, 23),
        ),  # The shifts at indices 8, 9, 10, and 11 are assigned a ranking of 3
        (
            4,
            (12, 13, 14, 15, 16, 17, 18, 19, 20, 21),
        ),  # The shifts at indices 12, 13, 14, 15, 16, 17, 18, and 19 are assigned a ranking of 4
        # Add more shift rankings here
    ]

    # Creating a list of tuples to represent rankings for different shift types.
    # Each tuple contains a ranking and a corresponding tuple of shift type indices.
    # This assigns a priority  or preference order to different shift types,
    shift_type_ranking_list = [
        (1, (0,)),  # The shift type at index 2 is assigned a ranking of 1
        (3, (1, 3)),  # The shift types at indices 1 and 3 are assigned a ranking of 3
        (9, (2,)),  # The shift type at index 0 is assigned a ranking of 9
        # Add more shift type rankings here
    ]

    shifts_data = {
        "shift_date_data": shift_date_data,
        "shift_time_data": shift_time_data,
        "shift_capacity_data": shift_capacity_data,
        "shift_ranking_data": shift_ranking_list,
        "shift_type_ranking_data": shift_type_ranking_list,
        "shift_category_data": shift_category_data,
        "sv_shift_capacity_data": sv_shift_capacity_data,
    }
    return people_data, shifts_data


def createFile(
    best_solution,
    name_list,
    individual_costs,
    shift_name_list,
    dates_list,
    output_buffer,
):
    workbook = openpyxl.Workbook()
    worksheet = workbook.active
    worksheet.title = "Shifts"

    # Write shift names as headers
    for col_index, _ in enumerate(best_solution):
        shift_name = shift_name_list[col_index % len(shift_name_list)][1]
        cell = worksheet.cell(row=1, column=col_index * 2 + 2)
        cell.value = col_index
        for dates in dates_list:
            if dates[0] == col_index:
                day_name = dates[1]
                cell1 = worksheet.cell(row=2, column=col_index * 2 + 2)
                cell1.value = day_name
        cell2 = worksheet.cell(row=3, column=col_index * 2 + 2)
        cell2.value = shift_name

    name_colors = {}
    white_font = Font(color="FFFFFF")
    dark_font = Font(color="000000")

    # Track the maximum row needed to accommodate the longest shift
    max_row = 4

    for col_index, shift in enumerate(best_solution, start=1):
        row_index = 4

        for shift_type in shift:
            # Write shift type header
            shift_type_header_cell = worksheet.cell(row=row_index, column=col_index * 2)
            shift_type_header_cell.value = shift_type
            shift_type_header_cell.font = dark_font
            row_index += 1

            # Sort and write shift names for the shift type
            shift_names = sorted(
                [
                    next(name for index, name in name_list if index == person)
                    for person in shift[shift_type]
                ]
            )
            for name in shift_names:
                index = next(
                    index
                    for index, name_list_name in name_list
                    if name_list_name == name
                )
                name_cell = worksheet.cell(row=row_index, column=col_index * 2)
                name_cell.value = name
                if name not in name_colors:
                    color = ColorHash(name).hex
                    color = "FF" + color[1:]
                    name_colors[name] = PatternFill(
                        start_color=color, end_color=color, fill_type="solid"
                    )
                name_cell.fill = name_colors[name]
                name_cell.font = white_font

                cost_cell = worksheet.cell(row=row_index, column=col_index * 2 + 1)
                cost_cell.fill = name_colors[name]
                cost_cell.value = individual_costs[index]
                cost_cell.font = white_font

                row_index += 1

        # Update the max row if necessary
        if row_index > max_row:
            max_row = row_index

    # Add row numbers for the shifts
    for row in range(5, max_row):
        cell = worksheet.cell(row=row, column=1)
        cell.value = row - 4
        cell.font = dark_font

    # Create a new worksheet for the cost details
    cost_details_sheet = workbook.create_sheet(title="Cost Details")

    # Write the cost details to the new worksheet, split at ":" and "="
    cost_details = output_buffer.split("\n")
    for row_index, line in enumerate(cost_details, start=1):
        parts = [part.strip() for part in line.replace("=", ":").split(":")]
        for col_index, part in enumerate(parts, start=1):
            cell = cost_details_sheet.cell(row=row_index, column=col_index)
            # Try to convert to integer or float
            try:
                if "." in part:
                    cell.value = float(part)
                else:
                    cell.value = int(part)
            except ValueError:
                cell.value = part

    # Get the current time
    now = datetime.now()
    now_str = now.strftime("%H-%M-%S")

    # Save the workbook with the formatted time in the filename
    workbook.save(now_str + "_shifts.xlsx")

def convert_names_to_indices(shift_data, name_list):
    converted_shift_data = {}
    for shift_index in shift_data:
        converted_shift_data[shift_index] = {}
        for shift_type in shift_data[shift_index]:
            converted_shift_data[shift_index][shift_type] = [
                next(index for index, name in name_list if name == person_name)
                for person_name in shift_data[shift_index][shift_type]
            ]
    return converted_shift_data

def reconstruct_solution_matrix(converted_shift_data, num_shifts, num_shift_types):
    solution = [
        {shift_type: set() for shift_type in range(num_shift_types)}
        for _ in range(num_shifts)
    ]
    for shift_index in converted_shift_data:
        for shift_type in converted_shift_data[shift_index]:
            solution[shift_index][shift_type] = set(converted_shift_data[shift_index][shift_type])
    return solution



def load_excel_and_create_solution(file_path, dates_list, name_list, shift_types):
    workbook = openpyxl.load_workbook(file_path)
    worksheet = workbook["Shifts_RAW"]

    num_shifts = len(dates_list)
    # Read the shift data from the worksheet
    solution_matrix  = [
        {shift_type: set() for shift_type in shift_types}
        for _ in range(num_shifts)
    ]
    
    current_shift_type = None
    shift_index = -1

    for col in range(1, worksheet.max_column + 1, 2): 
        shift_index += 1
        current_shift_type = None
        for row in range(1, worksheet.max_row + 1):
            cell_value = worksheet.cell(row=row, column=col).value

            if cell_value is None:
                continue

            if cell_value in shift_types:
                current_shift_type = cell_value
            elif current_shift_type is not None:
                name = cell_value
                index = next((i for i, name_tuple in enumerate(name_list) if name_tuple[1] == name), None)
                if index is not None:
                    solution_matrix[shift_index][current_shift_type].add(index)
         

    return solution_matrix


