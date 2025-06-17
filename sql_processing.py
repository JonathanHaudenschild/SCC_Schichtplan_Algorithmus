from datetime import datetime, time
import math
import os
from enum import Enum

# Import the work_type_mapping and the helper function
from subbotnik_helpers import (
    work_type_mapping,
    get_work_type_name,
    get_shift_importance_integer,
)

class ShiftOccurance(Enum):
    DAILY = 1
    WEEKLY = 2
    MONTHLY = 3
    YEARLY = 4
    WEEKENDS = 5
    NDays = 6


def process_supporter_data(db_connection, project_id, states, periods):
    cursor = db_connection.cursor()

    delete_previous_entries(db_connection, project_id)
    # SQL query to retrieve supporter data
    supporters_query = f"""
        SELECT sp.id as supporterProjectId,
            sp.supporter_id as supporter_id,
            sg.name as groupName,
            p.start_at as periodStart,
            ifnull(ewd.date, p.end_at) as periodEnd,
            p.name as periodName,
            ewd.date as extraWorkingDay,
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
        AND NOT EXISTS (
            SELECT 1
            FROM shift_supporter_project ssp
            WHERE ssp.supporter_project_id = sp.id
            AND ssp.active = 1
        )
        GROUP BY sp.id, sg.name, p.start_at, ifnull(ewd.date, p.end_at), p.name
    """

    params = [project_id] + states + periods
    cursor.execute(supporters_query, params)

    rows = cursor.fetchall()

    # Preparing the data lists
    name_data = []
    capacity_limits = []
    shift_types_data = []
    day_off_requests = []
    minimum_break_duration = []
    collaboration_preferences = []
    unavailability_periods = []
    time_preferences = []
    mandatory_coverage_periods = []
    number_of_bottle_deposit_people = 0
    number_of_steward_people = 0
    for row in rows:
        (
            supporterProjectId,
            supporter_id,
            groupName,
            periodStart,
            periodEnd,
            periodName,
            extraWorkingDay,
            workTypes,
            dayOffStart,
            dayOffEnd,
        ) = row

        # name_data corresponds to supporterProjectId
        name_data.append((supporterProjectId, supporter_id))

        # capacity_limits corresponds to shiftsNeeded
        shiftsNeeded = 13
        if periodName == "pre1":
            shiftsNeeded = 13
        elif periodName == "pre2":
            shiftsNeeded = 6
        elif periodName == "during":
            shiftsNeeded = 3
        elif periodName == "pre3":
            shiftsNeeded = 4
        elif periodName == "after":
            shiftsNeeded = 4

        capacity_limits.append((supporterProjectId, (shiftsNeeded, shiftsNeeded)))

        # shift_types_data construction
        shift_type_dict = {}

        # # Check if steward needs to be added to workTypes
        steward_check_query = """
            SELECT id
            FROM supporter_project
            WHERE steward_form_received = true
              AND project_id = %s
              AND supporter_id  = %s
        """
        cursor.execute(steward_check_query, (project_id, supporter_id,))
        steward_result = cursor.fetchall()

        # # Add "steward" to workTypes if the condition is met
        if steward_result:
            if workTypes:
                workTypes += ",steward"
            else:
                workTypes = "steward"

        # # Check if bottleDeposit needs to be added to workType

        if workTypes is not None:
            # Add steward shifts if applicable
            if "steward" in workTypes:
                mapped_work_type = work_type_mapping["steward"]
                if periodName == "pre2":
                    shift_type_dict[mapped_work_type] = (0, 1, shiftsNeeded)
                else:
                    shift_type_dict[mapped_work_type] = (0, 1, shiftsNeeded)
                number_of_steward_people += 1
            elif "bottleDeposit" in workTypes and not periodName == "after":
                mapped_work_type = work_type_mapping["bottleDeposit"]
                if periodName == "pre2":
                    shift_type_dict[mapped_work_type] = (0, 1, shiftsNeeded)
                else:
                    shift_type_dict[mapped_work_type] = (0, 1, shiftsNeeded)
                number_of_bottle_deposit_people += 1
           
            # Add work types
            
            if workTypes and "bottleDeposit" not in workTypes and "steward" not in workTypes:
                workTypeList = workTypes.split(",")
                for workType in workTypeList:
                    workType = workType.strip()  # Clean up any surrounding whitespace
                    if workType in work_type_mapping:
                        if workType == 'hygiene' and periodName == "pre1":
                            mapped_work_type = work_type_mapping["kitchen"]
                            shift_type_dict[mapped_work_type] = (0, 0, 1)
                        if workType == 'kitchen' and periodName == "pre1":
                            mapped_work_type = work_type_mapping["kitchen"]
                            shift_type_dict[mapped_work_type] = (0, 3, 5)
                        if workType == 'entrance' and periodName == "pre1":
                            mapped_work_type = work_type_mapping["entrance"]
                            shift_type_dict[mapped_work_type] = (0, 1, 2)
                        if workType == 'mobile' and periodName == "pre1":
                            mapped_work_type = work_type_mapping["mobile"]
                            shift_type_dict[mapped_work_type] = (0, 3, 5)
                        else:    
                            mapped_work_type = work_type_mapping[workType]
                            shift_type_dict[mapped_work_type] = (0, 0, 0)
                    else:
                        print(
                            f"Warning: Work type '{workType}' is not recognized and will be ignored."
                        )

        shift_types_data.append((supporterProjectId, shift_type_dict))
        # minimum_break_duration - standard 12 hours
        
        if periodName == "pre3":
            minimum_break_duration.append((supporterProjectId, time(9, 0, 0)))
        if periodName == "after":
            minimum_break_duration.append((supporterProjectId, time(9, 0, 0)))
        else:
            minimum_break_duration.append((supporterProjectId, time(12, 0, 0)))

        # collaboration_preferences - pick others with the same groupName
        cursor.execute(
            "SELECT id FROM supporter_project WHERE supporter_group_id IN (SELECT id FROM supporter_group WHERE name = %s)",
            (groupName,),
        )
        same_group_ids = [result[0] for result in cursor.fetchall()]
        preferences = [(gid, -1) for gid in same_group_ids if gid != supporterProjectId]
        collaboration_preferences.append((supporterProjectId, preferences))

        # unavailability_periods - periods before periodStart or after periodEnd
        start_of_time = datetime(1970, 1, 1)
        end_of_time = datetime(9999, 12, 31, 23, 59, 59)
        
        start_of_pre2 = datetime(2025, 6, 19, 0, 0, 0)
        
        start_of_pre3 = datetime(2025, 6, 23, 0, 0, 0)
        
        end_of_pre3 = datetime(2025, 6, 26, 23, 59, 0)
        
        start_of_during = datetime(2025, 6, 25, 10, 0, 0)
        
        end_of_during = datetime(2025, 6, 29, 23, 59, 0)
        if extraWorkingDay:
            end_of_during = extraWorkingDay

        start_of_after = datetime(2025, 6, 29, 12, 0, 0)

        unavailability = []
             # day_off_requests corresponds to dayOffStart and dayOffEnd
        unavailability.append((dayOffStart, dayOffEnd))

        if periodStart and periodName == "pre2":
            unavailability.append((start_of_time, start_of_pre2))
        if periodStart and periodName == "pre3":
            unavailability.append((start_of_time, start_of_pre3))
            unavailability.append((end_of_pre3, end_of_time))
        if periodStart and periodName == "during":
            unavailability.append((start_of_time, start_of_during))
            unavailability.append((end_of_during, end_of_time))
        elif periodStart and periodName == "after":
            unavailability.append((start_of_time, start_of_after))
        if periodEnd:
            unavailability.append((periodEnd, end_of_time))

        unavailability.append((dayOffStart, dayOffEnd))
        
        unavailability_periods.append((supporterProjectId, unavailability))

        # Add to time_preferences
        preferences = [
            ((time(8, 0, 0), time(12, 0, 0)), 4),
            ((time(22, 0, 0), time(8, 0, 0)), 9),
            ((time(18, 0, 0), time(22, 0, 0)), 5),
            ((time(12, 0, 0), time(18, 0, 0)), 0),
        ]
        time_preferences.append((supporterProjectId, preferences))

        # if periodName == "after":
        #     # Add to mandatory_coverage_periods
        #     monday_shift = (
        #         datetime(2025, 6, 29, 12, 0, 0),
        #         datetime(2025, 7, 1, 6, 0, 0),
        #     )
        #     mandatory_coverage_periods.append((supporterProjectId, monday_shift))

    shift_occurrence_rule = []
    # print(capacity_limits)
    # print(shift_types_data)
    # print(day_off_requests)
    # print(minimum_break_duration)
    # print(collaboration_preferences)
    # print(unavailability_periods)
    # print(time_preferences)
    print(number_of_bottle_deposit_people, number_of_steward_people)

    # Returning the data in the required format
    return {
        "name_data": name_data,
        "capacity_limits": capacity_limits,
        "shift_types_data": shift_types_data,
        "day_off_requests": day_off_requests,
        "unavailability_periods": unavailability_periods,  # Filled with before periodStart and after periodEnd
        "minimum_break_duration": minimum_break_duration,
        "shift_occurrence_rule": shift_occurrence_rule,
        "collaboration_preferences": collaboration_preferences,
        "time_preferences": time_preferences,  # Default data
        "gender_data": [],  # Default data
        "experience_level": [],  # Default data
        "mandatory_coverage_periods": mandatory_coverage_periods,  # Default data
    }


