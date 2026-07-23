"""
TOSCA Node Template Schema Validator

Validates TOSCA node template field values against dynamically generated schema definitions.
Supports validation of primitive types, union types, lists, dictionaries, and complex
requirement structures with detailed error reporting and field path tracking.

This module provides comprehensive type validation ensuring that template fields conform
to their expected schema with definitions including data types, structure constraints, and
nested object validation.
"""

import inspect
from typing import Any, List, Dict

from src.utils.logger import get_logger, log_function_calls

logger = get_logger()


def validate_field_schema(field_path: str, value: Any, schema: Any) -> None:
    """
    Validate a field value against its schema definition with comprehensive type checking.

    Performs recursive validation of field values against their schema definitions,
    supporting primitive types, union types, collections, and nested structures.
    Provides detailed error context through hierarchical field path tracking.

    Args:
        field_path: Dot-notation path to the field being validated (e.g., "template.properties.image")
        value: The actual field value to validate against schema
        schema: Schema definition (str for types, list for arrays, dict for objects)

    Raises:
        ValueError: When validation fails, with detailed error context:
                   - Field path for precise error location
                   - Expected vs. actual type information
                   - Available options for union types
                   - Schema constraint violations

    Examples:
        >>> validate_field_schema("app.image", "nginx:latest", "str") # ✓ Valid
        >>> validate_field_schema("app.port", 80, "int") # ✓ Valid
        >>> validate_field_schema("app.args", ["--help"], ["str"]) # ✓ Valid
        >>> validate_field_schema("app.image", None, "str") # ✗ ValueError
    """
    function_name = inspect.currentframe().f_code.co_name
    logger.debug(
        f"{function_name}: ⚡ Schema validation for field '{field_path}' with value type '{type(value).__name__}'")

    # Reject None values to enforce field presence requirements
    # None indicates missing or undefined values which should be handled at model level
    if value is None:
        msg = (
            f"Validation failed for '{field_path}': None values are not permitted. "
            f"Field must have a valid value or be omitted from template definition."
        )
        logger.error(f"{function_name}: {msg}")
        raise ValueError(msg)

    # Router validation to the appropriate handler based on the schema type
    if isinstance(schema, str):
        # Handle primitive types and union types (e.g., "str", "float|int|str")
        _validate_primitive_schema(field_path, value, schema)
    elif isinstance(schema, list):
        # Handle array schemas with element type definitions
        _validate_list_schema(field_path, value, schema)
    elif isinstance(schema, dict):
        # Handle object schemas with property definitions
        _validate_dict_schema(field_path, value, schema)
    else:
        # Unsupported schema format - indicates development/configuration error
        msg = (
            f"Schema validation error for '{field_path}': "
            f"Unsupported schema type '{type(schema).__name__}'. "
            f"Expected schema formats: str (for primitives), list (for arrays), or dict (for objects)."
        )
        logger.error(f"{function_name}: {msg}")
        raise ValueError(msg)

    logger.debug(
        f"{function_name}: ✅ Schema validation for field '{field_path}' with value type '{type(value).__name__}' completed")


