"""URL configuration model for FastAPI application endpoints.

Provides validated URL paths for FastAPI documentation and OpenAPI endpoints
including Swagger UI, ReDoc, and OpenAPI schema paths with conflict detection.
"""
from typing import ClassVar, Optional

from pydantic import BaseModel, Field, field_validator, model_validator, ValidationInfo, ConfigDict

from src.utils.logger import get_logger
from src.utils.validators import StringValidator

logger = get_logger()


class URLs(BaseModel):
    """FastAPI URL endpoint configuration.

    Manages URL paths for FastAPI documentation and API endpoints with validation
    to ensure a proper URL format and prevent path conflicts. Documentation endpoints
    are disabled by default and can be enabled by providing paths.

    Attributes:
        docs_url: Swagger UI documentation path (disabled by default)
        redoc_url: ReDoc documentation path (disabled by default)
        openapi_url: OpenAPI schema JSON endpoint path (required)
    """

    URL_PATH_PATTERN: ClassVar[str] = r'^/[a-zA-Z0-9/_.-]+$'
    """Regex pattern for valid URL paths starting with slash."""

    URL_PATH_PATTERN_DESCRIPTION: ClassVar[
        str] = 'URL path starting with "/" and containing only letters, numbers, slashes, dots, hyphens, and underscores'
    """Human-readable description of the URL path pattern."""

    docs_url: Optional[str] = Field(
        default=None,
        description="Swagger UI documentation path. None disables Swagger UI.",
        examples=["/docs", "/api/docs", "/swagger", None]
    )
    redoc_url: Optional[str] = Field(
        default=None,
        description="ReDoc documentation path. None disables ReDoc.",
        examples=["/redoc", "/api/redoc", "/documentation", None]
    )
    openapi_url: str = Field(
        default="/openapi.json",
        description="OpenAPI schema JSON endpoint path (required)",
        examples=["/openapi.json", "/api/openapi.json", "/schema.json"]
    )

    model_config = ConfigDict(
        extra="forbid",
    )

    @field_validator("docs_url", "redoc_url", "openapi_url", mode="before")
    @classmethod
    def validate_url_path(cls, v: Optional[str], info: ValidationInfo) -> Optional[str]:
        """Validate URL path format and requirements.

        Args:
            v: URL path value to validate
            info: Validation context containing field information

        Returns:
            Validated URL path or None if allowed

        Raises:
            ValueError: If openapi_url is None or the path format is invalid
        """
        field_name = info.field_name if info and hasattr(info, 'field_name') else 'url_path'

        # Allow None for optional endpoints
        if v is None:
            if field_name == "openapi_url":
                msg = f"{field_name} cannot be None"
                logger.error(msg)
                raise ValueError(msg)
            return None

        return StringValidator.validate_string(
            v,
            str(field_name),
            allow_empty=False,
            allow_padding=False,
            ascii_only=True,
            pattern=cls.URL_PATH_PATTERN,
            pattern_description=cls.URL_PATH_PATTERN_DESCRIPTION
        )

    @model_validator(mode="after")
    def validate_unique_paths(self) -> "URLs":
        """Ensure all non-None URL paths are unique to prevent conflicts.

        Returns:
            Validated URLs instance

        Raises:
            ValueError: If any URL paths conflict with each other
        """
        paths = {}

        for field in ["docs_url", "redoc_url", "openapi_url"]:
            value = getattr(self, field)
            if value:
                if value in paths:
                    msg = f"{field} path '{value}' conflicts with {paths[value]}"
                    logger.error(msg)
                    raise ValueError(msg)
                paths[value] = field

        return self
