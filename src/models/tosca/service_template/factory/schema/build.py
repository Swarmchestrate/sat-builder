"""
TOSCA Schema Extractor

Extracts and merges schema information from YAML configuration files.
Processes all nested levels and combines similar structures into unified schemas.

This module provides functionality to:
- Extract schema information from TOSCA definitions
- Merge schemas from multiple definitions of the same type
- Collect constraints
- Generate JSON output
"""

import inspect
import json
from typing import Any, Dict

from src.utils.config import get_config, get_config_file_path
from src.utils.logger import (
    get_logger,
    log_function_calls,
    log_file_operations
)
from .build_constraints import build_constraints
from .build_schema import build_schema

logger = get_logger()


@log_function_calls()
@log_file_operations()
def build_tosca_schema(
        tosca_file_name: str,
        tosca_component: str,
        path: list[str],
        schema_file_name: str
) -> Dict[str, Any]:
    """Extract the unified schema from all TOSCA definitions."""
    function_name = inspect.currentframe().f_code.co_name

    # Load TOSCA templates from configuration
    templates, tosca_document = get_config(path, tosca_file_name)

    # Process each template and collect schemas and constraints
    schema = build_schema(templates)
    constraints_document = tosca_document[f"{tosca_component}_constraints"]
    constraints = build_constraints(templates, constraints_document)

    result = {
        f'{tosca_component}_types': list(schema.keys()),
        'schema': schema,
        'constraints': constraints
    }

    output_file = get_config_file_path(tosca_file_name).parent / schema_file_name
    with open(output_file, "w") as f:
        json.dump(result, f, indent=2)
        logger.debug(f"{function_name}: Schema saved at {output_file}")

    return result
