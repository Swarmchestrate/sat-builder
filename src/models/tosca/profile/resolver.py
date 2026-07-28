"""TOSCA profile loading and type resolution.

Loads a profile directory, merges its type sections, and resolves the
derived_from chain so a concrete type exposes every inherited property and
capability. Subtypes may override any part of an inherited definition, which is
how CloudCapacity sets a default on resource.type without restating it.
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List

import yaml

from src.utils.logger import get_logger

logger = get_logger()

TYPE_SECTIONS = (
    "data_types",
    "capability_types",
    "node_types",
    "policy_types",
    "relationship_types",
)

# Guards against a derived_from cycle in a hand-edited profile.
MAX_INHERITANCE_DEPTH = 32


@dataclass
class ResolvedType:
    """A profile type with its inheritance chain already applied."""

    name: str
    section: str
    properties: Dict[str, Any] = field(default_factory=dict)
    capabilities: Dict[str, Any] = field(default_factory=dict)
    requirements: List[Any] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    description: str | None = None
    ancestry: List[str] = field(default_factory=list)


@dataclass
class Profile:
    """Every type in a profile, indexed by section."""

    version: str | None
    raw: Dict[str, Dict[str, Any]]
    gui_bindings: Dict[str, str] = field(default_factory=dict)

    def type_names(self, section: str) -> List[str]:
        return sorted(self.raw.get(section, {}))

    def resolve(self, name: str, section: str = "node_types") -> ResolvedType:
        """Resolve a single type, applying inheritance and capability types."""
        chain = self._ancestry(name, section)

        merged: Dict[str, Any] = {}
        # Walk root-first so each subtype overrides what it inherited.
        for ancestor in reversed(chain):
            merged = _deep_merge(merged, self.raw[section][ancestor] or {})

        resolved = ResolvedType(
            name=name,
            section=section,
            properties=merged.get("properties") or {},
            requirements=merged.get("requirements") or [],
            metadata=merged.get("metadata") or {},
            description=merged.get("description"),
            ancestry=chain,
        )
        resolved.capabilities = self._expand_capabilities(merged.get("capabilities") or {})
        return resolved

    def _ancestry(self, name: str, section: str) -> List[str]:
        """Return [name, parent, grandparent, ...] for a type."""
        chain: List[str] = []
        current = name
        while current:
            if current in chain:
                raise ValueError(
                    f"Circular derived_from in {section}: {' -> '.join(chain + [current])}"
                )
            if current not in self.raw.get(section, {}):
                raise KeyError(f"Unknown {section} '{current}' (resolving '{name}')")
            chain.append(current)
            if len(chain) > MAX_INHERITANCE_DEPTH:
                raise ValueError(f"derived_from chain for '{name}' exceeds {MAX_INHERITANCE_DEPTH}")
            parent = (self.raw[section][current] or {}).get("derived_from")
            # Profile-qualified parents (swch:Capacity) refer to this profile.
            current = parent.split(":")[-1] if parent else None
        return chain

    def _expand_capabilities(self, capabilities: Dict[str, Any]) -> Dict[str, Any]:
        """Inline each capability type's properties under its assignment."""
        expanded: Dict[str, Any] = {}
        for cap_name, cap_def in capabilities.items():
            cap_def = cap_def or {}
            cap_type = (cap_def.get("type") or "").split(":")[-1]
            props: Dict[str, Any] = {}
            if cap_type and cap_type in self.raw.get("capability_types", {}):
                props = self.resolve(cap_type, "capability_types").properties
            # A node type may override parts of a capability's properties,
            # e.g. EdgeCapacity pinning capacity.instances to a default of 1.
            props = _deep_merge(props, cap_def.get("properties") or {})
            expanded[cap_name] = {
                "type": cap_type or None,
                "description": cap_def.get("description"),
                "properties": props,
            }
        return expanded


def load_profile(profile_dir: str | Path) -> Profile:
    """Load every YAML file in a profile directory and merge its type sections."""
    profile_dir = Path(profile_dir)
    if not profile_dir.is_dir():
        raise NotADirectoryError(f"Profile directory not found: {profile_dir}")

    raw: Dict[str, Dict[str, Any]] = {section: {} for section in TYPE_SECTIONS}
    version: str | None = None
    gui_bindings: Dict[str, str] = {}

    for path in sorted(profile_dir.glob("*.yaml")):
        document = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        version = version or document.get("profile")
        gui_bindings.update((document.get("metadata") or {}).get("gui_bindings") or {})

        for section in TYPE_SECTIONS:
            for type_name, definition in (document.get(section) or {}).items():
                if type_name in raw[section]:
                    logger.warning(
                        f"load_profile: duplicate {section} '{type_name}' in {path.name}, overriding"
                    )
                raw[section][type_name] = definition

    counts = ", ".join(f"{section}={len(raw[section])}" for section in TYPE_SECTIONS if raw[section])
    logger.info(f"load_profile: loaded {profile_dir.name} ({version}) - {counts}")
    return Profile(version=version, raw=raw, gui_bindings=gui_bindings)


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Merge override onto base, recursing into nested dicts."""
    result = dict(base)
    for key, value in (override or {}).items():
        if key == "derived_from":
            continue
        existing = result.get(key)
        if isinstance(existing, dict) and isinstance(value, dict):
            result[key] = _deep_merge(existing, value)
        else:
            result[key] = value
    return result
