from typing import Any

from src.utils.validators.helpers.invalid_type import raise_invalid_type


def check_values_recursively(
        field_value: Any,
        field_name: str
) -> None:
    """Recursively validate field values and raise ValueError if any is invalid."""
    if isinstance(field_value, dict):
        from src.utils.validators.dict_validator import DictValidator
        DictValidator.check_if_empty_dict(field_value, field_name)
    elif isinstance(field_value, list):
        from src.utils.validators.list_validator import ListValidator
        ListValidator.check_if_empty_list(field_value, field_name)
    elif isinstance(field_value, str):
        from src.utils.validators.string_validator import StringValidator
        StringValidator.check_if_empty_string(field_value, field_name)
    elif not isinstance(field_value, int) and not isinstance(field_value, float) and not isinstance(field_value, bool):
        raise_invalid_type(field_value, field_name, 'string, dict, list, int, float, or bool')
