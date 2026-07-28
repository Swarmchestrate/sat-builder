"""Profile Configuration"""

import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()


class ProfileSettings(BaseSettings):
    """TOSCA profile source configuration."""

    model_config = SettingsConfigDict(
        env_prefix="PROFILE__",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="forbid",
        env_file_encoding="utf-8"
    )

    source: str = Field(
        ...,
        description="Where to load the profile from: the URL of a profile index "
                    "(profile.yaml), or a local directory holding one"
    )
    import_url: str = Field(
        ...,
        description="Profile URL written into the imports of generated documents. "
                    "Separate from source, which may be a local checkout"
    )
    namespace: str = Field(
        ...,
        description="Import namespace prefix applied to node types, e.g. swch"
    )
    cache_dir: str = Field(
        ...,
        description="Local directory a fetched profile is cached in"
    )
    refresh_seconds: int = Field(
        ...,
        ge=0,
        description="How often to re-check the profile for updates. 0 checks every load"
    )
    offline: bool = Field(
        ...,
        description="Skip the network entirely and use the cached profile"
    )

    @model_validator(mode="before")
    @classmethod
    def validate_profile_env_vars(cls, values):
        """Validate that all PROFILE__ env vars map to valid fields."""
        profile_env_vars = {k: v for k, v in os.environ.items() if k.startswith("PROFILE__")}

        valid_fields = {
            "source", "import_url", "namespace", "cache_dir", "refresh_seconds", "offline",
        }

        for env_var in profile_env_vars.keys():
            field_name = env_var[9:].lower()  # Remove "PROFILE__" (9 chars)

            if field_name not in valid_fields:
                raise ValueError(
                    f"Unknown PROFILE__ environment variable: '{env_var}'. "
                    f"Valid variables are: {', '.join(['PROFILE__' + f.upper() for f in sorted(valid_fields)])}"
                )

        return values

    @field_validator("source")
    @classmethod
    def validate_source(cls, v: str) -> str:
        if v.startswith(("http://", "https://")):
            return v
        if Path(v).is_dir():
            return v
        raise ValueError(
            f"Profile source must be an http(s) URL or an existing directory, got '{v}'"
        )

    @field_validator("import_url")
    @classmethod
    def validate_import_url(cls, v: str) -> str:
        if not v.startswith(("http://", "https://")):
            raise ValueError("Profile import URL must be an http or https URL")
        return v

    @field_validator("cache_dir")
    @classmethod
    def validate_cache_dir(cls, v: str) -> str:
        if not v:
            raise ValueError("Profile cache directory cannot be empty")
        return v


_profile_settings_instance: ProfileSettings | None = None


def get_profile_settings() -> ProfileSettings:
    """Get the global PROFILE app_cfg instance."""
    global _profile_settings_instance
    profile_settings = _profile_settings_instance
    if profile_settings is None:
        profile_settings = ProfileSettings()
        _profile_settings_instance = profile_settings
    return profile_settings
