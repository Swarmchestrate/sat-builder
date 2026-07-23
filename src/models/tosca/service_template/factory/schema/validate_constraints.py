"""
TOSCA Node Template Constraint Validator

Validates TOSCA node template fields against business rule constraints and domain-specific
validation requirements. This module enforces constraints beyond basic type validation,
ensuring templates comply with TOSCA specification requirements and organizational policies.

Key Features:
- List constraint validation (merged_list, strict_list)
- Requirement dependency validation (requires)
- Element count constraints (min_elements, max_elements)
- Nested constraint path resolution
- Comprehensive error reporting with field context
"""

import inspect
from typing import Any, Dict

from src.utils.logger import get_logger, log_validation_results, log_function_calls

logger = get_logger()


@log_validation_results()
def validate_field_constraints(schema_path: str, schema_top_level: str, schema: Any,
                               constraints: Dict[str, Any]) -> None:
    """
    Validate field values against defined constraint rules for TOSCA templates.

    Applies business logic constraints that go beyond basic type validation, ensuring
    templates conform to organizational policies and TOSCA specification requirements.
    Constraints are dynamically applied based on field paths and constraint definitions.

    Args:
        schema_path: Full dot-notation path to the field being validated
        schema_top_level: Top-level field name for constraint matching
        schema: Field value to validate against constraints
        constraints: Dictionary of constraint definitions organized by field name

    Raises:
        ValueError: When constraint validation fails with detailed error context
    """
    function_name = inspect.currentframe().f_code.co_name
    logger.debug(
        f"{function_name}: validating field '{schema_top_level}' at path '{schema_path}'")

    # Search for applicable constraints for this field
    for constraints_top_level, constraints_config in constraints.items():
        if schema_top_level == constraints_top_level:
            logger.debug(
                f"{function_name}: found {len(constraints_config)} constraint definitions for '{constraints_top_level}'")

            # Extract all constraint rules from the configuration
            constraints_list = _collect_constraints(constraints_config, constraints_top_level)

            # Apply each constraint rule to the field data
            for constraint_info in constraints_list:
                constraint_parent_key = constraint_info["parent_key"]
                constraint_type = constraint_info["constraint_type"]
                constraint_values = constraint_info["value"]
                constraint_path = constraint_info["path"]

                # Determine the appropriate data to validate
                data_for_validation = None
                apply_constraint = False

                # Check if constraint applies to top-level field directly
                if constraint_parent_key == schema_top_level.split(".")[-1]:
                    logger.debug(
                        f"{function_name}: ⚡ Applying '{constraint_type}' constraint at top level")
                    data_for_validation = schema
                    apply_constraint = True
                else:
                    # Search for constraint target in nested field structure
                    schema_data = find_values_in_path(schema, constraint_path[:-1])
                    if schema_data:
                        logger.debug(
                            f"{function_name}: ⚡ Applying '{constraint_type}' constraint at nested level")
                        # Extract values from path search results
                        data_values = [value for path, value in schema_data]
                        data_for_validation = data_values
                        apply_constraint = True

                # Execute constraint validation if applicable
                if apply_constraint:
                    try:
                        check_for_constrain(constraint_parent_key, constraint_type,
                                            constraint_values, constraint_path, data_for_validation)
                        logger.debug(
                            f"{function_name}: ✅ Constraint '{constraint_type}' validation passed")
                    except ValueError as constraint_error:
                        msg = f"Constraint validation failed for field '{schema_path}': {constraint_error}"
                        logger.error(
                            f"{function_name}: {msg}")
                        raise ValueError(msg) from constraint_error


