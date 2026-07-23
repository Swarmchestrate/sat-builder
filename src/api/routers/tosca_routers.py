"""TOSCA Template Routers Builder - Dynamic router generation for TOSCA templates."""
from typing import List, Tuple

from fastapi import APIRouter, Query, Body

from src.models.app import get_router_config, get_tosca_types
from src.models.responses import get_build_response_class
from src.models.settings import get_server_settings
from src.models.tosca.definitions import (
    get_definitions_version_class,
    Description,
    get_response_type_class,
    get_template_version_class,
    get_imports_class,
    get_metadata_class,
    get_service_template_class
)
from src.utils.logger import get_logger, log_api_calls, log_performance
from src.utils.project import get_project_root
from src.logic import generate

logger = get_logger()

# Get config once at module level
project_root = get_project_root()
tosca_types = get_tosca_types()
server_settings = get_server_settings()


def _create_tosca_router(tosca_type: str) -> APIRouter:
    """Create a single TOSCA router for the given type."""
    logger.info("=" * 60)
    logger.info(f"Router configuration TOSCA {tosca_type.upper()} initiated")
    router_cfg = get_router_config(tosca_type)
    router_path = router_cfg.path
    config_file = str(router_cfg.config_file)
    template_dir = str(router_cfg.template_dir)

    # noinspection HttpUrlsUsage
    # pylint: disable=consider-using-https-url
    logger.info(
        f"Router configuration TOSCA {tosca_type.upper()}: http://{server_settings.host}:{server_settings.port}{router_path}")

    router = APIRouter()

    # Parse endpoints from config
    if router_cfg.endpoints:
        for endpoint_name, endpoint in router_cfg.endpoints.items():

            endpoint_path = endpoint.path
            endpoint_tag = endpoint.tag
            endpoint_summary = endpoint.summary
            endpoint_description = endpoint.description

            _validate_tosca_config(tosca_type, endpoint_path, config_file, template_dir)

            # Get all factory-generated classes for this TOSCA type and config
            logger.debug(
                f"Router configuration TOSCA {tosca_type.upper()} - generating classes for endpoint {endpoint_name.upper()}")

            # Load factory-generated classes from input parameters

            # Request parameter - processing configuration
            # noinspection PyPep8Naming
            ResponseType = get_response_type_class(config_file)
            # noinspection PyPep8Naming
            TemplateVersion = get_template_version_class(
                tosca_type, config_file)

            # Request parameter echoes - TOSCA configuration
            # noinspection PyPep8Naming
            DefinitionsVersion = get_definitions_version_class(config_file)
            # noinspection PyPep8Naming
            Imports = get_imports_class(config_file)
            # noinspection PyPep8Naming
            Metadata = get_metadata_class(config_file)
            # noinspection PyPep8Naming
            ServiceTemplate = get_service_template_class(tosca_type, config_file)

            # Load factory-generated classes for the responses
            # noinspection PyPep8Naming
            BuildResponse = get_build_response_class(tosca_type, config_file)

            logger.debug(f"Router configuration TOSCA {tosca_type.upper()} - classes generated successfully")

            endpoint_full_path = router_path + endpoint_path

            # noinspection HttpUrlsUsage
            # pylint: disable=consider-using-https-url
            logger.info(
                f"Router configuration TOSCA {tosca_type.upper()} - endpoint {endpoint_name.upper()}: http://{server_settings.host}:{server_settings.port}{endpoint_full_path}")

            @log_api_calls()
            @log_performance()
            @router.post(
                endpoint_full_path,
                response_model=BuildResponse,
                summary=endpoint_summary,
                description=endpoint_description,
                tags=[endpoint_tag]
            )
            async def build_endpoint(

                    # Request parameter - processing configuration
                    response_type: ResponseType = Query(
                        ResponseType.default(),
                        description="Output format type requested by client and used for generation. "
                                    f"Allowed values: {', '.join(str(member.value) for member in ResponseType.__members__.values())}",
                    ),
                    template_version: TemplateVersion = Query(
                        default=TemplateVersion.default(),
                        description="Specific template version used for generation after validation "
                                    "and potential modification (e.g., 001, 002, 003, latest)"
                    ),
                    # Request parameter - TOSCA configuration
                    definitions_version: DefinitionsVersion = Query(
                        default=DefinitionsVersion.default(),
                        description="TOSCA definitions version specification used for template generation. "
                                    "Defines the TOSCA specification version (e.g., tosca_2_0)"
                    ),
                    description: Description = Query(
                        ...,
                        description=f"Human-readable description of the {tosca_type} template's intended "
                                    "purpose, functionality, and deployment context",
                    ),
                    imports: Imports = Body(
                        default_factory=Imports,
                        description="TOSCA imports configuration defining external dependencies, "
                                    "required type definitions, and template inheritance relationships"
                    ),
                    metadata: Metadata = Body(
                        default_factory=Metadata,
                        description="Complete TOSCA template metadata section including name, version, "
                                    "authorship details, creation/update timestamps, and categorization tags"
                    ),
                    service_template: ServiceTemplate = Body(
                        ...,
                        description=f"Core TOSCA service template configuration defining the {tosca_type} "
                                    "structure including node templates, policies, and relationships"
                    )

            ) -> BuildResponse:
                """Dynamic build endpoint generated from config."""

                # Collect any warnings from validation
                warnings_list = []

                validated_definitions_version, definitions_version_warning_msg = DefinitionsVersion.validate_and_warn(
                    definitions_version)
                if definitions_version_warning_msg:
                    warnings_list.append(definitions_version_warning_msg)

                validated_response_type, response_type_warning_msg = ResponseType.validate_and_warn(response_type)
                if response_type_warning_msg:
                    warnings_list.append(response_type_warning_msg)

                # Apply validation and warnings
                validated_template_version, template_version_warning_msg = TemplateVersion.validate_and_warn(template_version)
                if template_version_warning_msg:
                    warnings_list.append(template_version_warning_msg)

                # generate template
                template_yaml, template_json, template_warnings = generate(
                    tosca_type=tosca_type,
                    response_type=validated_response_type.value,
                    template_version=validated_template_version.value,
                    definitions_version=validated_definitions_version.value,
                    description=description,
                    imports=imports,
                    metadata=metadata,
                    service_template=service_template
                )
                if template_warnings:
                    warnings_list.extend(template_warnings)

                # Return the properly typed response
                return BuildResponse(
                    tosca_type=tosca_type,
                    response_type=validated_response_type.value,
                    template_version=validated_template_version.value,
                    definitions_version=validated_definitions_version.value,
                    description=description,
                    imports=imports.model_dump(),
                    metadata=metadata.model_dump(),
                    service_template=service_template.model_dump(),
                    template_yaml=template_yaml,
                    template_json=template_json,
                    warnings=warnings_list
                )
    else:
        msg = f"Router configuration TOSCA {tosca_type.upper()} - no endpoints defined"
        logger.error(msg)
        raise ValueError(msg)

    logger.info(f"Router configuration TOSCA {tosca_type.upper()} complete")
    logger.info("=" * 60)
    return router


