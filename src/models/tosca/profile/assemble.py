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

from .bindings import (
    Binding,
    ENTRY_OPERATOR,
    KeyValueBinding,
    NodeFilterBinding,
    RANGE_OPERATOR,
    collect_bindings,
    document_bindings,
    filterable_targets,
    free_property_binding,
    node_filter_binding,
    policy_bindings,
)
from .resolver import Profile, ResolvedType

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


class InlineList(list):
    """A list that reads better on one line.

    A property lookup path and a range are single values written as sequences,
    so expanding them over five lines each buries the filter they belong to.
    Rendering honours this; JSON is unaffected, as it is still a list.
    """


@log_function_calls()
def assemble(
        profile: Profile,
        type_names: str | Sequence[str],
        payload: Mapping[str, Any],
        namespace: str = "swch",
        definitions_version: str = "tosca_2_0",
        imports: Any = None,
        metadata: Dict[str, Any] | None = None,
        description: str | None = None,
        bindings_group: str | None = None,
) -> Tuple[Dict[str, Any], List[Dict[str, str]]]:
    """Build a TOSCA document for one capacity.

    A type whose bindings read the instance table produces one node template per
    row of it. A type whose bindings do not - a totals node such as
    OverallCapacity - produces a single node template, and only when the payload
    actually carries data for it.

    Args:
        profile: Resolved profile providing types and bindings
        type_names: Node type, or types, to instantiate
        payload: Database rows keyed by table name
        namespace: Import namespace prefix applied to node types
        definitions_version: TOSCA definitions version for the document
        imports: Imports block to emit verbatim
        metadata: Base metadata, merged under any bound values
        description: Overrides the bound description when given
        bindings_group: Which document-level binding group to use, e.g.
            'capacity' or 'application'

    Returns:
        Tuple of (document, warnings)
    """
    requested = [type_names] if isinstance(type_names, str) else list(type_names)
    documents = document_bindings(profile, bindings_group)
    free_binding = free_property_binding(profile, bindings_group)
    filter_binding = node_filter_binding(profile, bindings_group)
    warnings: List[Dict[str, str]] = []

    instance_table, name_column = documents.get("node_template.name", (None, None))
    if not instance_table:
        raise ValueError(
            "Profile is missing a 'node_template.name' gui_binding; "
            "nothing designates which table produces node templates."
        )

    instance_rows = _as_rows(payload.get(instance_table))
    document_name = _document_value(documents.get("metadata.name"), payload)

    claimed: Dict[str, set] = {}
    node_templates: Dict[str, Any] = {}
    per_row_types = []

    for type_name in requested:
        resolved = profile.resolve(type_name)
        bindings = collect_bindings(resolved, profile)
        for table, columns in _claimed_columns(bindings, free_binding, filter_binding).items():
            claimed.setdefault(table, set()).update(columns)

        if any(binding.table == instance_table for binding in bindings):
            per_row_types.append(type_name)
            _add_per_row(
                node_templates, warnings, bindings, payload, instance_rows,
                instance_table, name_column, type_name, namespace,
                resolved, free_binding, filter_binding, profile,
            )
        else:
            _add_singleton(
                node_templates, warnings, bindings, payload,
                instance_table, type_name, namespace, document_name,
            )

    if per_row_types and not instance_rows:
        warnings.append({
            "payload": f"No rows for '{instance_table}', so no node templates were produced"
        })

    document: Dict[str, Any] = {"tosca_definitions_version": definitions_version}

    resolved_metadata = dict(metadata or {})
    # Any metadata.<key> binding populates that key, so author, version and the
    # rest need no special case here - only a binding in the profile.
    for target, source in documents.items():
        if not target.startswith("metadata."):
            continue
        value = _document_value(source, payload)
        if value not in (None, ""):
            resolved_metadata[target[len("metadata."):]] = value
    if resolved_metadata:
        document["metadata"] = resolved_metadata

    resolved_description = description or _document_value(documents.get("description"), payload)
    if resolved_description:
        document["description"] = resolved_description

    if imports:
        document["imports"] = imports

    service_template: Dict[str, Any] = {"node_templates": node_templates}
    policies = _build_policies(profile, payload, bindings_group, namespace)
    if policies:
        service_template["policies"] = policies
    document["service_template"] = service_template

    warnings.extend(_unclaimed(payload, claimed, documents, profile))
    return document, warnings


def _add_per_row(
        node_templates: Dict[str, Any],
        warnings: List[Dict[str, str]],
        bindings: Sequence[Binding],
        payload: Mapping[str, Any],
        instance_rows: Sequence[Mapping[str, Any]],
        instance_table: str,
        name_column: str | None,
        type_name: str,
        namespace: str,
        resolved: ResolvedType | None = None,
        free_binding: KeyValueBinding | None = None,
        filter_binding: NodeFilterBinding | None = None,
        profile: Profile | None = None,
) -> None:
    """One node template per row of the instance table."""
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

        node = _build_node(
            bindings, payload, row, instance_table, f"{namespace}:{type_name}"
        )
        _add_free_properties(
            node, warnings, free_binding, payload, row, instance_table, resolved
        )
        _add_node_filter(
            node, warnings, filter_binding, payload, row, instance_table, profile
        )
        node_templates[str(name)] = node


