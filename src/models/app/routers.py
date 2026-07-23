"""Router configuration models for FastAPI application routing.

Provides comprehensive Pydantic models for managing FastAPI router configurations
loaded from YAML configuration files. Handles validation of router paths, tags,
file paths, and endpoint definitions with robust security checks and conflict detection.

The router configuration system includes:
- Individual endpoint configuration with path and tag validation
- Router configuration with nested endpoints and file path management
- Comprehensive path conflict detection across all routers and endpoints
- Tag reference validation to ensure all referenced tags exist
- ASCII-only validation for security and compatibility
- Dynamic router field discovery for maintainable validation logic
"""
from typing import Optional, Dict, ClassVar

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator, ValidationInfo

from src.utils.logger import get_logger
from src.utils.validators.string_validator import StringValidator

logger = get_logger()


class Endpoint(BaseModel):
    """Individual endpoint configuration with comprehensive validation.

    Represents a single API endpoint within a router with validated path, tag,
    and optional documentation fields. Ensures endpoint paths follow proper
    URL conventions and tags conform to OpenAPI specifications.

    All string fields are validated for security with ASCII-only characters,
    proper formatting, and content requirements to prevent injection attacks
    and ensure compatibility across different systems.

    Attributes:
        path: Endpoint path segment (must start with "/")
        tag: OpenAPI tag for endpoint grouping and documentation
        summary: Optional brief endpoint description for API documentation
        description: Optional detailed endpoint description for API documentation
    """

    PATH_PATTERN: ClassVar[str] = r'^/[a-zA-Z0-9/_.-]*[a-zA-Z0-9]$'
    """Regex pattern for valid endpoint paths starting with slash."""

    PATH_PATTERN_DESCRIPTION: ClassVar[
        str] = 'path starting with "/" and containing only letters, numbers, slashes, dots, hyphens, and underscores'
    """Human-readable description of the path pattern requirements."""

    TAG_PATTERN: ClassVar[str] = r'^[a-zA-Z][a-zA-Z0-9_-]*$'
    """Regex pattern for valid OpenAPI tags starting with letter."""

    TAG_PATTERN_DESCRIPTION: ClassVar[
        str] = 'tag starting with a letter and containing only letters, numbers, underscores, and hyphens'
    """Human-readable description of the tag pattern requirements."""

    model_config = ConfigDict(
        extra="forbid"
    )

    path: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Endpoint path segment",
        examples=["/build", "/validate", "/status"]
    )
    tag: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="OpenAPI tag for endpoint grouping",
        examples=["application", "capacity", "health"]
    )
    summary: Optional[str] = Field(
        None,
        min_length=1,
        max_length=100,
        description="Brief endpoint description for API documentation",
        examples=["Build Application Template", "Validate Template Configuration"]
    )
    description: Optional[str] = Field(
        None,
        min_length=1,
        max_length=500,
        description="Detailed endpoint description for API documentation",
        examples=["Build and generate a complete TOSCA application template with validation"]
    )

    @field_validator("path")
    @classmethod
    def validate_path(cls, v: str) -> str:
        """Validate endpoint path format and security.

        Ensures the path follows proper URL conventions, starts with a slash,
        and contains only safe characters to prevent path traversal attacks
        and ensure compatibility with web servers.

        Args:
            v: Path string to validate

        Returns:
            Validated and normalized path string

        Raises:
            ValueError: If the path format is invalid or contains unsafe characters
        """
        return StringValidator.validate_string(
            v,
            'path',
            allow_empty=False,
            allow_padding=False,
            ascii_only=True,
            pattern=cls.PATH_PATTERN,
            pattern_description=cls.PATH_PATTERN_DESCRIPTION
        )

    @field_validator("tag")
    @classmethod
    def validate_tag(cls, v: str) -> str:
        """Validate OpenAPI tag format and requirements.

        Ensures the tag follows OpenAPI specification requirements for
        tag naming, starting with a letter and containing only safe
        characters for use in documentation generation.

        Args:
            v: Tag string to validate

        Returns:
            Validated tag string

        Raises:
            ValueError: If the tag format is invalid or doesn't meet OpenAPI requirements
        """
        return StringValidator.validate_string(
            v,
            'tag',
            allow_empty=False,
            allow_padding=False,
            ascii_only=True,
            pattern=cls.TAG_PATTERN,
            pattern_description=cls.TAG_PATTERN_DESCRIPTION
        )

    @field_validator("summary", "description")
    @classmethod
    def validate_text_fields(cls, v: Optional[str], info: ValidationInfo) -> Optional[str]:
        """Validate optional documentation text fields.

        Ensures summary and description fields, when provided, contain
        meaningful content and are properly formatted for API documentation
        generation and display.

        Args:
            v: Text string to validate or None
            info: Validation context containing field information

        Returns:
            Validated text string or None if not provided

        Raises:
            ValueError: If text is whitespace-only or contains invalid characters
        """
        if v is None:
            return None

        field_name = info.field_name if info and hasattr(info, 'field_name') else 'text_field'
        return StringValidator.validate_string(
            v,
            str(field_name),
            allow_empty=False,
            allow_padding=False,
            ascii_only=True
        )


