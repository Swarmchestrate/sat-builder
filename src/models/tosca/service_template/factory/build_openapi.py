"""TOSCA OpenAPI Schema Generation - Dynamic Factory"""

import inspect
from typing import Any, Dict, Callable

from src.utils.logger import (
    get_logger,
    enable_debug_mode,
    log_function_calls,
    log_cache_operations
)
from .openapi import build_openapi_specs

logger = get_logger()

# Module-level cache for OpenAPI data - keyed by (tosca_component, file_name) tuple
_CACHED_OPENAPI: Dict[tuple[str, str], Dict[str, Any]] = {}


@log_function_calls()
@log_cache_operations()
def _get_openapi_specs(
        tosca_file_name: str,
        tosca_component: str,
        schema_func: Callable[[str], Dict[str, Any]]
) -> Dict[str, Any]:
    """Convert TOSCA schema to OpenAPI schema format dynamically.

    Args:
        tosca_file_name: Name of the TOSCA configuration file
        tosca_component: Type of TOSCA component (e.g., 'node', 'policy')
        schema_func: Function that returns the schema for the given tosca_file_name

    Returns:
        Dictionary containing the generated OpenAPI specifications
    """
    # noinspection DuplicatedCode
    function_name = inspect.currentframe().f_code.co_name

    # Use composite cache key for different type/file combinations
    cache_key = (tosca_component, tosca_file_name)

    if cache_key in _CACHED_OPENAPI:
        logger.debug(
            f"{function_name}: OpenAPI cache hit for '{tosca_component}' in '{tosca_file_name}'")
        return _CACHED_OPENAPI[cache_key]

    logger.debug(
        f"{function_name}: OpenAPI cache miss for '{tosca_component}' in '{tosca_file_name}', building...")

    # Generate OpenAPI file name based on input parameters
    openapi_file_name = f"{tosca_file_name}_{tosca_component}_openapi.json"

    _CACHED_OPENAPI[cache_key] = build_openapi_specs(
        tosca_file_name=tosca_file_name,
        openapi_file_name=openapi_file_name,
        get_schema=lambda: schema_func(tosca_file_name)
    )

    logger.debug(
        f"{function_name}: OpenAPI cached for '{tosca_component}' in '{tosca_file_name}'")

    return _CACHED_OPENAPI[cache_key]


def get_node_openapi_specs(tosca_file_name: str) -> Dict[str, Any]:
    """Convert TOSCA node schema to OpenAPI schema format."""
    from .build_schema import get_node_schema
    return _get_openapi_specs(tosca_file_name, "node", get_node_schema)


def get_policy_openapi_specs(tosca_file_name: str) -> Dict[str, Any]:
    """Convert TOSCA policy schema to OpenAPI schema format."""
    from .build_schema import get_policy_schema
    return _get_openapi_specs(tosca_file_name, "policy", get_policy_schema)


if __name__ == "__main__":
    """Test OpenAPI conversion for both node and policy types when run as script."""

    enable_debug_mode()

    test_files = ["tosca_application_template", "tosca_capacity_template"]

    for file_name in test_files:
        logger.debug(f"__main__: Node OpenAPI Schema Extraction Started for '{file_name}'")
        node_openapi_specs = get_node_openapi_specs(file_name)
        for spec_type in node_openapi_specs.keys():
            logger.debug(f"__main__: OpenAPI type created - {spec_type}")
        logger.debug(f"__main__: Node OpenAPI Schema Extraction Completed for '{file_name}'. "
                     f"Schema saved and {len(node_openapi_specs)} types found")

        logger.debug(f"__main__: Policy OpenAPI Schema Extraction Started for '{file_name}'")
        policy_openapi_specs = get_policy_openapi_specs(file_name)
        for spec_type in policy_openapi_specs.keys():
            logger.debug(f"__main__: OpenAPI type created - {spec_type}")
        logger.debug(f"__main__: Policy OpenAPI Schema Extraction Completed for '{file_name}'. "
                     f"Schema saved and {len(policy_openapi_specs)} types found")
