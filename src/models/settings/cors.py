"""CORS Configuration"""

import os

from dotenv import load_dotenv
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()


class CORSSettings(BaseSettings):
    """CORS configuration app_cfg."""

    model_config = SettingsConfigDict(
        env_prefix="CORS__",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="forbid",
        env_file_encoding="utf-8"
    )

    enabled: bool = Field(
        ...,
        description="Enable CORS middleware"
    )
    origins: str = Field(
        ...,
        description="Allowed origins (comma-separated)"
    )
    allow_credentials: bool = Field(
        ...,
        description="Allow credentials in CORS requests"
    )
    allow_methods: str = Field(
        ...,
        description="Allowed HTTP methods (comma-separated)"
    )
    allow_headers: str = Field(
        ...,
        description="Allowed HTTP headers (comma-separated)"
    )

    @model_validator(mode="before")
    @classmethod
    def validate_cors_env_vars(cls, values):
        """Validate that all CORS__ env vars map to valid fields."""
        # Get all CORS__ env vars
        cors_env_vars = {k: v for k, v in os.environ.items() if k.startswith("CORS__")}

        # Valid field names (what should exist after prefix removal)
        valid_fields = {
            "enabled", "origins", "allow_credentials",
            "allow_methods", "allow_headers"
        }

        # Check each CORS__ env var
        for env_var in cors_env_vars.keys():
            # Remove prefix to get field name
            field_name = env_var[6:].lower()  # Remove "CORS__" (6 chars)

            if field_name not in valid_fields:
                raise ValueError(
                    f"Unknown CORS__ environment variable: '{env_var}'. "
                    f"Valid variables are: {', '.join(['CORS__' + f.upper() for f in sorted(valid_fields)])}"
                )

        return values

    @field_validator("origins", mode="after")
    @classmethod
    def validate_origins(cls, v: str) -> str:
        if not v or v.strip() == "":
            return "*"

        if "," in v:
            origins = [item.strip() for item in v.split(",")]
            for origin in origins:
                # noinspection HttpUrlsUsage
                if origin != "*" and not origin.startswith(("http://", "https://")):
                    # noinspection HttpUrlsUsage
                    raise ValueError(f"Origin '{origin}' must start with http:// or https://")

        return v

    @property
    def origins_list(self) -> list[str]:
        if self.origins == "*":
            return ["*"]
        return [item.strip() for item in self.origins.split(",") if item.strip()]

    @property
    def methods_list(self) -> list[str]:
        if self.allow_methods == "*":
            return ["*"]
        return [item.strip() for item in self.allow_methods.split(",") if item.strip()]

    @property
    def headers_list(self) -> list[str]:
        if self.allow_headers == "*":
            return ["*"]
        return [item.strip() for item in self.allow_headers.split(",") if item.strip()]


_cors_instance: CORSSettings | None = None


def get_cors_settings() -> CORSSettings:
    """Get the global CORS app_cfg instance."""
    global _cors_instance
    cors_settings = _cors_instance
    if cors_settings is None:
        cors_settings = CORSSettings()
        _cors_instance = cors_settings
    return cors_settings
