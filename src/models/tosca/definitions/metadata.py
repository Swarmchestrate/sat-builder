"""TOSCA metadata factory for creating dynamic Metadata classes."""

import inspect
from datetime import date
from typing import ClassVar, Type, Annotated

from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator
from ruamel.yaml import YAML

from src.utils.config import get_config_file_path
from src.utils.logger import get_logger
from src.utils.validators import DateValidator, ListValidator, StringValidator

logger = get_logger()

# Module-level cache for TOSCA metadata configuration data
# Format: {tosca_file_name: {name: str, version: str, created_by: str, tags: list}}
# Thread-safe as dictionary operations are atomic in CPython
_METADATA_CACHE = {}


def get_metadata_class(tosca_file_name: str) -> Type[BaseModel]:
    """Create a dynamic Metadata class for a TOSCA configuration.

    Args:
        tosca_file_name: TOSCA configuration file name (without .yaml extension)

    Returns:
        Pydantic model with template metadata fields and validation

    Raises:
        ValueError: When configuration file structure is invalid
        FileNotFoundError: When the configuration file cannot be found
    """

    # noinspection DuplicatedCode
    def _load_default_metadata() -> dict:
        """Load TOSCA metadata configuration with caching."""
        function_name = inspect.currentframe().f_code.co_name

        # Performance optimization: check cache before expensive file operations
        if tosca_file_name in _METADATA_CACHE:
            logger.debug(f"{function_name}: '{tosca_file_name}' cache hit")
            return _METADATA_CACHE[tosca_file_name]

        logger.debug(f"{function_name}: '{tosca_file_name}' cache miss, building...")

        # Load and parse YAML configuration file
        tosca_file = get_config_file_path(tosca_file_name)
        yaml = YAML(typ='safe', pure=True)

        with open(tosca_file, 'r', encoding='utf-8') as f:
            tosca_data = yaml.load(f)

        # Validate required top-level structure
        if 'metadata' not in tosca_data:
            msg = f"Missing 'metadata' section in {tosca_file_name}.yaml"
            logger.error(msg)
            raise ValueError(msg)

        metadata = tosca_data['metadata']

        # Validate required fields exist
        required_fields = ['name', 'version', 'created_by', 'tags']
        for field in required_fields:
            if field not in metadata:
                msg = f"Missing '{field}' in metadata section"
                logger.error(msg)
                raise ValueError(msg)

        # Build structured result for caching and return
        default_metadata_data = {
            "name": metadata['name'],
            "version": metadata['version'],
            "created_by": metadata['created_by'],
            "created_at": date.today(),  # Use the current date
            "updated_at": date.today(),  # Use the current date
            "tags": metadata['tags']
        }

        # Cache for future requests - thread-safe dictionary operation
        _METADATA_CACHE[tosca_file_name] = default_metadata_data
        logger.debug(f"{function_name}: '{tosca_file_name}' cached for future use")
        return default_metadata_data

    # Load configuration and determine field requirements
    default_metadata = _load_default_metadata()

    class Metadata(BaseModel):
        """Template metadata with version, authorship, and lifecycle information."""

        # Validation constants for external access
        VALID_NAME_PATTERN: ClassVar[str] = r'^[a-zA-Z0-9,.\s]+$'
        VALID_NAME_PATTERN_DESCRIPTION: ClassVar[str] = 'latin letters, numbers, commas, dots, and spaces'
        VALID_NAME_MIN_LENGTH: ClassVar[int] = 1
        VALID_NAME_MAX_LENGTH: ClassVar[int] = 255
        VALID_VERSION_PATTERN: ClassVar[str] = r'^(\d+)\.(\d+)\.(\d+)(-[a-zA-Z0-9\.-]+)?$'
        VALID_VERSION_PATTERN_DESCRIPTION: ClassVar[
            str] = 'text in the following format (e.g., 0.0.1, 1.0.0, 2.1.3-alpha)'
        VALID_VERSION_MIN_LENGTH: ClassVar[int] = 5
        VALID_VERSION_MAX_LENGTH: ClassVar[int] = 20
        VALID_CREATED_BY_PATTERN: ClassVar[str] = r'^[a-zA-Z\s]+$'
        VALID_CREATED_BY_PATTERN_DESCRIPTION: ClassVar[str] = 'latin letters and spaces'
        VALID_CREATED_BY_MIN_LENGTH: ClassVar[int] = 3
        VALID_CREATED_BY_MAX_LENGTH: ClassVar[int] = 100
        VALID_TAGS_PATTERN: ClassVar[str] = r'^[a-zA-Z0-9,._-]+(?:\s+[a-zA-Z0-9,._-]+)*$'
        VALID_TAGS_PATTERN_DESCRIPTION: ClassVar[
            str] = 'latin letters, numbers, commas, dots, spaces, underscores, and dashes'
        VALID_TAGS_MIN_LENGTH: ClassVar[int] = 1
        VALID_TAGS_MAX_LENGTH: ClassVar[int] = 50

        name: str = Field(
            default=default_metadata["name"],
            description="Template name",
            pattern=VALID_NAME_PATTERN,
            min_length=VALID_NAME_MIN_LENGTH,
            max_length=VALID_NAME_MAX_LENGTH,
            examples=["Swarmchestrate Application Template", "My Custom Template"]
        )
        version: str = Field(
            default=default_metadata["version"],
            description="Template version",
            pattern=VALID_VERSION_PATTERN,
            min_length=VALID_VERSION_MIN_LENGTH,
            max_length=VALID_VERSION_MAX_LENGTH,
            examples=["1.0.0", "2.1.3-alpha", "0.0.1"]
        )
        created_by: str = Field(
            default=default_metadata["created_by"],
            description="Template author",
            pattern=VALID_CREATED_BY_PATTERN,
            min_length=VALID_CREATED_BY_MIN_LENGTH,
            max_length=VALID_CREATED_BY_MAX_LENGTH,
            examples=["Swarmchestrate Project", "John Doe", "Development Team"]
        )
        created_at: date = Field(
            default_factory=date.today,
            description="Creation date",
            examples=["2024-01-01", "2024-12-07"]
        )
        updated_at: date = Field(
            default_factory=date.today,
            description="Last update date",
            examples=["2024-01-01", "2024-12-07"]
        )
        tags: list[Annotated[str, Field(
            pattern=VALID_TAGS_PATTERN,
            min_length=VALID_TAGS_MIN_LENGTH,
            max_length=VALID_TAGS_MAX_LENGTH,
            description="Tag value matching allowed pattern"
        )]] = Field(
            default=default_metadata["tags"],
            description="Template tags",
            examples=[["application", "default_metadata"], ["capacity", "cloud", "aws"]]
        )

        model_config = ConfigDict(extra="forbid")

        @field_validator('name')
        @classmethod
        def validate_name(cls, v: str) -> str:
            """Validate the name field."""
            return StringValidator.validate_string(
                v, 'name',
                allow_empty=False,
                allow_padding=False,
                ascii_only=True,
                pattern=cls.VALID_NAME_PATTERN,
                pattern_description=cls.VALID_NAME_PATTERN_DESCRIPTION,
                min_len=cls.VALID_NAME_MIN_LENGTH,
                max_len=cls.VALID_NAME_MAX_LENGTH
            )

        @field_validator('version')
        @classmethod
        def validate_version(cls, v: str) -> str:
            """Validate the version field."""
            return StringValidator.validate_string(
                v, 'version',
                allow_empty=False,
                allow_padding=False,
                ascii_only=True,
                pattern=cls.VALID_VERSION_PATTERN,
                pattern_description=cls.VALID_VERSION_PATTERN_DESCRIPTION,
                min_len=cls.VALID_VERSION_MIN_LENGTH,
                max_len=cls.VALID_VERSION_MAX_LENGTH
            )

        @field_validator('created_by')
        @classmethod
        def validate_created_by(cls, v: str) -> str:
            """Validate the created_by field."""
            return StringValidator.validate_string(
                v, 'created_by',
                allow_empty=False,
                allow_padding=False,
                ascii_only=True,
                pattern=cls.VALID_CREATED_BY_PATTERN,
                pattern_description=cls.VALID_CREATED_BY_PATTERN_DESCRIPTION,
                min_len=cls.VALID_CREATED_BY_MIN_LENGTH,
                max_len=cls.VALID_CREATED_BY_MAX_LENGTH
            )

        @field_validator('tags')
        @classmethod
        def validate_tags(cls, v: list[str]) -> list[str]:
            """Validate the tags' field."""
            cleaned_tags = [
                StringValidator.validate_string(
                    tag, f'tags[{idx}]',
                    allow_empty=False,
                    allow_padding=False,
                    ascii_only=True,
                    pattern=cls.VALID_TAGS_PATTERN,
                    pattern_description=cls.VALID_TAGS_PATTERN_DESCRIPTION,
                    min_len=cls.VALID_TAGS_MIN_LENGTH,
                    max_len=cls.VALID_TAGS_MAX_LENGTH
                )
                for idx, tag in enumerate(v)
            ]

            ListValidator.check_duplicates(
                cleaned_tags, 'tags',
                allow_duplicates=False,
                allow_only_string=True,
                raise_unhashable_items=True,
            )

            return cleaned_tags

        @model_validator(mode='after')
        def validate_dates(self) -> 'Metadata':
            """Validate date field relationships."""
            DateValidator.validate_two_dates(
                self.created_at, 'created_at',
                self.updated_at, 'updated_at'
            )
            return self

    return Metadata
