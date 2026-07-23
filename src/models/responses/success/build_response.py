"""Dynamic BuildResponse factory for TOSCA template generation responses.

This module provides a factory function that creates customized Pydantic response
models for different TOSCA template types. Each generated model includes:

- System-controlled fields (request tracking, timestamps, status)
- Request parameter echoes (for client verification)
- Template generation outputs (YAML/JSON formats)
- Intelligent validation and status calculation
- Rich OpenAPI documentation examples

Key Features:
- Performance-optimized caching system
- Dynamic field generation based on TOSCA configuration
- Automatic status calculation based on warnings
- Type-safe response models with comprehensive validation
"""

import inspect
import uuid
from datetime import datetime, UTC
from io import StringIO
from typing import Dict, Any, List, Literal

from pydantic import BaseModel, Field, model_validator
from ruamel.yaml import YAML

from src.models.app import get_tosca_types
from src.models.tosca.definitions import (
    get_definitions_version_class,
    Description,
    get_imports_class,
    get_metadata_class,
    get_response_type_class,
    get_service_template_class,
    get_template_version_class
)
from src.utils.logger import get_logger

logger = get_logger()

# Module-level cache for build response classes - optimizes repeated requests
# Key format: "{tosca_type}_{config_file}" -> BuildResponse class
_BUILD_RESPONSE_CACHE = {}