class Router(BaseModel):
    """Single router configuration with the comprehensive path and file validation.

    Represents a complete router configuration including base path, tag association,
    optional configuration files, template directories, and nested endpoints.
    Provides validation for all path-related fields to ensure security and
    proper file system access.

    Router configurations support both simple routers (path and tag only) and
    complex routers with additional configuration files, template directories,
    and nested endpoint definitions for dynamic API generation.

    Attributes:
        path: Base router path for all endpoints
        tag: OpenAPI tag for router grouping and documentation
        config_file: Optional configuration file path for router setup
        template_dir: Optional template directory path for dynamic content
        endpoints: Optional nested endpoint configurations
    """

    PATH_PATTERN: ClassVar[str] = r'^/[a-zA-Z0-9/_.-]*$'
    """Regex pattern for valid router base paths starting with slash."""

    PATH_PATTERN_DESCRIPTION: ClassVar[
        str] = 'path starting with "/" and containing only letters, numbers, slashes, dots, hyphens, and underscores'
    """Human-readable description of the router path pattern requirements."""

    TAG_PATTERN: ClassVar[str] = r'^[a-zA-Z][a-zA-Z0-9_-]*$'
    """Regex pattern for valid OpenAPI tags starting with letter."""

    TAG_PATTERN_DESCRIPTION: ClassVar[
        str] = 'tag starting with a letter and containing only letters, numbers, underscores, and hyphens'
    """Human-readable description of the tag pattern requirements."""

    FILE_PATH_PATTERN: ClassVar[str] = r'^[a-zA-Z0-9][a-zA-Z0-9_./\-]*[a-zA-Z0-9]$'
    """Regex pattern for safe file paths with alphanumeric boundaries."""

    FILE_PATH_PATTERN_DESCRIPTION: ClassVar[
        str] = 'safe file path with alphanumeric start/end, containing only letters, numbers, dots, slashes, hyphens, and underscores'
    """Human-readable description of the file path pattern requirements."""

    model_config = ConfigDict(
        extra="forbid"
    )

    path: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Base router path for all endpoints",
        examples=["/", "/health", "/application", "/capacity"]
    )
    tag: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="OpenAPI tag for router grouping and documentation",
        examples=["info", "health", "application", "capacity"]
    )
    config_file: Optional[str] = Field(
        None,
        min_length=1,
        max_length=200,
        description="Optional configuration file path for router setup",
        examples=["tosca_application_template", "tosca_capacity_template"]
    )
    template_dir: Optional[str] = Field(
        None,
        min_length=1,
        max_length=200,
        description="Optional template directory path for dynamic content generation",
        examples=["templates/application", "templates/capacity"]
    )
    endpoints: Optional[Dict[str, Endpoint]] = Field(
        None,
        description="Optional nested endpoint configurations for dynamic API generation"
    )

    @field_validator("path")
    @classmethod
    def validate_path(cls, v: str) -> str:
        """Validate router base path format and security.

        Ensures the router path follows proper URL conventions and contains
        only safe characters to prevent path traversal attacks and ensure
        compatibility with web servers and reverse proxies.

        Args:
            v: Path string to validate

        Returns:
            Validated and normalized path string

        Raises:
            ValueError: If the path format is invalid or contains unsafe characters
        """
        return StringValidator.validate_string(
            v,
            'path',
            allow_empty=False,
            allow_padding=False,
            ascii_only=True,
            pattern=cls.PATH_PATTERN,
            pattern_description=cls.PATH_PATTERN_DESCRIPTION
        )

    @field_validator("tag")
    @classmethod
    def validate_tag(cls, v: str) -> str:
        """Validate OpenAPI tag format and requirements.

        Ensures the tag follows OpenAPI specification requirements for
        tag naming and contains only safe characters for use in API
        documentation generation and client code generation.

        Args:
            v: Tag string to validate (required field)

        Returns:
            Validated tag string

        Raises:
            ValueError: If the tag format is invalid or doesn't meet OpenAPI requirements
        """
        return StringValidator.validate_string(
            v,
            'tag',
            allow_empty=False,
            allow_padding=False,
            ascii_only=True,
            pattern=cls.TAG_PATTERN,
            pattern_description=cls.TAG_PATTERN_DESCRIPTION
        )

    @field_validator("config_file", "template_dir")
    @classmethod
    def validate_file_paths(cls, v: Optional[str], info: ValidationInfo) -> Optional[str]:
        """Validate file and directory paths for security and accessibility.

        Ensures file and directory paths, when provided, follow safe naming
        conventions and contain only characters that are compatible across
        different file systems and operating systems.

        Args:
            v: File path string to validate or None
            info: Validation context containing field information

        Returns:
            Validated file path string or None if not provided

        Raises:
            ValueError: If the file path format is invalid or contains unsafe characters
        """
        if v is None:
            return None

        field_name = info.field_name if info and hasattr(info, 'field_name') else 'file_path'
        return StringValidator.validate_string(
            v,
            str(field_name),
            allow_empty=False,
            allow_padding=False,
            ascii_only=True,
            pattern=cls.FILE_PATH_PATTERN,
            pattern_description=cls.FILE_PATH_PATTERN_DESCRIPTION
        )


