"""TOSCA types configuration model for FastAPI applications.

Provides validated TOSCA type definitions used for dynamic API generation
and template validation. TOSCA types represent different categories of
cloud application components that can be templated and deployed.
"""
from typing import List, ClassVar

from pydantic import RootModel, Field, field_validator

from src.utils.logger import get_logger
from src.utils.validators import StringValidator, ListValidator

logger = get_logger()


class ToscaTypes(RootModel[List[str]]):
    """TOSCA types configuration with validation.

    Manages a list of valid TOSCA type identifiers used for API endpoint
    generation and template validation. Each type represents a category
    of cloud application components (e.g., 'application', 'capacity').

    TOSCA types must follow package naming conventions since they correspond
    to installable packages and API endpoints.
    """

    VALID_TYPE_PATTERN: ClassVar[str] = r'^[a-z_]+$'
    """Regex pattern for TOSCA type names - lowercase letters and underscores only."""

    VALID_TYPE_PATTERN_DESCRIPTION: ClassVar[str] = 'lowercase letters and underscores only'
    """Human-readable description of the TOSCA type pattern."""

    VALID_TYPE_MIN_LENGTH: ClassVar[int] = 3
    """Minimum length for TOSCA type names."""

    VALID_TYPE_MAX_LENGTH: ClassVar[int] = 20
    """Maximum length for TOSCA type names."""

    root: List[str] = Field(
        ...,
        min_length=1,
        description="List of valid TOSCA type identifiers",
        examples=[["application", "capacity"], ["web_server", "database", "load_balancer"]]
    )

    @field_validator("root")
    @classmethod
    def validate_tosca_types(cls, v: List[str]) -> List[str]:
        """Validate TOSCA type names and ensure uniqueness.

        Args:
            v: List of TOSCA type names to validate

        Returns:
            Validated list of TOSCA type names

        Raises:
            ValueError: If any type name is invalid or duplicates exist
        """
        cleaned_types = [
            StringValidator.validate_string(
                tosca_type.lower(),
                f'tosca_types[{idx}]',
                allow_empty=False,
                allow_padding=False,
                ascii_only=True,
                pattern=cls.VALID_TYPE_PATTERN,
                pattern_description=cls.VALID_TYPE_PATTERN_DESCRIPTION,
                min_len=cls.VALID_TYPE_MIN_LENGTH,
                max_len=cls.VALID_TYPE_MAX_LENGTH
            )
            for idx, tosca_type in enumerate(v)
        ]

        ListValidator.check_duplicates(
            cleaned_types,
            'tosca_types',
            allow_duplicates=False,
            allow_only_string=True,
            raise_unhashable_items=True,
        )

        return cleaned_types

    def __iter__(self):
        """Allow iteration over TOSCA types."""
        return iter(self.root)

    def __len__(self):
        """Return the number of TOSCA types."""
        return len(self.root)

    def __getitem__(self, index):
        """Allow indexing into TOSCA types."""
        return self.root[index]

    def __contains__(self, item):
        """Allow membership testing."""
        return item in self.root

    def to_list(self) -> List[str]:
        """Return the TOSCA types as a plain list.

        Returns:
            List of TOSCA type names for use with operations that need
            plain Python lists (like str.join())
        """
        return self.root