@log_function_calls()
def _validate_primitive_schema(field_path: str, value: Any, schema: str) -> None:
    """
    Validate a value against string-based schema definitions.

    Handles both single primitive types and union types separated by pipe characters.
    Performs exact type matching using Python's built-in type system for accurate
    validation and clear error reporting.

    Args:
        field_path: Field location path for error context
        value: Value to validate
        schema: Type definition string (e.g., "str", "float|int|str")

    Raises:
        ValueError: When the value type doesn't match any allowed types in schema

    Examples:
        >>> _validate_primitive_schema("port", 80, "int") # ✓ Valid
        >>> _validate_primitive_schema("count", 3.14, "float|int") # ✓ Valid (float allowed)
        >>> _validate_primitive_schema("name", 123, "str") # ✗ ValueError
    """
    function_name = inspect.currentframe().f_code.co_name
    logger.debug(f"{function_name}: ⚡ Primitive schema validation for '{field_path}'")

    actual_type = type(value).__name__

    if '|' in schema:
        # Handle union types (multiple allowed types separated by |)
        allowed_types = [type_name.strip() for type_name in schema.split('|')]

        # Check for numeric compatibility: int can satisfy float requirements
        if actual_type == 'int' and 'float' in allowed_types:
            logger.debug(
                f"{function_name}: ✅ Primitive schema validation for '{field_path}' completed")
            return  # int is acceptable for float validation

        if actual_type not in allowed_types:
            # Format allowed types for user-friendly error message
            types_list = "', '".join(allowed_types)
            msg = (
                f"Type validation attempt failed for '{field_path}': "
                f"Expected one of ['{types_list}'], but received '{actual_type}'. "
                f"Value: {repr(value)}"
            )
            logger.warning(f"{function_name}: {msg}")
            raise ValueError(msg)
    else:
        # Handle single type requirement
        expected_type = schema.strip()

        # Allow int when float is expected (numeric compatibility)
        if actual_type == 'int' and expected_type == 'float':
            logger.debug(
                f"{function_name}: ✅ Primitive schema validation for '{field_path}' completed")
            return

        if actual_type != expected_type:
            msg = (
                f"Type validation attempt failed for '{field_path}': "
                f"Expected '{expected_type}', but received '{actual_type}'. "
                f"Value: {repr(value)}"
            )
            logger.warning(f"{function_name}: {msg}")
            raise ValueError(msg)

    logger.debug(f"{function_name}: ✅ Primitive schema validation for '{field_path}' completed")


@log_function_calls()
def _validate_list_schema(field_path: str, value: Any, schema: List[Any]) -> None:
    """
    Validate a value against list schema definitions with element validation.

    Ensures the value is a list and validates each element against the allowed
    schema types. Supports flexible schemas where list items can match any of
    multiple defined types, and it handles special cases like requirement objects.

    Args:
        field_path: Field location path for error context
        value: Value to validate (must be a list)
        schema: List of allowed element schemas

    Raises:
        ValueError: When the value is not a list or elements don't match schema

    Examples:
        >>> _validate_list_schema("args", ["--help"], ["str"]) # ✓ Valid
        >>> _validate_list_schema("ports", [80, 443], ["int"]) # ✓ Valid
        >>> _validate_list_schema("mixed", [1, "test"], ["int", "str"]) # ✓ Valid
        >>> _validate_list_schema("ports", "80", ["int"]) # ✗ ValueError
    """
    # noinspection DuplicatedCode
    function_name = inspect.currentframe().f_code.co_name
    logger.debug(f"{function_name}: ⚡ List schema validation for '{field_path}'")

    # Ensure the value is actually a list type
    if not isinstance(value, list):
        error_msg = (
            f"Type validation failed for '{field_path}': "
            f"Expected list, but received '{type(value).__name__}'. "
            f"Value: {repr(value)}"
        )
        logger.error(f"{function_name}: {error_msg}")
        raise ValueError(error_msg)

    # Handle empty schema as permissive (any list content allowed)
    if not schema:
        logger.debug(
            f"{function_name}: empty schema for list field '{field_path}' - validation skipped")
        return

    # Validate each list element against schema options
    for index, item in enumerate(value):
        item_path = f"{field_path}[{index}]"
        logger.debug(f"{function_name}: validating list element at index {index}")

        # Special handling for requirement objects (single-key dictionaries)
        # These represent TOSCA requirements like {'host': 'resource-1'}
        if isinstance(item, dict) and len(item) == 1:
            requirement_name, requirement_value = next(iter(item.items()))
            _validate_requirement_item(item_path, requirement_name, requirement_value, schema)
            continue

        # Attempt to match the item against any valid schema type
        # noinspection DuplicatedCode
        validation_succeeded = False

        for schema_type in schema:
            try:
                validate_field_schema(item_path, item, schema_type)
                validation_succeeded = True
                break  # Found valid schema match, stop checking
            except ValueError:
                continue  # Try the next schema option

        # Only log error when ALL options fail
        if not validation_succeeded:
            schema_descriptions = [str(s) for s in schema]
            error_msg = (
                f"List element validation failed for '{item_path}': "
                f"Element doesn't match any allowed schema types {schema_descriptions}. "
                f"Element type: '{type(item).__name__}', Value: {repr(item)}"
            )
            logger.error(f"{function_name}: {error_msg}")
            raise ValueError(error_msg)

    logger.debug(f"{function_name}: ✅ List schema validation for '{field_path}' completed")