def _add_singleton(
        node_templates: Dict[str, Any],
        warnings: List[Dict[str, str]],
        bindings: Sequence[Binding],
        payload: Mapping[str, Any],
        instance_table: str,
        type_name: str,
        namespace: str,
        document_name: str | None,
) -> None:
    """A single node template, emitted only when the payload has data for it."""
    node = _build_node(bindings, payload, {}, instance_table, f"{namespace}:{type_name}")
    if len(node) == 1:
        # Only 'type' was set, so nothing in the payload belongs to this node.
        return

    name = _unique_name(node_templates, document_name or type_name.lower(), type_name)
    node_templates[name] = node


def _unique_name(taken: Mapping[str, Any], preferred: str, type_name: str) -> str:
    """Pick a node template name that does not collide with an existing one."""
    if preferred not in taken:
        return preferred
    qualified = f"{preferred}-{type_name.lower()}"
    if qualified not in taken:
        return qualified
    index = 2
    while f"{qualified}-{index}" in taken:
        index += 1
    return f"{qualified}-{index}"


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
        value = resolve_value(binding, payload, instance_row, instance_table)
        if value is None or value == [] or value == {}:
            # Absent values are omitted; the profile's defaults still apply
            # when the template is parsed against it.
            continue
        _set_path(node, binding.path, value)

    return node


def resolve_value(
        binding: Binding,
        payload: Mapping[str, Any],
        instance_row: Mapping[str, Any],
        instance_table: str,
) -> Any:
    """Resolve a single binding against the payload.

    Validation uses this too, so what it reports missing is exactly what
    assembly would leave out.
    """
    if binding.is_list:
        return _list_value(binding, payload, instance_row, instance_table)

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


def _list_value(
        binding: Binding,
        payload: Mapping[str, Any],
        instance_row: Mapping[str, Any] | None = None,
        instance_table: str | None = None,
) -> List[Any] | None:
    """Resolve a list-typed binding into a list of entries."""
    if instance_table and binding.table == instance_table:
        # A list column on the instance table belongs to the row being built,
        # not to every row of it.
        rows = [instance_row] if instance_row else []
        rows = [row for row in rows if _matches(row, binding.filters)]
    else:
        rows = _scoped_rows(
            binding.table, binding.filters, payload, instance_row, instance_table
        )
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


def _scoped_rows(
        table: str,
        filters: Mapping[str, str],
        payload: Mapping[str, Any],
        instance_row: Mapping[str, Any] | None,
        instance_table: str | None,
) -> List[Mapping[str, Any]]:
    """Rows of a child table belonging to the node template being built.

    A child table that carries a `<instance_table>_id` column is per-instance:
    each node template gets only its own rows. One that does not is shared, and
    every node template gets all of them - which is how a capacity's port rules
    apply to all of its flavours.
    """
    rows = [row for row in _as_rows(payload.get(table)) if _matches(row, filters)]
    if not rows or not instance_row or not instance_table:
        return rows

    foreign_key = f"{instance_table}_id"
    if not any(foreign_key in row for row in rows):
        return rows

    instance_id = instance_row.get("id")
    if instance_id is None:
        return rows
    return [row for row in rows if row.get(foreign_key) == instance_id]


def _add_free_properties(
        node: Dict[str, Any],
        warnings: List[Dict[str, str]],
        free_binding: KeyValueBinding | None,
        payload: Mapping[str, Any],
        instance_row: Mapping[str, Any],
        instance_table: str,
        resolved: ResolvedType | None,
) -> None:
    """Place properties the payload names for itself onto a node template.

    Unknown names are dropped with a warning rather than emitted: validation
    rejects them outright, so anything reaching here in a build that skipped
    validation would produce a document the profile cannot parse.
    """
    if not free_binding:
        return

    declared = (resolved.properties if resolved else {}) or {}
    rows = _scoped_rows(
        free_binding.table, free_binding.filters, payload, instance_row, instance_table
    )

    for row in rows:
        name = row.get(free_binding.key_column)
        value = row.get(free_binding.value_column)
        if not name or value is None:
            continue
        definition = declared.get(str(name))
        if definition is None:
            warnings.append({
                "properties": f"'{name}' is not a property of this type and was not set"
            })
            continue
        _set_path(node, ("properties", str(name)), _coerce(value, definition))


