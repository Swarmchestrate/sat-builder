"""OpenAPI Tags Configuration.

Provides validated OpenAPI tag definitions loaded dynamically from YAML configuration
for FastAPI application documentation. Tags are used for grouping API endpoints
and must follow package-style naming conventions with proper structure validation.
"""
from typing import List, Dict, Any, ClassVar

from pydantic import BaseModel, ConfigDict, field_validator

from src.utils.logger import get_logger
from src.utils.validators import StringValidator

logger = get_logger()


class Tags(BaseModel):
    """OpenAPI tags configuration with validation.

    Manages OpenAPI tags loaded dynamically from YAML configuration with validation
    to ensure proper tag structure and naming conventions. Tags are used for grouping
    API endpoints in documentation and must follow package-style naming.

    Note:
        Tags are loaded as extra fields from YAML configuration. Each tag must
        contain 'name' and 'description' fields following package naming conventions.
    """

    TAG_NAME_PATTERN: ClassVar[str] = r'^[a-z][a-z0-9_]*$'
    """Regex pattern for tag names - lowercase package-style names starting with letter."""

    TAG_PATTERN_DESCRIPTION: ClassVar[str] = 'lowercase package-style name starting with letter'
    """Human-readable description of the tag name pattern."""

    model_config = ConfigDict(
        extra="allow",  # Allow extra tag fields from YAML
    )

    @field_validator("*", mode="before")
    @classmethod
    def validate_tag_structure(cls, v: Any) -> Any:
        """Validate that each tag has a proper structure.

        Args:
            v: Tag value to validate

        Returns:
            Validated tag dictionary with name and description

        Raises:
            ValueError: If the tag structure is invalid or missing required fields
        """
        if isinstance(v, dict):
            if "name" not in v or "description" not in v:
                msg = "Tag must have 'name' and 'description' fields"
                logger.error(msg)
                raise ValueError(msg)

            # Validate name pattern
            name = StringValidator.validate_string(
                v["name"], 'tag_name',
                allow_empty=False,
                allow_padding=False,
                ascii_only=True,
                pattern=cls.TAG_NAME_PATTERN,
                pattern_description=cls.TAG_PATTERN_DESCRIPTION
            )

            # Validate description
            description = StringValidator.validate_string(
                v["description"], 'tag_description',
                allow_empty=False,
                ascii_only=True
            )

            return {"name": name, "description": description}
        return v

    def get_openapi_tags(self) -> List[Dict[str, Any]]:
        """Get OpenAPI tags list from all validated tag fields.

        Returns:
            List of tag dictionaries suitable for FastAPI OpenAPI configuration
        """
        tags = []

        # Get extra fields (the actual tag definitions)
        extra_fields = getattr(self, '__pydantic_extra__', {})

        for field_name, field_value in extra_fields.items():
            if isinstance(field_value, dict) and "name" in field_value:
                tags.append(field_value)

        return tags
