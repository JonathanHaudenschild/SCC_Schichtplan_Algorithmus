from datetime import datetime, timezone, timedelta


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
    Convert a time object to the total seconds since midnight.
    """
    if isinstance(ts, (int, float)):
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
    else:
        dt = ts
    return dt.hour * 3600 + dt.minute * 60 + dt.second


def seconds_since_midnight_to_time(seconds):
    """
    Convert total seconds since midnight back to a time object.
    """
    return (datetime.min + timedelta(seconds=seconds)).time()


def convert_time(data):
    return [(id, time_to_seconds_since_midnight(time)) for id, time in data]


def transform_times_data(unavailability_data):
    return [
        (
            id,
            [
                (datetime_to_timestamp(start), datetime_to_timestamp(end))
                for start, end in dates
            ],
        )
        for id, dates in unavailability_data
    ]


def transform_shift_preference_data(shift_preference_data):
    print(shift_preference_data)

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
    people_transformed_data = {
        "name_dict": create_dict_from_list(people_data["name_data"]),
        "person_capacity_dict": create_dict_from_list(people_data["capacity_data"]),
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
        "experience_dict": create_dict_from_list(people_data["experience_data"]),
        "minimum_break_dict": create_dict_from_list(
            convert_time(people_data["minimum_break_data"])
        ),
        "preference_dict": create_dict_from_list(people_data["preference_data"]),
        "people_shift_types_dict": create_dict_from_list(
            people_data["shift_types_data"]
        ),
        "shift_preference_dict": create_dict_from_list(
            transform_shift_preference_data(people_data["shift_preference_data"])
        ),
    }

    return people_transformed_data


def transform_shifts_data(shifts_data):
    shifts_transformed_data = {
        "shift_time_dict": create_dict_from_list(
            convert_datetimes(shifts_data["shift_time_data"])
        ),
        "shift_capacity_dict": create_dict_from_list(
            shifts_data["shift_capacity_data"]
        ),
        "shift_type_dict": create_dict_from_list(shifts_data["shift_type_data"]),
        "restrict_shift_type_dict": create_dict_from_list(
            shifts_data["restrict_shift_type_data"]
        ),
        "shift_priority_dict": create_dict_from_list(
            shifts_data["shift_priority_data"]
        ),
        "shift_cost_dict": create_dict_from_list(shifts_data["shift_cost_data"]),
    }

    return shifts_transformed_data


def create_total_friends_array(preference_list):
    total_friends_array = {}

    for person, preferences in preference_list.items():
        total_friends_array[person] = 0
        if preferences[1] < 0:
            total_friends_array[person] += 1

    return total_friends_array
