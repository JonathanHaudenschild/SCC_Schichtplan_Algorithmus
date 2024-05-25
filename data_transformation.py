
NUM_OF_SHIFTS_PER_PERSON = 5
NUM_OF_SHIFTS_PER_SV = 2

def transform_data(people_data, shifts_data):
    num_of_shifts = len(shifts_data["shift_date_data"])
    num_people = len(people_data["name_data"])
    num_of_shift_types = len(shifts_data["shift_time_data"])
    preference_matrix = create_preference_matrix(
        people_data["preference_data"], num_people
    )

    people_transformed_data = {
        "name_array": people_data["name_data"],
        "person_capacity_array": create_persons_capacity_array(
            people_data["capacity_data"], num_people
        ),
        "preference_matrix": preference_matrix,
        "unavailability_matrix": create_unavailability_matrix(
            people_data["unavailability_data"], num_of_shifts, num_people
        ),
        "off_shifts_matrix": create_unavailability_matrix(
            people_data["off_shifts_data"], num_of_shifts, num_people
        ),
        "preferred_shift_matrix": create_preferred_shift_matrix(
            people_data["shift_preference_data"], num_of_shift_types, num_people
        ),
        "preferred_shift_category_array": create_preferred_shift_category_array(
            people_data["preferred_shift_category_data"], num_people
        ),
        "gender_array": create_gender_array(people_data["gender_data"], num_people),
        "experience_array": create_experience_array(
            people_data["experience_data"], num_people
        ),
        "minimum_array": create_minimum_array(people_data["minimum_data"], num_people),
        "total_friends": create_total_friends_array(
            people_data["preference_data"], num_people
        ),
        "sv_array": create_sv_array(people_data["sv_data"], num_people),
        "sv_experience_array": create_sv_experience_array(people_data["sv_experience_data"], num_people),
        "sv_capacity_array": create_sv_capacity_array(people_data["sv_capacity_data"], num_people)
    }

    shifts_transformed_data = {
        "shift_date_array": shifts_data["shift_date_data"],
        "shift_time_array": shifts_data["shift_time_data"],
        "shift_capacity_matrix": create_shift_capacity_matrix(
            shifts_data["shift_capacity_data"], num_of_shifts
        ),
        "ranking_array": create_ranking_array(
            shifts_data["shift_ranking_data"],
            shifts_data["shift_type_ranking_data"],
            num_of_shifts,
            num_of_shift_types,
        ),
        "shift_category_array": create_shift_category_array(
            shifts_data["shift_category_data"], num_of_shifts
        ),
        "shift_type_array": shifts_data["shift_type_ranking_data"],
        "shift_sv_capacity_matrix": create_shift_sv_capacity_matrix(
            shifts_data["sv_shift_capacity_data"], num_of_shifts
        )
    }
    return people_transformed_data, shifts_transformed_data


def create_preference_matrix(preference_list, num_people):
    preference_matrix = [[0 for _ in range(num_people)] for _ in range(num_people)]
    for person1, person2, preference in preference_list:
        preference_matrix[person1][person2] = preference
        preference_matrix[person2][person1] = preference
    return preference_matrix


def create_persons_capacity_array(capacity_list, num_people):
    capacity_array = [NUM_OF_SHIFTS_PER_PERSON] * num_people
    for capacity in capacity_list:
        capacity_array[capacity[0]] = capacity[1]
    return capacity_array


def create_preferred_shift_matrix(pref_shift_list, num_of_shift_types, num_people):
    matrix = [[1] * num_of_shift_types for _ in range(num_people)]
    for person, shift_values in pref_shift_list:
        matrix[person] = list(shift_values)
    return matrix


def create_preferred_shift_category_array(pref_shift_category_list, num_people):
    pref_shift_category_array = [0] * num_people
    for pref_shift_category in pref_shift_category_list:
        pref_shift_category_array[pref_shift_category[0]] = pref_shift_category[1]
    return pref_shift_category_array


def create_experience_array(experience_list, num_people):
    experience_array = [1] * num_people
    for experience in experience_list:
        experience_array[experience[0]] = experience[1]
    return experience_array


def create_minimum_array(minimum_list, num_people):
    minimum_array = [0] * num_people
    for minimum in minimum_list:
        minimum_array[minimum[0]] = minimum[1]
    return minimum_array


def create_gender_array(gender_list, num_people):
    gender_array = [0] * num_people
    for gender in gender_list:
        gender_array[gender[0]] = gender[1]
    return gender_array


def create_shift_category_array(shift_category_list, num_of_shifts):
    shift_category_array = [0] * num_of_shifts
    for shift_category in shift_category_list:
        shift_category_array[shift_category[0]] = shift_category[1]
    return shift_category_array


def create_unavailability_matrix(unavailability_list, num_of_shifts, num_people):
    unavailability_matrix = [
        [0 for _ in range(num_of_shifts)] for _ in range(num_people)
    ]
    for person, shifts in unavailability_list:
        for shift in shifts:
            unavailability_matrix[person][shift] = 1
    return unavailability_matrix


def create_shift_capacity_matrix(shift_capacity_list, num_of_shifts):
    shift_capacity_matrix = [[0 for _ in range(num_of_shifts)] for _ in range(2)]
    for shift, capacity in shift_capacity_list:
        shift_capacity_matrix[0][shift] = capacity[0]
        shift_capacity_matrix[1][shift] = capacity[1]
    return shift_capacity_matrix


def create_ranking_array(
    shift_ranking_list, shift_type_ranking_list, num_of_shifts, num_of_shift_types
):
    cost_array = [0] * num_of_shifts
    for cost, shifts in shift_ranking_list:
        for shift_index in shifts:
            for type_cost, shifts in shift_type_ranking_list:
                for shift in shifts:
                    if shift_index % num_of_shift_types == shift:
                        cost_array[shift_index] = type_cost * cost
    return cost_array


def create_total_friends_array(preference_list, num_people):
    total_friends_array = [0] * num_people
    for person1, person2, preference in preference_list:
        if preference < 0:
            total_friends_array[person1] += 1
    return total_friends_array

def create_sv_array(sv_list, num_people):
    sv_array = [0] * num_people
    for sv in sv_list:
        sv_array[sv[0]] = sv[1]
    return sv_array

def create_sv_experience_array(sv_experience_list, num_people):
    sv_experience_array = [0] * num_people
    for sv_experience in sv_experience_list:
        sv_experience_array[sv_experience[0]] = sv_experience[1]
    return sv_experience_array

def create_sv_capacity_array(sv_capacity_list, num_people):
    sv_capacity_array = [0] * num_people
    for sv_capacity in sv_capacity_list:
        sv_capacity_array[sv_capacity[0]] = sv_capacity[1]
    return sv_capacity_array

def create_shift_sv_capacity_matrix(shift_sv_list, num_of_shifts):
    shift_sv_capacity_matrix = [[0 for _ in range(num_of_shifts)] for _ in range(2)]
    for shift, capacity in shift_sv_list:
        shift_sv_capacity_matrix[0][shift] = capacity[0]
        shift_sv_capacity_matrix[1][shift] = capacity[1]
    return shift_sv_capacity_matrix