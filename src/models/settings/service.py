"""Service Configuration"""

import os
import re
from typing import ClassVar

from dotenv import load_dotenv
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()


class ServiceSettings(BaseSettings):
    """Service configuration app_cfg."""

    model_config = SettingsConfigDict(
        env_prefix="SERVICE__",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="forbid",
        env_file_encoding="utf-8"
    )

    # Service ID pattern - strict (for technical identifiers)
    ID_PATTERN: ClassVar[str] = r'^[a-zA-Z0-9][a-zA-Z0-9_-]*[a-zA-Z0-9]$|^[a-zA-Z0-9]$'

    # Service name pattern - more lenient (allows spaces for display names)
    NAME_PATTERN: ClassVar[str] = r'^[a-zA-Z0-9][a-zA-Z0-9_\-\s]*[a-zA-Z0-9]$|^[a-zA-Z0-9]$'

    id: str = Field(..., description="Service ID")
    name: str = Field(..., description="Service name")

    @model_validator(mode="before")
    @classmethod
    def validate_service_env_vars(cls, values):
        """Validate that all SERVICE__ env vars map to valid fields."""
        # Get all SERVICE__ env vars
        service_env_vars = {k: v for k, v in os.environ.items() if k.startswith("SERVICE__")}

        # Valid field names (what should exist after prefix removal)
        valid_fields = {"id", "name"}

        # Check each SERVICE__ env var
        for env_var in service_env_vars.keys():
            # Remove prefix to get field name
            field_name = env_var[9:].lower()  # Remove "SERVICE__" (9 chars)

            if field_name not in valid_fields:
                raise ValueError(
                    f"Unknown SERVICE__ environment variable: '{env_var}'. "
                    f"Valid variables are: {', '.join(['SERVICE__' + f.upper() for f in valid_fields])}"
                )

        return values

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        if not v:
            raise ValueError("Service ID cannot be empty")
        if not re.match(cls.ID_PATTERN, v):
            raise ValueError(
                "Service ID must contain only alphanumeric characters, "
                "hyphens, and underscores, and cannot start or end with special characters"
            )
        return v

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v:
            raise ValueError("Service name cannot be empty")
        if not re.match(cls.NAME_PATTERN, v):
            raise ValueError(
                "Service name must contain only alphanumeric characters, spaces, "
                "hyphens, and underscores, and cannot start or end with special characters"
            )
        return v


_service_settings_instance: ServiceSettings | None = None


def get_service_settings() -> ServiceSettings:
    """Get the global service app_cfg instance."""
    global _service_settings_instance
    service_settings = _service_settings_instance
    if service_settings is None:
        service_settings = ServiceSettings()
        _service_settings_instance = service_settings
    return service_settings
