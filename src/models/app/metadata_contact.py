"""Contact information model for FastAPI application metadata.

Provides validated contact details including name, email, and URL
for API documentation and support information.
"""
from typing import ClassVar, Optional

from pydantic import BaseModel, Field, field_validator, ConfigDict, EmailStr

from src.utils.logger import get_logger
from src.utils.validators import UrlValidator, StringValidator

logger = get_logger()


class ContactInfo(BaseModel):
    """Contact information for API support and documentation.

    All fields are optional, allowing flexible contact configurations.
    Email validation ensures proper format, URL validation ensures security,
    and name validation prevents whitespace-only values.

    Attributes:
        name: Contact person or organization name
        email: Valid email address for support contact
        url: Support website or documentation URL
    """

    VALID_URL_SCHEMES: ClassVar[tuple[str, ...]] = ('https',)
    """Allowed URL schemes for contact URLs."""

    VALID_URL_PATTERN: ClassVar[str] = r'^[^\s<>"{}|\\^`\[\]]+$'
    """Regex pattern excluding dangerous characters from URLs."""

    VALID_URL_PATTERN_DESCRIPTION: ClassVar[str] = 'valid URL without spaces or invalid characters'
    """Human-readable description of the URL pattern."""

    name: Optional[str] = Field(
        default=None,
        description="Contact name",
        examples=["API Support Team", "John Doe"]
    )
    email: Optional[EmailStr] = Field(
        default=None,
        description="Contact email",
        examples=["support@example.com", "api-team@company.org"]
    )
    url: Optional[str] = Field(
        default=None,
        description="Contact URL",
        examples=["https://example.com/support", "https://api-docs.company.com"]
    )

    model_config = ConfigDict(
        extra="forbid",
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        """Validate contact name is not whitespace-only.

        Args:
            v: Name value to validate

        Returns:
            Validated name or None if not provided

        Raises:
            ValueError: If the name is whitespace-only or invalid
        """
        return StringValidator.validate_string(
            v, 'name',
            allow_empty=True,
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
