"""Application build endpoint.

Accepts database rows keyed by table name and returns the TOSCA document the
profile's bindings produce from them, one node template per microservice.

Only the commonly used properties have a column of their own. Anything else the
profile declares is reached through application_property, whose rows name the
property they set; a name the type does not declare, or a value that will not
coerce to its declared type, comes back as a 422 rather than being dropped.
"""
from typing import Any, Dict, List

from fastapi import APIRouter
from pydantic import BaseModel, Field

from src.models.tosca.profile import (
    filterable_targets,
    get_profile,
    node_filter_binding,
    operators_for,
)
from src.utils.logger import get_logger, log_api_calls

from .build_router import BuildResponse, create_build_router

__all__ = ["BuildResponse", "application_router"]

logger = get_logger()

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


class FilterTarget(BaseModel):
    """One capability property a resource requirement can constrain."""

    target: str = Field(description="Capability property, as 'capability.property'")
    capability: str = Field(description="Capability it belongs to")
    property: str = Field(description="Property within that capability")
    type: str | None = Field(description="Type the profile declares for it")
    description: str | None = Field(default=None, description="What the property means")
    operators: List[str] = Field(description="Operators that make sense for this type")


class FilterTargetsResponse(BaseModel):
    """Everything a resource requirement may be written against."""

    target_type: str = Field(description="Node type whose capabilities these are")
    targets: List[FilterTarget] = Field(description="Targets, ordered by capability then property")


@application_router.get(
    "/application/node-filter/targets",
    response_model=FilterTargetsResponse,
    tags=["application"],
    summary="List Resource Requirement Targets",
    description=(
        "Every capability property a microservice's resource requirements can constrain, "
        "with the operators legal for each. Derived from the profile, so a capability "
        "property added there appears here without any changeticket elsewhere."
    ),
)
@log_api_calls()
async def node_filter_targets() -> FilterTargetsResponse:
    """List what a resource requirement can be written against."""
    profile = get_profile()
    binding = node_filter_binding(profile, "application")
    if not binding:
        return FilterTargetsResponse(target_type="", targets=[])

    targets = []
    for name, definition in sorted(filterable_targets(profile, binding.target_type).items()):
        operators = operators_for(definition)
        if not operators:
            # A map has no operator that means anything, so offering it would
            # only let a user build a requirement nothing can satisfy.
            continue
        capability, _, prop = name.partition(".")
        targets.append(FilterTarget(
            target=name,
            capability=capability,
            property=prop,
            type=(definition or {}).get("type"),
            description=(definition or {}).get("description"),
            operators=operators,
        ))

    return FilterTargetsResponse(target_type=binding.target_type, targets=targets)
