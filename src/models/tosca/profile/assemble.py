"""Assemble a TOSCA document from database rows.

The caller sends rows keyed by table name; the profile's gui_name bindings say
where each column lands. Cardinality comes from the payload itself: the table
that supplies node template names contributes one node template per row, and
single-row tables are shared across all of them.

Nothing is dropped silently. Any table or column in the payload that no binding
claims is reported as a warning, so data that cannot be placed is visible rather
than quietly discarded.
"""
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from src.utils.logger import get_logger, log_function_calls

from .bindings import Binding, collect_bindings, document_bindings
from .resolver import Profile

logger = get_logger()

# TOSCA scalar types that map onto a Python builtin. Everything else
# (map, list, timestamp, version, scalar-unit.*) passes through untouched.
_COERCIONS = {
    "integer": int,
    "float": float,
    "string": str,
}

_TRUTHY = {"true", "t", "yes", "y", "1"}
_FALSEY = {"false", "f", "no", "n", "0"}


@log_function_calls()
def assemble(
        profile: Profile,
        type_name: str,
        payload: Mapping[str, Any],
        namespace: str = "swch",
        definitions_version: str = "tosca_2_0",
        imports: Any = None,
        metadata: Dict[str, Any] | None = None,
        description: str | None = None,
) -> Tuple[Dict[str, Any], List[Dict[str, str]]]:
    """Build a TOSCA document for one capacity.

    Args:
        profile: Resolved profile providing types and bindings
        type_name: Node type to instantiate (e.g. CloudCapacity)
        payload: Database rows keyed by table name
        namespace: Import namespace prefix applied to node types
        definitions_version: TOSCA definitions version for the document
        imports: Imports block to emit verbatim
        metadata: Base metadata, merged under any bound values
        description: Overrides the bound description when given

    Returns:
        Tuple of (document, warnings)
    """
    resolved = profile.resolve(type_name)
    bindings = collect_bindings(resolved, profile)
    documents = document_bindings(profile)

    warnings: List[Dict[str, str]] = []
    claimed = _claimed_columns(bindings)

    instance_table, name_column = documents.get("node_template.name", (None, None))
    if not instance_table:
        raise ValueError(
            "Profile is missing a 'node_template.name' gui_binding; "
            "nothing designates which table produces node templates."
        )

    instance_rows = _as_rows(payload.get(instance_table))
    if not instance_rows:
        warnings.append({
            "payload": f"No rows for '{instance_table}', so no node templates were produced"
        })

    node_templates: Dict[str, Any] = {}
    for index, row in enumerate(instance_rows):
        name = row.get(name_column) if name_column else None
        if not name:
            name = f"{type_name.lower()}-{index + 1}"
            warnings.append({
                "node_template": f"Row {index + 1} of '{instance_table}' has no "
                                 f"{name_column}, named '{name}' instead"
            })
        if name in node_templates:
            warnings.append({"node_template": f"Duplicate node template name '{name}', overwriting"})

        node_templates[str(name)] = _build_node(
            bindings, payload, row, instance_table, f"{namespace}:{type_name}"
        )

    document: Dict[str, Any] = {"tosca_definitions_version": definitions_version}

    resolved_metadata = dict(metadata or {})
    bound_name = _document_value(documents.get("metadata.name"), payload)
    if bound_name:
        resolved_metadata["name"] = bound_name
    if resolved_metadata:
        document["metadata"] = resolved_metadata

    resolved_description = description or _document_value(documents.get("description"), payload)
    if resolved_description:
        document["description"] = resolved_description

    if imports:
        document["imports"] = imports

    document["service_template"] = {"node_templates": node_templates}

    warnings.extend(_unclaimed(payload, claimed, documents, profile))
    return document, warnings


def _build_node(
        bindings: Sequence[Binding],
        payload: Mapping[str, Any],
        instance_row: Mapping[str, Any],
        instance_table: str,
        node_type: str,
) -> Dict[str, Any]:
    """Build one node template by placing each bound value at its path."""
    node: Dict[str, Any] = {"type": node_type}

    for binding in bindings:
        value = _value_for(binding, payload, instance_row, instance_table)
        if value is None or value == [] or value == {}:
            # Absent values are omitted; the profile's defaults still apply
            # when the template is parsed against it.
            continue
        _set_path(node, binding.path, value)

    return node


def _value_for(
        binding: Binding,
        payload: Mapping[str, Any],
        instance_row: Mapping[str, Any],
        instance_table: str,
) -> Any:
    """Resolve a single binding against the payload."""
    if binding.is_list:
        return _list_value(binding, payload)

    if binding.table == instance_table:
        source = instance_row
    else:
        rows = _as_rows(payload.get(binding.table))
        if not rows:
            return None
        if len(rows) > 1:
            logger.debug(
                f"_value_for: '{binding.table}' has {len(rows)} rows for a single-valued "
                f"binding, using the first"
            )
        source = rows[0]

    return _coerce(source.get(binding.column), binding.definition)


