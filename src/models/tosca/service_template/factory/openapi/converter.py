"""Convert TOSCA schema to OpenAPI format."""

import inspect
from typing import Dict, Any, List

from src.utils.logger import get_logger

logger = get_logger()


def convert_tosca_to_openapi(tosca_schema: Dict[str, Any]) -> Dict[str, Any]:
    """Convert the full TOSCA schema to OpenAPI format."""
    function_name = inspect.currentframe().f_code.co_name
    if 'schema' not in tosca_schema:
        msg = "Invalid TOSCA schema: missing 'schema' field"
        logger.debug(f"{function_name}: {msg}")
        raise ValueError(msg)

    # Simply convert all schemas in the 'schema' field directly
    return {
        node_type: _convert_schema_to_openapi(schema)
        for node_type, schema in tosca_schema['schema'].items()
    }


def _convert_schema_to_openapi(schema: Any) -> Dict[str, Any]:
    """Convert individual schema element to OpenAPI format."""
    if isinstance(schema, str):
        return _convert_string_schema(schema)
    elif isinstance(schema, dict):
        return _convert_dict_schema(schema)
    elif isinstance(schema, list):
        return _convert_list_schema(schema)
    else:
        return {"type": "string"}  # fallback


def _convert_string_schema(schema: str) -> Dict[str, Any]:
    """Convert string schema to OpenAPI format."""
    # Handle union types like "float|int|str"
    if '|' in schema:
        types = [_map_type_to_openapi(t.strip()) for t in schema.split('|')]
        # Remove duplicates while preserving order
        unique_types = []
        for t in types:
            if t not in unique_types:
                unique_types.append(t)

        if len(unique_types) == 1:
            return unique_types[0]
        else:
            return {"anyOf": unique_types}
    else:
        return _map_type_to_openapi(schema)


def _convert_dict_schema(schema: Dict[str, Any]) -> Dict[str, Any]:
    """Convert dictionary schema to OpenAPI format."""
    if not schema:
        return {"type": "object"}

    return {
        "type": "object",
        "properties": {
            key: _convert_schema_to_openapi(value)
            for key, value in schema.items()
        },
        "additionalProperties": False
    }


def _convert_list_schema(schema: List[Any]) -> Dict[str, Any]:
    """Convert list schema to OpenAPI format."""
    if not schema:
        return {"type": "array", "items": {}}

    # Convert each possible item type
    item_schemas = [_convert_schema_to_openapi(item) for item in schema]

    # Try to merge compatible object schemas
    merged_schemas = _merge_compatible_schemas(item_schemas)

    if len(merged_schemas) == 1:
        return {
            "type": "array",
            "items": merged_schemas[0]
        }
    else:
        return {
            "type": "array",
            "items": {
                "anyOf": merged_schemas
            }
        }


def _merge_compatible_schemas(schemas: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Merge compatible object schemas and remove duplicates."""
    if not schemas:
        return []

    # Remove exact duplicates first
    unique_schemas = []
    for schema in schemas:
        if schema not in unique_schemas:
            unique_schemas.append(schema)

    # Group by type for potential merging
    objects_to_merge = []
    other_schemas = []

    for schema in unique_schemas:
        if schema.get("type") == "object" and "properties" in schema:
            objects_to_merge.append(schema)
        else:
            other_schemas.append(schema)

    # Merge object schemas that have compatible properties
    if len(objects_to_merge) > 1:
        merged_object = {
            "type": "object",
            "properties": {},
            "additionalProperties": False
        }

        # Collect all properties from all objects
        for obj_schema in objects_to_merge:
            merged_object["properties"].update(obj_schema.get("properties", {}))

        if merged_object["properties"]:
            other_schemas.append(merged_object)
    elif len(objects_to_merge) == 1:
        other_schemas.extend(objects_to_merge)

    return other_schemas if other_schemas else unique_schemas


def _map_type_to_openapi(type_name: str) -> Dict[str, Any]:
    """Map TOSCA type names to OpenAPI type definitions."""
    type_mapping = {
        "str": {"type": "string"},
        "string": {"type": "string"},
        "int": {"type": "integer"},
        "integer": {"type": "integer"},
        "float": {"type": "number"},
        "number": {"type": "number"},
        "bool": {"type": "boolean"},
        "boolean": {"type": "boolean"},
        "dict": {"type": "object"},
        "list": {"type": "array"},
        "object": {"type": "object"},
        "array": {"type": "array"}
    }

    return type_mapping.get(type_name, {"type": "string"})
