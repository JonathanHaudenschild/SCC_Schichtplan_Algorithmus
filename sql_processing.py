from datetime import datetime, time
import math

# Import the work_type_mapping and the helper function
from subbotnik_helpers import (
    work_type_mapping,
    get_work_type_name,
    get_shift_importance_integer,
)


def process_supporter_data(db_connection, project_id, states, periods):
    cursor = db_connection.cursor()

    # SQL query to retrieve supporter data
    supporters_query = f"""
        SELECT sp.id as supporterProjectId,
               sg.name as groupName,
               p.start_at as periodStart,
               ifnull(ewd.date, p.end_at) as periodEnd,
               p.name as periodName,
               group_concat(wt.name separator ',') as workTypes,
               min(timestamp(date(do.date))) AS dayOffStart,
               max(timestamp(date(do.date), '33:00:00')) AS dayOffEnd
        FROM supporter_project sp
        LEFT JOIN supporter_group sg ON sp.supporter_group_id = sg.id
        LEFT JOIN supporter_project_work_type spwt ON spwt.supporter_project_work_types_id = sp.id
        LEFT JOIN work_type wt ON wt.id = spwt.work_type_id
        LEFT JOIN days_off_preset dop ON sp.days_off_preset_id = dop.id
        LEFT JOIN days_off_preset_day_off dopdo ON dopdo.days_off_preset_days_off_id = dop.id
        LEFT JOIN day_off do ON dopdo.day_off_id = do.id
        JOIN period p ON sp.period_id = p.id
        LEFT JOIN extra_working_day ewd ON sp.extra_working_day_id = ewd.id AND ewd.period_id = p.id
        WHERE sp.project_id = %s
        AND sp.state IN ({','.join(['%s'] * len(states))})
        AND p.name IN ({','.join(['%s'] * len(periods))})
        GROUP BY sp.id, sg.name, p.start_at, ifnull(ewd.date, p.end_at), p.name
    """

    params = [project_id] + states + periods
    cursor.execute(supporters_query, params)

    rows = cursor.fetchall()

    # Preparing the data lists
    name_data = []
    capacity_data = []
    shift_types_data = []
    day_off_data = []
    minimum_break_data = []
    preference_data = []
    unavailability_data = []
    shift_preference_data = []

    for row in rows:
        (
            supporterProjectId,
            groupName,
            periodStart,
            periodEnd,
            periodName,
            workTypes,
            dayOffStart,
            dayOffEnd,
        ) = row

        # name_data corresponds to supporterProjectId
        name_data.append((supporterProjectId, supporterProjectId))

        # capacity_data corresponds to shiftsNeeded
        shiftsNeeded = 2
        capacity_data.append((supporterProjectId, (shiftsNeeded, shiftsNeeded)))

        # shift_types_data construction
        shift_type_dict = {}

        if workTypes is not None:
            # Add steward shifts if applicable
            if "steward" in workTypes:
                mapped_work_type = work_type_mapping[workType]
                shift_type_dict[mapped_work_type] = (0, shiftsNeeded, shiftsNeeded)

            # Add bottleDeposit shifts if applicable
            if "bottleDeposit" in workTypes:
                mapped_work_type = work_type_mapping[workType]
                shift_type_dict[mapped_work_type] = (0, shiftsNeeded, shiftsNeeded)

        # Add work types
        if workTypes:
            workTypeList = workTypes.split(",")
            for workType in workTypeList:
                workType = workType.strip()  # Clean up any surrounding whitespace
                if workType in work_type_mapping:
                    mapped_work_type = work_type_mapping[workType]
                    shift_type_dict[mapped_work_type] = (0, 0, 0)
                else:
                    print(
                        f"Warning: Work type '{workType}' is not recognized and will be ignored."
                    )

        shift_types_data.append((supporterProjectId, shift_type_dict))

        # day_off_data corresponds to dayOffStart and dayOffEnd
        day_off_data.append((supporterProjectId, (dayOffStart, dayOffEnd)))

        # minimum_break_data - standard 12 hours
        minimum_break_data.append((supporterProjectId, time(12, 0, 0)))

        # preference_data - pick others with the same groupName
        cursor.execute(
            "SELECT id FROM supporter_project WHERE supporter_group_id IN (SELECT id FROM supporter_group WHERE name = %s)",
            (groupName,),
        )
        same_group_ids = [result[0] for result in cursor.fetchall()]
        preferences = [(gid, -1) for gid in same_group_ids if gid != supporterProjectId]
        preference_data.append((supporterProjectId, preferences))

        # unavailability_data - periods before periodStart or after periodEnd
        start_of_time = datetime(1970, 1, 1)
        end_of_time = datetime(9999, 12, 31, 23, 59, 59)

        unavailability_periods = []
        if periodStart:
            unavailability_periods.append((start_of_time, periodStart))
        if periodEnd:
            unavailability_periods.append((periodEnd, end_of_time))

        unavailability_data.append((supporterProjectId, unavailability_periods))

        # Add to shift_preference_data
        preferences = [
            ((time(20, 0, 0), time(6, 0, 0)), 10),
            ((time(6, 0, 0), time(20, 0, 0)), 0),
        ]
        shift_preference_data.append((supporterProjectId, preferences))

    print(name_data)
    print(capacity_data)
    print(shift_types_data)
    print(day_off_data)
    print(minimum_break_data)
    print(preference_data)
    print(unavailability_data)
    print(shift_preference_data)

    # Returning the data in the required format
    return {
        "name_data": name_data,
        "capacity_data": capacity_data,
        "shift_types_data": shift_types_data,
        "day_off_data": day_off_data,
        "unavailability_data": unavailability_data,  # Filled with before periodStart and after periodEnd
        "minimum_break_data": minimum_break_data,
        "preference_data": preference_data,
        "shift_preference_data": shift_preference_data,  # Default data
        "gender_data": [],  # Default data
        "experience_data": [],  # Default data
        "mandatory_data": [],  # Default data
    }


