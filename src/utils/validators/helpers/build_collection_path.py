from typing import Any


def build_collection_path(
        field_name: str,
        inner_field: Any
) -> str:
    """Build a path string for nested validation."""
    return f"{field_name}[{inner_field}]"