def _list_value(binding: Binding, payload: Mapping[str, Any]) -> List[Any] | None:
    """Resolve a list-typed binding into a list of entries."""
    rows = [row for row in _as_rows(payload.get(binding.table)) if _matches(row, binding.filters)]
    if not rows:
        return None

    if not binding.entry_bindings:
        # A plain list column, e.g. explicit_tcp_allow, whose entry_schema is a
        # primitive rather than a data type.
        values = [row.get(binding.column) for row in rows] if binding.column else rows
        flattened = [v for value in values for v in (value if isinstance(value, list) else [value])]
        return [v for v in flattened if v is not None] or None

    entries = []
    for row in rows:
        entry = {
            path[0]: _coerce(row.get(entry_binding.column), entry_binding.definition)
            for entry_binding in binding.entry_bindings
            if (path := entry_binding.path) and row.get(entry_binding.column) is not None
        }
        if entry:
            entries.append(entry)
    return entries or None


def _document_value(source: Tuple[str, str | None] | None, payload: Mapping[str, Any]) -> Any:
    """Resolve a document-level binding, e.g. metadata.name."""
    if not source:
        return None
    table, column = source
    rows = _as_rows(payload.get(table))
    if not rows or not column:
        return None
    return rows[0].get(column)


def _matches(row: Mapping[str, Any], filters: Mapping[str, str]) -> bool:
    return all(str(row.get(key)) == value for key, value in (filters or {}).items())


def _coerce(value: Any, definition: Mapping[str, Any]) -> Any:
    """Coerce a database value to the type the profile declares."""
    if value is None:
        return None

    declared = (definition or {}).get("type")

    if declared == "boolean":
        if isinstance(value, bool):
            return value
        text = str(value).strip().lower()
        if text in _TRUTHY:
            return True
        if text in _FALSEY:
            return False
        return value

    coercion = _COERCIONS.get(declared)
    if not coercion or isinstance(value, bool):
        return value

    try:
        return coercion(value)
    except (TypeError, ValueError):
        logger.warning(f"_coerce: cannot convert {value!r} to {declared}, passing through")
        return value


def _set_path(target: Dict[str, Any], path: Sequence[str], value: Any) -> None:
    """Set a value at a nested path, creating intermediate dicts."""
    node = target
    for key in path[:-1]:
        node = node.setdefault(key, {})
    node[path[-1]] = value


def _as_rows(value: Any) -> List[Mapping[str, Any]]:
    """Normalise a payload entry to a list of rows."""
    if value is None:
        return []
    if isinstance(value, Mapping):
        return [value]
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return [row for row in value if isinstance(row, Mapping)]
    return []


def _claimed_columns(bindings: Sequence[Binding]) -> Dict[str, set]:
    """Every column a set of bindings reads, including entries and filters."""
    claimed: Dict[str, set] = {}
    for binding in bindings:
        columns = claimed.setdefault(binding.table, set())
        if binding.column:
            columns.add(binding.column)
        # Filters and entry properties read columns the binding never names.
        columns.update(binding.filters)
        columns.update(
            entry.column for entry in binding.entry_bindings if entry.column
        )
    return claimed


def _profile_wide_columns(profile: Profile) -> Dict[str, set]:
    """Columns bound anywhere in the profile, across every node type."""
    everywhere: Dict[str, set] = {}
    for type_name in profile.type_names("node_types"):
        try:
            bindings = collect_bindings(profile.resolve(type_name), profile)
        except (KeyError, ValueError):
            continue
        for table, columns in _claimed_columns(bindings).items():
            everywhere.setdefault(table, set()).update(columns)
    return everywhere


def _unclaimed(
        payload: Mapping[str, Any],
        claimed: Mapping[str, set],
        documents: Mapping[str, Tuple[str, str | None]],
        profile: Profile,
) -> List[Dict[str, str]]:
    """Report payload data that no binding places into the document.

    Data bound on another node type is reported separately from data bound
    nowhere at all: the first is a payload/type mismatch, the second means the
    value has no home in the profile and would be lost.
    """
    warnings: List[Dict[str, str]] = []

    document_columns: Dict[str, set] = {}
    for table, column in documents.values():
        document_columns.setdefault(table, set()).add(column)

    elsewhere = _profile_wide_columns(profile)

    for table, rows in payload.items():
        table_rows = _as_rows(rows)
        if not table_rows:
            continue

        used = set(claimed.get(table, set())) | set(document_columns.get(table, set()))
        known = used | set(elsewhere.get(table, set()))
        present = {column for row in table_rows for column in row}
        # Keys and timestamps are structural, not template content.
        candidates = {
            column for column in present
            if not column.endswith("_id") and column not in {"id", "created_at", "updated_at"}
        }

        unbound = candidates - known
        if unbound:
            warnings.append({
                "payload": f"Columns on '{table}' have no gui_name binding anywhere in the "
                           f"profile and were not used: {', '.join(sorted(unbound))}"
            })

        other_type_only = candidates - used - unbound
        if other_type_only:
            warnings.append({
                "payload": f"Columns on '{table}' are bound on another node type and were "
                           f"not used here: {', '.join(sorted(other_type_only))}"
            })

    return warnings
