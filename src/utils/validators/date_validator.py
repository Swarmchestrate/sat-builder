from datetime import date

from src.utils.logger import get_logger
from .helpers import ErrorMessage

logger = get_logger()


class DateValidator:
    """Handles date validation operations."""

    @staticmethod
    def validate_two_dates(
            first_date_value: date,
            first_date_name: str,
            second_date_value: date,
            second_date_name: str,
            date_format: str = '%Y-%m-%d'
    ) -> tuple[str, str]:
        """Validate that the second date is not before the first date."""
        if second_date_value < first_date_value:
            msg = ErrorMessage.INVALID_DATES.format(
                second_date_name=second_date_name,
                first_date_name=first_date_name
            )
            logger.error(msg)
            raise ValueError(msg)
        return first_date_value.strftime(date_format), second_date_value.strftime(date_format)
