"""Template rendering functionality for TOSCA YAML generation."""
import inspect
import logging
from jinja2 import Template, TemplateRuntimeError

from pydantic import BaseModel

from src.utils.logger import get_logger, log_function_calls

logger = get_logger()


@log_function_calls()
def render_template(
        jinja_template: Template,
        definitions_version: str,
        description: str,
        imports: BaseModel,
        metadata: BaseModel,
        service_template: BaseModel
) -> str:
    """Render Jinja template with provided TOSCA data.

    Args:
        jinja_template: Loaded Jinja2 template object
        definitions_version: TOSCA definitions version
        description: Template description
        imports: TOSCA imports configuration
        metadata: Template metadata
        service_template: Service template configuration

    Returns:
        rendered_yaml: Rendered YAML template as string

    Raises:
        ValueError: When template rendering fails due to invalid data
        RuntimeError: When template rendering encounters system errors
    """
    function_name = inspect.currentframe().f_code.co_name

    try:
        # Prepare template context
        template_context = {
            "tosca_definitions_version": definitions_version,
            "description": description,
            "imports": imports.model_dump(),
            "metadata": metadata.model_dump(),
            "service_template": service_template.model_dump()
        }

        logger.debug(f"{function_name}: Rendering template with context keys: {list(template_context.keys())}")

        # Render the template
        rendered_yaml = jinja_template.render(**template_context)

        # Basic validation of rendered output
        if not rendered_yaml or not rendered_yaml.strip():
            msg = "Template rendering produced empty output"
            logger.error(msg)
            raise ValueError(msg)

        logger.debug(f"{function_name}: Successfully rendered template")

        return rendered_yaml

    except TemplateRuntimeError as e:
        msg = f"Template runtime error during rendering: {e}"
        logger.error(msg, exc_info=logger.isEnabledFor(logging.DEBUG))
        raise RuntimeError(msg)
    except Exception as e:
        msg = f"Unexpected error during template rendering: {e}"
        logger.error(msg, exc_info=logger.isEnabledFor(logging.DEBUG))
        raise ValueError(msg)