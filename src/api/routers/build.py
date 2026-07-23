"""Build template endpoint."""
from typing import Optional, Union

from fastapi import APIRouter, Body, Query, HTTPException, status
from fastapi.responses import Response

from src.models.tosca.service_template import DefinitionsVersion
from src.models.tosca.service_template import Description
from src.models.tosca.definitions import Imports
from src.models.tosca.definitions import Metadata
from src.models.tosca.definitions import ResponseType
from src.models.tosca.definitions import ServiceTemplate
from src.models.tosca.definitions import TemplateVersion
from src.utils.logger import get_logger
from ..dependencies import get_config, get_api_logger
from ..models import BuildResponse, ErrorResponse
from ..utils import create_build_response

logger = get_logger()

yaml_cfg = get_config()
logger = get_api_logger()

router = APIRouter(tags=[yaml_cfg.routers.build.tag])


@router.post(
    yaml_cfg.routers.build.path,
    response_model=BuildResponse,
    responses={
        code: {
            "description": resp.description,
            "model": ErrorResponse if resp.model == "ErrorResponse" else
                     BuildResponse if resp.model == "BuildResponse" else None
        }
        for code, resp in yaml_cfg.routers.build.responses.items()
    },
    summary=yaml_cfg.routers.build.summary,
    description=yaml_cfg.routers.build.description
)
async def build(
        response_type: ResponseType = Query(
            default=ResponseType.YAML_JSON,
            description=yaml_cfg.routers.build.parameters["response_type"].description,
        ),
        template_version: TemplateVersion = Query(
            default=TemplateVersion.LATEST,
            description=yaml_cfg.routers.build.parameters["template_version"].description,
        ),
        tosca_definitions_version: DefinitionsVersion = Query(
            default=DefinitionsVersion.tosca_2_0,
            description=yaml_cfg.routers.build.parameters["definitions_version"].description,
        ),
        tosca_description: Description = Query(
            ...,
            description=yaml_cfg.routers.build.parameters["tosca_description"].description,
        ),
        tosca_metadata: Optional[Metadata] = Body(
            default=None,
            description=yaml_cfg.routers.build.parameters["metadata"].description,
        ),
        tosca_imports: Imports = Body(
            default_factory=Imports,
    description=yaml_cfg.routers.build.parameters["imports"].description,
        ),
        tosca_service_template: ServiceTemplate = Body(
            ...,
            description=yaml_cfg.routers.build.parameters["service_template"].description,
        )
) -> Union[BuildResponse, Response]:
    """Build a Swarmchestrate Application Template."""
    try:
        log_message = yaml_cfg.messages.log_build_request.format(
            template_version=template_version.value,
            response_type=response_type.value,
            tosca_version=tosca_definitions_version.value
        )
        logger.info(log_message)
        logger.debug(f"Description: {tosca_description}")
        logger.debug(f"Namespace: {tosca_imports.namespace}")
        logger.debug(f"Has metadata: {tosca_metadata is not None}")

        # TODO: Implement actual template building logic
        response_data = create_build_response(
            response_type,
            template_version,
            tosca_definitions_version
        )

        logger.info(yaml_cfg.messages.log_build_success)
        return response_data

    except ValueError as e:
        error_detail = yaml_cfg.messages.error_invalid_input.format(str(e))
        logger.error(yaml_cfg.messages.log_validation_error.format(error=str(e)))

        # Don't expose internal details in production
        if is_production():
            error_detail = yaml_cfg.messages.error_invalid_input.format(
                yaml_cfg.messages.error_validation_failed
            )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_detail
        )
    except Exception as e:
        logger.error(
            yaml_cfg.messages.log_unexpected_error.format(error=str(e)),
            exc_info=True
        )

        # Provide detailed error only in non-production environments
        error_message = yaml_cfg.messages.error_template_build_failed
        if not is_production():
            error_message = f"{yaml_cfg.messages.error_template_build_failed}: {str(e)}"

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_message
        )