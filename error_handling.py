from logger import logging


class CapacityError(Exception):
    """Custom exception for capacity-related errors."""

    pass


class InvalidAssignmentError(Exception):
    """Custom exception for invalid assignment errors."""

    pass


class ScheduleCreationError(Exception):
    """Custom exception for schedule creation errors."""

    pass

class NotFoundError(Exception):
    """Custom exception for not found errors."""
    pass


def raise_not_found_error(message):
    """Log and raise a not found error with the given message."""
    logging.error(message)
    raise NotFoundError(message)

def raise_capacity_error(message):
    """Log and raise a capacity error with the given message."""
    logging.fatal(message)
    raise CapacityError(message)


def raise_invalid_assignment_error(message):
    """Log and raise an invalid assignment error with the given message."""
    logging.warning(message)
    raise InvalidAssignmentError(message)


def raise_schedule_creation_error(message):
    """Log and raise a schedule creation error with the given message."""
    logging.fatal(message)
    raise ScheduleCreationError(message)
