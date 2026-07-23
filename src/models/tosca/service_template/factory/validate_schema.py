"""TOSCA Schema Validator - Dynamic Factory"""

from typing import Any, Dict, Callable

from src.utils.logger import (
    get_logger,
    enable_debug_mode,
    log_function_calls
)
from .schema import manual_tosca_schema_validation, validate_tosca_schema

logger = get_logger()


@log_function_calls()
def _validate_schema(
        template_name: str,
        template_data: Dict[str, Any],
        tosca_component: str,
        schema_func: Callable[[str], Dict[str, Any]],
        tosca_file_name: str
) -> bool:
    """Validate a TOSCA template against schema and constraint definitions dynamically.

    Args:
        template_name: Name of the template being validated
        template_data: Template data to validate
        tosca_component: Type of TOSCA component (e.g., 'node', 'policy')
        schema_func: Function that returns the schema for validation
        tosca_file_name: Name of the TOSCA configuration file

    Returns:
        True if validation passes

    Raises:
        ValueError: If validation fails
    """

    schema = schema_func(tosca_file_name)

    validate_tosca_schema(
        tosca_component=tosca_component,
        schema_data=schema,
        template_data=template_data,
        template_name=template_name
    )

    return True


def validate_node_schema(tosca_file_name: str, template_name: str, template_data: Dict[str, Any]) -> bool:
    """Validate a TOSCA node template against schema and constraint definitions."""
    from .build_schema import get_node_schema
    return _validate_schema(template_name, template_data, "node", get_node_schema, tosca_file_name)


def validate_policy_schema(tosca_file_name: str, template_name: str, template_data: Dict[str, Any]) -> bool:
    """Validate a TOSCA policy template against schema and constraint definitions."""
    from .build_schema import get_policy_schema
    return _validate_schema(template_name, template_data, "policy", get_policy_schema, tosca_file_name)


if __name__ == "__main__":
    """Test validation for both node and policy types when run as script."""

    enable_debug_mode()

    test_files = ["tosca_application_template", "tosca_capacity_template"]

    for test_file in test_files:
        logger.debug(f"__main__: Node Schema Validation Started for '{test_file}'")
        manual_tosca_schema_validation("node", f"test_{test_file}.yaml", validate_node_schema)
        logger.debug(f"__main__: Node Schema Validation Completed for '{test_file}'.")

        logger.debug(f"__main__: Policy Schema Validation Started for '{test_file}'")
        manual_tosca_schema_validation("policy", f"test_{test_file}.yaml", validate_policy_schema)
        logger.debug(f"__main__: Policy Schema Validation Completed for '{test_file}'.")