def process_supporter_shifts_data(db_connection, project_id, shifts_start, shifts_end):
    cursor = db_connection.cursor()

    # SQL query to retrieve shift data
    shifts_query = f"""
        SELECT 
            s.id as shiftId,
            s.start_at as startAt,
            s.end_at as endAt,
            GREATEST(s.slots - COUNT(DISTINCT ssp.id), 0) AS slots,
            IF(l.stewards_needed OR s.only_stewards, 1, 0) as stewards,
            s.bottle_deposit as bottleDeposit,
            wt.name as workType,
            l.name as location,
            s.importance as importance,
            s.overloadable as overloadable
        FROM shift s
        LEFT JOIN location l ON s.location_id = l.id
        LEFT JOIN work_type wt ON l.work_type_id = wt.id
        LEFT JOIN shift_supporter_project ssp ON ssp.shift_id = s.id AND ssp.active = 1
        WHERE s.project_id = %s
        AND s.start_at >= %s
        AND s.start_at <= %s
        AND s.enabled = 1
        GROUP BY s.id, s.start_at, s.end_at, s.slots, l.stewards_needed, s.only_stewards, 
                s.bottle_deposit, wt.name, l.name, s.importance, s.overloadable
        HAVING (s.slots - COUNT(DISTINCT ssp.id) > 0 OR s.overloadable = 1)
    """

    params = [project_id, shifts_start, shifts_end]
    cursor.execute(shifts_query, params)

    rows = cursor.fetchall()

    # Preparing the data lists
    shift_time_data = []
    shift_capacity_limits = []
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

        start_of_during = datetime(2025, 6, 25, 10, 0, 0)
        end_of_during = datetime(2025, 6, 29, 23, 59, 0)
        shift_is_during = (
            startAt >= start_of_during
            and startAt <= end_of_during
        )

        # shift_capacity_limits (slots used as min and max)
        if workType == 'mobile' and overloadable:
            upper_limit = math.ceil((slots))  # 100% overload
            shift_capacity_limits.append(
                (shiftId, (0, slots*2))
            )  # 100% overload
        elif workType == 'mobile' and not overloadable:
            upper_limit = math.ceil((slots))  # 100% overload
            shift_capacity_limits.append(
                (shiftId, (0, slots))
            )  # 100% overload
        elif workType == 'kitchen':
            shift_capacity_limits.append((shiftId, (slots, slots)))
        elif stewards:
            shift_capacity_limits.append((shiftId, (slots, slots)))
        elif bottleDeposit:
            shift_capacity_limits.append((shiftId, (slots, slots)))
        else:
            shift_capacity_limits.append((shiftId, (0, slots)))

        # shift_type_data
        if stewards:
            restrict_shift_type_data.append((shiftId, True))
            shift_type_data.append((shiftId, work_type_mapping["steward"]))
        elif bottleDeposit:
            restrict_shift_type_data.append((shiftId, True))
            shift_type_data.append((shiftId, work_type_mapping["bottleDeposit"]))
        elif workType:
            shift_type_data.append((shiftId, work_type_mapping[workType]))

        # shift_priority_data
        if stewards or bottleDeposit:
            shift_priority_data.append((shiftId, 10))
        else:
            shift_priority_data.append((shiftId, get_shift_importance_integer(importance)))

    # No equivalent in your example for restrict_shift_type or shift_cost_data
    # Assuming these fields are not necessary or not applicable in this context


    return {
        "shift_time_data": shift_time_data,
        "shift_capacity_limits": shift_capacity_limits,
        "shift_type_data": shift_type_data,
        "shift_priority_data": shift_priority_data,
        "restrict_shift_type_data": restrict_shift_type_data,
        "shift_cost_data": shift_cost_data,  # Default data, if applicable
    }