class Routers(BaseModel):
    """Complete router configuration with comprehensive validation and conflict detection.

    Manages all router configurations for the FastAPI application with robust
    validation to prevent path conflicts, ensure tag consistency, and maintain
    routing integrity across the entire application.

    The validation system performs comprehensive checks:
    - Path uniqueness across all routers and nested endpoints
    - Tag reference validation against available tag definitions
    - Dynamic field discovery for maintainable validation logic
    - Comprehensive conflict detection and reporting

    Router configurations are loaded from YAML and provide the foundation
    for dynamic API generation and routing setup.

    Attributes:
        info: Information and root endpoint router configuration
        health: Health check and monitoring endpoint router configuration
        application: Application template generation router configuration
        capacity: Capacity template generation router configuration
    """

    model_config = ConfigDict(
        extra="forbid"
    )

    info: Router = Field(
        ...,
        description="Information and root endpoint router configuration"
    )
    health: Router = Field(
        ...,
        description="Health check and monitoring endpoint router configuration"
    )
    application: Router = Field(
        ...,
        description="Application template generation router configuration"
    )
    capacity: Router = Field(
        ...,
        description="Capacity template generation router configuration"
    )

    @model_validator(mode="after")
    def validate_unique_paths(self) -> "Routers":
        """Ensure all router and endpoint paths are unique across the application.

        Performs comprehensive path conflict detection across all routers and
        their nested endpoints to prevent routing conflicts that would cause
        ambiguous request handling or server startup failures.

        The validation process checks:
        1. Base router path uniqueness across all routers
        2. Full endpoint path uniqueness (router path plus endpoint path)
        3. Conflict detection between router paths and composite endpoint paths

        Returns:
            Validated Routers instance with confirmed unique paths

        Raises:
            ValueError: If any path conflicts are detected, with detailed
                       conflict information for debugging and resolution
        """
        paths = {}
        all_paths = set()

        # Dynamically discover router fields instead of hard-coding
        router_fields = self.model_fields.keys()

        # Check main router paths for uniqueness
        for router_name in router_fields:
            router = getattr(self, router_name)
            path = router.path

            # Check for duplicate router base paths
            if path in paths:
                msg = f"Duplicate router path '{path}' found in routers '{router_name}' and '{paths[path]}'"
                logger.error(msg)
                raise ValueError(msg)
            paths[path] = router_name
            all_paths.add(path)

            # Check endpoint paths within each router for conflicts
            if router.endpoints:
                for endpoint_name, endpoint in router.endpoints.items():
                    # Construct the full endpoint path by combining router and endpoint paths
                    full_path = f"{path.rstrip('/')}{endpoint.path}"

                    if full_path in all_paths:
                        msg = f"Duplicate endpoint path '{full_path}' found in routers '{router_name}.{endpoint_name}' and '{paths[full_path]}'"
                        logger.error(msg)
                        raise ValueError(msg)
                    all_paths.add(full_path)

        return self

    def get_all_referenced_tags(self) -> set[str]:
        """Get all tag names referenced by routers and their endpoints.

        Discovers all OpenAPI tags referenced throughout the router configuration.
        Including both router-level tags and endpoint-level tags. Used for
        validation against available tag definitions to ensure consistency.

        Returns:
            Set of all unique tag names referenced across routers and endpoints

        Note:
            Uses dynamic field discovery to automatically include new router
            types without requiring code changes to this method
        """
        referenced_tags = set()

        # Dynamically discover router fields instead of hard-coding
        router_fields = self.model_fields.keys()

        for router_name in router_fields:
            router = getattr(self, router_name)

            # Add router-level tag
            referenced_tags.add(router.tag)

            # Add endpoint-level tags if endpoints exist
            if router.endpoints:
                for endpoint in router.endpoints.values():
                    referenced_tags.add(endpoint.tag)

        return referenced_tags

    def validate_tags_exist(self, available_tags: set[str]) -> None:
        """Validate that all referenced tags exist in the tag configuration.

        Ensures all tags referenced by routers and endpoints are properly
        defined in the application's tag configuration to prevent runtime
        errors in API documentation generation and client code generation.

        Args:
            available_tags: Set of tag names available in the application configuration

        Raises:
            ValueError: If any referenced tags are not found in the available
                       tags, with a detailed list of missing tags for debugging
        """
        referenced_tags = self.get_all_referenced_tags()
        missing_tags = referenced_tags - available_tags

        if missing_tags:
            msg = (f"Routers reference non-existent tags: {sorted(missing_tags)}\n"
                   f"Please ensure all referenced tags are defined in the tags configuration.")
            logger.error(msg)
            raise ValueError(msg)
