from typing import Any

from src.utils.logger import get_logger
from .error_messages import ErrorMessage

logger = get_logger()


def check_if_empty(
        field_value: Any,
        field_name: str
) -> None:
    """Validate that a value is not empty and raise a ValueError if it is."""
    if not field_value:
        msg = ErrorMessage.EMPTY_TYPE.format(
            field_name=field_name,
            expected_type=type(field_value).__name__)
        logger.error(msg)
        raise ValueError(msg)