def get_build_response_class(tosca_type: str, config_file: str):
    """Create a dynamic BuildResponse class for TOSCA template operations.

    Generates a specialized Pydantic response model tailored to specific TOSCA types.
    The model includes system-generated fields, request parameter echoes, and template
    outputs with intelligent caching for optimal performance.

    Features:
    - System-controlled fields (request_id, status, timestamp) with init=False
    - Request parameter echoes for client verification
    - Template outputs in YAML/JSON formats
    - Automatic status calculation based on warnings
    - Rich OpenAPI examples with realistic data
    - Performance-optimized caching system

    Args:
        tosca_type: TOSCA template category (e.g., 'application', 'capacity').
                   Must be defined in app.yaml tosca_types configuration.
        config_file: TOSCA configuration file name without .yaml extension
                    (e.g., 'tosca_application_template')

    Returns:
        type[BuildResponse]: Dynamically generated Pydantic model class with:
            - Complete field validation and type safety
            - Realistic OpenAPI documentation examples
            - Automatic warning-based status calculation
            - System field protection via init=False

    Raises:
        ValueError: When tosca_type is not in configured TOSCA types or
                   when required configuration files are missing.
        FileNotFoundError: When TOSCA configuration files cannot be located

    Cache Behavior:
        Results are cached using the key format "{tosca_type}_{config_file}" for
        optimal performance on repeated requests. Cache persists for the application lifetime.
    """
    function_name = inspect.currentframe().f_code.co_name

    # Load TOSCA types configuration for validation
    tosca_types = get_tosca_types()
    tosca_types_literal = tuple(tosca_types.to_list())

    # Input validation - ensure tosca_type is configured and supported
    if tosca_type not in tosca_types:
        error_msg = f"Invalid TOSCA type '{tosca_type}'. Supported types: {', '.join(tosca_types.to_list())}"
        logger.error(f"{function_name}: {error_msg}")
        raise ValueError(error_msg)

    # Check performance cache first - avoids expensive regeneration
    cache_key = f"{tosca_type}_{config_file}"
    if cache_key in _BUILD_RESPONSE_CACHE:
        logger.debug(f"{function_name}: Cache hit for BuildResponse class '{cache_key}'")
        return _BUILD_RESPONSE_CACHE[cache_key]

    logger.debug(f"{function_name}: Cache miss for '{cache_key}' - generating new BuildResponse class")

    # Load all required factory classes, for the json_schema_extra example
    # These are used only for creating realistic OpenAPI documentation examples
    logger.debug(f"{function_name}: Loading factory classes for TOSCA type '{tosca_type}'")

    # Request parameter - processing configuration
    # noinspection PyPep8Naming
    ResponseType = get_response_type_class(config_file)
    # noinspection PyPep8Naming
    TemplateVersion = get_template_version_class(tosca_type, config_file)

    # Request parameter echoes - TOSCA configuration
    # noinspection PyPep8Naming
    DefinitionsVersion = get_definitions_version_class(config_file)
    # noinspection PyPep8Naming
    Imports = get_imports_class(config_file)
    # noinspection PyPep8Naming
    Metadata = get_metadata_class(config_file)
    # noinspection PyPep8Naming
    ServiceTemplate = get_service_template_class(tosca_type, config_file)

    logger.debug(f"{function_name}: Factory classes loaded successfully for '{cache_key}'")

    template_json_output, template_yaml_output, service_template_example = _generate_openapi_examples(
        ServiceTemplate, DefinitionsVersion, Imports, Metadata, tosca_type
    )

    class BuildResponse(BaseModel):
        """Dynamic BuildResponse model for TOSCA template generation results.

        This model represents a complete response from TOSCA template generation
        operations, including system metadata, request parameters, and generated
        template content in multiple formats.

        Field Categories:
        - System fields: Auto-generated, protected from user input
        - Request echoes: Mirror input parameters for client verification
        - Template outputs: Generated TOSCA templates in requested formats
        """

        # =============================================================================
        # SYSTEM-CONTROLLED FIELDS - Protected from user input via init=False
        # =============================================================================

        request_id: str = Field(
            default_factory=lambda: f"req_{uuid.uuid4().hex[:12]}",
            pattern=r"^req_[a-f0-9]{12}$",
            description="Unique request identifier for tracking and debugging purposes. "
                        "Automatically generated in format 'req_' + 12-character hex string.",
            init=False
        )

        status: Literal["success", "warning"] = Field(
            default="success",
            description="Overall build operation status. Automatically set to 'warning' "
                        "when validation warnings are present, 'success' otherwise.",
            init=False
        )

        timestamp: datetime = Field(
            default_factory=lambda: datetime.now(UTC),
            description="ISO 8601 timestamp of template generation completion in UTC timezone.",
            init=False
        )

        # =============================================================================
        # TOSCA ROUTER IDENTIFICATION
        # =============================================================================

        tosca_type: Literal[tosca_types_literal] = Field(  # type: ignore[misc]
            description=f"TOSCA template category that was processed for generation. "
                        f"Allowed values: {', '.join(tosca_types.to_list())}"
        )

        # =============================================================================
        # REQUEST PARAMETER ECHOES - Processing Configuration
        # =============================================================================

        response_type: ResponseType = Field(  # type: ignore[misc]
            description="Output format type requested by client and used for generation. "
                        f"Allowed values: {', '.join(str(member.value) for member in ResponseType.__members__.values())}",
        )

        template_version: TemplateVersion = Field(  # type: ignore[misc]
            description="Specific template version used for generation after validation "
                        f"Allowed values: {', '.join(str(member.value) for member in TemplateVersion.__members__.values())}",
        )

        # =============================================================================
        # REQUEST PARAMETER ECHOES - TOSCA Configuration
        # =============================================================================

        definitions_version: DefinitionsVersion = Field(  # type: ignore[misc]
            description="TOSCA definitions version specification used for template generation. "
                        f"Allowed values: {', '.join(str(member.value) for member in DefinitionsVersion.__members__.values())}",
        )

        description: Description = Field(
            description="Human-readable description of the generated template's intended "
                        "purpose, functionality, and deployment context"
        )

        imports: Imports = Field(
            description="TOSCA imports configuration defining external dependencies, "
                        "required type definitions, and template inheritance relationships"
        )

        metadata: Metadata = Field(
            description="Complete TOSCA template metadata section including name, version, "
                        "authorship details, creation/update timestamps, and categorization tags"
        )

        service_template: ServiceTemplate = Field(
            description="Core TOSCA service template configuration defining the application "
                        "or capacity structure including node templates, policies, and relationships"
        )

        # =============================================================================
        # TEMPLATE GENERATION OUTPUTS - Final Results
        # =============================================================================

        template_yaml: str = Field(
            description="Complete TOSCA template rendered as YAML string. Contains full template "
                        "when YAML output is requested, empty string when YAML output not requested."
        )

        template_json: Dict[str, Any] = Field(
            description="Complete TOSCA template rendered as JSON object structure. Contains "
                        "full template when JSON output is requested, empty object when JSON output not requested."
        )

        warnings: List[Dict[str, str]] = Field(
            description="Collection of non-critical validation warnings and informational "
                        "messages encountered during template generation and processing"
        )

        # =============================================================================
        # OPENAPI DOCUMENTATION CONFIGURATION
        # =============================================================================

        model_config = {
            "json_schema_extra": {
                "example": {
                    # System-controlled fields - demonstrate auto-generation
                    "request_id": "req_abc123def456",
                    "status": "warning",
                    "timestamp": "2024-01-01T12:00:00Z",

                    # TOSCA router identification
                    "tosca_type": str(tosca_type),

                    # Request parameter echoes - processing configuration
                    "response_type": ResponseType.default(to_string=True),
                    "template_version": TemplateVersion.default(to_string=True),

                    # Request parameter echoes - TOSCA configuration
                    "definitions_version": DefinitionsVersion.default(to_string=True),
                    "description": f"{tosca_type} template description",
                    "imports": Imports().model_dump(),
                    "metadata": Metadata().model_dump(),
                    "service_template": service_template_example,

                    # Template generation outputs - realistic examples
                    "template_yaml": template_yaml_output,
                    "template_json": template_json_output,
                    "warnings": [
                        {"template_version": "Template version '001' is deprecated and will be removed in future releases"},
                        {"definitions_version": "Definitions version 'tosca_1_0' is deprecated and will be removed in future releases"},
                        {"response_type": "Response format 'yaml' provides limited output capabilities"}
                    ]
                }
            }
        }

        @model_validator(mode='after')
        def set_status_based_on_warnings(self) -> 'BuildResponse':
            """Automatically calculate response status based on validation warnings.

            Implements intelligent status determination by analyzing the warnings.
            This ensures API consumers can quickly identify responses that succeeded
            but encountered non-critical issues during processing.

            Status Logic:
            - 'warning': When the warnings' list is not empty
            - 'success': When there are no warnings

            Returns:
                BuildResponse: Self with updated status field reflecting warning state

            Note:
                This validator runs after fields validation and cannot be overridden
                by user input due to the init=False configuration on the status field.
            """
            if self.warnings:
                self.status = "warning"
            else:
                self.status = "success"
            return self

    # Cache the generated class for performance optimization
    _BUILD_RESPONSE_CACHE[cache_key] = BuildResponse
    logger.debug(f"{function_name}: BuildResponse class generated and cached for '{cache_key}'")

    return BuildResponse


