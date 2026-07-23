"""TOSCA Schema Extractor - Dynamic Factory"""

import inspect
from typing import Any, Dict, List

from src.utils.logger import (
    get_logger,
    enable_debug_mode,
    log_function_calls,
    log_cache_operations
)
from .schema import build_tosca_schema

logger = get_logger()

# Module-level cache for schema data - keyed by (tosca_component, file_name) tuple
_CACHED_SCHEMAS: Dict[tuple[str, str], Dict[str, Any]] = {}


@log_function_calls()
@log_cache_operations()
def _get_schema(
        tosca_file_name: str,
        tosca_component: str,
        path: List[str]
) -> Dict[str, Any]:
    """Extract unified schema from TOSCA components dynamically.

    Args:
        tosca_file_name: Name of the TOSCA configuration file
        tosca_component: Component of TOSCA component (e.g., 'node', 'policy')
        path: Path to the component in TOSCA structure (e.g., ['service_template', 'node_templates'])

    Returns:
        Dictionary containing the extracted and unified schema
    """
    # noinspection DuplicatedCode
    function_name = inspect.currentframe().f_code.co_name

    # Use composite cache key for different component/file combinations
    cache_key = (tosca_component, tosca_file_name)

    if cache_key in _CACHED_SCHEMAS:
        logger.debug(
            f"{function_name}: Schema cache hit for '{tosca_component}' in '{tosca_file_name}'")
        return _CACHED_SCHEMAS[cache_key]

    logger.debug(
        f"{function_name}: Schema cache miss for '{tosca_component}' in '{tosca_file_name}', building...")

    # Generate schema file name based on input parameters
    schema_file_name = f"{tosca_file_name}_{tosca_component}_schema.json"

    _CACHED_SCHEMAS[cache_key] = build_tosca_schema(
        tosca_file_name=tosca_file_name,
        tosca_component=tosca_component,
        path=path,
        schema_file_name=schema_file_name,
    )

    logger.debug(
        f"{function_name}: Schema cached for '{tosca_component}' in '{tosca_file_name}'")

    return _CACHED_SCHEMAS[cache_key]


def get_node_schema(tosca_file_name: str) -> Dict[str, Any]:
    """Extract the unified schema from all TOSCA nodes."""
    return _get_schema(
        tosca_file_name=tosca_file_name,
        tosca_component="node",
        path=["service_template", "node_templates"]
    )


def get_policy_schema(tosca_file_name: str) -> Dict[str, Any]:
    """Extract the unified schema from all TOSCA policies."""
    return _get_schema(
        tosca_file_name=tosca_file_name,
        tosca_component="policy",
        path=["service_template", "policies"]
    )


if __name__ == "__main__":
    """Test schema extraction for both node and policy types when run as script."""

    enable_debug_mode()

    test_files = ["tosca_application_template", "tosca_capacity_template"]

    for file_name in test_files:
        logger.debug(f"__main__: Node Schema Extraction Started for '{file_name}'")
        node_schema = get_node_schema(file_name)
        logger.debug(f"__main__: Node Schema Extraction Completed for '{file_name}'. "
                     f"Schema saved and {len(node_schema)} types found")

        logger.debug(f"__main__: Policy Schema Extraction Started for '{file_name}'")
        policy_schema = get_policy_schema(file_name)
        logger.debug(f"__main__: Policy Schema Extraction Completed for '{file_name}'. "
                     f"Schema saved and {len(policy_schema)} types found")