def _build_policies(
        profile: Profile,
        payload: Mapping[str, Any],
        bindings_group: str | None,
        namespace: str,
) -> List[Dict[str, Any]]:
    """Build the document's policies from the profile's declarations.

    A policy is emitted only when the payload gives at least one of its
    properties a value, so an application that sets no budgets carries no
    policies rather than empty ones.
    """
    policies: List[Dict[str, Any]] = []

    for binding in policy_bindings(profile, bindings_group):
        declared = profile.resolve(binding.type_name, "policy_types").properties
        properties: Dict[str, Any] = {}

        for prop, source in binding.properties.items():
            value = _document_value(source, payload)
            if value is None or value == "":
                continue
            properties[prop] = _coerce(value, declared.get(prop) or {})

        if properties:
            policies.append({binding.name: {
                "type": f"{namespace}:{binding.type_name}",
                "properties": properties,
            }})

    return policies


def _add_node_filter(
        node: Dict[str, Any],
        warnings: List[Dict[str, str]],
        filter_binding: NodeFilterBinding | None,
        payload: Mapping[str, Any],
        instance_row: Mapping[str, Any],
        instance_table: str,
        profile: Profile | None,
) -> None:
    """Attach placement constraints to the node template's requirement.

    Each row becomes one clause. Clauses are joined with $and, which is what
    matching a candidate against every constraint at once means.
    """
    if not filter_binding or not profile:
        return

    targets = filterable_targets(profile, filter_binding.target_type)
    rows = _scoped_rows(
        filter_binding.table, {}, payload, instance_row, instance_table
    )

    clauses = []
    for row in rows:
        target = row.get(filter_binding.target_column)
        operator = row.get(filter_binding.operator_column)
        definition = targets.get(str(target)) if target else None
        if not target or not operator or definition is None:
            # Validation reports these; assembly leaves them out rather than
            # emitting a filter no capacity could ever satisfy.
            warnings.append({
                "node_filter": f"Constraint on '{target}' was not applied"
            })
            continue

        clause = _filter_clause(filter_binding, row, target, operator, definition)
        if clause is not None:
            clauses.append(clause)

    requirement: Dict[str, Any] = {}
    count = instance_row.get(filter_binding.count_source[1]) if filter_binding.count_source else None
    if count is not None:
        requirement["count"] = _coerce(count, {"type": "integer"})
    if clauses:
        requirement["node_filter"] = {"$and": clauses}

    if requirement:
        node.setdefault("requirements", []).append({filter_binding.requirement: requirement})


def _filter_clause(
        filter_binding: NodeFilterBinding,
        row: Mapping[str, Any],
        target: str,
        operator: str,
        definition: Mapping[str, Any],
) -> Dict[str, Any] | None:
    """One node_filter clause: operator, the target's value, and the bound(s)."""
    capability, _, prop = str(target).partition(".")
    # SELF is the node being filtered, so the path names the candidate's own
    # capability and property.
    lookup = {"$get_property": InlineList(["SELF", "TARGET", "CAPABILITY", capability, prop])}

    if operator == ENTRY_OPERATOR:
        entries = entry_values(row.get(filter_binding.value_column), definition)
        return {operator: [lookup, InlineList(entries)]} if entries else None

    value = _coerce(row.get(filter_binding.value_column), definition)
    if value is None:
        return None

    if operator == RANGE_OPERATOR:
        upper = _coerce(row.get(filter_binding.value_max_column), definition)
        if upper is None:
            return None
        return {operator: [lookup, InlineList([value, upper])]}

    return {operator: [lookup, value]}


def entry_values(value: Any, definition: Mapping[str, Any]) -> List[Any]:
    """Split a $has_any_entry value into the entries to look for.

    One row can name several, comma-separated, because asking whether a list
    contains any of ALL or 80 is one constraint rather than two.
    """
    if value is None:
        return []
    items = value if isinstance(value, list) else str(value).split(",")
    entry_type = (definition or {}).get("entry_schema")
    if isinstance(entry_type, dict):
        entry_type = entry_type.get("type")
    schema = {"type": entry_type} if isinstance(entry_type, str) else {}

    entries = []
    for item in items:
        item = item.strip() if isinstance(item, str) else item
        if item not in (None, ""):
            entries.append(_coerce(item, schema))
    return entries


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


def _claimed_columns(
        bindings: Sequence[Binding],
        free_binding: KeyValueBinding | None = None,
        filter_binding: NodeFilterBinding | None = None,
) -> Dict[str, set]:
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

    if free_binding:
        columns = claimed.setdefault(free_binding.table, set())
        columns.update({free_binding.key_column, free_binding.value_column})
        columns.update(free_binding.filters)

    if filter_binding:
        claimed.setdefault(filter_binding.table, set()).update({
            filter_binding.target_column,
            filter_binding.operator_column,
            filter_binding.value_column,
            filter_binding.value_max_column,
        })

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