@log_function_calls()
def check_for_constrain(constraint_parent_key: str, constraint_type: str, constraint_values: Any,
                        constraint_path: list, data_for_validation: Any) -> None:
    """
    Execute specific constraint validation logic based on the constraint type.

    Applies the appropriate validation algorithm for each constraint type, ensuring
    field data conforms to the specified business rules and requirements. Handles
    different data structures and provides detailed error reporting for failures.

    Args:
        constraint_parent_key: Parent field name that owns this constraint
        constraint_type: Type of constraint to apply (merged_list, strict_list, etc.)
        constraint_values: Expected values or limits defined by the constraint
        constraint_path: Full path to the constraint definition for error context
        data_for_validation: Field data to validate against the constraint

    Raises:
        ValueError: When constraint validation fails with specific error details
    """
    function_name = inspect.currentframe().f_code.co_name
    logger.debug(
        f"{function_name}: executing '{constraint_type}' constraint for '{constraint_parent_key}'")

    # Skip validation if no data is provided (empty/null fields)
    if not data_for_validation:
        logger.debug(
            f"{function_name}: no data to validate - constraint '{constraint_type}' skipped")
        return

    # List-based constraints: validate list membership and allowed values
    if constraint_type in ["merged_list", "strict_list"]:
        # Ensure data is in list format for processing
        if not isinstance(data_for_validation, list):
            msg = (
                f"List constraint '{constraint_type}' requires list data type. "
                f"Got {type(data_for_validation).__name__} at path '{' → '.join(map(str, constraint_path))}'. "
                f"Expected format: list of values."
            )
            logger.error(f"{function_name}: {msg}")
            raise ValueError(msg)

        # Validate each item in the list against allowed constraint values
        for item_index, item in enumerate(data_for_validation):
            try:
                # Check if the item is in the allowed values list
                if item not in constraint_values:
                    allowed_values_str = "', '".join(map(str, constraint_values))
                    msg = (
                        f"Invalid value '{item}' found in {constraint_type} constraint. "
                        f"Allowed values: ['{allowed_values_str}']. "
                        f"Location: {' → '.join(map(str, constraint_path))}[{item_index}]"
                    )
                    logger.error(f"{function_name}: {msg}")
                    raise ValueError(msg)

            except TypeError as type_error:
                # Handle unhashable types that can't use the 'in' operator
                msg = (
                    f"Constraint validation error in '{constraint_type}': "
                    f"Cannot validate unhashable type '{type(item).__name__}' against constraint values. "
                    f"Item: {item}. Path: {' → '.join(map(str, constraint_path))}[{item_index}]. "
                    f"Hashable types required for membership testing."
                )
                logger.error(f"{function_name}: {msg}")
                raise ValueError(msg) from type_error

    # Requires constraint: validate presence of required keys in data structure
    elif constraint_type == "requires":
        # Ensure data is in list format for iteration
        if not isinstance(data_for_validation, list):
            msg = (
                f"Requires constraint needs list data type for key validation. "
                f"Got {type(data_for_validation).__name__} at path '{' → '.join(map(str, constraint_path))}'. "
                f"Expected format: list of dictionaries or objects with required keys."
            )
            logger.error(f"{function_name}: {msg}")
            raise ValueError(msg)

        # Check each required key exists in the data structure
        for required_key in constraint_values:
            key_found_in_any_item = False

            # Search for the required key in each data item
            for item in data_for_validation:
                found_value = find_key_value(item, required_key)
                if found_value is not None:  # Explicitly check for None (allows falsy values)
                    key_found_in_any_item = True
                    break

            # Raise error if the required key is missing from all data items
            if not key_found_in_any_item:
                msg = (
                    f"Required key '{required_key}' not found in any data items. "
                    f"Constraint path: {' → '.join(map(str, constraint_path))}. "
                    f"Ensure all required keys are present in the data structure."
                )
                logger.error(f"{function_name}: {msg}")
                raise ValueError(msg)

    # Min/Max elements constraints: validate count requirements
    elif constraint_type in ["min_elements", "max_elements"]:
        # Ensure data is in list format for counting
        if not isinstance(data_for_validation, list):
            msg = (
                f"{constraint_type.title()} constraint requires list data type for counting. "
                f"Got {type(data_for_validation).__name__} at path '{' → '.join(map(str, constraint_path))}'. "
                f"Expected format: list of countable items."
            )
            logger.error(f"{function_name}: {msg}")
            raise ValueError(msg)

        # Validate element count for each item in the data list
        for item_index, item in enumerate(data_for_validation):
            # Ensure item supports length measurement
            if not hasattr(item, '__len__'):
                msg = (
                    f"{constraint_type.title()} constraint error: Item of type '{type(item).__name__}' "
                    f"does not support length measurement. Path: {' → '.join(map(str, constraint_path))}[{item_index}]. "
                    f"Only countable types (list, dict, str, etc.) are supported."
                )
                logger.error(f"{function_name}: {msg}")
                raise ValueError(msg)

            item_length = len(item)

            # Check element count constraints
            if constraint_type == "min_elements" and item_length < constraint_values:
                msg = (
                    f"Minimum elements constraint violation: Item has {item_length} elements, "
                    f"but minimum required is {constraint_values}. "
                    f"Location: {' → '.join(map(str, constraint_path))}[{item_index}]. "
                    f"Add more elements to meet the requirement."
                )
                logger.error(f"{function_name}: {msg}")
                raise ValueError(msg)
            elif constraint_type == "max_elements" and item_length > constraint_values:
                msg = (
                    f"Maximum elements constraint violation: Item has {item_length} elements, "
                    f"but maximum allowed is {constraint_values}. "
                    f"Location: {' → '.join(map(str, constraint_path))}[{item_index}]. "
                    f"Remove elements to meet the limit."
                )
                logger.error(f"{function_name}: {msg}")
                raise ValueError(msg)

    # Comparison constraints: validate numeric thresholds
    elif constraint_type in ["greater_than", "less_than"]:
        # Ensure data is in a list format
        if not isinstance(data_for_validation, list):
            msg = (
                f"{constraint_type.title()} constraint requires list data type. "
                f"Got {type(data_for_validation).__name__} at path '{' → '.join(map(str, constraint_path))}'. "
                f"Expected format: list of numeric values."
            )
            logger.error(f"{function_name}: {msg}")
            raise ValueError(msg)

        # Validate each numeric value in the list
        for item_index, item in enumerate(data_for_validation):
            if isinstance(item, (int, float)):
                if ((constraint_type == "greater_than" and item <= constraint_values) or
                        (constraint_type == "less_than" and item >= constraint_values)):
                    operator = "greater than" if constraint_type == "greater_than" else "less than"
                    msg = (
                        f"{constraint_type.title()} constraint violation: Item at index {item_index} "
                        f"has value {item}, but must be {operator} {constraint_values}. "
                        f"Location: {' → '.join(map(str, constraint_path))}[{item_index}]."
                    )
                    logger.error(f"{function_name}: {msg}")
                    raise ValueError(msg)
            else:
                msg = (
                    f"{constraint_type.title()} constraint error: Item of type '{type(item).__name__}' "
                    f"cannot be compared numerically. Path: {' → '.join(map(str, constraint_path))}[{item_index}]. "
                    f"Only numeric types (int, float) are supported."
                )
                logger.error(f"{function_name}: {msg}")
                raise ValueError(msg)

    # Unsupported constraint types: provide helpful error message
    else:
        supported_types = ["merged_list", "strict_list", "requires", "min_elements", "max_elements", "less_than",
                           "greater_than"]
        error_msg = (
            f"Unsupported constraint type '{constraint_type}' encountered at path "
            f"'{' → '.join(map(str, constraint_path))}'.\n"
            f"Supported constraint types: {', '.join(supported_types)}.\n"
            f"Check constraint definition for typos or update validator to support new type."
        )
        logger.error(f"{function_name}: {error_msg}")
        raise ValueError(error_msg)


