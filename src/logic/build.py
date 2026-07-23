from fastapi import HTTPException
from src.sat_builder.builder.metadata import process_metadata
from src.sat_builder.builder.render import render_template

from src.utils.logger import get_logger

logger = get_logger()


def _validate_result(result: tuple, error_status_code: int):
    """Validate operation results and raise HTTPException if there's an error."""
    value, error_message = result
    if error_message:
        raise HTTPException(status_code=error_status_code, detail=error_message)
    return value


def build_template(data: dict) -> dict:
    """Validate metadata and render the template."""
    template_version = _validate_result(
        process_metadata(data["metadata"]),
        error_status_code=400
    )
    rendered_template = _validate_result(
        render_template(template_version, data["tosca_input"]),
        error_status_code=500
    )

    return rendered_template