@log_function_calls()
def _validate_requirement_item(item_path: str, req_name: str, req_value: Any, schema: List[Any]) -> None:
    """
    Validate TOSCA requirement items with specialized requirement name and value validation.

    Requirements are special TOSCA constructs representing dependencies between nodes,
    formatted as single-key dictionaries like {'host': 'target-node'} or
    {'volume': {'node_filter': {...}}}. This function locates the appropriate
    requirement schema and validates both the requirement name and its value.

    Args:
        item_path: Path to the requirement item for error context
        req_name: The requirement name (key) from the requirement dictionary
        req_value: The requirement value to validate
        schema: List of possible requirement schemas

    Raises:
        ValueError: When the requirement name is not found in the schema or value is invalid

    Examples:
        >>> # Valid requirement validation
        >>> _validate_requirement_item("reqs[0]", "host", "web-server",
        ... [{"host": ["str"]}]) # ✓ Valid
        >>> # Invalid requirement name
        >>> _validate_requirement_item("reqs[0]", "storage", "disk1",
        ... [{"host": ["str"]}]) # ✗ ValueError
    """
    function_name = inspect.currentframe().f_code.co_name
    logger.debug(
        f"{function_name}: ⚡ Requirement validation '{req_name}' value under path '{item_path}'")
    # Search for the requirement schema that defines this requirement name
    matching_requirement_schema = None
    available_requirement_names = set()

    for schema_item in schema:
        if isinstance(schema_item, dict):
            # Collect all available requirement names for error reporting
            available_requirement_names.update(schema_item.keys())

            # Check if this schema item contains our requirement
            if req_name in schema_item:
                matching_requirement_schema = schema_item[req_name]
                break

    # Handle case where the requirement name is not defined in any schema
    if matching_requirement_schema is None:
        sorted_available = sorted(available_requirement_names)
        error_msg = (
            f"Unknown requirement validation error for '{item_path}': "
            f"Requirement name '{req_name}' is not defined in the schema. "
            f"Available requirement names: {sorted_available}"
        )
        logger.error(f"{function_name}: {error_msg}")
        raise ValueError(error_msg)

    # Validate the requirement value against its specific schema
    requirement_value_path = f"{item_path}.{req_name}"
    logger.debug(
        f"{function_name}: validating requirement '{req_name}' found at path '{requirement_value_path}'")

    _validate_requirement_value(requirement_value_path, req_value, matching_requirement_schema)

    logger.debug(
        f"{function_name}: ✅ Requirement validation '{req_name}' value under path '{item_path}' completed")


