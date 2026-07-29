"""Shared build endpoint.

Capacity and application documents are built the same way: validate the rows
against the profile, assemble them, render, then hand the result to the TOSCA
processor. Only the binding group and the wording differ, so both endpoints are
made from this one factory rather than kept as parallel copies.
"""
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

import yaml
from fastapi import APIRouter, Body, HTTPException, Query
from pydantic import BaseModel, Field

from src.models.app import get_router_config, get_validation_config
from src.models.settings import get_profile_settings
from src.models.tosca.profile import assemble, get_profile, payload_schema, validate
from src.models.tosca.profile.assemble import InlineList
from src.models.tosca.puccini import validate_document
from src.utils.logger import get_logger, log_api_calls

logger = get_logger()

RESPONSE_TYPES = ("yaml", "json", "yaml_and_json")


class BuildResponse(BaseModel):
    """Result of a build request."""

    request_id: str = Field(description="Identifier for correlating logs with this request")
    status: str = Field(description="'ok', or 'warning' when the document built with warnings")
    timestamp: str = Field(description="When the document was built")
    node_types: List[str] = Field(description="Node types that were instantiated")
    definitions_version: str = Field(description="TOSCA definitions version of the document")
    profile_version: str | None = Field(description="Version of the profile the document was built from")
    template_yaml: str | None = Field(default=None, description="Document as YAML")
    template_json: Dict[str, Any] | None = Field(default=None, description="Document as JSON")
    warnings: List[Dict[str, str]] = Field(default_factory=list, description="Non-fatal issues")


def create_build_router(
        kind: str,
        bindings_group: str,
        node_types_help: str,
        payload_help: str,
) -> APIRouter:
    """Build the POST /<kind>/build endpoint for one kind of document.

    Args:
        kind: Router name in the app config, e.g. 'capacity'
        bindings_group: Which document-level binding group the profile declares
        node_types_help: Description of the node_types query parameter
        payload_help: Description of the request body

    Returns:
        A router carrying the single build endpoint
    """
    router_cfg = get_router_config(kind)
    endpoint = (router_cfg.endpoints or {}).get("build")
    full_path = router_cfg.path + (endpoint.path if endpoint else "/build")
    router = APIRouter()

    logger.info(f"{kind.capitalize()} router: POST {full_path}")

    @router.post(
        full_path,
        response_model=BuildResponse,
        response_model_exclude_none=True,
        tags=[endpoint.tag if endpoint else kind],
        summary=endpoint.summary if endpoint else f"Build {kind.capitalize()} Template",
        description=endpoint.description if endpoint else None,
        # The body shape follows the profile's bindings rather than a fixed
        # model, so its schema is derived at startup instead of declared.
        openapi_extra={
            "requestBody": {
                "required": True,
                "content": {"application/json": {"schema": _payload_schema(bindings_group)}},
            }
        },
    )
    @log_api_calls()
    async def build(
            node_types: List[str] = Query(..., description=node_types_help),
            response_type: str = Query(
                "yaml_and_json",
                description=f"One of {', '.join(RESPONSE_TYPES)}",
            ),
            definitions_version: str = Query(
                "tosca_2_0",
                description="TOSCA definitions version of the generated document",
            ),
            description: str | None = Query(
                None,
                description="Overrides the description bound from the payload",
            ),
            payload: Dict[str, Any] = Body(..., description=payload_help),
    ) -> BuildResponse:
        if response_type not in RESPONSE_TYPES:
            raise HTTPException(
                status_code=422,
                detail=f"Unsupported response_type '{response_type}'. "
                       f"Expected one of: {', '.join(RESPONSE_TYPES)}",
            )

        profile = get_profile()

        errors = validate(profile, node_types, payload, bindings_group=bindings_group)
        if errors:
            raise HTTPException(status_code=422, detail=[error.as_dict() for error in errors])

        settings = get_profile_settings()
        document, warnings = assemble(
            profile,
            node_types,
            payload,
            namespace=settings.namespace,
            definitions_version=definitions_version,
            imports=[{"namespace": settings.namespace, "url": settings.import_url}],
            description=description,
            bindings_group=bindings_group,
        )

        # Always render, so the document can be checked by the TOSCA processor
        # even when the caller only wants JSON back.
        document_yaml = _to_yaml(document)

        if get_validation_config()["sardou"]:
            problems, processor_available = validate_document(document_yaml)
            if problems:
                raise HTTPException(
                    status_code=422,
                    detail=[
                        {"path": "service_template", "message": list(p.values())[0],
                         "kind": "tosca_validation"}
                        for p in problems
                    ],
                )
            if not processor_available:
                warnings.append({
                    "tosca_validation": "TOSCA processor unavailable, the document was not validated"
                })
        else:
            warnings.append({"tosca_validation": "TOSCA validation is disabled, skipped"})

        if response_type == "json":
            warnings.append({
                "response_type": "Response type 'json' selected: YAML was not generated"
            })
        elif response_type == "yaml":
            warnings.append({
                "response_type": "Response type 'yaml' selected: JSON was not generated"
            })

        return BuildResponse(
            request_id=f"req_{uuid.uuid4().hex[:12]}",
            status="warning" if warnings else "ok",
            timestamp=datetime.now(timezone.utc).isoformat(),
            node_types=node_types,
            definitions_version=definitions_version,
            profile_version=profile.version,
            template_yaml=document_yaml if response_type in ("yaml", "yaml_and_json") else None,
            template_json=document if response_type in ("json", "yaml_and_json") else None,
            warnings=warnings,
        )

    return router


def _payload_schema(bindings_group: str) -> Dict[str, Any]:
    """Derive the request body schema, falling back if the profile is unreachable."""
    try:
        return payload_schema(get_profile(), bindings_group=bindings_group)
    except Exception as error:  # noqa: BLE001 - documentation must not stop startup
        logger.warning(f"_payload_schema: could not derive request schema ({error})")
        return {"type": "object", "description": "Database rows keyed by table name"}


yaml.SafeDumper.add_representer(
    InlineList,
    lambda dumper, data: dumper.represent_sequence(
        "tag:yaml.org,2002:seq", data, flow_style=True
    ),
)


def _to_yaml(document: Dict[str, Any]) -> str:
    # sort_keys=False keeps TOSCA's conventional ordering rather than alphabetising.
    return yaml.safe_dump(document, sort_keys=False, default_flow_style=False, allow_unicode=True)
