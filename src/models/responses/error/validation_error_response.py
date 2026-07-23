from typing import List, Dict, Any, Optional

from pydantic import Field

from src.models.responses import BaseErrorResponse


class ValidationErrorResponse(BaseErrorResponse):
    """422 Validation Error response model."""

    errors: List[Dict[str, Any]] = Field(description="Detailed validation errors")
    failed_validations: Optional[List[str]] = Field(default=None,
                                                    description="List of validation rule names that failed")

    model_config = {
        "json_schema_extra": {
            "example": {
                "detail": "TOSCA validation failed",
                "errors": [
                    {
                        "field": "service_template.node_templates",
                        "message": "Missing required node template",
                        "rule": "required_node_template"
                    },
                    {
                        "field": "imports.namespace",
                        "message": "Invalid namespace format",
                        "rule": "namespace_format"
                    }
                ],
                "failed_validations": ["required_node_template", "namespace_format"]
            }
        }
    }