@log_function_calls()
def _validate_requirement_value(field_path: str, value: Any, schema: Any) -> None:
    """
    Validate requirement values against their schema definitions with flexible type support.

    Requirement values can be simple strings (node names), lists of constraints,
    or complex objects with filters and conditions. This function handles all
    requirement value types and validates them against their respective schemas.

    Args:
        field_path: Path to requirement value for error context
        value: The requirement value to validate
        schema: Schema definition for this requirement value

    Raises:
        ValueError: When requirement value doesn't conform to schema

    Examples:
        >>> # Simple string requirement value
        >>> _validate_requirement_value("req.host", "web-server", "str") # ✓ Valid
        >>> # Complex requirement value with multiple options
        >>> _validate_requirement_value("req.host", {"node_filter": {}},
        ... ["str", {"node_filter": "dict"}]) # ✓ Valid
    """
    function_name = inspect.currentframe().f_code.co_name
    logger.debug(
        f"{function_name}: ⚡ Requirement schema validation of type '{type(value).__name__}'")

    # Handle schema lists (multiple allowed value types)
    if isinstance(schema, list):

        # Special handling for list values - validate each element
        if isinstance(value, list):
            logger.debug(
                f"{function_name}: validating list requirement value with {len(value)} elements")

            for index, element in enumerate(value):
                element_path = f"{field_path}[{index}]"
                # noinspection DuplicatedCode
                element_matched = False

                # Try to match the element against each schema option
                for schema_option in schema:
                    try:
                        validate_field_schema(element_path, element, schema_option)
                        element_matched = True
                        break
                    except ValueError:
                        continue  # Try the next schema option - don't log intermediate failures

                # Only log error when ALL options fail
                if not element_matched:
                    schema_types = [str(s) for s in schema]
                    error_msg = (
                        f"Requirement list element validation failed for '{element_path}': "
                        f"Element doesn't match any allowed types {schema_types}. "
                        f"Element type: '{type(element).__name__}', Value: {repr(element)}"
                    )
                    logger.error(f"{function_name}: {error_msg}")
                    raise ValueError(error_msg)
            return

        # Handle non-list values - try each schema option
        # noinspection DuplicatedCode
        validation_succeeded = False
        for schema_option in schema:
            try:
                validate_field_schema(field_path, value, schema_option)
                validation_succeeded = True
                break
            except ValueError:
                continue  # Try the next schema option

        # Only log error when ALL options fail
        if not validation_succeeded:
            schema_types = [str(s) for s in schema]
            error_msg = (
                f"Requirement value validation failed for '{field_path}': "
                f"Value doesn't match any allowed tosca_types {schema_types}. "
                f"Value type: '{type(value).__name__}', Value: {repr(value)}"
            )
            logger.error(f"{function_name}: {error_msg}")
            raise ValueError(error_msg)
    else:
        # Single schema type - direct validation
        logger.debug(f"{function_name}: validating single-schema requirement value")
        validate_field_schema(field_path, value, schema)

    logger.debug(
        f"{function_name}: ✅ Requirement schema validation of type '{type(value).__name__}' completed")


@log_function_calls()
def _validate_dict_schema(field_path: str, value: Any, schema: Dict[str, Any]) -> None:
    """
    Validate dictionary values against object schema definitions with property validation.

    Ensures the value is a dictionary, validates that all keys are defined in the schema,
    and recursively validates each property value against its schema definition.
    Provides comprehensive validation for nested object structures.

    Args:
        field_path: Field location path for error context
        value: Value to validate (must be a dictionary)
        schema: Dictionary schema with property definitions

    Raises:
        ValueError: When the value is not a dict, contains unknown keys, or property values are invalid

    Examples:
        >>> sample_schema = {"name": "str", "port": "int"}
        >>> _validate_dict_schema("config", {"name": "app", "port": 80}, sample_schema)  # ✓ Valid
        >>> _validate_dict_schema("config", {"name": "app", "ssl": True}, sample_schema) # ✗ ValueError (unknown key 'ssl')
        >>> _validate_dict_schema("config", "not-a-dict", sample_schema)                 # ✗ ValueError (not a dict)
    """
    # noinspection DuplicatedCode
    function_name = inspect.currentframe().f_code.co_name
    logger.debug(f"{function_name}: ⚡ Dictionary schema validation for '{field_path}'")

    # Ensure the value is actually a dictionary type
    if not isinstance(value, dict):
        error_msg = (
            f"Type validation failed for '{field_path}': "
            f"Expected dict, but received '{type(value).__name__}'. "
            f"Value: {repr(value)}"
        )
        logger.error(f"{function_name}: {error_msg}")
        raise ValueError(error_msg)

    # Validate that all dictionary keys are defined in schema
    unknown_keys = []
    for key in value.keys():
        if key not in schema:
            unknown_keys.append(key)

    if unknown_keys:
        allowed_keys = sorted(schema.keys())
        error_msg = (
            f"Dictionary validation failed for '{field_path}': "
            f"Unknown keys {unknown_keys} found. "
            f"Allowed keys: {allowed_keys}"
        )
        logger.error(f"{function_name}: {error_msg}")
        raise ValueError(error_msg)

    # Recursively validate each property value against its schema
    for property_name, property_value in value.items():
        if property_name in schema:
            property_path = f"{field_path}.{property_name}"
            property_schema = schema[property_name]

            logger.debug(
                f"{function_name}: validating property '{property_name}' of type '{type(property_value).__name__}'")
            validate_field_schema(property_path, property_value, property_schema)

    logger.debug(
        f"{function_name}: ✅ Dictionary schema validation for '{field_path}' completed")
