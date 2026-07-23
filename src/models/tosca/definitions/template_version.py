"""TOSCA Template Version Factory.

Provides dynamic creation of template version validation with an enum-based approach.
Automatically discovers available template versions from the filesystem and creates
validated enums with deprecation support and configuration-driven defaults.

Key Features:
- Filesystem-based template version discovery
- Dynamic enum generation with automatic "latest" resolution
- Deprecation support with warning generation
- Performance-optimized caching system
- Jinja template content validation
"""

import inspect
import os
import re
import warnings
from enum import Enum
from typing import Set, Tuple, Dict, Type, Union, Protocol

from ruamel.yaml import YAML

from src.utils.config import get_config_file_path
from src.utils.logger import get_logger
from src.utils.project import get_project_root

logger = get_logger()

# Module-level caches for performance optimization
# Thread-safe as dictionary operations are atomic in CPython
_DEFAULT_VERSION_CACHE = {}
_TEMPLATES_CACHE = {}


class TemplateVersionProtocol(Protocol):
    """Protocol interface for dynamically created TemplateVersion enums.

    Ensures type safety for dynamic enums by defining the required interface
    that all generated TemplateVersion classes must implement.
    """

    # Enum member attributes
    value: str
    name: str
    __members__: Dict[str, 'TemplateVersionProtocol']

    @classmethod
    def default(cls, to_string: bool = False) -> Union['TemplateVersionProtocol', str]:
        """Get the default template version from configuration."""
        ...

    @classmethod
    def deprecated_versions(cls) -> Set[str]:
        """Get a set of deprecated version values."""
        ...

    def is_deprecated(self) -> bool:
        """Check if this version is deprecated."""
        ...

    @classmethod
    def validate_and_warn(cls, version_enum: 'TemplateVersionProtocol') -> Tuple[
        'TemplateVersionProtocol', Dict[str, str] | None]:
        """Validation function that handles deprecation warnings."""
        ...


