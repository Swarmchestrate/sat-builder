"""TOSCA profile resolution.

The profile is the source of truth for types, properties and constraints.
This package reads it directly, replacing the schema factory's inference of
types from example instances.
"""
from .resolver import Profile, ResolvedType, load_profile
from .fetcher import ensure_profile
from .provider import get_profile
from .bindings import Binding, collect_bindings, document_bindings, entry_bindings, parse_gui_name
from .assemble import assemble
from .validate import ValidationError, validate
from .openapi import payload_schema

__all__ = [
    "assemble",
    "validate",
    "ValidationError",
    "payload_schema",
    "Profile",
    "ResolvedType",
    "load_profile",
    "ensure_profile",
    "get_profile",
    "Binding",
    "collect_bindings",
    "document_bindings",
    "entry_bindings",
    "parse_gui_name",
]
