from datetime import datetime, timezone, timedelta, time


NUM_OF_SHIFTS_PER_PERSON = 5
NUM_OF_SHIFTS_PER_SV = 2


create_dict_from_list = lambda data: {id: value for id, value in data}


def datetime_to_timestamp(dt):
    """
    Convert a datetime object to a singular integer representing the total seconds since the epoch.
    """
    return int(dt.replace(tzinfo=timezone.utc).timestamp())


def convert_datetimes(data):
    return [
        (id, (datetime_to_timestamp(start), datetime_to_timestamp(end)))
        for id, (start, end) in data
    ]


def time_to_seconds_since_midnight(ts):
    """
    Convert a time object or a timestamp to the total seconds since midnight.
    """
    try:
        if isinstance(ts, (int, float)):
            # Convert timestamp to datetime
            dt = datetime.fromtimestamp(ts, tz=timezone.utc).time()
        elif isinstance(ts, time):
            # ts is already a time object, so use it directly
            dt = ts
        elif isinstance(ts, datetime):
            # ts is already a time object, so use it directly
            dt = ts
        else:
            raise ValueError(f"Invalid time format: {ts}")

        # Convert the time object to seconds since midnight
        return dt.hour * 3600 + dt.minute * 60 + dt.second
    except Exception as e:
        print(f"Error converting time: {e}")
        return None  # Return None or raise the exception, depending on your needs


def seconds_since_midnight_to_time(seconds):
    """
    Convert total seconds since midnight back to a time object.
    """
    try:
        return (datetime.min + timedelta(seconds=seconds)).time()
    except Exception as e:
        print(f"Error converting seconds to time: {e}")
        return None  # Return None or raise the exception, depending on your needs


def convert_time(data):
    converted_data = []
    for id, time in data:
        try:
            converted_time = time_to_seconds_since_midnight(time)
            if converted_time is not None:
                converted_data.append((id, converted_time))
            else:
                print(f"Skipping id {id} due to conversion error.")
        except Exception as e:
            print(f"Error converting time for id {id} with time '{time}': {e}")
            continue  # Skip this entry if an error occurs
    return converted_data



def calculate_total_shift_capacity(shift_type_dict, shift_capacity_dict):
    """
    Calculate total shift capacity for each shift type.
    
    Args:
        shift_type_dict (dict): A dictionary mapping shifts to their types.
        shift_capacity_dict (dict): A dictionary mapping shifts to their capacities (as tuples).
        
    Returns:
        dict: A dictionary with total capacities for each shift type.
    """
    shift_types_capacity = {}
    
    for shift, shift_type in shift_type_dict.items():
        # Initialize the shift type capacity if it doesn't exist
        if shift_type not in shift_types_capacity:
            shift_types_capacity[shift_type] = [0, 0]  # Changed to a list to allow in-place modification
        
        # Add the capacity for the shift to the total capacity for its type
        shift_types_capacity[shift_type][0] += shift_capacity_dict[shift][0]
        shift_types_capacity[shift_type][1] += shift_capacity_dict[shift][1]
        
    return shift_types_capacity

def calculate_total_capacity_needed(person_capacity_dict, people_shift_types_dict):
    """
    Calculate the total capacity needed for each shift type.
    
    Args:
        person_capacity_dict (dict): A dictionary mapping people to their capacity requirements.
        people_shift_types_dict (dict): A dictionary mapping people to their preferred shift types.
        
    Returns:
        dict: A dictionary with total capacities needed for each shift type.
    """
    total_capacity = {}

    for person, capacity in person_capacity_dict.items():
        for shift_type, shift in people_shift_types_dict[person].items():
            if shift_type not in total_capacity:
                total_capacity[shift_type] = [0, 0]  # Changed to a list to allow in-place modification
                
            total_capacity[shift_type][0] += shift[0]
            total_capacity[shift_type][1] += shift[1]

    return total_capacity

