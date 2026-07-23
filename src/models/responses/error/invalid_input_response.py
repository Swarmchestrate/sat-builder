from typing import Optional, List

from pydantic import Field

from src.models.responses import BaseErrorResponse


class InvalidInputResponse(BaseErrorResponse):
    """400 Bad Request response model."""

    invalid_fields: Optional[List[str]] = Field(default=None, description="List of invalid field names")
    suggestions: Optional[List[str]] = Field(default=None, description="Suggestions for fixing the input")

    model_config = {
        "json_schema_extra": {
            "example": {
                "detail": "Invalid input data provided",
                "invalid_fields": ["tosca_description", "response_type"],
                "suggestions": [
                    "Ensure tosca_description contains valid characters"
                ]
            }
        }
    }
