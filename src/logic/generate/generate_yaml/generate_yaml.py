from pydantic import BaseModel
from typing import Dict, List, Tuple
from .load_template import load_template
from .render_template import render_template
from .validate_template import validate_template
from src.models.app import get_validation_config

from src.utils.logger import get_logger

logger = get_logger()


def generate_yaml(
        tosca_type: str,
        template_version: str,
        definitions_version: str,
        description: str,
        imports: BaseModel,
        metadata: BaseModel,
        service_template: BaseModel
) -> Tuple[str, List[Dict[str, str]]]:
    """Generate TOSCA template in YAML format.

    Args:
        tosca_type: TOSCA template type identifier
        template_version: Template version value
        definitions_version: TOSCA definitions version value
        description: Template description
        imports: TOSCA imports configuration as BaseModel
        metadata: Template metadata as BaseModel
        service_template: Service template configuration as BaseModel

    Returns:
        Tuple of (template_yaml, yaml_warnings)
        - template_yaml: Generated YAML content as string
        - yaml_warnings: List of warning dictionaries from YAML generation

    Raises:
        ValueError: When template generation fails due to invalid input
        RuntimeError: When YAML rendering encounters system errors
    """
    yaml_warnings = []


    # 1. Load the appropriate Jinja template based on tosca_type and template_version
    jinja_template = load_template(tosca_type, template_version)

   # 2. Render template with provided data
    template_yaml = render_template(
        jinja_template,
        definitions_version,
        description,
        imports,
        metadata,
        service_template
    )

    # 3. Validate generated YAML
    validation_config = get_validation_config()
    if validation_config["sardou"]:
        logger.warning("Sardou validation enable. Processing...")
        validation_warnings = validate_template(template_yaml)
        if validation_warnings:
            yaml_warnings.extend(validation_warnings)
    else:
        logger.warning("Sardou validation is disabled. Skipping...")
        yaml_warnings.append({
            "template_validation": "Sardou validation is disabled. Skipped"
        })

    return template_yaml, yaml_warnings