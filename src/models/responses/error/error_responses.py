"""
API Error Response Models

Error response models for API endpoints including validation errors,
client errors, and server errors with structured error information.
"""

from pydantic import BaseModel, Field

from src.utils.logger import get_logger

logger = get_logger()


class BaseErrorResponse(BaseModel):
    """Base error response model."""

    detail: str = Field(description="Error description")


