"""Capacity build endpoint.

Accepts database rows keyed by table name and returns the TOSCA document the
profile's bindings produce from them. The caller needs no TOSCA knowledge beyond
naming the node types it wants built.
"""
from .build_router import BuildResponse, create_build_router

__all__ = ["BuildResponse", "capacity_router"]

capacity_router = create_build_router(
    kind="capacity",
    bindings_group="capacity",
    node_types_help=(
        "Node types to build, e.g. CloudCapacity. A totals type such as "
        "OverallCapacity is only emitted when the payload has data for it"
    ),
    payload_help=(
        "Database rows keyed by table name. Single-row tables may be sent "
        "as an object; per-flavour tables as an array"
    ),
)
