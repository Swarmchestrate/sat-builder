"""Template loading functionality for TOSCA YAML generation."""

import inspect
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, Template

from src.utils.logger import get_logger, log_function_calls
from src.utils.project import get_project_root

logger = get_logger()


@log_function_calls()
def load_template(tosca_type: str, template_version: str) -> Template:
    """Load Jinja template for TOSCA YAML generation.

    Args:
        tosca_type: TOSCA template type (e.g., 'application', 'capacity')
        template_version: Template version (e.g., '001', '002', 'latest')

    Returns:
        Jinja2 Template object ready for rendering

    Raises:
        FileNotFoundError: When the template file doesn't exist
        ValueError: When the template version is invalid
        RuntimeError: When template loading fails
    """
    function_name = inspect.currentframe().f_code.co_name

    # Get project root and templates directory
    project_root = get_project_root()
    templates_dir = project_root / "templates" / tosca_type

    # Validate templates directory exists
    if not templates_dir.exists():
        msg = f"Templates directory not found: {templates_dir}"
        logger.error(msg)
        raise FileNotFoundError(msg)

    # Resolve template version to actual filename
    template_filename = _resolve_template_filename(templates_dir, template_version)

    # Set up the Jinja2 environment
    env = Environment(
        loader=FileSystemLoader(str(templates_dir)),
        autoescape=False,  # YAML doesn't need HTML escaping
        trim_blocks=False,
        lstrip_blocks=False
    )

    # Load the template
    template = env.get_template(template_filename)

    logger.debug(f"{function_name}: Successfully loaded template '{template_filename}' for type '{tosca_type}'")
    return template


def _resolve_template_filename(templates_dir: Path, template_version: str) -> str:
    """Resolve template version to actual filename.

    Args:
        templates_dir: Directory containing template files
        template_version: Version string (e.g., '001', 'latest')

    Returns:
        Actual template filename

    Raises:
        ValueError: When the template version is invalid or not found
    """
    function_name = inspect.currentframe().f_code.co_name
    template_files = list(templates_dir.glob("*.yaml"))
    if not template_files:
        raise ValueError(f"No template files found in {templates_dir}")

    # Get all valid numbered templates at once
    numbered_templates = {}  # version -> filename
    for template_file in template_files:
        stem = template_file.stem
        if stem.endswith("_depr"):
            version = stem[:-5]  # Remove "_depr"
            if version.isdigit() and len(version) == 3:
                numbered_templates[version] = template_file.name
        elif stem.isdigit() and len(stem) == 3:
            numbered_templates[stem] = template_file.name

    if not numbered_templates:
        msg = f"No valid numbered templates found in {templates_dir}"
        logger.error(msg)
        raise ValueError(msg)

    # Get the requested version
    if template_version == "latest":
        version = max(numbered_templates.keys())
        logger.debug(f"{function_name}: Resolved 'latest' to '{numbered_templates[version]}'")
        return numbered_templates[version]
    elif template_version in numbered_templates:
        return numbered_templates[template_version]
    else:
        # Not found
        available_templates = [f.name for f in template_files]
        raise ValueError(
            f"Template version '{template_version}' not found. "
            f"Available templates: {available_templates}"
        )