def process_supporter_shifts_data(db_connection, project_id, shifts_start, shifts_end):
    cursor = db_connection.cursor()

    # SQL query to retrieve shift data
    shifts_query = f"""
        SELECT s.id as shiftId,
               s.start_at as startAt,
               s.end_at as endAt,
               s.slots as slots,
               if(l.stewards_needed or s.only_stewards, 1, 0) as stewards,
               s.bottle_deposit as bottleDeposit,
               wt.name as workType,
               l.name as location,
               s.importance as importance,
               s.overloadable as overloadable
        FROM shift s
        LEFT JOIN location l on s.location_id = l.id
        LEFT JOIN work_type wt on l.work_type_id = wt.id
        WHERE s.project_id = {'%s'}
        AND s.start_at >= {'%s'}
        AND s.start_at <= {'%s'}
        AND s.enabled = 1
    """

    params = [project_id, shifts_start, shifts_end]
    cursor.execute(shifts_query, params)

    rows = cursor.fetchall()

    # Preparing the data lists
    shift_time_data = []
    shift_capacity_data = []
    shift_type_data = []
    shift_priority_data = []
    restrict_shift_type_data = []
    shift_cost_data = []

    for row in rows:
        (
            shiftId,
            startAt,
            endAt,
            slots,
            stewards,
            bottleDeposit,
            workType,
            location,
            importance,
            overloadable,
        ) = row

        # shift_time_data
        shift_time_data.append((shiftId, (startAt, endAt)))

        # shift_capacity_data (slots used as min and max)
        if overloadable:
            shift_capacity_data.append(
                (shiftId, (0, math.ceil(slots + (slots * 0.0))))
            )  # 10% overload
        else:
            shift_capacity_data.append((shiftId, (slots, slots)))

        # shift_type_data
        if stewards:
            restrict_shift_type_data.append((shiftId, True))
            shift_type_data.append((shiftId, work_type_mapping[stewards]))
        elif bottleDeposit:
            restrict_shift_type_data.append((shiftId, True))
            shift_type_data.append((shiftId, work_type_mapping[bottleDeposit]))
        elif workType:
            shift_type_data.append((shiftId, work_type_mapping[workType]))

        # shift_priority_data
        shift_priority_data.append((shiftId, get_shift_importance_integer(importance)))

    # No equivalent in your example for restrict_shift_type or shift_cost_data
    # Assuming these fields are not necessary or not applicable in this context

    return {
        "shift_time_data": shift_time_data,
        "shift_capacity_data": shift_capacity_data,
        "shift_type_data": shift_type_data,
        "shift_priority_data": shift_priority_data,
        "restrict_shift_type_data": restrict_shift_type_data,
        "shift_cost_data": shift_cost_data,  # Default data, if applicable
    }


def write_to_db(db_connection, project_id, schedule):
    print("Writing to database...")
    print(schedule)

    cursor = db_connection.cursor()

    # Delete previous automatically created entries
    delete_queries = [
        """
        DELETE FROM shift_supporter_project_event
        WHERE shift_supporter_project_id IN (
            SELECT id FROM shift_supporter_project 
            WHERE shift_id IN (
                SELECT id FROM shift 
                WHERE project_id = %s AND created_automatically = 1
            )
        )
        """,
        """
        DELETE FROM shift_supporter_project 
        WHERE shift_id IN (
            SELECT id FROM shift 
            WHERE project_id = %s AND created_automatically = 1
        )
        """,
    ]

    # Execute delete queries
    for query in delete_queries:
        cursor.execute(query, (project_id,))

    db_connection.commit()

    # Insert new entries
    insert_shift_supporter_query = """
        INSERT INTO shift_supporter_project 
        (version, created_automatically, active, shift_id, supporter_project_id, got_food_stamp) 
        VALUES (0, true, true, %s, %s, false)
    """

    insert_event_query = """
        INSERT INTO shift_supporter_project_event 
        (version, created_at, created_by_id, shift_supporter_project_id, state) 
        VALUES (0, %s, 3, %s, 'ASSIGNED')
    """

    for shift_id, supporter_ids in schedule.items():
        for supporter_id in supporter_ids:
            cursor.execute(insert_shift_supporter_query, (shift_id, supporter_id))
            last_id = cursor.lastrowid
            current_time = datetime.now()
            cursor.execute(insert_event_query, (current_time, last_id))

    db_connection.commit()
