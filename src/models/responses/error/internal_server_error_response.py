from typing import Optional

from pydantic import Field

from src.models.responses import BaseErrorResponse


class InternalServerErrorResponse(BaseErrorResponse):
    """500 Internal Server Error response model."""

    error_type: Optional[str] = Field(default=None, description="Type of internal error")
    support_reference: Optional[str] = Field(default=None, description="Support reference for assistance")

    model_config = {
        "json_schema_extra": {
            "example": {
                "detail": "An internal server error occurred during template generation",
                "error_type": "TemplateGenerationError",
            }
        }
    }