def _generate_openapi_examples(ServiceTemplate, DefinitionsVersion, Imports, Metadata, tosca_type):
    """Generate OpenAPI documentation examples for template outputs."""

    # Get the original examples from schema first
    service_template_schema = ServiceTemplate.model_json_schema()
    node_templates_examples = []
    policies_examples = []

    if "properties" in service_template_schema:
        # Get node_templates examples
        if "node_templates" in service_template_schema["properties"]:
            nt_field = service_template_schema["properties"]["node_templates"]
            if "examples" in nt_field:
                node_templates_examples = nt_field["examples"]

        # Get policies examples
        if "policies" in service_template_schema["properties"]:
            pol_field = service_template_schema["properties"]["policies"]
            if "examples" in pol_field:
                policies_examples = pol_field["examples"]

    # Build original service template example
    original_service_template_example = {
        "node_templates": node_templates_examples[0] if node_templates_examples else {},
        "policies": policies_examples[0] if policies_examples else None
    }

    # Try to apply resource extraction to the examples
    try:
        imports_instance = Imports()

        # Create ServiceTemplate instance with the original examples
        sample_service_template = ServiceTemplate(**original_service_template_example)

        # Apply resource extraction
        updated_service_template, warnings = sample_service_template.update_service_template(
            namespace=imports_instance.namespace,
            extract_resources=True
        )

        # Use the updated service template
        service_template_example = updated_service_template.model_dump()

    except Exception:
        # Use original examples if update fails
        service_template_example = original_service_template_example

    # Build complete template
    template_json_output = {
        "tosca_definitions_version": DefinitionsVersion.default(to_string=True),
        "description": f"{tosca_type} template description",
        "imports": Imports().model_dump(),
        "metadata": Metadata().model_dump(),
        "service_template": service_template_example
    }

    # Convert to YAML
    yaml_handler = YAML()
    yaml_handler.preserve_quotes = False
    yaml_handler.default_flow_style = False
    template_yaml_output = StringIO()
    yaml_handler.dump(template_json_output, template_yaml_output)

    return template_json_output, template_yaml_output.getvalue(), service_template_example