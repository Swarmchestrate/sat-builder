from typing import Any

from src.utils.logger import get_logger
from src.utils.validators.helpers import (
    build_collection_path,
    check_if_empty,
    raise_invalid_type,
    check_values_recursively
)

logger = get_logger()


class DictValidator:
    """Handles dict validation operations."""

    @staticmethod
    def validate_dict(
            field_value: dict[str, Any],
            field_name: str
    ) -> None:
        """Validate recursively that a dictionary is not empty and contains no empty values."""
        DictValidator._empty_dict_validation(field_value, field_name)
        for inner_field, inner_value in field_value.items():
            check_values_recursively(inner_value, f'{field_name}[{inner_field}]')

    @staticmethod
    def _empty_dict_validation(
            field_value: dict[str, Any],
            field_name: str
    ) -> None:
        """Validate that a dictionary is not empty."""
        if not isinstance(field_value, dict):
            raise_invalid_type(field_value, field_name, 'dict')
        check_if_empty(field_value, field_name)

    @staticmethod
    def check_if_empty_dict(
            field_value: dict,
            field_name: str
    ) -> None:
        """Check that a dictionary is not empty and recursively validate its elements."""
        check_if_empty(field_value, field_name)
        for inner_field, inner_value in field_value.items():
            inner_path = build_collection_path(field_name, inner_field)
            check_values_recursively(inner_value, inner_path)
