"""
TOSCA Schema Builder

Builds unified schemas from TOSCA definitions by analyzing structure
and merging similar templates. Extracts type information, property schemas, and
nested object definitions to create comprehensive validation schemas.
"""

import inspect
from typing import Any, List

from src.utils.logger import get_logger, log_function_calls

logger = get_logger()


@log_function_calls()
def build_schema(templates: dict[str, Any]) -> dict[Any, Any]:
    """
    Build unified schema from TOSCA definitions.

    Processes each template to extract schema information and merges
    the schemas for templates of the same type.

    Args:
        templates: Dictionary of template configurations keyed by name

    Returns:
        dict: Schema organized by type with merged field definitions

    Raises:
        ValueError: When the template is missing the required 'type' field

    Example:
        >>> sample_templates = {
        ... "web": {"type": "Application", "properties": {"image": "nginx"}},
        ... "db": {"type": "Application", "properties": {"image": "postgres"}}
        ... }
        >>> build_schema(sample_templates)
        {"Application": {"properties": {"image": "str"}}}
    """
    function_name = inspect.currentframe().f_code.co_name
    logger.debug(f"{function_name}: processing TOSCA templates")
    schema = {}

    if isinstance(templates, dict) and templates:
        # For nodes: templates["node-name"]
        _process_templates(schema, templates)
    elif isinstance(templates, list):
        # For policies: templates[0]["policy-name"]
        for template in templates:
            _process_templates(schema, template)
    else:
        error_msg = "Invalid TOSCA templates format"
        logger.error(f"{function_name}: {error_msg}")
        raise ValueError(error_msg)

    logger.debug(f"{function_name}: built schema for {len(schema)} types")
    return schema


def _process_templates(schema: dict[Any, Any], templates: dict[str, Any]):
    """Process each template to extract and merge schemas."""
    function_name = inspect.currentframe().f_code.co_name
    logger.debug(f"{function_name}: processing {len(templates)} templates")

    for template_name, template_values in templates.items():
        # Validate required 'type' field presence
        if 'type' not in template_values:
            error_msg = (
                f"Template '{template_name}' is missing required 'type' field. "
                f"All TOSCA templates must specify their type."
            )
            logger.error(f"{function_name}: {error_msg}")
            raise ValueError(error_msg)

        # Extract type name (remove namespace prefix if present)
        type_name = template_values['type'].split(':')[-1]

        # Initialize schema for this type if not exists
        schema.setdefault(type_name, {})

        # Process each field in the template (except 'type')
        for field_name, field_values in template_values.items():
            if field_name == 'type':
                continue  # Skip the type field as it's metadata

            # Extract schema properties from field value
            field_schema = _get_properties(field_values)

            # Merge with the existing schema for this field
            existing_schema = schema[type_name].get(field_name)
            merged_schema = _merge_schema(existing_schema, field_schema)
            schema[type_name][field_name] = merged_schema


def _get_properties(value: Any) -> Any:
    """
    Extract schema representation from a value by analyzing its structure.

    Recursively processes values to create schema definitions that capture
    type information, structure patterns, and nested object definitions.

    Args:
        value: Value to analyze for schema extraction

    Returns:
        Schema representation based on the value type:
        - Primitives: Type name string (e.g., "str", "int")
        - Dictionaries: Nested schema object with property definitions
        - Lists: Array of possible element schemas
        - Empty containers: Container type name

    Examples:
        >>> _get_properties("hello")
        'str'
        >>> _get_properties({"name": "test", "count": 5})
        {'name': 'str', 'count': 'int'}
        >>> _get_properties([1, "text", {"key": "value"}])
        ['int|str', {'key': 'str'}]
    """
    if isinstance(value, dict):
        # Handle dictionary values - process each property
        if not value:
            return "dict"

        schema = {}
        for key, val in value.items():
            schema[str(key)] = _get_properties(val)

        return schema

    elif isinstance(value, list):
        # Handle list values - merge all element schemas
        if not value:
            return "list"

        # Separate different types of elements for organized processing
        merged_dict = {}  # Dictionary elements merged into a single schema
        primitive_types = set()  # Unique primitive type names
        nested_list_schema = None  # Schema for nested list structures

        for item in value:
            if isinstance(item, dict):
                if item:  # Only process non-empty dictionaries
                    # Merge dictionary properties into a unified schema
                    for k, v in item.items():
                        existing_prop = merged_dict.get(k)
                        new_prop = _get_properties(v)
                        merged_dict[k] = _merge_schema(existing_prop, new_prop)
                else:
                    primitive_types.add("dict")

            elif isinstance(item, list):
                # Process nested lists and merge their schemas
                item_schema = _get_properties(item)
                if nested_list_schema is None:
                    nested_list_schema = item_schema
                else:
                    nested_list_schema = _merge_schema(nested_list_schema, item_schema)

            else:
                # Primitive types - collect unique type names
                item_type = type(item).__name__
                primitive_types.add(item_type)

        # Build result with consistent ordering: primitives → nested lists → objects
        result = []

        # Add primitive types (as union if multiple types exist)
        if primitive_types:
            if len(primitive_types) == 1:
                result.append(list(primitive_types)[0])
            else:
                # Create a union type from sorted primitive types
                union_type = "|".join(sorted(primitive_types))
                result.append(union_type)

        # Add the nested list schema if present
        if nested_list_schema is not None:
            result.append(nested_list_schema)

        # Add the merged dictionary schema if present
        if merged_dict:
            result.append(merged_dict)

        return result

    else:
        # Handle primitive values - return type name
        return type(value).__name__


