"""Collect constraints for TOSCA schema."""

import inspect
from typing import Dict, Any, List, Union

from src.utils.logger import get_logger, log_function_calls

logger = get_logger()

ALLOWED_CONSTRAINTS = [
    "merged_list",
    "strict_list",
    "min_elements",
    "max_elements",
    "requires",
    "greater_than",
    "less_than"
]


@log_function_calls()
def build_constraints(
        templates: Union[Dict[str, Dict[str, Any]], List[Dict[str, Any]]],
        constraints_document: Dict[str, Dict[str, Any]]
) -> Dict[str, Dict[str, Any]]:
    """
    Collect and process constraints from TOSCA templates.

    Constraint types:
    - merged_list: Merges multiple lists into a single list
    - strict_list: Captures actual template values for validation
    - min_elements/max_elements: Enforces list size limits
    - requires: Specifies field dependencies
    """
    function_name = inspect.currentframe().f_code.co_name
    logger.debug(f"{function_name}: processing {len(constraints_document)} constraint fields")

    constraints = {}
    for field_name, field_constraints in constraints_document.items():
        template_paths = _find_paths_in_dict(templates, field_name)
        logger.debug(
            f"{function_name}: found {len(template_paths)} paths for field '{field_name}'")

        for field_path in template_paths:
            if field_path[0].isdigit():
                # For policies: templates[0]["policy-name"]
                type_name = templates[int(field_path[0])][field_path[1]].get("type").split(":")[-1]
                cleaned_path = _remove_array_indices([type_name] + field_path[2:])
            else:
                # For nodes: templates["node-name"]
                type_name = templates[field_path[0]].get("type").split(":")[-1]
                cleaned_path = _remove_array_indices([type_name] + field_path[1:])

            for constraint_name, constraint_config in field_constraints.items():
                if constraint_name not in ALLOWED_CONSTRAINTS:
                    error_msg = f"Invalid constraint '{constraint_name}' for field '{field_name}'"
                    logger.error(f"{function_name}: {error_msg}")
                    raise ValueError(error_msg)

                constraint_applied = False
                cleaned_value_path = cleaned_path + [constraint_name]
                _build_nested_dict(constraints, cleaned_value_path)

                if constraint_name == "merged_list" and constraint_config:
                    values = _get_value_from_path(templates, field_path)
                    # noinspection DuplicatedCode
                    if not isinstance(values, list):
                        error_msg = f"Invalid constraint '{constraint_name}' for field '{field_name}'. List expected."
                        logger.error(f"{function_name}: {error_msg}")
                        raise ValueError(error_msg)
                    for value in values:
                        _put_list_value_to_path(constraints, cleaned_value_path, value)
                    constraint_applied = True

                elif constraint_name == "strict_list" and constraint_config:
                    values = _get_value_from_path(templates, field_path)
                    if not isinstance(values, list):
                        error_msg = f"Invalid constraint '{constraint_name}' for field '{field_name}'. List expected."
                        logger.error(f"{function_name}: {error_msg}")
                        raise ValueError(error_msg)
                    _put_list_value_to_path(constraints, cleaned_value_path, values)
                    constraint_applied = True

                elif constraint_name in ["min_elements", "max_elements"]:
                    if not (isinstance(constraint_config, int) and constraint_config > 0):
                        error_msg = f"Invalid constraint '{constraint_name}' for field '{field_name}'. Integer >0 expected."
                        logger.error(f"{function_name}: {error_msg}")
                        raise ValueError(error_msg)
                    _put_int_value_to_path(constraints, cleaned_value_path, constraint_config)
                    constraint_applied = True

                elif constraint_name == "requires":
                    # noinspection DuplicatedCode
                    if not isinstance(constraint_config, list):
                        error_msg = f"Invalid constraint '{constraint_name}' for field '{field_name}'. List expected."
                        logger.error(f"{function_name}: {error_msg}")
                        raise ValueError(error_msg)
                    for value in constraint_config:
                        if not isinstance(value, str):
                            error_msg = f"Invalid constraint '{constraint_name}' for field '{field_name}'. List of strings expected."
                            logger.error(f"{function_name}: {error_msg}")
                            raise ValueError(error_msg)
                        _put_list_value_to_path(constraints, cleaned_value_path, value)
                    constraint_applied = True

                elif constraint_name in ["less_than", "greater_than"]:
                    if not isinstance(constraint_config, int):
                        error_msg = f"Invalid constraint '{constraint_name}' for field '{field_name}'. Integer expected."
                        logger.error(f"{function_name}: {error_msg}")
                        raise ValueError(error_msg)
                    _put_int_value_to_path(constraints, cleaned_value_path, constraint_config)
                    constraint_applied = True

                if not constraint_applied:
                    error_msg = f"Invalid constraint '{constraint_name}' for field '{field_name}'"
                    logger.error(f"{function_name}: {error_msg}")
                    raise ValueError(error_msg)

    logger.debug(f"{function_name}: built constraints for {len(constraints)} types")
    return constraints


