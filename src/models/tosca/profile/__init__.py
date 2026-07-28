"""TOSCA profile resolution.

The profile is the source of truth for types, properties and constraints.
This package reads it directly, replacing the schema factory's inference of
types from example instances.
"""
from .resolver import Profile, ResolvedType, load_profile
from .bindings import Binding, collect_bindings, document_bindings, entry_bindings, parse_gui_name

__all__ = [
    "Profile",
    "ResolvedType",
    "load_profile",
    "Binding",
    "collect_bindings",
    "document_bindings",
    "entry_bindings",
    "parse_gui_name",
]
