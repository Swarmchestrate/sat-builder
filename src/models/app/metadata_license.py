"""License information model for FastAPI application metadata.

Provides validated license details including name and URL
for API documentation and legal information.
"""
from typing import ClassVar, Optional

from pydantic import BaseModel, Field, field_validator, ConfigDict

from src.utils.logger import get_logger
from src.utils.validators import UrlValidator, StringValidator

logger = get_logger()


class LicenseInfo(BaseModel):
    """License information for API legal documentation.

    Provides license details with validation for name and optional URL.
    Name validation prevents whitespace-only values, URL validation ensures security.

    Attributes:
        name: License name (required)
        url: Optional URL to license text or documentation
    """

    VALID_URL_SCHEMES: ClassVar[tuple[str, ...]] = ('https',)
    """Allowed URL schemes for license URLs."""

    VALID_URL_PATTERN: ClassVar[str] = r'^[^\s<>"{}|\\^`\[\]]+$'
    """Regex pattern excluding dangerous characters from URLs."""

    VALID_URL_PATTERN_DESCRIPTION: ClassVar[str] = 'valid URL without spaces or invalid characters'
    """Human-readable description of the URL pattern."""

    name: str = Field(
        ...,
        min_length=1,
        description="License name",
        examples=["MIT", "Apache 2.0", "GPL-3.0", "BSD-3-Clause"]
    )
    url: Optional[str] = Field(
        default=None,
        description="License URL",
        examples=["https://opensource.org/licenses/MIT", "https://www.apache.org/licenses/LICENSE-2.0"]
    )

    model_config = ConfigDict(
        extra="forbid",
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate license name is not whitespace-only.

        Args:
            v: License name to validate

        Returns:
            Validated license name

        Raises:
            ValueError: If the name is whitespace-only or invalid
        """
        return StringValidator.validate_string(
            v, 'name',
            allow_empty=False,
            allow_padding=False,
            ascii_only=True
        )

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: Optional[str]) -> Optional[str]:
        """Validate URL format and security.

        Args:
            v: URL value to validate

        Returns:
            Validated URL or None if not provided

        Raises:
            ValueError: If the URL format is invalid or contains dangerous characters
        """
        if v is None:
            return v
        return UrlValidator.validate_url(
            v,
            'url',
            cls.VALID_URL_SCHEMES,
            pattern=cls.VALID_URL_PATTERN,
            pattern_description=cls.VALID_URL_PATTERN_DESCRIPTION
        )
