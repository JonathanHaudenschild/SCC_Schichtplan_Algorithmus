
# Define the mapping from work type names to integers
work_type_mapping = {
    "garbage": 1,
    "mobile": 2,
    "stage": 3,
    "kitchen": 4,
    "hygiene": 5,
    "steward": 6,
    "bottleDeposit": 7,
    "other": 8,
    "fence": 9,
    "parking": 10,
    "entrance": 11,
}

# Example of a helper function
def get_work_type_name(type_id):
    for name, id in work_type_mapping.items():
        if id == type_id:
            return name
    return None


def get_shift_importance_integer(importance_str):
    # Convert importance from string to integer, assuming this is a placeholder.
    # Replace with actual logic as needed.
    importance_map = {"LOW": 1, "MIDDLE": 1, "HIGH": 3}
    return importance_map.get(importance_str.lower(), 0)
