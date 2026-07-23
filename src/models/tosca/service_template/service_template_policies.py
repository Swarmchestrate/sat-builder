"""
TOSCA Service Template Policies Factory

Creates dynamic Pydantic model classes for TOSCA policies with validation
and conversion capabilities. Uses the new factory approach with TOSCA configuration loading.
"""

import inspect
from typing import Dict, Any, List

from pydantic import Field, RootModel, model_validator
from ruamel.yaml import YAML

from src.utils.config import get_config_file_path
from src.utils.logger import get_logger
from src.utils.validators import DictValidator
from .factory import get_policy_openapi_specs, validate_policy_schema

logger = get_logger()

# Module-level cache for performance
_POLICIES_CACHE = {}


def get_policies_class(tosca_type: str, tosca_file_name: str):
    """
    Create a dynamic Policies class for TOSCA policy collections.

    Args:
        tosca_type: TOSCA type identifier (e.g., 'application', 'capacity')
        tosca_file_name: TOSCA configuration file name (without .yaml extension)

    Returns:
        Dynamic Pydantic model class with policies' field and validation
    """
    function_name = inspect.currentframe().f_code.co_name
    logger.debug(f"{function_name}: creating Policies class for type '{tosca_type}', config '{tosca_file_name}'")

    # Load examples from TOSCA config
    cache_key = (tosca_type, tosca_file_name)
    if cache_key not in _POLICIES_CACHE:
        tosca_file = get_config_file_path(tosca_file_name)
        yaml = YAML(typ='safe', pure=True)

        with open(tosca_file, 'r', encoding='utf-8') as f:
            tosca_data = yaml.load(f)

        service_template = tosca_data['service_template']['policies']
        _POLICIES_CACHE[cache_key] = service_template

    defaults = _POLICIES_CACHE[cache_key]

    # Load OpenAPI specs for schema generation
    openapi_specs = get_policy_openapi_specs(tosca_file_name)

    class Policies(RootModel[List[Dict[str, Dict[str, Any]]]]):
        """
        Collection of validated TOSCA policies.

        Policies are defined as a list of policy dictionaries according to TOSCA specifications.
        Each policy dictionary contains policy instances with their specific types and properties.
        """

        root: List[Dict[str, Dict[str, Any]]] = Field(
            description="List of TOSCA policy dictionaries",
            examples=[defaults] if isinstance(defaults, list) else [[defaults]],
            json_schema_extra={
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": openapi_specs if openapi_specs else {},
                    "additionalProperties": True,
                    "description": "Dictionary containing TOSCA policy instances"
                }
            }
        )

        @model_validator(mode='after')
        def validate_policies_list(self) -> 'Policies':
            """Validate the policies' list and each policy against OpenAPI specs."""
            _function_name = inspect.currentframe().f_code.co_name

            # Validate root is a list
            if not isinstance(self.root, list):
                raise ValueError("Policies must be a list")

            # Validate each policy dictionary in the list
            for i, policy_dict in enumerate(self.root):
                DictValidator.validate_dict(policy_dict, f"policies[{i}]")

                # Validate each policy within the dictionary
                for policy_name, policy_data in policy_dict.items():
                    logger.debug(f"{_function_name}: validating policy '{policy_name}' from list[{i}]")
                    DictValidator.validate_dict(policy_data, f"policies[{i}].{policy_name}")
                    validate_policy_schema(tosca_file_name, policy_name, policy_data)

            return self

    logger.debug(f"{function_name}: successfully created Policies class")
    return Policies
