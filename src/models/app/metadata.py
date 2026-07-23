"""FastAPI Application Metadata Configuration.

This module provides Pydantic models for managing FastAPI application metadata.
Including title, version, description, license, and contact information. It handles
validation of semantic versioning and ensures proper formatting of all metadata fields.

The metadata configuration supports:
- Semantic version validation (e.g., 1.0.0, 2.1.3-beta)
- String field validation with whitespace handling
- Optional license and contact information
"""
from typing import ClassVar, Optional

from pydantic import BaseModel, Field, field_validator, ConfigDict, ValidationInfo

from src.utils.logger import get_logger
from src.utils.validators import StringValidator
from .metadata_contact import ContactInfo
from .metadata_license import LicenseInfo

logger = get_logger()


class Metadata(BaseModel):
    """FastAPI application metadata configuration.

    Provides comprehensive metadata for FastAPI applications. Including basic
    information, version control, and optional contact/license details.
    All fields are validated for proper formatting and content.

    Attributes:
        title: Application title with length constraints
        version: Semantic version string (e.g., 1.0.0, 2.1.3-alpha)
        description: Detailed application description
        license: Optional license information
        contact: Optional contact information for API support
    """

    # Semantic version validation pattern (major.minor.patch with optional pre-release)
    VALID_VERSION_PATTERN: ClassVar[str] = r'^(\d+)\.(\d+)\.(\d+)(-[a-zA-Z0-9\.-]+)?$'
    """Regex pattern for semantic versioning validation."""

    VALID_VERSION_PATTERN_TEXT: ClassVar[str] = 'semantic version format (e.g., 1.0.0, 2.1.3-alpha, 1.0.0+build123)'
    """Human-readable description of the version pattern."""

    VALID_VERSION_MIN_LENGTH: ClassVar[int] = 5
    """Minimum length for version strings (e.g., "1.0.0")."""

    VALID_VERSION_MAX_LENGTH: ClassVar[int] = 20
    """Maximum length for version strings including pre-release identifiers."""

    title: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="API title displayed in documentation",
        examples=["Application API", "TOSCA Builder API"]
    )
    version: str = Field(
        ...,
        description="API version following semantic versioning",
        examples=["1.0.0", "2.1.3-beta", "1.0.0+build123"]
    )

    description: str = Field(
        ...,
        min_length=10,
        max_length=1000,
        description="Detailed API description for documentation",
        examples=["OpenAPI-compatible RESTful API", "Comprehensive TOSCA template builder API"]
    )

    license: Optional[LicenseInfo] = Field(
        default=None,
        description="License information for the API"
    )
    contact: Optional[ContactInfo] = Field(
        default=None,
        description="Contact information for API support"
    )

    model_config = ConfigDict(
        extra="forbid"
    )

    @field_validator("title", "description")
    @classmethod
    def validate_strings(cls, v: str, info: ValidationInfo) -> str:
        """Validate string fields for proper content and formatting.

        Ensures string fields are not empty or whitespace-only and contain
        meaningful content for API documentation.

        Args:
            v: String value to validate
            info: Validation context containing field information

        Returns:
            Validated and cleaned string value

        Raises:
            ValueError: If the string is empty, whitespace-only, or invalid
        """
        field_name = info.field_name if info and hasattr(info, 'field_name') else 'string_field'
        return StringValidator.validate_string(
            v,
            str(field_name),
            allow_empty=False,
            allow_padding=False,
            ascii_only=True
        )

    @field_validator("version")
    @classmethod
    def validate_version(cls, v: str) -> str:
        """Validate version string follows the semantic versioning pattern.

        Ensures the version follows the semantic versioning (semver) format with
        major.minor.patch structure and optional pre-release/build metadata.

        Args:
            v: Version string to validate

        Returns:
            Validated version string

        Raises:
            ValueError: If the version doesn't match the semantic versioning pattern
        """
        return StringValidator.validate_string(
            v,
            'version',
            allow_empty=False,
            allow_padding=False,
            ascii_only=True,
            pattern=cls.VALID_VERSION_PATTERN,
            pattern_description=cls.VALID_VERSION_PATTERN_TEXT,
            min_len=cls.VALID_VERSION_MIN_LENGTH,
            max_len=cls.VALID_VERSION_MAX_LENGTH
        )