def _find_paths_in_dict(data: Any, field_name: str, path: List[str] = None) -> List[List[str]]:
    """Recursively find all paths where field_name exists in nested dictionaries."""
    if path is None:
        path = []

    templated_paths = []

    if isinstance(data, dict):
        for key, value in data.items():
            new_path = path + [key]

            if key == field_name:
                templated_paths.append(new_path)

            # Recurse into nested structures
            templated_paths.extend(_find_paths_in_dict(value, field_name, new_path))

    elif isinstance(data, list):
        for i, item in enumerate(data):
            new_path = path + [str(i)]
            templated_paths.extend(_find_paths_in_dict(item, field_name, new_path))

    return templated_paths


def _remove_array_indices(path: List[str]) -> List[str]:
    """Remove numeric array indices from the path list."""
    cleaned_path = []

    for step in path:
        # Check if the step is a numeric string (array index)
        if not step.isdigit():
            cleaned_path.append(step)

    return cleaned_path


def _build_nested_dict(data: Dict[str, Any], path: List[str]) -> None:
    """Build a nested dictionary from the path list, preserving existing values."""
    if not path:
        return

    current = data

    # Create a nested structure up to but not including the final step
    for step in path[:-1]:
        if step not in current:
            current[step] = {}
        elif not isinstance(current[step], dict):
            current[step] = {}
        current = current[step]

    # Set the final step to None if it doesn't exist, preserve existing values
    final_step = path[-1]
    if final_step not in current:
        current[final_step] = None


def _get_value_from_path(data: Any, path: List[str]) -> Any:
    """Get value from a nested dictionary using a list path."""
    current = data

    for key in path:
        if isinstance(current, dict) and key in current:
            current = current[key]
        elif isinstance(current, list):
            try:
                index = int(key)
                if 0 <= index < len(current):
                    current = current[index]
                else:
                    return None
            except ValueError:
                return None
        else:
            return None

    return current


def _put_list_value_to_path(data: Dict[str, Any], path: List[str], value: Any) -> None:
    """Append value to the nested dictionary path if it doesn't already exist."""
    current = data

    # Navigate to parent of target location
    for step in path[:-1]:
        if step not in current:
            current[step] = {}
        elif not isinstance(current[step], dict):
            current[step] = {}
        current = current[step]

    # Append the final value if it doesn't already exist
    if path:
        key = path[-1]
        if key not in current:
            current[key] = []
        elif not isinstance(current[key], list):
            current[key] = []

        # Only append if the value doesn't already exist
        if value not in current[key]:
            current[key].append(value)


def _put_int_value_to_path(data: Dict[str, Any], path: List[str], value: Any) -> None:
    """Set integer value directly at the nested dictionary path."""
    current = data

    # Navigate to parent of target location
    for step in path[:-1]:
        if step not in current:
            current[step] = {}
        elif not isinstance(current[step], dict):
            current[step] = {}
        current = current[step]

    # Set the final value directly (not in a list)
    if path:
        key = path[-1]
        current[key] = value
