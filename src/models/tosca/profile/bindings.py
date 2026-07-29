"""gui_name binding extraction.

A binding ties one profile property to one database column. The reference is
written in database vocabulary (`table.column`), so resolving it needs the shape
of the payload but no TOSCA knowledge, and assembling needs the profile but no
database access.

Supported forms:
    capacity_new.ssh_port                  a column on a table
    capacity_port_rule[direction=ingress]  rows of a table, filtered
    application_property{key: value}       rows naming the property they set
"""
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple

from .resolver import DEFAULT_BINDING_GROUP, Profile, ResolvedType

# Which operators a filter may use, and the property types each one makes sense
# for. A range on a string, or an ordering on a boolean, is a mistake worth
# reporting rather than emitting.
FILTER_OPERATORS: Dict[str, Tuple[str, ...]] = {
    "$greater_or_equal": ("integer", "float"),
    "$greater_than": ("integer", "float"),
    "$less_or_equal": ("integer", "float"),
    "$less_than": ("integer", "float"),
    "$in_range": ("integer", "float"),
    "$equal": ("integer", "float", "string", "boolean"),
    "$has_any_entry": ("list",),
}

# The only operator that reads a second value.
RANGE_OPERATOR = "$in_range"

# Asks whether a list property contains any of the given entries, so its value
# is one or more entries rather than a list to compare against. Several are
# written comma-separated, as BookInfo's [ ALL, 80 ].
ENTRY_OPERATOR = "$has_any_entry"

GUI_NAME_RE = re.compile(
    r"^(?P<table>\w+)"
    r"(?:\[(?P<filters>[^\]]+)\])?"
    r"(?:\{(?P<pairs>[^}]+)\})?"
    r"(?:\.(?P<column>\w+))?$"
)


@dataclass
class PolicyBinding:
    """One policy of the generated document, and where its properties come from.

    The name is the key the policy appears under; the type is the policy type it
    instantiates. Application policies target the application as a whole, so
    nothing here resolves targets.
    """

    name: str
    type_name: str
    # Property name -> (table, column).
    properties: Dict[str, Tuple[str, str | None]] = field(default_factory=dict)


@dataclass
class NodeFilterBinding:
    """Rows that become clauses of a requirement's node_filter.

    A filter is not a value placed at a path but a predicate: the row names a
    capability property of the target type, an operator, and one or two values.
    Every capability of target_type is filterable, so nothing has to be
    enumerated - adding a capability property makes it filterable at once.
    """

    table: str
    requirement: str
    target_type: str
    target_column: str = "target"
    operator_column: str = "operator"
    value_column: str = "value"
    value_max_column: str = "value_max"


@dataclass
class KeyValueBinding:
    """A table whose rows each name the property they set.

    Where an ordinary binding fixes its property at profile-authoring time, this
    one defers it to the data: key_column holds the property name and
    value_column its value. That is what lets a user add a property the form
    never anticipated, and what makes the property name itself something worth
    validating.
    """

    table: str
    key_column: str
    value_column: str
    filters: Dict[str, str] = field(default_factory=dict)


@dataclass
class Binding:
    """One profile property bound to a database source."""

    path: Tuple[str, ...]
    table: str
    column: str | None
    filters: Dict[str, str] = field(default_factory=dict)
    definition: Dict[str, Any] = field(default_factory=dict)
    # Populated for list properties whose entry_schema is a bound data type,
    # so each row of the source table becomes one entry.
    entry_bindings: List["Binding"] = field(default_factory=list)

    @property
    def declared_type(self) -> str | None:
        return self.definition.get("type")

    @property
    def is_list(self) -> bool:
        return self.declared_type == "list"

    @property
    def entry_schema(self) -> str | None:
        """The entry type name, however the profile spelled it.

        TOSCA allows both `entry_schema: string` and `entry_schema: {type: string}`;
        the profile uses each in places.
        """
        declared = self.definition.get("entry_schema")
        if isinstance(declared, dict):
            declared = declared.get("type")
        return declared.split(":")[-1] if isinstance(declared, str) else None


def parse_gui_name(reference: str) -> Tuple[str, str | None, Dict[str, str]]:
    """Split a gui_name into (table, column, filters)."""
    match = _match(reference)

    filters: Dict[str, str] = {}
    if match.group("filters"):
        for clause in match.group("filters").split(","):
            if "=" not in clause:
                raise ValueError(f"Malformed filter in gui_name: {reference!r}")
            key, value = clause.split("=", 1)
            filters[key.strip()] = value.strip()

    return match.group("table"), match.group("column"), filters


def parse_key_value_gui_name(reference: str) -> KeyValueBinding:
    """Parse the `table{key_column: value_column}` form."""
    match = _match(reference)
    pairs = match.group("pairs")
    if not pairs or ":" not in pairs:
        raise ValueError(
            f"Expected a key/value gui_name of the form "
            f"table{{key_column: value_column}}, got {reference!r}"
        )
    key_column, value_column = (part.strip() for part in pairs.split(":", 1))
    if not key_column or not value_column:
        raise ValueError(f"Malformed key/value gui_name: {reference!r}")

    _, _, filters = parse_gui_name(reference)
    return KeyValueBinding(
        table=match.group("table"),
        key_column=key_column,
        value_column=value_column,
        filters=filters,
    )


def _match(reference: str) -> "re.Match[str]":
    match = GUI_NAME_RE.match(reference.strip())
    if not match:
        raise ValueError(f"Malformed gui_name: {reference!r}")
    return match


