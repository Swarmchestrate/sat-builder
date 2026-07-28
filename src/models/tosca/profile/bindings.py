"""gui_name binding extraction.

A binding ties one profile property to one database column. The reference is
written in database vocabulary (`table.column`), so resolving it needs the shape
of the payload but no TOSCA knowledge, and assembling needs the profile but no
database access.

Supported forms:
    capacity_new.ssh_port                  a column on a table
    capacity_port_rule[direction=ingress]  rows of a table, filtered
"""
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple

from .resolver import Profile, ResolvedType

GUI_NAME_RE = re.compile(r"^(?P<table>\w+)(?:\[(?P<filters>[^\]]+)\])?(?:\.(?P<column>\w+))?$")


@dataclass
class Binding:
    """One profile property bound to a database source."""

    path: Tuple[str, ...]
    table: str
    column: str | None
    filters: Dict[str, str] = field(default_factory=dict)
    definition: Dict[str, Any] = field(default_factory=dict)

    @property
    def declared_type(self) -> str | None:
        return self.definition.get("type")

    @property
    def is_list(self) -> bool:
        return self.declared_type == "list"

    @property
    def entry_schema(self) -> str | None:
        return self.definition.get("entry_schema")


def parse_gui_name(reference: str) -> Tuple[str, str | None, Dict[str, str]]:
    """Split a gui_name into (table, column, filters)."""
    match = GUI_NAME_RE.match(reference.strip())
    if not match:
        raise ValueError(f"Malformed gui_name: {reference!r}")

    filters: Dict[str, str] = {}
    if match.group("filters"):
        for clause in match.group("filters").split(","):
            if "=" not in clause:
                raise ValueError(f"Malformed filter in gui_name: {reference!r}")
            key, value = clause.split("=", 1)
            filters[key.strip()] = value.strip()

    return match.group("table"), match.group("column"), filters


def collect_bindings(resolved: ResolvedType) -> List[Binding]:
    """Every bound property on a resolved type, with its node-template path."""
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

    return bindings


def entry_bindings(profile: Profile, data_type_name: str) -> List[Binding]:
    """Bindings for a data type used as a list's entry_schema."""
    resolved = profile.resolve(data_type_name.split(":")[-1], "data_types")
    return [
        binding
        for name, definition in (resolved.properties or {}).items()
        if (binding := _binding_for((name,), definition))
    ]


def document_bindings(profile: Profile) -> Dict[str, Tuple[str, str | None]]:
    """Document-level bindings (template metadata, node template naming)."""
    parsed: Dict[str, Tuple[str, str | None]] = {}
    for target, reference in (profile.gui_bindings or {}).items():
        table, column, _ = parse_gui_name(reference)
        parsed[target] = (table, column)
    return parsed


def _binding_for(path: Tuple[str, ...], definition: Any) -> Binding | None:
    if not isinstance(definition, dict):
        return None
    reference = (definition.get("metadata") or {}).get("gui_name")
    if not reference:
        return None
    table, column, filters = parse_gui_name(reference)
    return Binding(path=path, table=table, column=column, filters=filters, definition=definition)