def _merge_schema(a: Any, b: Any, depth: int = 0, max_depth: int = 100) -> Any:
    """
    Intelligently merge two schema values with type-specific strategies.

    Combines schema representations from multiple sources using appropriate
    merge strategies based on value types. Includes recursion protection
    for deeply nested structures.

    Args:
        a: First schema value to merge
        b: Second schema value to merge
        depth: Current recursion depth (for protection)
        max_depth: Maximum allowed recursion depth

    Returns:
        Merged schema using the appropriate strategy for input types

    Examples:
        >>> _merge_schema({"name": "str"}, {"age": "int"})
        {'name': 'str', 'age': 'int'}
        >>> _merge_schema("str", "int")
        'int|str'
        >>> _merge_schema(["str"], ["int"])
        ['int|str']
    """
    function_name = inspect.currentframe().f_code.co_name
    # Recursion protection - prevent stack overflow on deep nesting
    if depth > max_depth:
        logger.warning(f"{function_name}: max recursion depth reached, using fallback merge")
        return b  # Fallback: prefer second value

    # Handle null/empty cases - prefer non-empty values
    if not a:
        return b
    if not b:
        return a
    if a == b:
        return a  # Identical values don't need merging

    # Merge dictionaries recursively by combining all keys
    if isinstance(a, dict) and isinstance(b, dict):
        result = a.copy()

        for key, value in b.items():
            if key in result:
                # Merge overlapping key
                result[key] = _merge_schema(result[key], value, depth + 1, max_depth)
            else:
                # Add a new key
                result[key] = value

        return result

    # Merge lists using the specialized list merge function
    if isinstance(a, list) and isinstance(b, list):
        return _merge_list(a, b, depth + 1, max_depth)

    # Merge string types by creating union types
    if isinstance(a, str) and isinstance(b, str):
        # Split existing union types and combine with new types
        types_a = set(a.split("|"))
        types_b = set(b.split("|"))
        combined_types = types_a.union(types_b)

        return "|".join(sorted(combined_types))

    # Different types - preserve both by returning as an array
    return [a, b]


def _merge_list(a: List, b: List, depth: int = 0, max_depth: int = 100) -> List:
    """
    Merge two schema lists by combining elements and merging similar structures.

    Specialized list merging for schema purposes that combines primitive types
    into unions, merges dictionary objects, and handles nested list structures.

    Args:
        a: First list to merge
        b: Second list to merge
        depth: Current recursion depth
        max_depth: Maximum recursion depth

    Returns:
        Merged the list with combined primitives, merged objects, and nested structures

    Examples:
        >>> _merge_list(["str", {"name": "str"}], ["int", {"age": "int"}])
        ['int|str', {'name': 'str', 'age': 'int'}]
    """
    function_name = inspect.currentframe().f_code.co_name
    # Recursion protection
    if depth > max_depth:
        logger.warning(f"{function_name}: max recursion depth reached in list merge")
        return a + b  # Fallback: simple concatenation

    result = []
    merged_dict = {}  # Accumulator for dictionary merging
    nested_lists = []  # Collector for nested list schemas
    primitive_types = set()  # Set to avoid duplicate primitive types

    # Process all elements from both lists
    all_items = a + b

    for item in all_items:
        if isinstance(item, dict):
            # Merge dictionary items into a unified structure
            for key, value in item.items():
                existing_value = merged_dict.get(key)
                merged_dict[key] = _merge_schema(existing_value, value, depth + 1, max_depth)

        elif isinstance(item, list):
            # Collect nested lists for later merging
            nested_lists.append(item)

        elif isinstance(item, str):
            # Handle string types - check for union types
            if '|' in item:
                # Split union types and add individual types
                primitive_types.update(item.split('|'))
            else:
                primitive_types.add(item)

    # Build result in consistent order: primitives → nested lists → dictionaries

    # Add merged primitive types
    if primitive_types:
        if len(primitive_types) == 1:
            primitive_result = list(primitive_types)[0]
        else:
            primitive_result = '|'.join(sorted(primitive_types))

        result.append(primitive_result)

    # Merge and add nested lists
    if nested_lists:
        merged_nested = nested_lists[0]

        for nested_list in nested_lists[1:]:
            merged_nested = _merge_schema(merged_nested, nested_list, depth + 1, max_depth)

        result.append(merged_nested)

    # Add the merged dictionary if it contains properties
    if merged_dict:
        result.append(merged_dict)

    return result
