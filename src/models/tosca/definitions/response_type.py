"""TOSCA response type factory for creating dynamic ResponseType classes."""

import inspect
import warnings
from enum import Enum
from typing import Type, Union, Dict, Tuple, Protocol

from ruamel.yaml import YAML

from src.utils.config import get_config_file_path
from src.utils.logger import get_logger

logger = get_logger()

# Module-level cache for TOSCA response type configuration data
# Format: {tosca_file_name: default_response_type_string}
# Thread-safe as dictionary operations are atomic in CPython
_RESPONSE_TYPE_CACHE = {}


class ResponseTypeProtocol(Protocol):
    """Protocol interface for dynamically created ResponseType enums.

    This protocol ensures type safety for dynamic enums by defining the required
    interface that all generated ResponseType classes must implement.
    """

    # Enum member attributes
    value: str
    name: str
    __members__: Dict[str, 'ResponseTypeProtocol']

    @classmethod
    def default(cls, to_string: bool = False) -> Union['ResponseTypeProtocol', str]:
        """Get the default response type from the configuration.

        Args:
            to_string: If True, return the string value; if False, return the enum instance

        Returns:
            Default response type as enum instance or string value
        """
        ...

    @classmethod
    def validate_and_warn(cls, response_enum: 'ResponseTypeProtocol') -> Tuple[
        'ResponseTypeProtocol', Dict[str, str] | None]:
        """Validation function that handles output format warnings.

        Args:
            response_enum: ResponseType enum instance to validate

        Returns:
            Tuple of (response_enum, warning_msg) where warning_msg is None if no warning
        """
        ...


def get_response_type_class(tosca_file_name: str) -> Type[ResponseTypeProtocol]:
    """Create the ResponseType enum class for a TOSCA configuration.

    Args:
        tosca_file_name: TOSCA configuration file name (without .yaml extension)

    Returns:
        ResponseType enum class implementing ResponseTypeProtocol

    Raises:
        ValueError: When configuration file structure is invalid
        FileNotFoundError: When the configuration file cannot be found
    """

    # Enum definitions for Enum() constructor
    response_type_definitions = {
        "YAML": "yaml",
        "JSON": "json",
        "YAML_AND_JSON": "yaml_and_json"
    }

    # Metadata for Enum() methods
    response_type_metadata = {
        "yaml": {
            "limited_output": True,
            "warning_message": "Response type 'yaml' selected: JSON template will not be generated"
        },
        "json": {
            "limited_output": True,
            "warning_message": "Response type 'json' selected: YAML template will not be generated"
        },
        "yaml_and_json": {
            "limited_output": False,
            "warning_message": None
        }
    }

    # noinspection DuplicatedCode
    def _load_default_response_type() -> str:
        """Load TOSCA response type configuration with caching."""
        function_name = inspect.currentframe().f_code.co_name

        # Performance optimization: check cache before expensive file operations
        if tosca_file_name in _RESPONSE_TYPE_CACHE:
            logger.debug(f"{function_name}: '{tosca_file_name}' cache hit")
            return _RESPONSE_TYPE_CACHE[tosca_file_name]

        logger.debug(f"{function_name}: '{tosca_file_name}' cache miss, building...")

        # Load and parse YAML configuration file
        tosca_file = get_config_file_path(tosca_file_name)
        yaml = YAML(typ='safe', pure=True)

        with open(tosca_file, 'r', encoding='utf-8') as f:
            tosca_data = yaml.load(f)

        # Validate required top-level structure
        if 'default_response_type' not in tosca_data:
            msg = f"Missing 'default_response_type' section in {tosca_file_name}.yaml"
            logger.error(msg)
            raise ValueError(msg)

        default_response_type_loaded = tosca_data['default_response_type']

        # Validate against the enum definitions
        valid_types = set(response_type_definitions.values())
        if default_response_type_loaded not in valid_types:
            msg = f"Invalid 'default_response_type' in {tosca_file_name}.yaml: '{default_response_type_loaded}'. Must be one of {list(valid_types)}"
            logger.error(msg)
            raise ValueError(msg)

        # Cache for future requests - thread-safe dictionary operation
        _RESPONSE_TYPE_CACHE[tosca_file_name] = default_response_type_loaded
        logger.debug(f"{function_name}: '{tosca_file_name}' cached for future use")
        return default_response_type_loaded

    # Load configuration and get the default value from YAML
    default_response_type_str = _load_default_response_type()

    # Create enum dynamically from the definitions
    # noinspection PyPep8Naming
    ResponseType = Enum(
        'ResponseType',
        response_type_definitions,
        type=str
    )

    # Add custom methods to the dynamically created enum
    def default(cls, to_string: bool = False) -> Union['ResponseType', str]:
        """Get the default response type from the configuration.

        Args:
            cls: Enum class to get default value from
            to_string: If True, return the string value; if False, return the enum instance

        Returns:
            Default response type as enum instance or string value
        """
        default_response_type = cls(default_response_type_str)
        if to_string:
            return default_response_type.value
        return default_response_type

    def validate_and_warn(_cls, response_enum: 'ResponseType') -> Tuple['ResponseType', Dict[str, str] | None]:
        """Validation function that handles output format warnings.

        Args:
            _cls: Enum class to validate
            response_enum: ResponseType enum instance to validate

        Returns:
            Tuple of (response_enum, warning_msg) where warning_msg is None if no warning
        """
        warning_msg = None
        metadata = response_type_metadata.get(response_enum.value)

        if metadata and metadata["limited_output"] and metadata["warning_message"]:
            warning_text = metadata["warning_message"]
            warnings.warn(warning_text, UserWarning, stacklevel=2)
            logger.warning(f"Output format warning issued for response type '{response_enum.value}'")
            warning_msg = {"response_type": warning_text}

        return response_enum, warning_msg

    # Add the schema extension method
    def get_pydantic_json_schema(cls, core_schema, handler):
        """Extend the schema with output format info."""
        json_schema = handler(core_schema)

        # Add helpful descriptions for each option
        descriptions = {
            "yaml": "YAML output only (JSON template will be empty)",
            "json": "JSON output only (YAML template will be empty)",
            "yaml_and_json": "Both YAML and JSON outputs generated"
        }

        json_schema.update({
            'description': f"Template output format type. Default configured as '{cls.default(to_string=True)}'.",
            'x-format-descriptions': descriptions
        })

        return json_schema

    # Attach methods to the dynamically created enum class
    ResponseType.default = classmethod(default)
    ResponseType.validate_and_warn = classmethod(validate_and_warn)

    # Attach the schema extension method
    ResponseType.__get_pydantic_json_schema__ = classmethod(get_pydantic_json_schema)

    # Set proper docstring
    ResponseType.__doc__ = "Available TOSCA response output format types."

    return ResponseType