def delete_previous_entries(db_connection, project_id):
    cursor = db_connection.cursor()

    # Delete previous automatically created entries
    delete_queries = [
        """
        DELETE FROM shift_supporter_project_event
        WHERE shift_supporter_project_id IN (
            SELECT id FROM shift_supporter_project 
            WHERE created_automatically = 1
            AND import_identifier = 'TEST'
            AND shift_id IN (
                SELECT id FROM shift 
                WHERE project_id = %s
            )
        )
        """,
        """
        DELETE FROM shift_supporter_project 
        WHERE created_automatically = 1
        AND import_identifier = 'TEST'
        AND shift_id IN (
            SELECT id FROM shift 
            WHERE project_id = %s
        )
        """
    ]
    # Execute delete queries
    for query in delete_queries:
        cursor.execute(query, (project_id,))

    db_connection.commit()

def write_to_db(db_connection, project_id, schedule):
    print("Writing to database...")
    print(schedule)

    delete_previous_entries(db_connection, project_id)

    # Insert new entries
    insert_shift_supporter_query = """
        INSERT INTO shift_supporter_project 
        (version, created_automatically, active, shift_id, supporter_project_id, got_food_stamp, status, import_identifier) 
        VALUES (0, true, true, %s, %s, false, 'FINAL', %s)
    """

    insert_event_query = """
        INSERT INTO shift_supporter_project_event 
        (version, created_at, created_by_id, shift_supporter_project_id, state) 
        VALUES (0, %s, 3, %s, 'ASSIGNED')
    """
    
    
    cursor = db_connection.cursor()

    for shift_id, supporter_ids in schedule.items():
        for supporter_id in supporter_ids:
            cursor.execute(insert_shift_supporter_query, (shift_id, supporter_id, 'TEST'))
            last_id = cursor.lastrowid
            current_time = datetime.now()
            cursor.execute(insert_event_query, (current_time, last_id))

    db_connection.commit()

    # Prepare the output file
    output_file = "db_changes.txt"

    try:
        # Open the file in write mode
        with open(output_file, "w") as f:
            print(f"Writing to file: {output_file}")
            # Loop through the schedule and generate SQL insert statements
            for shift_id, supporter_ids in schedule.items():
                for supporter_id in supporter_ids:
                    # SQL for shift_supporter_project insert
                    insert_shift_supporter_query_text = f"""
    INSERT INTO shift_supporter_project 
    (version, created_automatically, active, shift_id, supporter_project_id, got_food_stamp, status, import_identifier) 
    VALUES (0, true, true, {shift_id}, {supporter_id}, false, 'FINAL', 'AUTO_GENERATED_250613');
    """
                    f.write(insert_shift_supporter_query_text)
                    print(
                        f"Wrote shift supporter insert for shift_id: {shift_id}, supporter_id: {supporter_id}"
                    )

                    # Simulate getting the last inserted ID
                    last_id_text = "LAST_INSERT_ID()"

                    # Get the current timestamp in string format
                    current_time_text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                    # SQL for shift_supporter_project_event insert
                    insert_event_query_text = f"""
    INSERT INTO shift_supporter_project_event 
    (version, created_at, created_by_id, shift_supporter_project_id, state) 
    VALUES (0, '{current_time_text}', 3, {last_id_text}, 'ASSIGNED');
    """
                    f.write(insert_event_query_text)
                    print(f"Wrote event insert for shift_id: {shift_id}")

        print(f"SQL insert statements have been successfully written to {output_file}.")
        print(f"Full path of the output file: {os.path.abspath(output_file)}")

    except Exception as e:
        print(f"An error occurred: {e}")