def get_template_version_class(tosca_type: str, tosca_file_name: str) -> Type[TemplateVersionProtocol]:
    """Create the TemplateVersion enum class for a TOSCA configuration.

    This factory function dynamically generates a TemplateVersion enum class by discovering
    available template files from the filesystem, loading configuration defaults, and creating
    an enum with custom __new__ method for automatic "latest" resolution.

    Template Discovery Process:
    - Scans templates/{tosca_type}/ directory for .yaml files
    - Validates filenames against the pattern: /^(\d{3}(_depr)?\.yaml)$/
    - Identifies deprecated versions by "_depr" suffix
    - Validates Jinja template content structure
    - Builds enum with V001, V002, V003, etc. members

    Input/Output Examples:
        User sends "latest" → __new__ resolves to "003" → Returns V003 → Response shows "003"
        User sends "002" → __new__ passes through → Returns V002 → Response shows "002"

    Args:
        tosca_type: The TOSCA type directory name (e.g., 'capacity', 'application')
        tosca_file_name: The configuration file name (without .yaml extension)

    Returns:
        TemplateVersion enum class implementing TemplateVersionProtocol

    Raises:
        FileNotFoundError: When the template directory or config file doesn't exist
        ValueError: When the config file is missing required sections, or the default version is invalid
    """

    # Template version validation configuration
    validation_config = {
        "version_pattern": r'^(latest|\d{3})$',
        "version_pattern_description": 'exactly 3 digits (001-999) or latest',
        "file_pattern": r'^(\d{3}(_depr)?\.yaml)$',
        "file_pattern_description": '3-digit filename with optional _depr suffix and .yaml extension (001.yaml, 001_depr.yaml)',
        "version_length": 3,
        "supported_extensions": [".yaml"],
        "deprecated_suffix": "_depr"
    }

    def _load_default_template_version() -> str:
        """Load the default template version from the TOSCA configuration file."""
        function_name = inspect.currentframe().f_code.co_name

        cache_key = (tosca_type, tosca_file_name)
        if cache_key in _DEFAULT_VERSION_CACHE:
            logger.debug(f"{function_name}: '{tosca_type}-{tosca_file_name}' cache hit")
            return _DEFAULT_VERSION_CACHE[cache_key]

        logger.debug(f"{function_name}: '{tosca_type}-{tosca_file_name}' cache miss, building...")

        # Load and parse YAML configuration file
        tosca_file = get_config_file_path(tosca_file_name)
        yaml = YAML(typ='safe', pure=True)

        with open(tosca_file, 'r', encoding='utf-8') as f:
            tosca_data = yaml.load(f)

        # Validate required top-level structure
        if 'default_template_version' not in tosca_data:
            msg = f"Missing 'default_template_version' section in {tosca_file_name}.yaml"
            logger.error(msg)
            raise ValueError(msg)

        configured_default = tosca_data['default_template_version']

        # Only accept string values
        if not isinstance(configured_default, str):
            msg = f"default_template_version must be a string, got {type(configured_default).__name__} in {tosca_file_name}.yaml"
            logger.error(msg)
            raise ValueError(msg)

        # Validate default version against pattern
        if not re.match(validation_config["version_pattern"], configured_default):
            msg = f"Invalid default_template_version '{configured_default}' in {tosca_file_name}.yaml: must be {validation_config['version_pattern_description']}"
            logger.error(msg)
            raise ValueError(msg)

        logger.debug(
            f"{function_name}: Loaded default template version '{configured_default}' from {tosca_file_name}.yaml")

        configured_default = str(configured_default)
        _DEFAULT_VERSION_CACHE[cache_key] = configured_default
        logger.debug(f"{function_name}: '{tosca_type}-{tosca_file_name}' cached for future use")
        return configured_default

    def _validate_template_file(file_path) -> bool:
        """Validate that the Jinja template file has a proper template structure.

        Performs basic validation of Jinja template files and ensure they contain
        required TOSCA sections.

        Args:
            file_path: Path to the template file to validate

        Returns:
            True if the template is valid, False otherwise

        Note:
            This validates the template structure, not the rendered output.
            Jinja variables and expressions are preserved during validation.
        """
        if not os.path.isfile(file_path):
            logger.error(f"Template file '{file_path.name}' does not exist")
            return False

        with open(file_path, 'r', encoding='utf-8') as f:
            template_content = f.read()

        if not template_content.strip():
            logger.error(f"Template file '{file_path.name}' is empty")
            return False

        # Check for Jinja patterns
        jinja_patterns = [r'{%.*%}', r'{{.*}}', r'{#.*#}']
        if not any(re.search(pattern, template_content) for pattern in jinja_patterns):
            msg = f"Template file '{file_path.name}' does not contain any Jinja patterns"
            logger.error(msg)
            return False

        # Check for TOSCA keys as text (will be rendered by Jinja) - ALL must exist
        tosca_text_keys = ['tosca_definitions_version', 'imports', 'service_template']
        missing_keys = [key for key in tosca_text_keys if key not in template_content]
        if missing_keys:
            msg = f"Template file '{file_path.name}' is missing required TOSCA keys: {", ".join(missing_keys)}"
            logger.error(msg)
            return False

        logger.debug(
            f"Template file '{file_path.name}' validated successfully - contains Jinja patterns and required TOSCA keys")
        return True

    def _discover_template_versions():
        """Discover template files and build enum metadata."""
        function_name = inspect.currentframe().f_code.co_name

        cache_key = (tosca_type, tosca_file_name)
        if cache_key in _TEMPLATES_CACHE:
            logger.debug(f"{function_name}: '{tosca_type}-{tosca_file_name}' cache hit")
            return _TEMPLATES_CACHE[cache_key]

        logger.debug(f"{function_name}: '{tosca_type}-{tosca_file_name}' cache miss, building...")

        # Locate templates directory
        templates_dir = get_project_root() / "templates" / tosca_type
        if not templates_dir.exists():
            msg = f"Template discovery failed: No '{tosca_type}' directory found in templates/"
            logger.error(msg)
            raise FileNotFoundError(msg)

        # Discover template files using supported extensions from config
        discovered_files = []
        for ext in validation_config["supported_extensions"]:
            discovered_files.extend(templates_dir.glob(f"*{ext}"))

        logger.debug(f"{function_name}: Found {len(discovered_files)} template files")

        discovered_count = 0
        version_numbers = []
        version_metadata = []  # (enum_name, version_value, is_deprecated)

        for discovered_file in discovered_files:
            filename = discovered_file.name

            # Validate filename against pattern
            if not re.match(validation_config["file_pattern"], filename):
                logger.warning(
                    f"Skipping invalid template filename '{filename}': must be {validation_config['file_pattern_description']}")
                continue

            # Validate template file content
            if not _validate_template_file(discovered_file):
                msg = f"Template validation failed: Template file '{filename}' has invalid content or structure"
                logger.error(msg)
                raise ValueError(msg)

            filename_stem = discovered_file.stem

            # Handle deprecated templates
            if filename_stem.endswith(validation_config["deprecated_suffix"]):
                deprecated_suffix_length = len(validation_config["deprecated_suffix"])
                version_number = filename_stem[:-deprecated_suffix_length]
                deprecated = True
            elif filename_stem.isdigit() and len(filename_stem) == validation_config["version_length"]:
                version_number = filename_stem
                deprecated = False
            else:
                msg = f"Template file '{filename}' passed regex validation but failed logic validation - this indicates a bug in the validation logic"
                logger.error(msg)
                raise ValueError(msg)

            # Common validation and processing
            if version_number.isdigit() and len(version_number) == validation_config["version_length"]:
                if version_number in version_numbers:
                    msg = f"Duplicate template version '{version_number}' found - both regular and deprecated versions exist"
                    logger.error(msg)
                    raise ValueError(msg)

                enum_name = f"V{version_number}"
                version_metadata.append((enum_name, version_number, deprecated))
                discovered_count += 1
                version_numbers.append(version_number)

                status = "deprecated" if deprecated else "active"
                logger.debug(f"{function_name}: Added {status} version {version_number}")

        if discovered_count == 0:
            msg = f"Template validation failed: No valid templates found in {templates_dir}"
            logger.error(msg)
            raise FileNotFoundError(msg)

        # Find latest version for resolving "latest" requests
        highest_version_value = max(version_numbers)

        # Sort template versions: descending order by version
        discovered_versions_values = sorted(version_metadata, key=lambda x: x[1], reverse=True)

        discovery_result = (discovered_versions_values, highest_version_value)
        _TEMPLATES_CACHE[cache_key] = discovery_result
        logger.debug(f"{function_name}: '{tosca_type}-{tosca_file_name}' cached for future use")
        return discovery_result

    # Discover templates
    discovered_versions, highest_version = _discover_template_versions()

    # Load default version
    default_version_str = _load_default_template_version()

    # Validate that default version exists in discovered templates
    available_versions = [value for name, value, deprecated in discovered_versions]
    if default_version_str not in available_versions and default_version_str != "latest":
        msg_ = f"Default template version '{default_version_str}' not found in available templates:\n" + "\n".join(
            available_versions)
        logger.error(msg_)
        raise ValueError(msg_)

    # Create the enum values list
    enum_values = [(name, value) for name, value, deprecated in discovered_versions]

    # Create enum dynamically from discovered template files
    # noinspection PyPep8Naming
    TemplateVersion = Enum('TemplateVersion', enum_values, type=str)

    # Override constructor to auto-resolve "latest"
    def __new__(cls, value):
        """Auto-resolve 'latest' to the actual latest version."""
        if value == "latest":
            logger.debug(f"Resolving 'latest' input to version '{highest_version}'")
            value = highest_version

        # Find the member with this value
        for member in cls:
            if member.value == value:
                return member

        # If not found, raise ValueError like normal enum behavior
        msg = f"{value!r} is not a valid {cls.__name__}"
        logger.error(msg)
        raise ValueError(msg)

    TemplateVersion.__new__ = __new__

    # Attach deprecation metadata to enum members based on _depr suffix detection
    for name, value, deprecated in discovered_versions:
        getattr(TemplateVersion, name)._deprecated_ = deprecated

    def default(cls, to_string: bool = False) -> Union['TemplateVersion', str]:
        """Get the default template version from configuration."""
        default_version = cls(default_version_str)
        if to_string:
            return default_version.value
        return default_version

    def deprecated_versions(_cls) -> Set[str]:
        """Get a set of deprecated version values."""
        return {version.value for version in TemplateVersion if getattr(version, '_deprecated_', False)}

    def is_deprecated(self) -> bool:
        """Check if this version is deprecated."""
        return getattr(self, '_deprecated_', False)

    def validate_and_warn(_cls, version_enum: 'TemplateVersion') -> Tuple['TemplateVersion', Dict[str, str] | None]:
        """Validation function that handles deprecation warnings."""
        warning_msg = None

        # version_enum is already resolved by __new__ at this point
        if version_enum.is_deprecated():
            warning_text = f"Template version '{version_enum.value}' is deprecated and will be removed in future releases"
            warnings.warn(warning_text, DeprecationWarning, stacklevel=2)
            logger.warning(f"Deprecation warning issued for version '{version_enum.value}'")
            warning_msg = {"template_version": warning_text}
        return version_enum, warning_msg

    # Attach methods to the dynamically created enum class
    TemplateVersion.default = classmethod(default)
    TemplateVersion.deprecated_versions = classmethod(deprecated_versions)
    TemplateVersion.is_deprecated = is_deprecated
    TemplateVersion.validate_and_warn = classmethod(validate_and_warn)

    def get_pydantic_json_schema(cls, core_schema, handler):
        """Extend the schema with deprecation info."""
        json_schema = handler(core_schema)

        # Add "latest" to the enum values since it's accepted by __new__
        current_enum = json_schema.get('enum', [])
        if 'latest' not in current_enum:
            current_enum.append('latest')
            json_schema['enum'] = current_enum

        # Simple deprecation info
        deprecated = list(cls.deprecated_versions())
        if deprecated:
            json_schema.update({
                'description': f"Template version for {tosca_type}. Note: {', '.join(deprecated)} deprecated. 'latest' resolves to newest version.",
                'x-deprecated': deprecated
            })
        else:
            json_schema.update({
                'description': f"Template version for {tosca_type}. 'latest' resolves to newest version."
            })

        return json_schema

    # Attach the schema extension method
    TemplateVersion.__get_pydantic_json_schema__ = classmethod(get_pydantic_json_schema)

    # Set proper docstring
    TemplateVersion.__doc__ = f"Available template versions for {tosca_type} templates."

    return TemplateVersion
