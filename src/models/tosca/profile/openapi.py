"""Describe the payload a build endpoint accepts, derived from the bindings.

The request body is database rows keyed by table, so its shape is not a fixed
model - it follows whatever the profile's gui_name bindings read. Deriving the
schema here keeps the documentation honest: a binding added to the profile shows
up in Swagger without anything else being edited.
"""
from typing import Any, Dict, List, Sequence

from src.utils.logger import get_logger

from .bindings import Binding, collect_bindings, document_bindings, free_property_binding
from .resolver import Profile

logger = get_logger()

# TOSCA declared types to JSON Schema types.
_JSON_TYPES = {
    "integer": "integer",
    "float": "number",
    "string": "string",
    "boolean": "boolean",
    "list": "array",
    "map": "object",
}


def payload_schema(
        profile: Profile,
        type_names: Sequence[str] | None = None,
        bindings_group: str | None = None,
) -> Dict[str, Any]:
    """Build a JSON Schema for the table-keyed payload.

    Args:
        profile: Profile supplying the bindings
        type_names: Node types to document. Defaults to every bound type, so
            the schema covers everything the endpoint can consume.
        bindings_group: Which document-level binding group to document

    Returns:
        A JSON Schema object describing the request body
    """
    documents = document_bindings(profile, bindings_group)
    free_binding = free_property_binding(profile, bindings_group)
    instance_table, _ = documents.get("node_template.name", (None, None))

    if type_names is None:
        type_names = _bound_node_types(profile)

    tables: Dict[str, Dict[str, Any]] = {}
    required: Dict[str, set] = {}
    arrays: set = {instance_table} if instance_table else set()

    for target, (table, column) in documents.items():
        if column:
            _add_column(tables, table, column, {"type": "string"},
                        f"Populates {target} of the generated document")

    for type_name in type_names:
        for binding in collect_bindings(profile.resolve(type_name), profile):
            _add_binding(tables, required, arrays, binding, type_name)

    if free_binding:
        arrays.add(free_binding.table)
        _add_column(tables, free_binding.table, free_binding.key_column, {"type": "string"},
                    "Name of the property to set. Must be one the node type declares")
        _add_column(tables, free_binding.table, free_binding.value_column, {"type": "string"},
                    "Value for that property, coerced to the type the profile declares")
        required.setdefault(free_binding.table, set()).add(free_binding.key_column)

    properties: Dict[str, Any] = {}
    for table, columns in sorted(tables.items()):
        row = {"type": "object", "properties": columns}
        if required.get(table):
            row["required"] = sorted(required[table])
        if table in arrays:
            properties[table] = {
                "type": "array",
                "items": row,
                "description": f"One entry per row of '{table}'",
            }
        else:
            properties[table] = {
                **row,
                "description": f"A single row of '{table}'. An array is also accepted, "
                               f"in which case the first row is used",
            }

    return {
        "type": "object",
        "title": f"{(bindings_group or 'Document').capitalize()} payload",
        "description": "Database rows keyed by table name. Derived from the profile's "
                       "gui_name bindings, so it changes with the profile.",
        "properties": properties,
        "additionalProperties": True,
    }


def _add_binding(
        tables: Dict[str, Dict[str, Any]],
        required: Dict[str, set],
        arrays: set,
        binding: Binding,
        type_name: str,
) -> None:
    """Record the columns one binding reads."""
    if binding.entry_bindings:
        # Rows of a child table, each becoming one entry of a list property.
        arrays.add(binding.table)
        for key in binding.filters:
            _add_column(tables, binding.table, key, {"type": "string"},
                        f"Selects rows for '{binding.path[-1]}'")
        for entry in binding.entry_bindings:
            _add_column(tables, binding.table, entry.column,
                        _json_type(entry.definition),
                        _describe(entry.definition, type_name, entry.path[-1]))
        return

    if not binding.column:
        return

    _add_column(tables, binding.table, binding.column, _json_type(binding.definition),
                _describe(binding.definition, type_name, binding.path[-1]))

    # Required with a default is satisfiable without the caller supplying it.
    if binding.definition.get("required") and "default" not in binding.definition:
        required.setdefault(binding.table, set()).add(binding.column)


def _add_column(
        tables: Dict[str, Dict[str, Any]],
        table: str,
        column: str | None,
        schema: Dict[str, Any],
        description: str,
) -> None:
    if not column:
        return
    columns = tables.setdefault(table, {})
    # First binding wins; a column read by two types has one shape.
    columns.setdefault(column, {**schema, "description": description})


def _json_type(definition: Dict[str, Any]) -> Dict[str, Any]:
    declared = (definition or {}).get("type")
    json_type = _JSON_TYPES.get(declared, "string")
    schema: Dict[str, Any] = {"type": json_type}
    if json_type == "array":
        entry = (definition or {}).get("entry_schema")
        schema["items"] = {"type": _JSON_TYPES.get(entry, "string")}
    return schema


def _describe(definition: Dict[str, Any], type_name: str, property_name: str) -> str:
    parts = [f"{type_name}.{property_name}"]
    if (definition or {}).get("description"):
        parts.append(str(definition["description"]).strip().splitlines()[0])
    if (definition or {}).get("default") is not None:
        parts.append(f"Defaults to {definition['default']!r} when omitted.")
    return " - ".join(parts)


def _bound_node_types(profile: Profile) -> List[str]:
    """Node types that have at least one binding."""
    bound = []
    for type_name in profile.type_names("node_types"):
        try:
            if collect_bindings(profile.resolve(type_name), profile):
                bound.append(type_name)
        except (KeyError, ValueError):
            continue
    return bound
