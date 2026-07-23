"""Logger Configuration"""

import os
from typing import Literal

from dotenv import load_dotenv
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()


class LoggerSettings(BaseSettings):
    """Logger configuration app_cfg."""

    model_config = SettingsConfigDict(
        env_prefix="LOGGING__",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="forbid",
        env_file_encoding="utf-8"
    )

    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        ..., description="Logging level"
    )
    to_file: bool = Field(
        ..., description="Enable logging to file"
    )
    to_console: bool = Field(
        ..., description="Enable logging to console"
    )
    file_path: str = Field(
        ..., description="Main log file path"
    )
    error_file_path: str = Field(
        ..., description="Error log file path"
    )
    access_file_path: str = Field(
        ..., description="Access log file path"
    )
    separate_error_log: bool = Field(
        ..., description="Enable separate error log file"
    )
    separate_access_log: bool = Field(
        ..., description="Enable separate access log file"
    )
    max_bytes: int = Field(
        ..., description="Maximum bytes per log file before rotation"
    )
    backup_count: int = Field(
        ..., description="Number of backup files to keep"
    )
    json_format: bool = Field(
        ..., description="Use JSON format for log output"
    )
    use_colors: bool = Field(
        ..., description="Use colors in console output"
    )

    @model_validator(mode="before")
    @classmethod
    def validate_logging_env_vars(cls, values):
        """Validate that all LOGGING__ env vars map to valid fields."""
        # Get all LOGGING__ env vars
        logging_env_vars = {k: v for k, v in os.environ.items() if k.startswith("LOGGING__")}

        # Valid field names (what should exist after prefix removal)
        valid_fields = {
            "level", "to_file", "to_console", "file_path", "error_file_path",
            "access_file_path", "separate_error_log", "separate_access_log",
            "max_bytes", "backup_count", "json_format", "use_colors"
        }

        # Check each LOGGING__ env var
        for env_var in logging_env_vars.keys():
            # Remove prefix to get field name
            field_name = env_var[9:].lower()  # Remove "LOGGING__" (9 chars)

            if field_name not in valid_fields:
                raise ValueError(
                    f"Unknown LOGGING__ environment variable: '{env_var}'. "
                    f"Valid variables are: {', '.join(['LOGGING__' + f.upper() for f in sorted(valid_fields)])}"
                )

        return values

    @model_validator(mode="after")
    def validate_logger_output(self):
        if not self.to_file and not self.to_console:
            raise ValueError("At least one of to_file or to_console must be enabled")
        return self


_logger_settings_instance: LoggerSettings | None = None


def get_logger_settings() -> LoggerSettings:
    """Get the global logger app_cfg instance."""
    global _logger_settings_instance
    logger_settings = _logger_settings_instance
    if logger_settings is None:
        logger_settings = LoggerSettings()
        _logger_settings_instance = logger_settings
    return logger_settings
