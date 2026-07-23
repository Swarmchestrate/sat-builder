"""FastAPI Application Validation Configuration

This module provides Pydantic models for managing FastAPI application validation features.
It allows enabling or disabling specific validation systems, such as template validation
and Sardou validation.
"""
from pydantic import BaseModel, ConfigDict, Field

from src.utils.logger import get_logger

logger = get_logger()


class Validation(BaseModel):
    """FastAPI application validation features.

    Controls which validation systems are enabled.

    Attributes:
        sardou: Enable/disable Sardou validation.
    """

    sardou: bool = Field(
        default=True,
        description="Enable Sardou validation"
    )

    model_config = ConfigDict(
        extra="forbid"
    )
