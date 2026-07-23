"""Swagger UI configuration model for FastAPI applications.

Provides validated Swagger UI customization settings loaded from YAML configuration
for enhanced API documentation interface. Supports standard Swagger UI parameters
with proper validation and aliasing for camelCase/snake_case compatibility.

The Swagger UI configuration includes:
- Deep linking for operations and tags navigation
- Request duration display for performance monitoring
- Tag filtering for organized documentation browsing
- Try-it-out functionality with configurable HTTP methods
- Comprehensive validation for HTTP method security and format
"""
from typing import ClassVar

from pydantic import BaseModel, Field, field_validator, ConfigDict

from src.utils.logger import get_logger
from src.utils.validators.list_validator import ListValidator
from src.utils.validators.string_validator import StringValidator

logger = get_logger()


class Swagger(BaseModel):
    """Swagger UI configuration with comprehensive validation.

    Manages Swagger UI customization parameters for FastAPI applications with
    robust validation to ensure proper configuration and security. Handles 
    camelCase YAML input with snake_case Python field names through aliases
    for seamless configuration file integration.

    All HTTP methods are validated for security, converted to lowercase for
    consistency, and checked against standard HTTP specifications. Duplicate
    methods are prevented to avoid configuration conflicts.

    Attributes:
        deep_linking: Enable deep linking for operations and tags navigation
        display_request_duration: Display request duration in Try-it-out responses
        filter: Enable tag filtering in the documentation interface
        try_it_out_enabled: Enable Try-it-out functionality for testing endpoints
        supported_submit_methods: HTTP methods available in Try-it-out interface
    """

    VALID_HTTP_METHODS: ClassVar[set[str]] = {"get", "post", "put", "delete", "patch", "head", "options", "trace"}
    """Set of valid HTTP methods for Swagger UI operations."""

    deep_linking: bool = Field(
        default=False,
        alias="deepLinking",
        description="Enable deep linking for operations and tags"
    )
    display_request_duration: bool = Field(
        default=False,
        alias="displayRequestDuration",
        description="Display request duration in Try-it-out responses"
    )
    filter: bool = Field(
        default=False,
        description="Enable tag filtering in the documentation interface"
    )
    try_it_out_enabled: bool = Field(
        default=True,
        alias="tryItOutEnabled",
        description="Enable Try-it-out functionality for testing endpoints"
    )
    supported_submit_methods: list[str] = Field(
        default=["get", "put", "post"],
        alias="supportedSubmitMethods",
        description="HTTP methods available in Try-it-out interface"
    )

    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True
    )

    @field_validator('supported_submit_methods')
    @classmethod
    def validate_supported_methods(cls, v: list[str]) -> list[str]:
        """Validate HTTP methods for Swagger UI with comprehensive security checks.

        Performs multi-stage validation of HTTP methods to ensure security,
        consistency, and compliance with HTTP specifications. Methods are
        normalized to lowercase, checked for ASCII-only characters, validated
        against standard HTTP methods, and verified for uniqueness.

        Args:
            v: List of HTTP method strings to validate

        Returns:
            List of validated and normalized HTTP method strings

        Raises:
            ValueError: If any method is invalid, non-ASCII, not a standard
                       HTTP method, or if duplicate methods are found
        """
        cleaned_methods = [
            StringValidator.validate_string(
                method.lower(),
                f'supported_submit_methods[{idx}]',
                allow_empty=False,
                allow_padding=False,
                ascii_only=True
            )
            for idx, method in enumerate(v)
        ]

        # Check for valid HTTP methods
        for method in cleaned_methods:
            if method not in cls.VALID_HTTP_METHODS:
                msg = f"Invalid HTTP method: {method}. Must be one of {sorted(cls.VALID_HTTP_METHODS)}"
                logger.error(msg)
                raise ValueError(msg)

        ListValidator.check_duplicates(
            cleaned_methods,
            'supported_submit_methods',
            allow_duplicates=False,
            allow_only_string=True,
            raise_unhashable_items=True,
        )

        return cleaned_methods