@log_function_calls()
def _collect_constraints(constraint_dict: Dict[str, Any], parent_key: str = None,
                         path: list = None) -> list:
    """
    Recursively traverse constraint definitions to extract all constraint rules.

    Walks through nested constraint dictionaries and lists to identify all
    constraint rules that need to be applied. Each constraint is returned with
    its full path context for accurate validation and error reporting.

    Args:
        constraint_dict: Dictionary containing constraint definitions
        parent_key: Parent field name for context tracking
        path: Current path in the constraint hierarchy

    Returns:
        List of constraint info dictionaries containing:
        - parent_key: Field that owns this constraint
        - constraint_type: Type of constraint (merged_list, requires, etc.)
        - value: Constraint parameters or expected values
        - path: Full path to constraint definition
    """
    function_name = inspect.currentframe().f_code.co_name
    # Initialize path tracking for recursive traversal
    if path is None:
        path = []

    # Handle invalid or empty constraint definitions
    if not isinstance(constraint_dict, dict) or not constraint_dict:
        logger.debug(
            f"{function_name}: invalid or empty constraint definition at path: {' → '.join(map(str, path))}")
        return []

    collected_constraints = []
    logger.debug(f"{function_name}: collecting constraints from: {' → '.join(map(str, path))}")

    # Traverse each key-value pair in the constraint dictionary
    for constraint_key, constraint_value in constraint_dict.items():
        current_path = path + [constraint_key]

        if isinstance(constraint_value, dict):
            # Nested dictionary - continue recursive traversal
            nested_constraints = _collect_constraints(
                constraint_value, parent_key=constraint_key, path=current_path
            )
            collected_constraints.extend(nested_constraints)

        elif isinstance(constraint_value, list):
            # List constraint value - check for nested dictionaries
            # Process each item in the constraint list
            for item_index, list_item in enumerate(constraint_value):
                if isinstance(list_item, dict):
                    # Nested dictionary within list - recurse with index
                    nested_constraints = _collect_constraints(
                        list_item, parent_key=constraint_key,
                        path=current_path + [str(item_index)]
                    )
                    collected_constraints.extend(nested_constraints)
                else:
                    # Simple list values - store as single constraint
                    collected_constraints.append({
                        "parent_key": parent_key,
                        "constraint_type": constraint_key,
                        "value": constraint_value,  # Store the entire list
                        "path": current_path
                    })
                    break  # Don't process individual items, we stored the whole list

        else:
            # Leaf constraint value (string, number, boolean, etc.)
            collected_constraints.append({
                "parent_key": parent_key,
                "constraint_type": constraint_key,
                "value": constraint_value,
                "path": current_path
            })

    logger.debug(f"{function_name}: collected {len(collected_constraints)} constraints")
    return collected_constraints


