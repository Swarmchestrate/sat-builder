"""FastAPI application configuration utilities and models.

Provides comprehensive configuration management for FastAPI applications through
validated Pydantic models loaded from YAML configuration files. Includes all
essential configuration functions and router model classes for building robust,
enterprise-grade FastAPI applications.

This module serves as the main entry point for:
- YAML-based application configuration loading
- FastAPI instance configuration and setup
- Router and endpoint configuration with validation
- Swagger UI and OpenAPI customization
- Application lifecycle management utilities
"""

# Configuration functions for FastAPI application setup
from .app import (
    get_fastapi_config,          # FastAPI app configuration (title, version, etc.)
    get_swagger_config,          # Swagger UI customization parameters
    get_router_config,           # Individual router configuration by name
    get_router_path,             # Router URL path retrieval
    get_router_summary,          # Router summary from associated tags
    get_router_description,      # Router description from associated tags
    get_lifespan_config,         # Application lifecycle configuration
    get_health_config,           # Health endpoint configuration
    get_info_config,             # Info endpoint configuration
    get_tosca_types,             # Available TOSCA type definitions
    get_validation_config        # TOSCA template validation configuration
)

__all__ = [
    # Configuration Functions
    "get_fastapi_config",        # Load FastAPI app settings from YAML
    "get_swagger_config",        # Load Swagger UI customization settings
    "get_router_config",         # Get router configuration by name
    "get_router_path",           # Get router URL path
    "get_router_summary",        # Get router summary text
    "get_router_description",    # Get router description text
    "get_lifespan_config",       # Get app lifecycle configuration
    "get_health_config",         # Get health check configuration
    "get_info_config",           # Get info endpoint configuration
    "get_tosca_types",           # Get all available TOSCA type list
    "get_validation_config"      # Get TOSCA template validation configuration
]