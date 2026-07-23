from typing import Any

from src.utils.logger import get_logger
from .error_messages import ErrorMessage

logger = get_logger()


def raise_invalid_type(
        field_value: Any,
        field_name: str,
        expected_type: str
) -> None:
    """Raise invalid-type ValueError."""
    msg = ErrorMessage.INVALID_TYPE.format(
        field_name=field_name,
        expected_type=expected_type,
        actual_type=type(field_value).__name__
    )
    logger.error(msg)
    raise ValueError(msg)