def collect_bindings(resolved: ResolvedType, profile: Profile | None = None) -> List[Binding]:
    """Every bound property on a resolved type, with its node-template path.

    Passing the profile resolves entry_schema bindings for list properties,
    which assembly needs to turn rows into entries.
    """
    bindings: List[Binding] = []

    for name, definition in (resolved.properties or {}).items():
        binding = _binding_for(("properties", name), definition)
        if binding:
            bindings.append(binding)

    for cap_name, capability in (resolved.capabilities or {}).items():
        for name, definition in (capability.get("properties") or {}).items():
            binding = _binding_for(("capabilities", cap_name, "properties", name), definition)
            if binding:
                bindings.append(binding)

    if profile:
        for binding in bindings:
            # A primitive entry_schema (string, integer) has no bindings of its
            # own; only a declared data type maps rows onto entry properties.
            if binding.is_list and binding.entry_schema in profile.raw.get("data_types", {}):
                binding.entry_bindings = entry_bindings(profile, binding.entry_schema)

    return bindings


def entry_bindings(profile: Profile, data_type_name: str) -> List[Binding]:
    """Bindings for a data type used as a list's entry_schema."""
    resolved = profile.resolve(data_type_name.split(":")[-1], "data_types")
    return [
        binding
        for name, definition in (resolved.properties or {}).items()
        if (binding := _binding_for((name,), definition))
    ]


def binding_group(profile: Profile, group: str | None = None) -> Dict[str, str]:
    """The raw document-level bindings for one kind of document.

    An unknown or unnamed group falls back to the default one, so a profile that
    still declares its bindings flat keeps working.
    """
    groups = profile.gui_bindings or {}
    declared = groups.get(group) if group else None
    if declared is None:
        declared = groups.get(DEFAULT_BINDING_GROUP, {})
    return declared


def document_bindings(
        profile: Profile,
        group: str | None = None,
) -> Dict[str, Tuple[str, str | None]]:
    """Document-level bindings (template metadata, node template naming).

    Key/value bindings are excluded: they name no single column, so they are
    read separately by free_property_binding.
    """
    parsed: Dict[str, Tuple[str, str | None]] = {}
    for target, reference in binding_group(profile, group).items():
        # Structured bindings (node_filter) and key/value ones name no single
        # column, so they are read by their own helpers instead.
        if not isinstance(reference, str) or _is_key_value(reference):
            continue
        table, column, _ = parse_gui_name(reference)
        parsed[target] = (table, column)
    return parsed


def node_filter_binding(
        profile: Profile,
        group: str | None = None,
) -> NodeFilterBinding | None:
    """The binding that turns rows into a requirement's node_filter."""
    declared = binding_group(profile, group).get("node_filter")
    if not declared:
        return None
    if not isinstance(declared, dict):
        raise ValueError(
            "'node_filter' must be a mapping declaring gui_name, requirement "
            f"and target_type, got {declared!r}"
        )

    missing = [k for k in ("gui_name", "requirement", "target_type") if not declared.get(k)]
    if missing:
        raise ValueError(f"'node_filter' binding is missing: {', '.join(missing)}")

    columns = declared.get("columns") or {}
    return NodeFilterBinding(
        table=parse_gui_name(declared["gui_name"])[0],
        requirement=declared["requirement"],
        target_type=declared["target_type"],
        target_column=columns.get("target", "target"),
        operator_column=columns.get("operator", "operator"),
        value_column=columns.get("value", "value"),
        value_max_column=columns.get("value_max", "value_max"),
    )


def policy_bindings(profile: Profile, group: str | None = None) -> List[PolicyBinding]:
    """The policies a document may carry, in the order the profile declares them."""
    declared = binding_group(profile, group).get("policies")
    if not declared:
        return []
    if not isinstance(declared, dict):
        raise ValueError(f"'policies' must be a mapping of name to policy, got {declared!r}")

    bindings: List[PolicyBinding] = []
    for name, policy in declared.items():
        policy = policy or {}
        type_name = policy.get("type")
        if not type_name:
            raise ValueError(f"Policy '{name}' declares no type")
        properties = {
            prop: parse_gui_name(reference)[:2]
            for prop, reference in (policy.get("properties") or {}).items()
        }
        bindings.append(PolicyBinding(name=name, type_name=type_name, properties=properties))
    return bindings


def filterable_targets(profile: Profile, type_name: str) -> Dict[str, Dict[str, Any]]:
    """Every capability property of a type, keyed 'capability.property'.

    This is the whole filterable surface: any capability a capacity declares can
    be constrained, so the set is derived rather than annotated.
    """
    resolved = profile.resolve(type_name)
    return {
        f"{cap_name}.{prop_name}": definition
        for cap_name, capability in (resolved.capabilities or {}).items()
        for prop_name, definition in (capability.get("properties") or {}).items()
    }


def free_property_binding(
        profile: Profile,
        group: str | None = None,
) -> KeyValueBinding | None:
    """The binding that lets rows supply arbitrary node template properties."""
    reference = binding_group(profile, group).get("node_template.properties")
    if not reference:
        return None
    return parse_key_value_gui_name(reference)


def _is_key_value(reference: str) -> bool:
    match = GUI_NAME_RE.match(reference.strip())
    return bool(match and match.group("pairs"))


def _binding_for(path: Tuple[str, ...], definition: Any) -> Binding | None:
    if not isinstance(definition, dict):
        return None
    reference = (definition.get("metadata") or {}).get("gui_name")
    if not reference:
        return None
    table, column, filters = parse_gui_name(reference)
    return Binding(path=path, table=table, column=column, filters=filters, definition=definition)
