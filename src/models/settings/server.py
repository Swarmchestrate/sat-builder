"""Server Configuration"""

import os
import re
from typing import ClassVar, Literal

from dotenv import load_dotenv
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()


class ServerSettings(BaseSettings):
    """Server configuration app_cfg."""

    model_config = SettingsConfigDict(
        env_prefix="SERVER__",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="forbid",
        env_file_encoding="utf-8"
    )

    HOST_PATTERN: ClassVar[str] = (
        r'^('
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}|'  # IPv4
        r'localhost|'  # localhost
        r'[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*'  # domains
        r')$'
    )

    host: str = Field(
        ...,
        description="Server host address"
    )
    port: int = Field(
        ...,
        ge=1,
        le=65535,
        description="Server port number"
    )
    reload: bool = Field(
        ...,
        description="Enable auto-reload in development"
    )
    log_level: Literal["critical", "error", "warning", "info", "debug", "trace"] = Field(
        ...,
        description="Server log level"
    )

    @model_validator(mode="before")
    @classmethod
    def validate_server_env_vars(cls, values):
        """Validate that all SERVER__ env vars map to valid fields."""
        # Get all SERVER__ env vars
        server_env_vars = {k: v for k, v in os.environ.items() if k.startswith("SERVER__")}

        # Valid field names (what should exist after prefix removal)
        valid_fields = {"host", "port", "reload", "log_level"}

        # Check each SERVER__ env var
        for env_var in server_env_vars.keys():
            # Remove prefix to get field name
            field_name = env_var[8:].lower()  # Remove "SERVER__" (8 chars)

            if field_name not in valid_fields:
                raise ValueError(
                    f"Unknown SERVER__ environment variable: '{env_var}'. "
                    f"Valid variables are: {', '.join(['SERVER__' + f.upper() for f in sorted(valid_fields)])}"
                )

        return values

    @field_validator("log_level", mode="before")
    @classmethod
    def validate_lowercase(cls, v: str) -> str:
        if isinstance(v, str):
            return v.lower()
        return v

    @field_validator("host")
    @classmethod
    def validate_host(cls, v: str) -> str:
        if not v:
            raise ValueError("Host cannot be empty")
        if not re.match(cls.HOST_PATTERN, v):
            raise ValueError("Invalid host format")
        return v


_server_settings_instance: ServerSettings | None = None


def get_server_settings() -> ServerSettings:
    """Get the global SERVER app_cfg instance."""
    global _server_settings_instance
    server_settings = _server_settings_instance
    if server_settings is None:
        server_settings = ServerSettings()
        _server_settings_instance = server_settings
    return server_settings
