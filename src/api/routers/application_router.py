"""Application build endpoint.

Accepts database rows keyed by table name and returns the TOSCA document the
profile's bindings produce from them, one node template per microservice.

Only the commonly used properties have a column of their own. Anything else the
profile declares is reached through application_property, whose rows name the
property they set; a name the type does not declare, or a value that will not
coerce to its declared type, comes back as a 422 rather than being dropped.
"""
from .build_router import BuildResponse, create_build_router

__all__ = ["BuildResponse", "application_router"]

application_router = create_build_router(
    kind="application",
    bindings_group="application",
    node_types_help="Node types to build, e.g. Microservice",
    payload_help=(
        "Database rows keyed by table name. Single-row tables may be sent as an "
        "object; per-microservice tables as an array. Child tables carrying an "
        "application_microservice_id are scoped to that microservice"
    ),
)
