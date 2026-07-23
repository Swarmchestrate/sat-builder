"""
TOSCA Service Template NodeTemplates Factory

Creates dynamic Pydantic model classes for TOSCA node_templates with validation
and conversion capabilities. Uses the new factory approach with TOSCA configuration loading.
"""

import inspect
from typing import Dict, Any

from pydantic import Field, RootModel, model_validator
from ruamel.yaml import YAML

from src.utils.config import get_config_file_path
from src.utils.logger import get_logger
from .factory import get_node_openapi_specs, validate_node_schema

logger = get_logger()

# Module-level cache for performance
_NODE_TEMPLATES_CACHE = {}


def get_node_templates_class(tosca_type: str, tosca_file_name: str):
    """
    Create a dynamic NodeTemplates class for TOSCA node_template collections.

    Args:
        tosca_type: TOSCA type identifier (e.g., 'application', 'capacity')
        tosca_file_name: TOSCA configuration file name (without .yaml extension)

    Returns:
        Dynamic Pydantic model class with node_templates field and validation
    """
    function_name = inspect.currentframe().f_code.co_name
    logger.debug(f"{function_name}: creating NodeTemplates class for type '{tosca_type}', config '{tosca_file_name}'")

    # Load examples from TOSCA config
    cache_key = (tosca_type, tosca_file_name)
    if cache_key not in _NODE_TEMPLATES_CACHE:
        tosca_file = get_config_file_path(tosca_file_name)
        yaml = YAML(typ='safe', pure=True)

        with open(tosca_file, 'r', encoding='utf-8') as f:
            tosca_data = yaml.load(f)

        service_template = tosca_data.get('service_template', {})
        _NODE_TEMPLATES_CACHE[cache_key] = service_template.get('node_templates', {})

    defaults = _NODE_TEMPLATES_CACHE[cache_key]

    # Load OpenAPI specs for schema generation
    openapi_specs = get_node_openapi_specs(tosca_file_name)

    class NodeTemplates(RootModel[Dict[str, Dict[str, Any]]]):
        """
        Collection of validated TOSCA node_templates.

        Node templates are defined with their specific types and properties according to TOSCA specifications.
        Each node template instance can be of any supported TOSCA node type.
        """

        root: Dict[str, Dict[str, Any]] = Field(
            description="Dictionary of TOSCA node template instances keyed by node name",
            examples=[defaults],
            json_schema_extra={
                "type": "object",
                "properties": openapi_specs if openapi_specs else {},
                "additionalProperties": True,
                "description": "TOSCA node templates with validated structure"
            }
        )

        @model_validator(mode='after')
        def validate_node_templates_dict(self) -> 'NodeTemplates':
            """Validate the node templates dictionary and each node template against OpenAPI specs."""
            _function_name = inspect.currentframe().f_code.co_name

            # Validate each node template against its schema
            for node_name, node_data in self.root.items():
                logger.debug(f"{_function_name}: validating node template '{node_name}'")

                # Validate against TOSCA schema
                validate_node_schema(tosca_file_name, node_name, node_data)

            return self

    logger.debug(f"{function_name}: successfully created NodeTemplates class")
    return NodeTemplates
