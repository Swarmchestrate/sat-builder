"""TOSCA description string."""

from typing import ClassVar

from src.utils.validators.string_validator import StringValidator


class Description(str):
    """TOSCA description string with validation."""

    VALID_DESCRIPTION_PATTERN: ClassVar[str] = r'^[a-zA-Z0-9,. ]+$'
    VALID_DESCRIPTION_PATTERN_TEXT: ClassVar[str] = 'latin letters, numbers, commas, dots, and spaces'
    VALID_DESCRIPTION_MIN_LENGTH: ClassVar[int] = 4
    VALID_DESCRIPTION_MAX_LENGTH: ClassVar[int] = 255

    def __new__(cls, value):
        """Create a new Description instance with validation."""
        validated_value = cls.validate_description(value)
        return super().__new__(cls, validated_value)

    @classmethod
    def __get_pydantic_core_schema__(cls, _source_type, _handler):
        """Pydantic v2 core schema definition."""
        from pydantic_core import core_schema
        return core_schema.no_info_after_validator_function(
            cls,
            core_schema.str_schema(),
        )

    @classmethod
    def __get_pydantic_json_schema__(cls, core_schema, handler):
        """Extend the default JSON schema with validation patterns."""
        # Get the default schema first
        json_schema = handler(core_schema)

        # Only add validation constraints, preserve everything else
        json_schema.update({
            'pattern': cls.VALID_DESCRIPTION_PATTERN,
            'minLength': cls.VALID_DESCRIPTION_MIN_LENGTH,
            'maxLength': cls.VALID_DESCRIPTION_MAX_LENGTH,
            'examples': ['Application template description', 'Capacity template for cloud deployment']
        })

        return json_schema

    @classmethod
    def validate_description(cls, v: str) -> str:
        """Validate the description string."""
        return StringValidator.validate_string(
            v,
            'description',
            allow_empty=False,
            allow_padding=False,
            ascii_only=True,
            pattern=cls.VALID_DESCRIPTION_PATTERN,
            pattern_description=cls.VALID_DESCRIPTION_PATTERN_TEXT,
            min_len=cls.VALID_DESCRIPTION_MIN_LENGTH,
            max_len=cls.VALID_DESCRIPTION_MAX_LENGTH
        )

    def __repr__(self):
        """String representation."""
        return f'Description({super().__repr__()})'
