"""Validate a payload against the profile's declared types.

Errors are reported in the caller's vocabulary - table, row and column - rather
than in terms of the generated document, so a client can map a failure back to
the field that caused it.

This is deliberately narrow. It checks what the profile declares: required
properties are present, and values match their declared types. Everything that
needs a resolved topology - expression functions, requirement and capability
matching, relationship validity - is left to a TOSCA processor.
"""
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence

from src.utils.logger import get_logger, log_function_calls

from .assemble import entry_values, resolve_value, _as_rows, _scoped_rows
from .bindings import (
    Binding,
    ENTRY_OPERATOR,
    FILTER_OPERATORS,
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

_TRUTHY = {"true", "t", "yes", "y", "1"}
_FALSEY = {"false", "f", "no", "n", "0"}


@dataclass
class ValidationError:
    """One problem with the payload, located in the caller's terms."""

    path: str
    message: str
    kind: str = "invalid"

    def as_dict(self) -> Dict[str, str]:
        return {"path": self.path, "message": self.message, "kind": self.kind}


@log_function_calls()
def validate(
        profile: Profile,
        type_names: str | Sequence[str],
        payload: Mapping[str, Any],
        bindings_group: str | None = None,
) -> List[ValidationError]:
    """Check a payload against the profile. An empty list means it is valid."""
    requested = [type_names] if isinstance(type_names, str) else list(type_names)
    documents = document_bindings(profile, bindings_group)
    free_binding = free_property_binding(profile, bindings_group)
    filter_binding = node_filter_binding(profile, bindings_group)
    instance_table, _ = documents.get("node_template.name", (None, None))
    if not instance_table:
        raise ValueError(
            "Profile is missing a 'node_template.name' gui_binding; "
            "nothing designates which table produces node templates."
        )

    instance_rows = _as_rows(payload.get(instance_table))
    errors: List[ValidationError] = []

    errors.extend(_check_policies(profile, payload, bindings_group))

    _, name_column = documents.get("node_template.name", (None, None))
    errors.extend(_duplicate_names(instance_rows, instance_table, name_column))

    for type_name in requested:
        resolved = profile.resolve(type_name)
        bindings = collect_bindings(resolved, profile)
        bound_paths = {binding.path for binding in bindings}

        errors.extend(_unsatisfiable(resolved, bound_paths, type_name))

        per_row = any(binding.table == instance_table for binding in bindings)
        # A totals node is only checked when the payload carries data for it.
        if not per_row and not _has_any_value(bindings, payload, instance_table):
            continue

        for binding in bindings:
            if per_row and binding.table == instance_table:
                # Varies per row, so report against each one.
                for index, row in enumerate(instance_rows):
                    errors.extend(_check(binding, payload, row, instance_table, index))
            else:
                # Shared across every node template; checking it once is enough.
                errors.extend(_check(binding, payload, {}, instance_table, None))

        errors.extend(
            _check_free_properties(
                free_binding, resolved, payload, instance_rows, instance_table
            )
        )
        errors.extend(
            _check_node_filters(
                filter_binding, profile, payload, instance_rows, instance_table
            )
        )

    return errors


def _check_policies(
        profile: Profile,
        payload: Mapping[str, Any],
        bindings_group: str | None,
) -> List[ValidationError]:
    """Check the document's policies against the types they instantiate.

    A property the policy type does not declare can never be satisfied, so it is
    reported against the profile rather than the payload.
    """
    errors: List[ValidationError] = []

    for binding in policy_bindings(profile, bindings_group):
        try:
            declared = profile.resolve(binding.type_name, "policy_types").properties
        except KeyError:
            errors.append(ValidationError(
                path=f"policies.{binding.name}",
                message=f"'{binding.type_name}' is not a policy type in the profile",
                kind="unbindable",
            ))
            continue

        for prop, source in binding.properties.items():
            if prop not in declared:
                errors.append(ValidationError(
                    path=f"policies.{binding.name}.{prop}",
                    message=f"'{prop}' is not a property of {binding.type_name}",
                    kind="unbindable",
                ))
                continue

            value = _document_value_for(source, payload)
            if value in (None, ""):
                continue
            problem = _type_problem(value, declared[prop])
            if problem:
                table, column = source
                errors.append(ValidationError(
                    path=f"{table}.{column}",
                    message=f"'{binding.name}' policy: '{prop}' {problem}",
                    kind="type",
                ))

    return errors


def _document_value_for(source, payload: Mapping[str, Any]) -> Any:
    table, column = source
    rows = _as_rows(payload.get(table))
    return rows[0].get(column) if rows and column else None


def _check_node_filters(
        filter_binding: NodeFilterBinding | None,
        profile: Profile,
        payload: Mapping[str, Any],
        instance_rows: Sequence[Mapping[str, Any]],
        instance_table: str,
) -> List[ValidationError]:
    """Check placement constraints against the capabilities they target.

    A constraint naming a property no capacity has, or comparing a string with
    a range, would produce a filter that silently matches nothing.
    """
    if not filter_binding:
        return []

    targets = filterable_targets(profile, filter_binding.target_type)
    errors: List[ValidationError] = []

    for index, instance_row in enumerate(instance_rows or [{}]):
        rows = _scoped_rows(filter_binding.table, {}, payload, instance_row, instance_table)
        for row in rows:
            target = row.get(filter_binding.target_column)
            operator = row.get(filter_binding.operator_column)
            path = f"{filter_binding.table}[{index}]"

            definition = targets.get(str(target)) if target else None
            if definition is None:
                known = ", ".join(sorted(targets)[:6])
                errors.append(ValidationError(
                    path=f"{path}.{filter_binding.target_column}",
                    message=f"'{target}' is not a capability property of "
                            f"{filter_binding.target_type} (e.g. {known})",
                    kind="unknown_property",
                ))
                continue

            allowed = FILTER_OPERATORS.get(str(operator))
            if allowed is None:
                errors.append(ValidationError(
                    path=f"{path}.{filter_binding.operator_column}",
                    message=f"'{operator}' is not a filter operator; expected one of "
                            f"{', '.join(sorted(FILTER_OPERATORS))}",
                    kind="operator",
                ))
                continue

            declared = (definition or {}).get("type")
            if declared not in allowed:
                errors.append(ValidationError(
                    path=f"{path}.{filter_binding.operator_column}",
                    message=f"'{operator}' cannot apply to '{target}', which the profile "
                            f"declares as {declared}",
                    kind="operator",
                ))
                continue

            errors.extend(_check_filter_values(filter_binding, row, target, operator, definition, path))

    return errors


def _check_filter_values(
        filter_binding: NodeFilterBinding,
        row: Mapping[str, Any],
        target: Any,
        operator: Any,
        definition: Mapping[str, Any],
        path: str,
) -> List[ValidationError]:
    """A constraint needs its value, and a range needs both ends."""
    errors: List[ValidationError] = []
    value = row.get(filter_binding.value_column)

    if value is None:
        return [ValidationError(
            path=f"{path}.{filter_binding.value_column}",
            message=f"the constraint on '{target}' has no value",
            kind="missing",
        )]

    if operator == ENTRY_OPERATOR:
        # The value names entries to look for, so it is checked against the
        # list's entry type rather than against the list itself.
        entries = entry_values(value, definition)
        if not entries:
            errors.append(ValidationError(
                path=f"{path}.{filter_binding.value_column}",
                message=f"the constraint on '{target}' names no entries to look for",
                kind="missing",
            ))
        return errors

    problem = _type_problem(value, definition)
    if problem:
        errors.append(ValidationError(
            path=f"{path}.{filter_binding.value_column}",
            message=f"'{target}' {problem}",
            kind="type",
        ))

    if operator != RANGE_OPERATOR:
        return errors

    upper = row.get(filter_binding.value_max_column)
    if upper is None:
        errors.append(ValidationError(
            path=f"{path}.{filter_binding.value_max_column}",
            message=f"{RANGE_OPERATOR} on '{target}' needs an upper bound as well",
            kind="missing",
        ))
        return errors

    problem = _type_problem(upper, definition)
    if problem:
        errors.append(ValidationError(
            path=f"{path}.{filter_binding.value_max_column}",
            message=f"'{target}' upper bound {problem}",
            kind="type",
        ))
    elif not problem and float(upper) < float(value):
        errors.append(ValidationError(
            path=f"{path}.{filter_binding.value_max_column}",
            message=f"the range on '{target}' is inverted: {value} to {upper}",
            kind="range",
        ))

    return errors


def _duplicate_names(
        instance_rows: Sequence[Mapping[str, Any]],
        instance_table: str,
        name_column: str | None,
) -> List[ValidationError]:
    """Reject two rows that would produce the same node template.

    Node template names are keys, so the second row would silently replace the
    first and its data would vanish from the document without trace.
    """
    if not name_column:
        return []

    seen: Dict[str, int] = {}
    errors: List[ValidationError] = []
    for index, row in enumerate(instance_rows):
        name = row.get(name_column)
        if not name:
            continue
        if name in seen:
            errors.append(ValidationError(
                path=f"{instance_table}[{index}].{name_column}",
                message=f"'{name}' is already used by row {seen[name] + 1}; "
                        f"each one needs its own name",
                kind="duplicate",
            ))
            continue
        seen[str(name)] = index
    return errors


def _check_free_properties(
        free_binding: KeyValueBinding | None,
        resolved: ResolvedType,
        payload: Mapping[str, Any],
        instance_rows: Sequence[Mapping[str, Any]],
        instance_table: str,
) -> List[ValidationError]:
    """Check properties the payload names for itself.

    These are the point of the free slots: the user supplies a property name the
    form never anticipated, and the profile is what says whether it exists and
    what type it should be.
    """
    if not free_binding:
        return []

    declared = resolved.properties or {}
    errors: List[ValidationError] = []

    for index, instance_row in enumerate(instance_rows or [{}]):
        rows = _scoped_rows(
            free_binding.table, free_binding.filters, payload,
            instance_row, instance_table,
        )
        for row in rows:
            name = row.get(free_binding.key_column)
            value = row.get(free_binding.value_column)
            path = f"{free_binding.table}[{index}].{free_binding.key_column}"

            if not name:
                errors.append(ValidationError(
                    path=path,
                    message=f"a row of '{free_binding.table}' has no property name",
                    kind="missing",
                ))
                continue

            definition = declared.get(str(name))
            if definition is None:
                errors.append(ValidationError(
                    path=path,
                    message=f"'{name}' is not a property of {resolved.name}",
                    kind="unknown_property",
                ))
                continue

            if value is None:
                continue

            problem = _type_problem(value, definition)
            if problem:
                errors.append(ValidationError(
                    path=f"{free_binding.table}[{index}].{free_binding.value_column}",
                    message=f"'{name}' {problem}",
                    kind="type",
                ))

    return errors


def _check(
        binding: Binding,
        payload: Mapping[str, Any],
        row: Mapping[str, Any],
        instance_table: str,
        index: int | None,
) -> List[ValidationError]:
    """Check one binding: present if required, and of the declared type."""
    value = resolve_value(binding, payload, row, instance_table)
    path = _path_for(binding, instance_table, index)

    if value is None:
        if _is_required(binding) and "default" not in binding.definition:
            return [ValidationError(
                path=path,
                message=f"'{_property_name(binding)}' is required by the profile but has no value",
                kind="missing",
            )]
        return []

    problem = _type_problem(value, binding.definition)
    if problem:
        return [ValidationError(
            path=path,
            message=f"'{_property_name(binding)}' {problem}",
            kind="type",
        )]

    return []


def _unsatisfiable(resolved, bound_paths, type_name: str) -> List[ValidationError]:
    """Required properties with no binding at all can never be satisfied."""
    errors = []

    def scan(definitions: Mapping[str, Any], path_prefix: tuple):
        for name, definition in (definitions or {}).items():
            if not isinstance(definition, dict) or not definition.get("required"):
                continue
            if "default" in definition:
                continue
            if (path_prefix + (name,)) in bound_paths:
                continue
            errors.append(ValidationError(
                path=f"{type_name}.{'.'.join(path_prefix + (name,))}",
                message=f"'{name}' is required by the profile but has no gui_name binding, "
                        f"so no payload can satisfy it",
                kind="unbindable",
            ))

    scan(resolved.properties, ("properties",))
    for cap_name, capability in (resolved.capabilities or {}).items():
        scan(capability.get("properties"), ("capabilities", cap_name, "properties"))

    return errors


def _has_any_value(
        bindings: Sequence[Binding],
        payload: Mapping[str, Any],
        instance_table: str,
) -> bool:
    return any(
        resolve_value(binding, payload, {}, instance_table) is not None
        for binding in bindings
    )


def _is_required(binding: Binding) -> bool:
    return bool(binding.definition.get("required"))


def _property_name(binding: Binding) -> str:
    return binding.path[-1]


def _path_for(binding: Binding, instance_table: str, index: int | None) -> str:
    """Locate a binding in the payload, e.g. capacity_instance_type[0].cpu."""
    if binding.table == instance_table and index is not None:
        location = f"{binding.table}[{index}]"
    else:
        location = binding.table
    return f"{location}.{binding.column}" if binding.column else location


def _type_problem(value: Any, definition: Mapping[str, Any]) -> str | None:
    """Describe why a value does not match its declared type, if it does not."""
    declared = (definition or {}).get("type")

    if declared == "boolean":
        if isinstance(value, bool):
            return None
        if isinstance(value, str) and value.strip().lower() in _TRUTHY | _FALSEY:
            return None
        return f"must be a boolean, got {type(value).__name__} {value!r}"

    if declared in ("integer", "float"):
        if isinstance(value, bool):
            return f"must be {'an integer' if declared == 'integer' else 'a float'}, got a boolean"
        converter = int if declared == "integer" else float
        try:
            converter(value)
        except (TypeError, ValueError):
            article = "an integer" if declared == "integer" else "a float"
            return f"must be {article}, got {type(value).__name__} {value!r}"
        return None

    if declared == "string":
        if isinstance(value, (dict, list)):
            return f"must be a string, got {type(value).__name__}"
        return None

    if declared == "list":
        if not isinstance(value, list):
            return f"must be a list, got {type(value).__name__}"
        return None

    if declared == "map":
        if not isinstance(value, dict):
            return f"must be a map, got {type(value).__name__}"
        return None

    return None