def transform_times_data(unavailability_data):
    earliest_date = datetime(1970, 1, 1)  # Use UNIX epoch as the earliest date
    latest_date = datetime(
        9999, 12, 31, 23, 59, 59
    )  # Use a far future date as the latest date

    transformed_data = []

    for id, dates in unavailability_data:
        try:
            if dates is None:
                continue  # Skip if dates is None or not a list
            
            if not isinstance(dates, list):
                continue  # Skip if dates is None or not a list

            transformed_dates = []
            for start, end in dates:
                try:
                    if start is None and end is None:
                        continue  # Skip this pair
                    if start is None:
                        start = earliest_date  # Use earliest possible date
                    if end is None:
                        end = latest_date  # Use latest possible date

                    transformed_dates.append(
                        (datetime_to_timestamp(start), datetime_to_timestamp(end))
                    )
                except Exception as e:
                    print(
                        f"Error processing start-end pair (start: {start}, end: {end}) for id {id}: {e}"
                    )
                    continue  # Skip this pair if an error occurs

            transformed_data.append((id, transformed_dates))

        except Exception as e:
            print(f"Error processing dates for id {id}: {e}")
            continue  # Skip this entry if an error occurs

    return transformed_data


def transform_shift_preference_data(shift_preference_data):
    return [
        (
            id,
            [
                (
                    [
                        (
                            time_to_seconds_since_midnight(date[0][0]),
                            time_to_seconds_since_midnight(date[0][1]),
                        )
                    ],
                    date[1],
                )
                for date in dates
            ],
        )
        for id, dates in shift_preference_data
    ]


def transform_people_data(people_data):
    person_capacity_dict = create_dict_from_list(people_data["capacity_data"])
    people_shift_types_dict = create_dict_from_list(people_data["shift_types_data"])
    people_transformed_data = {
        "name_dict": create_dict_from_list(people_data["name_data"]),
        "person_capacity_dict": person_capacity_dict,
        "unavailability_dict": create_dict_from_list(
            transform_times_data(people_data["unavailability_data"])
        ),
        "mandatory_dict": create_dict_from_list(
            transform_times_data(people_data["mandatory_data"])
        ),
        "off_shifts_dict": create_dict_from_list(
            transform_times_data(people_data["day_off_data"])
        ),
        "gender_dict": create_dict_from_list(people_data["gender_data"]),
        # "experience_dict": create_dict_from_list(people_data["experience_data"]),
        "minimum_break_dict": create_dict_from_list(
            convert_time(people_data["minimum_break_data"])
        ),
        "preference_dict": create_dict_from_list(people_data["preference_data"]),
        "people_shift_types_dict": people_shift_types_dict,
        "shift_preference_dict": create_dict_from_list(
            transform_shift_preference_data(people_data["shift_preference_data"])
        ),
        "total_capacity": calculate_total_capacity_needed(
            person_capacity_dict, people_shift_types_dict
        ),
    }

    return people_transformed_data


def transform_shifts_data(shifts_data):
    shift_type_dict = create_dict_from_list(shifts_data["shift_type_data"])
    shift_capacity_dict = create_dict_from_list(shifts_data["shift_capacity_data"])
    shifts_transformed_data = {
        "shift_time_dict": create_dict_from_list(
            convert_datetimes(shifts_data["shift_time_data"])
        ),
        "shift_capacity_dict": shift_capacity_dict,
        "shift_type_dict": shift_type_dict,
        "restrict_shift_type_dict": create_dict_from_list(
            shifts_data["restrict_shift_type_data"]
        ),
        "shift_priority_dict": create_dict_from_list(
            shifts_data["shift_priority_data"]
        ),
        "shift_cost_dict": create_dict_from_list(shifts_data["shift_cost_data"]),
        "total_capacity": calculate_total_shift_capacity(shift_type_dict, shift_capacity_dict),
    }

    return shifts_transformed_data



def create_total_friends_array(preference_list):
    total_friends_array = {}

    for person, preferences in preference_list.items():
        total_friends_array[person] = 0
        if preferences[1] < 0:
            total_friends_array[person] += 1

    return total_friends_array
