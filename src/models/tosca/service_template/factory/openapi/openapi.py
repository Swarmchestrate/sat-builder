"""
TOSCA to OpenAPI Schema Converter

Converts TOSCA node and policy schemas into OpenAPI-compatible schema definitions
for API documentation and validation. Provides utilities for generating OpenAPI
specifications from TOSCA template schemas with automatic file output.

This module provides functionality to:
- Convert TOSCA schemas to OpenAPI format
- Generate OpenAPI specification files
- Save OpenAPI definitions to JSON files

The conversion process transforms TOSCA field definitions into OpenAPI schema
objects that can be used for API documentation, request/response validation,
and client code generation.
"""

import inspect
import json
from typing import Callable, Any, Dict

from src.utils.config import get_config_file_path
from src.utils.logger import (
    get_logger,
    log_function_calls,
    log_file_operations
)
from .converter import convert_tosca_to_openapi

logger = get_logger()


@log_function_calls()
@log_file_operations()
def build_openapi_specs(
        openapi_file_name: str,
        tosca_file_name: str,
        get_schema: Callable[[], Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Convert TOSCA schema to OpenAPI specification format with file output.

    Retrieves TOSCA schema using the provided schema function, converts it to
    OpenAPI format using the converter module, and saves the result to a JSON
    file in the configuration directory.
    """

    function_name = inspect.currentframe().f_code.co_name
    # Get the source TOSCA schema using the provided function
    schema = get_schema()

    # Convert TOSCA schema to OpenAPI format
    openapi = convert_tosca_to_openapi(schema)

    output_file = get_config_file_path(tosca_file_name).parent / openapi_file_name
    with open(output_file, "w") as f:
        json.dump(openapi, f, indent=2)
        logger.debug(f"{function_name}: OpenAPI specification saved at {output_file}")

    return openapi