def find_key_value(data: Any, search_key: str) -> Any:
    """
    Recursively search for a specific key in nested data structures.

    Traverses dictionaries and lists to locate the specified key and return
    its associated value. Supports complex nested structures commonly found
    in TOSCA templates and constraint definitions.

    Args:
        data: Data structure to search (dict, list, or primitive)
        search_key: Key name to search for in the data structure

    Returns:
        Value associated with the search key, or None if not found
    """
    if isinstance(data, dict):
        # Direct key lookup in the dictionary
        if search_key in data:
            return data[search_key]

        # Recursive search in nested dictionaries
        for nested_value in data.values():
            result = find_key_value(nested_value, search_key)
            if result is not None:
                return result

    elif isinstance(data, list):
        # Search each item in the list
        for list_item in data:
            if isinstance(list_item, dict):
                result = find_key_value(list_item, search_key)
                if result is not None:
                    return result

    return None  # Key is not found anywhere in the data structure


def find_values_in_path(data: Any, search_path: list, current_path: list = None) -> list:
    """
    Locate values at specific paths in nested data structures, ignoring numeric indices.

    Traverses complex nested data to find values that match a specific path pattern.
    Numeric indices in paths are ignored to allow flexible matching of list-based
    structures. Returns all matching path-value pairs for comprehensive validation.

    Args:
        data: Root data structure to search through
        search_path: List of keys representing the target path to find
        current_path: Current position in the data traversal (internal use)

    Returns:
        List of tuples containing (full_path, value) for all matches
    """
    # Initialize path tracking for recursive search
    if current_path is None:
        current_path = []

    search_results = []

    # Create the path without numeric indices for flexible matching
    # This allows matching list structures regardless of index numbers
    path_without_indices = [
        path_element for path_element in current_path
        if not str(path_element).isdigit()
    ]

    # Check if the current path matches the target search path
    if (
            search_path and
            len(path_without_indices) >= len(search_path) and
            path_without_indices[-len(search_path):] == search_path
    ):
        return [(current_path, data)]

    # Continue recursive search based on the data type
    if isinstance(data, dict):
        # Search each key-value pair in the dictionary
        for dict_key, dict_value in data.items():
            extended_path = current_path + [dict_key]
            nested_results = find_values_in_path(dict_value, search_path, extended_path)
            search_results.extend(nested_results)

    elif isinstance(data, list):
        # Search each item in the list with index tracking
        for item_index, list_item in enumerate(data):
            extended_path = current_path + [str(item_index)]
            nested_results = find_values_in_path(list_item, search_path, extended_path)
            search_results.extend(nested_results)

    return search_results
