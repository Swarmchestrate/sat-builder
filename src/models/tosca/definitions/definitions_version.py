"""TOSCA definitions version factory for creating dynamic DefinitionsVersion classes."""

import inspect
import warnings
from enum import Enum
from typing import Type, Union, Dict, Tuple, Protocol, Set

from ruamel.yaml import YAML

from src.utils.config import get_config_file_path
from src.utils.logger import get_logger

logger = get_logger()

# Module-level cache for TOSCA definitions version configuration data
# Format: {tosca_file_name: default_definitions_version_string}
# Thread-safe as dictionary operations are atomic in CPython
_DEFINITIONS_VERSION_CACHE = {}


class DefinitionsVersionProtocol(Protocol):
    """Protocol interface for dynamically created DefinitionsVersion enums.

    This protocol ensures type safety for dynamic enums by defining the required
    interface that all generated DefinitionsVersion classes must implement.
    """

    # Enum member attributes
    value: str
    name: str
    __members__: Dict[str, 'DefinitionsVersionProtocol']

    @classmethod
    def default(cls, to_string: bool = False) -> Union['DefinitionsVersionProtocol', str]:
        """Get the default definitions version from configuration.

        Args:
            to_string: If True, return the string value; if False, return the enum instance

        Returns:
            Default definitions version as enum instance or string value
        """
        ...

    @classmethod
    def deprecated_versions(cls) -> Set[str]:
        """Get a set of deprecated version values."""
        ...

    def is_deprecated(self) -> bool:
        """Check if this version is deprecated."""
        ...

    @classmethod
    def validate_and_warn(cls, version_enum: 'DefinitionsVersionProtocol') -> Tuple[
        'DefinitionsVersionProtocol', Dict[str, str] | None]:
        """Validation function that handles deprecation warnings.

        Args:
            version_enum: DefinitionsVersion enum instance to validate

        Returns:
            Tuple of (version_enum, warning_msg) where warning_msg is None if no warning
        """
        ...


def get_definitions_version_class(tosca_file_name: str) -> Type[DefinitionsVersionProtocol]:
    """Create the DefinitionsVersion enum class for a TOSCA configuration.

    Args:
        tosca_file_name: TOSCA configuration file name (without .yaml extension)

    Returns:
        DefinitionsVersion enum class implementing DefinitionsVersionProtocol

    Raises:
        ValueError: When configuration file structure is invalid
        FileNotFoundError: When the configuration file cannot be found
    """

    # Enum definitions for Enum() constructor
    definitions_version_definitions = {
        "TOSCA_3_0": "tosca_3_1",
        "TOSCA_2_0": "tosca_2_0",
        "TOSCA_1_0": "tosca_1_0"
    }

    # Metadata for deprecated versions
    deprecated_versions_set = {"tosca_1_0"}

    # noinspection DuplicatedCode
    def _load_default_definitions_version() -> str:
        """Load TOSCA definitions version configuration with caching."""
        function_name = inspect.currentframe().f_code.co_name

        # Performance optimization: check cache before expensive file operations
        if tosca_file_name in _DEFINITIONS_VERSION_CACHE:
            logger.debug(f"{function_name}: '{tosca_file_name}' cache hit")
            return _DEFINITIONS_VERSION_CACHE[tosca_file_name]

        logger.debug(f"{function_name}: '{tosca_file_name}' cache miss, building...")

        # Load and parse YAML configuration file
        tosca_file = get_config_file_path(tosca_file_name)
        yaml = YAML(typ='safe', pure=True)

        with open(tosca_file, 'r', encoding='utf-8') as f:
            tosca_data = yaml.load(f)

        # Validate required top-level structure
        if 'tosca_definitions_version' not in tosca_data:
            msg = f"Missing 'tosca_definitions_version' section in {tosca_file_name}.yaml"
            logger.error(msg)
            raise ValueError(msg)

        default_definitions_version_loaded = tosca_data['tosca_definitions_version']

        # Validate against the enum definitions
        valid_versions = set(definitions_version_definitions.values())
        if default_definitions_version_loaded not in valid_versions:
            msg = f"Invalid 'tosca_definitions_version' in {tosca_file_name}.yaml: '{default_definitions_version_loaded}'. Must be one of {list(valid_versions)}"
            logger.error(msg)
            raise ValueError(msg)

        # Cache for future requests - thread-safe dictionary operation
        _DEFINITIONS_VERSION_CACHE[tosca_file_name] = default_definitions_version_loaded
        logger.debug(f"{function_name}: '{tosca_file_name}' cached for future use")
        return default_definitions_version_loaded

    # Load configuration and get the default value from YAML
    default_definitions_version_str = _load_default_definitions_version()

    # Create enum dynamically from the definitions
    # noinspection PyPep8Naming
    DefinitionsVersion = Enum(
        'DefinitionsVersion',
        definitions_version_definitions,
        type=str
    )

    # Add custom methods to the dynamically created enum
    def default(cls, to_string: bool = False) -> Union['DefinitionsVersion', str]:
        """Get the default definitions version from the configuration.

        Args:
            cls: Enum class to get default value from
            to_string: If True, return the string value; if False, return the enum instance

        Returns:
            Default definitions version as enum instance or string value
        """
        default_definitions_version = cls(default_definitions_version_str)
        if to_string:
            return default_definitions_version.value
        return default_definitions_version

    def deprecated_versions(_cls) -> Set[str]:
        """Set of deprecated version values.

        Returns:
            Set containing string values of deprecated versions
        """
        return deprecated_versions_set

    def is_deprecated(self) -> bool:
        """Check if this version is deprecated.

        Returns:
            True if this version is deprecated, False otherwise
        """
        return self.value in deprecated_versions_set

    def validate_and_warn(_cls, version_enum: 'DefinitionsVersion') -> Tuple[
        'DefinitionsVersion', Dict[str, str] | None]:
        """Validation function that handles deprecation warnings.

        Args:
            _cls: Enum class to validate
            version_enum: DefinitionsVersion enum instance to validate

        Returns:
            Tuple of (version_enum, warning_msg) where warning_msg is None if no warning
        """
        warning_msg = None
        if version_enum.is_deprecated():
            warning_text = f"Definitions version '{version_enum.value}' is deprecated and will be removed in future releases"
            warnings.warn(warning_text, DeprecationWarning, stacklevel=2)
            logger.warning(f"Deprecation warning issued for definitions version '{version_enum.value}'")
            warning_msg = {"definitions_version": warning_text}
        return version_enum, warning_msg

    # Add the schema extension method as a regular function first
    def get_pydantic_json_schema(cls, core_schema, handler):
        """Extend the schema with deprecation info."""
        json_schema = handler(core_schema)

        # Simple deprecation info
        deprecated = list(cls.deprecated_versions())
        if deprecated:
            json_schema.update({
                'description': f"TOSCA definitions version. Note: {', '.join(deprecated)} deprecated.",
                'x-deprecated': deprecated
            })

        return json_schema

    # Attach methods to the dynamically created enum class
    DefinitionsVersion.default = classmethod(default)
    DefinitionsVersion.deprecated_versions = classmethod(deprecated_versions)
    DefinitionsVersion.is_deprecated = is_deprecated
    DefinitionsVersion.validate_and_warn = classmethod(validate_and_warn)

    # Attach the schema extension method
    DefinitionsVersion.__get_pydantic_json_schema__ = classmethod(get_pydantic_json_schema)

    # Set proper docstring
    DefinitionsVersion.__doc__ = "Available TOSCA definitions versions."

    return DefinitionsVersion
