from collections import Counter
from typing import Any

from src.utils.logger import get_logger
from src.utils.validators.helpers import (
    build_collection_path,
    check_if_empty,
    ErrorMessage,
    raise_invalid_type,
    check_values_recursively
)

logger = get_logger()


class ListValidator:
    """Handles list validation operations."""

    @staticmethod
    def validate_list(
            field_value: list[Any],
            field_name: str
    ) -> None:
        """Validate recursively that a list is not empty and contains no empty values."""
        ListValidator._empty_list_validation(field_value, field_name)
        check_values_recursively(field_value, field_name)

    @staticmethod
    def _empty_list_validation(
            field_value: list[Any],
            field_name: str
    ) -> None:
        """Validate that a list is not empty."""
        if not isinstance(field_value, list):
            raise_invalid_type(field_value, field_name, 'list')
        check_if_empty(field_value, field_name)

    @staticmethod
    def check_if_empty_list(
            field_value: list,
            field_name: str
    ) -> None:
        """Check that a list is not empty and recursively validate its elements."""
        check_if_empty(field_value, field_name)
        ListValidator.check_duplicates(
            field_value,
            field_name,
            allow_duplicates=True,
            allow_only_string=False,
            raise_unhashable_items=True
        )
        for inner_field, inner_value in enumerate(field_value):
            inner_path = build_collection_path(field_name, inner_field)
            check_values_recursively(inner_value, inner_path)

    @staticmethod
    def check_duplicates(
            field_value: list[Any],
            field_name: str,
            allow_duplicates: bool = False,
            allow_only_string: bool = False,
            raise_unhashable_items: bool = False,
    ) -> list[Any]:
        """Validate a list for duplicates and return a sorted list of duplicate items.

        For lists with mixed hashable and unhashable items, only hashable items are checked
        for duplicates unless raise_unhashable_items is True.
        """
        if allow_only_string:
            for inner_field, inner_value in enumerate(field_value):
                if not isinstance(inner_value, str):
                    raise_invalid_type(inner_value, f'{field_name}[{inner_field}]', 'string')
        hashable = []
        unhashable = []
        for inner_field, inner_value in enumerate(field_value):
            try:
                hash(inner_value)
                hashable.append(inner_value)
            except TypeError:
                unhashable.append(inner_field)
        if unhashable and raise_unhashable_items:
            msg = ErrorMessage.INVALID_TYPE.format(
                field_name=field_name,
                expected_type='list of hashable items',
                actual_type=f'list containing unhashable items at indices: {unhashable}'
            )
            logger.error(msg)
            raise ValueError(msg)
        duplicates = []
        if hashable:
            values = Counter(hashable)
            duplicates = sorted([value for value, count in values.items() if count > 1])
        if duplicates and not allow_duplicates:
            msg = ErrorMessage.LIST_DUPLICATES.format(
                field_name=field_name,
                duplicates=', '.join(str(d) for d in duplicates)
            )
            logger.error(msg)
            raise ValueError(msg)
        return duplicates
