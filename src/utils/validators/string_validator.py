import re
from typing import Any, Optional

from src.utils.logger import get_logger
from .helpers import (
    check_if_empty,
    ErrorMessage,
    raise_invalid_type
)

logger = get_logger()


class StringValidator:
    """Handles string validation operations."""

    @staticmethod
    def validate_string(
            field_value: Any,
            field_name: str,
            allow_empty: bool = False,
            allow_padding: bool = False,
            ascii_only: bool = False,
            pattern: Optional[str] = None,
            pattern_description: Optional[str] = None,
            min_len: Optional[int] = None,
            max_len: Optional[int] = None
    ) -> str:
        """Validate that a string is not empty and meets optional criteria."""
        StringValidator._empty_string_validation(field_value, field_name, allow_empty)
        field_value_cleaned = field_value.strip()
        StringValidator._check_string_padding(field_value, field_value_cleaned, field_name, allow_padding)
        StringValidator._check_ascii_only(field_value_cleaned, field_name, ascii_only)
        StringValidator._check_string_pattern(field_value_cleaned, field_name, pattern, pattern_description)
        StringValidator._check_string_length(field_value_cleaned, field_name, min_len, max_len)
        return field_value_cleaned

    @staticmethod
    def _empty_string_validation(
            field_value: str,
            field_name: str,
            allow_empty: bool
    ) -> None:
        """Validate that a string is not empty or whitespace-only."""
        if not isinstance(field_value, str):
            raise_invalid_type(field_value, field_name, 'string')
        if not allow_empty:
            check_if_empty(field_value, field_name)
        if not field_value.strip():
            msg = ErrorMessage.WHITESPACE_ONLY.format(field_name=field_name)
            logger.error(msg)
            raise ValueError(msg)

    @staticmethod
    def check_if_empty_string(
            field_value: str,
            field_name: str
    ) -> None:
        """Validate that a string is not empty or whitespace-only."""
        StringValidator._empty_string_validation(field_value, field_name, allow_empty=False)

    @staticmethod
    def _check_string_padding(
            field_value: str,
            field_value_cleaned: str,
            field_name: str,
            allow_padding: bool
    ) -> None:
        """Validate whether a string has leading or trailing whitespace when not allowed."""
        if not allow_padding and field_value != field_value_cleaned:
            msg = ErrorMessage.WHITESPACE_PADDING.format(field_name=field_name)
            logger.error(msg)
            raise ValueError(msg)

    @staticmethod
    def _check_ascii_only(
            field_value_cleaned: str,
            field_name: str,
            ascii_only: bool
    ) -> None:
        """Validate whether a string contains only ASCII characters when required."""
        if ascii_only:
            try:
                field_value_cleaned.encode('ascii')
            except UnicodeEncodeError:
                msg = ErrorMessage.INVALID_ASCII.format(field_name=field_name)
                logger.error(msg)
                raise ValueError(msg)

    @staticmethod
    def _check_string_pattern(
            field_value_cleaned: str,
            field_name: str,
            pattern: Optional[str],
            pattern_description: Optional[str]
    ) -> None:
        """Validate whether a string matches the required pattern when provided."""
        if pattern and not re.fullmatch(pattern, field_value_cleaned):
            msg = ErrorMessage.INVALID_CHARACTERS.format(
                field_name=field_name,
                allowed_chars=pattern_description or "valid characters"
            )
            logger.error(msg)
            raise ValueError(msg)

    @staticmethod
    def _check_string_length(
            field_value_cleaned: str,
            field_name: str,
            min_len: Optional[int],
            max_len: Optional[int]
    ) -> None:
        """Validate whether a string meets minimum and maximum length requirements when provided."""
        if min_len and len(field_value_cleaned) < min_len:
            msg = ErrorMessage.MIN_LENGTH.format(
                field_name=field_name,
                min_length=min_len
            )
            logger.error(msg)
            raise ValueError(msg)
        if max_len and len(field_value_cleaned) > max_len:
            msg = ErrorMessage.MAX_LENGTH.format(
                field_name=field_name,
                max_length=max_len
            )
            logger.error(msg)
            raise ValueError(msg)
