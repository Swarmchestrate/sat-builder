"""TOSCA Template Generation Logic."""
from typing import Dict, Any, List, Tuple

from pydantic import BaseModel

from .generate_yaml import generate_yaml

from src.utils.logger import get_logger, log_function_calls

logger = get_logger()


@log_function_calls()
def generate(
        tosca_type: str,
        response_type: str,
        template_version: str,
        definitions_version: str,
        description: str,
        imports: BaseModel,
        metadata: BaseModel,
        service_template: BaseModel
) -> Tuple[str, Dict[str, Any], List[Dict[str, str]]]:
    """Generate TOSCA template content in YAML and JSON formats.

    Args:
        tosca_type: TOSCA template type identifier
        response_type: Response format type value (YAML, JSON, YAML_JSON, etc.)
        template_version: Template version value
        definitions_version: TOSCA definitions version value
        description: Template description
        imports: TOSCA imports configuration as BaseModel
        metadata: Template metadata as BaseModel
        service_template: Service template configuration as BaseModel

    Returns:
        Tuple of (template_yaml, template_json, template_warnings)
        - template_yaml: Generated YAML content as string (None if not requested)
        - template_json: Generated JSON content as dictionary (None if not requested)
        - template_warnings: List of warning dictionaries

    Raises:
        ValueError: When template generation fails due to invalid input
        RuntimeError: When template rendering encounters system errors
    """

    template_warnings = []
    template_yaml: str = ""
    template_json: Dict[str, Any] = {}

    updated_service_template, service_template_warnings = service_template.update_service_template(namespace=imports.namespace,extract_resources=True)
    if service_template_warnings:
        template_warnings.extend(service_template_warnings)

    # Generate content based on response_type
    if response_type in ["yaml", "yaml_and_json"]:
        template_yaml, template_yaml_warnings = generate_yaml(
            tosca_type=tosca_type,
            template_version=template_version,
            definitions_version=definitions_version,
            description=description,
            imports=imports,
            metadata=metadata,
            service_template=updated_service_template
        )
        if template_yaml_warnings:
            template_warnings.extend(template_yaml_warnings)

    if response_type in ["json", "yaml_and_json"]:
        # Generate JSON content
        template_json = {
            "definitions_version": definitions_version,
            "description": description,
            "imports": imports.model_dump(),
            "metadata": metadata.model_dump(),
            "service_template": updated_service_template.model_dump()
        }

    return template_yaml, template_json, template_warnings
