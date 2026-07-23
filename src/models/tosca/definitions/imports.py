"""TOSCA imports factory for creating dynamic Imports classes."""

import inspect
from typing import Type

from pydantic import BaseModel, Field, ConfigDict, field_validator, create_model
from ruamel.yaml import YAML

from src.utils.config import get_config_file_path
from src.utils.logger import get_logger
from src.utils.validators import StringValidator, UrlValidator

logger = get_logger()

# Module-level cache for TOSCA imports configuration data
# Format: {tosca_file_name: {namespace: str, url_field: str, url_value: str}}
# Thread-safe as dictionary operations are atomic in CPython
_IMPORTS_CACHE = {}


def get_imports_class(tosca_file_name: str) -> Type[BaseModel]:
    """Create a dynamic Imports class for a TOSCA configuration.

    Args:
        tosca_file_name: TOSCA configuration file name (without .yaml extension)

    Returns:
        Pydantic model with namespace and profile/url fields based on configuration

    Raises:
        ValueError: When configuration file structure is invalid
        FileNotFoundError: When the configuration file cannot be found
    """

    # noinspection DuplicatedCode
    def _load_default_imports() -> dict:
        """Load TOSCA imports configuration with caching."""
        function_name = inspect.currentframe().f_code.co_name

        # Performance optimization: check cache before expensive file operations
        if tosca_file_name in _IMPORTS_CACHE:
            logger.debug(f"{function_name}: '{tosca_file_name}' cache hit")
            return _IMPORTS_CACHE[tosca_file_name]

        logger.debug(f"{function_name}: '{tosca_file_name}' cache miss, building...")

        # Load and parse YAML configuration file
        tosca_file = get_config_file_path(tosca_file_name)
        yaml = YAML(typ='safe', pure=True)

        with open(tosca_file, 'r', encoding='utf-8') as f:
            tosca_data = yaml.load(f)

        # Validate required top-level structure
        if 'imports' not in tosca_data:
            msg = f"Missing 'imports' section in {tosca_file_name}.yaml"
            logger.error(msg)
            raise ValueError(msg)

        imports = tosca_data['imports']
        # TOSCA specification requires exactly one import entry for this use case
        if not imports or len(imports) != 1:
            msg = f"Invalid 'imports' section in {tosca_file_name}.yaml - must contain exactly one import entry"
            logger.error(msg)
            raise ValueError(msg)

        imports_data = imports[0]

        # Validate required namespace field
        if 'namespace' not in imports_data:
            msg = f"Missing 'namespace' in imports entry in {tosca_file_name}.yaml"
            logger.error(msg)
            raise ValueError(msg)

        # Handle mutual exclusivity of 'profile' vs. 'url' fields
        # This reflects different TOSCA specification variants
        has_profile = 'profile' in imports_data
        has_url = 'url' in imports_data

        if has_profile and has_url:
            msg = f"Cannot have both 'profile' and 'url' fields in imports entry in {tosca_file_name}.yaml"
            logger.error(msg)
            raise ValueError(msg)
        elif has_profile:
            url_field = 'profile'
            url_value = imports_data['profile']
        elif has_url:
            url_field = 'url'
            url_value = imports_data['url']
        else:
            msg = f"Missing 'profile' or 'url' in imports entry in {tosca_file_name}.yaml"
            logger.error(msg)
            raise ValueError(msg)

        # Build structured result for caching and return
        default_imports_data = {
            "namespace": imports_data['namespace'],
            "url_field": url_field,  # Store field name for dynamic model generation
            "url_value": url_value  # Store default value for Field() creation
        }

        # Cache for future requests - thread-safe dictionary operation
        _IMPORTS_CACHE[tosca_file_name] = default_imports_data
        logger.debug(f"{function_name}: '{tosca_file_name}' cached for future use")
        return default_imports_data

    # Load configuration and determine dynamic field requirements
    default_imports = _load_default_imports()
    url_field_name = default_imports["url_field"]

    # Build field definitions for create_model()
    # This approach ensures FastAPI can introspect the complete schema
    fields = {
        'namespace': (str, Field(
            default=default_imports["namespace"],
            description="TOSCA namespace identifier for imports"
        )),
        url_field_name: (str, Field(
            default=default_imports["url_value"],
            description="URL reference to external TOSCA profile or definition file"
        ))
    }

    # Create the model using Pydantic's factory function
    # This is crucial for FastAPI OpenAPI schema generation compatibility
    # noinspection PyPep8Naming
    Imports = create_model(
        'Imports',
        __base__=BaseModel,
        __config__=ConfigDict(extra="forbid"),
        **fields
    )

    # Attach validation constants to the class for external access
    # Direct assignment of literal values
    Imports.VALID_PROFILE_URL_SCHEMES = ('http', 'https')
    Imports.VALID_PROFILE_URL_PATTERN = r'^[^\s<>"{}|\\^`\[\]]+$'
    Imports.VALID_PROFILE_URL_PATTERN_DESCRIPTION = 'valid URL without spaces or invalid characters'
    Imports.VALID_NAMESPACE_PATTERN = r'^[a-z]+$'
    Imports.VALID_NAMESPACE_PATTERN_DESCRIPTION = 'lowercase latin letters (a-z)'
    Imports.VALID_NAMESPACE_MIN_LENGTH = 4
    Imports.VALID_NAMESPACE_MAX_LENGTH = 10

    # Create field validator functions
    def validate_namespace(_cls, v: str) -> str:
        """Validate the namespace field."""
        return StringValidator.validate_string(
            v, 'namespace',
            allow_empty=False,
            allow_padding=False,
            ascii_only=True,
            pattern=Imports.VALID_NAMESPACE_PATTERN,
            pattern_description=Imports.VALID_NAMESPACE_PATTERN_DESCRIPTION,
            min_len=Imports.VALID_NAMESPACE_MIN_LENGTH,
            max_len=Imports.VALID_NAMESPACE_MAX_LENGTH
        )

    def validate_url_field(_cls, v: str) -> str:
        """Validate URL field (profile/url)."""
        return UrlValidator.validate_url(
            v, url_field_name,
            Imports.VALID_PROFILE_URL_SCHEMES,
            pattern=Imports.VALID_PROFILE_URL_PATTERN,
            pattern_description=Imports.VALID_PROFILE_URL_PATTERN_DESCRIPTION
        )

    # Attach validators to the dynamically created class
    # Using setattr with proper decorator chaining for Pydantic field validation
    setattr(Imports, 'validate_namespace', field_validator('namespace')(classmethod(validate_namespace)))
    setattr(Imports, f'validate_{url_field_name}', field_validator(url_field_name)(classmethod(validate_url_field)))

    # Set a user-friendly docstring for the generated class
    Imports.__doc__ = f"""TOSCA imports configuration for external dependencies.

    Defines namespace and {url_field_name} reference for importing external TOSCA definitions.
    """

    # Create a custom JSON schema method to extend the default schema
    def __get_pydantic_json_schema__(cls, core_schema, handler):
        """Extend the default JSON schema with validation patterns."""
        # Get the default schema first
        json_schema = handler(core_schema)

        # Only add the pattern to the namespace field if it exists
        if 'properties' in json_schema and 'namespace' in json_schema['properties']:
            json_schema['properties']['namespace'].update({
                'pattern': cls.VALID_NAMESPACE_PATTERN,
                'minLength': cls.VALID_NAMESPACE_MIN_LENGTH,
                'maxLength': cls.VALID_NAMESPACE_MAX_LENGTH
            })

        # Add URL format validation to the profile/url field (format only, no pattern)
        if 'properties' in json_schema:
            if url_field_name in json_schema['properties']:
                json_schema['properties'][url_field_name].update({
                    'format': 'uri'
                })

        return json_schema

    # Attach the custom schema method using setattr as a classmethod
    setattr(Imports, '__get_pydantic_json_schema__', classmethod(__get_pydantic_json_schema__))

    # Force Pydantic to rebuild internal schema with attached validators
    # This step is crucial for proper validator integration
    Imports.model_rebuild()

    return Imports