def _validate_tosca_config(tosca_type: str, endpoint_path: str, config_file: str, template_dir: str):
    if endpoint_path != '/build':
        msg = f"Router configuration TOSCA {tosca_type.upper()} - invalid endpoint: '{endpoint_path}', currently only '/build' is supported"
        logger.error(msg)
        raise ValueError(msg)
    if not (project_root / "configs" / f"{config_file}.yaml").exists():
        msg = f"Router configuration TOSCA {tosca_type.upper()} - config file not found: configs/{config_file}.yaml"
        logger.error(msg)
        raise ValueError(msg)
    if not (project_root / template_dir).exists():
        msg = f"Router configuration TOSCA {tosca_type.upper()} - templates directory not found: {template_dir}"
        raise ValueError(msg)


def get_tosca_routers() -> List[Tuple[str, APIRouter]]:
    """Get all TOSCA routers configured in app.yaml."""
    logger.info("=" * 60)
    logger.info("Building TOSCA routers ...")

    tosca_routes = []

    for tosca_type in tosca_types.to_list():
        router = _create_tosca_router(tosca_type)
        tosca_routes.append((tosca_type, router))

    logger.info(f"Building TOSCA routers complete. Total: {len(tosca_routes)}")
    logger.info("=" * 60)
    return tosca_routes


tosca_routers = get_tosca_routers()

if __name__ == "__main__":
    get_tosca_routers()
