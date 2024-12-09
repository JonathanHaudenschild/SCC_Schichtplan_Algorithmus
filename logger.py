import logging
import os

# Define the log file name
log_file = "schedule_creation.log"

# Check if the log file exists
if os.path.exists(log_file):
    user_response = (
        input(
            f"The log file '{log_file}' already exists. Do you want to delete it? (yes/no): "
        )
        .strip()
        .lower()
    )
    if user_response in ["yes", "y"]:
        os.remove(log_file)
        print(f"Deleted the log file: {log_file}")
    else:
        print(f"Continuing without deleting the log file: {log_file}")


# Configure the logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("schedule_creation.log"),  # Log to a file
        # logging.StreamHandler()  # Log to console
    ],
)
