# test_cost_calculator.py

import unittest
import numpy as np
from cost_calculation import time_frame_cost, SHIFT_RANKING_FACTOR
from datetime import time

class TestTimeFrameCost(unittest.TestCase):
    def setUp(self):
        """Set up mock data for the tests."""
        self.person_id = "person_1"
        self.assigned_shifts = [
            "1a",  # Will match the person's final preference
            "2b",  # Will match a preference that gets overwritten
            "4c",  # A night shift (22:00-06:00)
            "5d",  # Another night shift (01:00-08:00)
        ]

        self.shifts_data = {
            "shift_cost_dict": {
                "1a": 10,
                "2b": 15,
                "4c": 20,
                "5d": 25,
            },
            "shift_time_dict": {
                "1a": (time(7, 0), time(13, 0)),
                "2b": (time(13, 0), time(19, 0)),
                "4c": (time(19, 0), time(1, 0)), # Spans midnight
                "5d": (time(1, 0), time(7, 0)), # Starts during night
            },
        }

        self.people_data = {
            "time_preferences_dict": {
                "person_1": [
                    ([(time(7, 0), time(13, 0))], 5), 
                    ([(time(13, 0), time(19, 0))], 0), 
                    ([(time(19, 0), time(1, 0))], 1), 
                    ([(time(1, 0), time(7, 0))], 0), 
                ]
            }
        }

    def test_cost_is_based_only_on_last_time_preference(self):
        """
        Tests that the final cost is calculated based ONLY on the last
        time preference in the person's list, due to the final line
        in the function overwriting all previous calculations.
        """
        # --- Expected Result Calculation ---
        # 1. The function calculates initial costs, night shift penalties, etc.
        #    but this is all thrown away by the final line.

        # 2. The function loops through preferences for "person_1".
        #    - First, it checks the evening preference (18:00-22:00).
        #      'shift_evening' (16:00-23:00) overlaps.
        #      The mask would be [False, True, False, False].
        #    - Second, it checks the morning preference (08:00-12:00).
        #      'shift_morning' (09:00-17:00) overlaps.
        #      The mask is OVERWRITTEN to be [True, False, False, False].
        
        # 3. The final calculation is `np.sum(mask * ranking_factor)`
        #    - mask = np.array([True, False, False, False]) -> [1, 0, 0, 0]
        #    - ranking_factor = SHIFT_RANKING_FACTOR = 10.0
        #    - calculation = np.sum([1, 0, 0, 0] * 10.0) = np.sum([10.0, 0, 0, 0])
        #    - expected_cost = 10.0
        
        expected_cost = 76.0

        # --- Function Call ---
        actual_cost = time_frame_cost(
            schedule=None,  # The 'schedule' argument is not used in the function
            person_id=self.person_id,
            assigned_shifts_person=self.assigned_shifts,
            people_data=self.people_data,
            shifts_data=self.shifts_data,
            ranking_factor=SHIFT_RANKING_FACTOR,
        )

        # --- Assertion ---
        self.assertEqual(actual_cost, expected_cost)
        self.assertIsInstance(actual_cost, float, "Cost should be a float")

    def test_no_matching_preferences(self):
        """
        Tests that the cost is zero if no assigned shifts match the
        (last) time preference.
        """
        
        self.shifts_data = {
            "shift_cost_dict": {
                "1a": 10,
                "2b": 15,
                "4c": 20,
                "5d": 25,
            },
            "shift_time_dict": {
            "1a": (time(7, 0), time(13, 0)),
                "2b": (time(13, 0), time(19, 0)),
                "4c": (time(19, 0), time(1, 0)), # Spans midnight
                "5d": (time(1, 0), time(7, 0)), # Starts during night
         },
        }
        self.people_data = {
                "time_preferences_dict": {
                    "person_1": [
                        ([(time(7, 0), time(13, 0))], 5), 
                        ([(time(13, 0), time(19, 0))], 0), 
                        ([(time(19, 0), time(1, 0))], 1), 
                        ([(time(1, 0), time(7, 0))], 11), 
                    ]
                }
            }
        expected_cost = 2.0
        
        actual_cost = time_frame_cost(
            schedule=None,
            person_id=self.person_id,
            assigned_shifts_person=self.assigned_shifts,
            people_data=self.people_data,
            shifts_data=self.shifts_data,
        )
        
        self.assertEqual(actual_cost, expected_cost)
        
    def test_three_night_shifts(self):
            """
            Tests that the cost is zero if no assigned shifts match the
            (last) time preference.
            """
            
            self.shifts_data = {
                "shift_cost_dict": {
                    "1a": 10,
                    "2b": 15,
                    "4c": 20,
                    "5d": 25,
                },
                "shift_time_dict": {
                    "1a": (time(7, 0), time(13, 0)),
                    "2b": (time(13, 0), time(19, 0)),
                    "4c": (time(19, 0), time(1, 0)), # Spans midnight
                    "5d": (time(1, 0), time(7, 0)), # Starts during night
            },
            }
            self.people_data = {
                "time_preferences_dict": {
                    "person_1": [
                        ([(time(7, 0), time(13, 0))], 5), 
                        ([(time(13, 0), time(19, 0))], 0), 
                        ([(time(19, 0), time(1, 0))], 1), 
                        ([(time(1, 0), time(7, 0))], 16), 
                    ]
                }
            }
            expected_cost = 0.0
            
            actual_cost = time_frame_cost(
                schedule=None,
                person_id=self.person_id,
                assigned_shifts_person=self.assigned_shifts,
                people_data=self.people_data,
                shifts_data=self.shifts_data,
            )
            
            self.assertEqual(actual_cost, expected_cost)

    def test_four_night_shifts(self):
            """
            Tests that the cost is zero if no assigned shifts match the
            (last) time preference.
            """
            
            self.shifts_data = {
                "shift_cost_dict": {
                    "1a": 10,
                    "2b": 15,
                    "4c": 20,
                    "5d": 25,
                },
                "shift_time_dict": {
                    "1a": (time(7, 0), time(13, 0)),
                    "2b": (time(13, 0), time(19, 0)),
                    "4c": (time(19, 0), time(1, 0)), # Spans midnight
                    "5d": (time(1, 0), time(7, 0)), # Stduring night
                },
            }
            self.people_data = {
                            "time_preferences_dict": {
                                "person_1": [
                                    ([(time(7, 0), time(13, 0))], 5), 
                                    ([(time(13, 0), time(19, 0))], 0), 
                                    ([(time(19, 0), time(1, 0))], 1), 
                                    ([(time(1, 0), time(7, 0))], 0), 
                                ]
                            }
                        }
            expected_cost = 0.0
            
            actual_cost = time_frame_cost(
                schedule=None,
                person_id=self.person_id,
                assigned_shifts_person=self.assigned_shifts,
                people_data=self.people_data,
                shifts_data=self.shifts_data,
            )
            
            self.assertEqual(actual_cost, expected_cost)



if __name__ == "__main__":
    unittest.main(argv=['first-arg-is-ignored'], exit=False)