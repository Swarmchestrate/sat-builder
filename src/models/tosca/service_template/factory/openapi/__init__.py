"""TOSCA to OpenAPI conversion utilities.

Provides functions for converting TOSCA schemas to OpenAPI specifications
for API documentation and validation purposes.
"""

from .openapi import build_openapi_specs

__all__ = ["build_openapi_specs"]
