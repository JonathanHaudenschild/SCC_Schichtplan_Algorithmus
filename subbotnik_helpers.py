
# Define the mapping from work type names to integers
work_type_mapping = {
    "garbage": 1,
    "stage": 2,
    "fence": 3,
    "entrance": 4,
    "parking": 5,
    "kitchen": 6,
    "hygiene": 7,
    "mobile": 8,
    "other": 9,
    "steward": 10,
    "bottleDeposit": 11
}

# Example of a helper function
def get_work_type_name(type_id):
    for name, id in work_type_mapping.items():
        if id == type_id:
            return name
    return None

importance_map = {"LOW": 1, "MEDIUM_LOW": 2, "MIDDLE": 3, "MEDIUM_HIGH": 4, "HIGH": 6}

def get_shift_importance_integer(importance_str):
    # Convert importance from string to integer, assuming this is a placeholder.
    # Replace with actual logic as needed.
    print(f"Converting importance '{importance_str}' to integer.")
    if not isinstance(importance_str, str):
        raise ValueError("Importance must be a string.")
    return importance_map.get(importance_str.upper(), 0)
