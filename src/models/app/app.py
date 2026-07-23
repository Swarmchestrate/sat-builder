"""FastAPI Application Configuration Management.

This module provides centralized configuration management for FastAPI applications
through YAML-based configuration loading and Pydantic validation. It handles all
aspects of application setup. Including metadata, routing, Swagger UI customization,
and TOSCA type definitions.
"""
import inspect
import json
from typing import Dict, Any, Tuple, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict, YamlConfigSettingsSource, PydanticBaseSettingsSource

from src.utils.logger import get_logger
from src.utils.project import get_project_root
from .metadata import Metadata
from .routers import Routers, Router
from .swagger import Swagger
from .tags import Tags
from .tosca_types import ToscaTypes
from .urls import URLs
from .validation import Validation

logger = get_logger()


class App(BaseSettings):
    """FastAPI application configuration loaded from app.yaml.

    Provides centralized configuration management for the entire FastAPI application,
    including metadata, routing, Swagger UI settings, and TOSCA type definitions.
    Configuration is loaded from YAML and validated using Pydantic models.

    Attributes:
        metadata: Application metadata (title, version, description, license, contact)
        swagger: Swagger UI configuration settings
        tosca_types: Available TOSCA type definitions
        urls: API endpoint URL configurations
        tags: OpenAPI tag definitions for documentation
        routers: Router configuration mappings
    """

    model_config = SettingsConfigDict(
        case_sensitive=False,
        extra="forbid",
        yaml_file=str(get_project_root() / "configs" / "app.yaml"),
        yaml_file_encoding="utf-8",
    )

    metadata: Metadata
    swagger: Swagger
    tosca_types: ToscaTypes
    urls: URLs
    tags: Tags
    routers: Routers
    validation: Validation

    @classmethod
    def settings_customise_sources(
            cls,
            settings_cls: type[BaseSettings],
            init_settings: PydanticBaseSettingsSource,
            env_settings: PydanticBaseSettingsSource,
            dotenv_settings: PydanticBaseSettingsSource,
            file_secret_settings: PydanticBaseSettingsSource,
    ) -> Tuple[PydanticBaseSettingsSource, ...]:
        """Customize configuration sources to load from YAML only.

        Returns:
            Tuple of configuration sources with YAML as the primary source
        """
        return init_settings, YamlConfigSettingsSource(settings_cls)

    def get_fastapi_config(self) -> Dict[str, Any]:
        """Get FastAPI application configuration dictionary.

        Returns:
            Configuration dict with title, version, description, license info,
            contact details, URL paths, and OpenAPI tags for FastAPI initialization
        """
        return {
            "title": self.metadata.title,
            "version": self.metadata.version,
            "description": self.metadata.description,
            "license_info": self.metadata.license.model_dump() if self.metadata.license else None,
            "contact": self.metadata.contact.model_dump() if self.metadata.contact else None,
            "openapi_url": self.urls.openapi_url,
            "docs_url": self.urls.docs_url,
            "redoc_url": self.urls.redoc_url,
            "openapi_tags": self.tags.get_openapi_tags(),
        }

    def get_swagger_config(self) -> Dict[str, Any]:
        """Get Swagger UI configuration dictionary.

        Returns:
            Configuration dict with UI display options, interaction settings,
            and supported HTTP methods for the Swagger documentation interface
        """
        return {
            "deepLinking": self.swagger.deep_linking,
            "displayRequestDuration": self.swagger.display_request_duration,
            "filter": self.swagger.filter,
            "tryItOutEnabled": self.swagger.try_it_out_enabled,
            "supportedSubmitMethods": self.swagger.supported_submit_methods,
        }

    def get_router_config(self, router_name: str) -> Router:
        """Get configuration for a specific router by name.

        Args:
            router_name: Name of the router to retrieve configuration for

        Returns:
            Router configuration object containing path and tag information

        Raises:
            AttributeError: If router_name does not exist in configuration
        """
        return getattr(self.routers, router_name)

    def get_router_path(self, router_name: str) -> str:
        """Get the URL path for a specific router.

        Args:
            router_name: Name of the router to get the path for

        Returns:
            URL path string for the specified router

        Raises:
            AttributeError: If router_name does not exist in configuration
        """
        router = getattr(self.routers, router_name)
        return router.path

    def get_router_summary(self, router_name: str) -> str:
        """Get the summary for a router from its referenced tag.

        Args:
            router_name: Name of the router to get summary for

        Returns:
            Summary text from the router's associated tag

        Raises:
            AttributeError: If router_name or its tag does not exist
        """
        router = getattr(self.routers, router_name)
        tag_dict = getattr(self.tags, router.tag)
        return tag_dict["name"]

    def get_router_description(self, router_name: str) -> str:
        """Get the description for a router from its referenced tag.

        Args:
            router_name: Name of the router to get description for

        Returns:
            Description text from the router's associated tag

        Raises:
            AttributeError: If router_name or its tag does not exist
        """
        router = getattr(self.routers, router_name)
        tag_dict = getattr(self.tags, router.tag)
        return tag_dict["description"]

    def get_tosca_types(self) -> ToscaTypes:
        """Get available TOSCA types configuration.

        Returns:
            ToscaTypes object containing all available TOSCA type definitions
        """
        return self.tosca_types

    def get_lifespan_config(self) -> Dict[str, str]:
        """Get configuration data needed for application lifespan management.

        Returns:
            Dictionary with application metadata and URL paths needed
            during startup and shutdown phases
        """
        return {
            "title": self.metadata.title,
            "version": self.metadata.version,
            "docs_url": self.urls.docs_url or "",
            "redoc_url": self.urls.redoc_url or "",
            "openapi_url": self.urls.openapi_url or ""
        }

    def get_health_config(self) -> Dict[str, str]:
        """Get configuration data needed for health check responses.

        Returns:
            Dictionary with service name and version for health endpoints
        """
        return {
            "service": self.metadata.title,
            "version": self.metadata.version
        }

    def get_info_config(self) -> Dict[str, Any]:
        """Get configuration data needed for application info responses.

        Returns:
            Dictionary with complete application metadata including title,
            version, description, license, contact, and documentation URLs
        """
        return {
            "title": self.metadata.title,
            "version": self.metadata.version,
            "description": self.metadata.description,
            "license": self.metadata.license.model_dump() if self.metadata.license else {},
            "contact": self.metadata.contact.model_dump() if self.metadata.contact else {},
            "docs": self.urls.docs_url,
            "redoc": self.urls.redoc_url,
            "openapi": self.urls.openapi_url
        }

    def get_validation_config(self) -> Dict[str, bool]:
        """Get validation feature flags configuration.

        Returns:
            Dictionary with validation options enabling validation features
            based on templates and/or sardou.
        """
        return {
            "sardou": self.validation.sardou,
        }


_app_instance: Optional[App] = None


def _get_app_config() -> App:
    """Get the singleton App configuration instance.

    Creates a new App instance on the call and returns the cached instance
    on later calls. This ensures a single source of configuration truth.

    Returns:
        App: Singleton App configuration instance

    Note:
        This is a private function - use the public API functions instead
    """
    # noinspection PyUnresolvedReferences
    function_name = inspect.currentframe().f_code.co_name
    global _app_instance
    app_instance = _app_instance
    if app_instance is None:
        logger.debug(f"{function_name}: initializing singleton instance")
        app_instance = App()
        _app_instance = app_instance
        logger.debug(f"{function_name}:\n{json.dumps(app_instance.model_dump(exclude_none=True), indent=2)}")
    return app_instance


# Public API functions
def get_fastapi_config() -> Dict[str, Any]:
    """Get FastAPI application configuration dictionary.

    Public API function that returns configuration suitable for FastAPI
    application initialization including metadata, URLs, and OpenAPI settings.

    Returns:
        Dictionary with FastAPI configuration parameters
    """
    # noinspection PyUnresolvedReferences
    function_name = inspect.currentframe().f_code.co_name
    fastapi_config = _get_app_config().get_fastapi_config()
    logger.debug(f"{function_name}:\n{json.dumps(fastapi_config, indent=2)}")
    return fastapi_config


def get_swagger_config() -> Dict[str, Any]:
    """Get Swagger UI configuration dictionary.

    Public API function that returns Swagger UI customization parameters
    for enhanced API documentation interface.

    Returns:
        Dictionary with Swagger UI configuration parameters
    """
    # noinspection PyUnresolvedReferences
    function_name = inspect.currentframe().f_code.co_name
    swagger_config = _get_app_config().get_swagger_config()
    logger.debug(f"{function_name}:\n{json.dumps(swagger_config, indent=2)}")
    return swagger_config


def get_router_config(router_name: str) -> Router:
    """Get configuration for a specific router.

    Public API function that retrieves router configuration by name
    including path and tag information.

    Args:
        router_name: Name of the router to retrieve

    Returns:
        Router configuration object

    Raises:
        AttributeError: If router_name does not exist
    """
    # noinspection PyUnresolvedReferences
    function_name = inspect.currentframe().f_code.co_name
    router_config = _get_app_config().get_router_config(router_name)
    logger.debug(f"{function_name}:\nRouter {router_name}: {json.dumps(router_config.model_dump(), indent=2)}")
    return router_config


def get_router_path(router_name: str) -> str:
    """Get the URL path for a specific router.

    Public API function that retrieves the URL path for a named router.

    Args:
        router_name: Name of the router to get the path for

    Returns:
        URL path string

    Raises:
        AttributeError: If router_name does not exist
    """
    # noinspection PyUnresolvedReferences
    function_name = inspect.currentframe().f_code.co_name
    router_path = _get_app_config().get_router_path(router_name)
    logger.debug(f"{function_name}:\nRouter {router_name}: {router_path}")
    return router_path


def get_router_summary(router_name: str) -> str:
    """Get the summary text for a router.

    Public API function that retrieves the summary from a router's
    associated tag configuration.

    Args:
        router_name: Name of the router to get summary for

    Returns:
        Router summary text

    Raises:
        AttributeError: If router_name or its tag does not exist
    """
    # noinspection PyUnresolvedReferences
    function_name = inspect.currentframe().f_code.co_name
    router_summary = _get_app_config().get_router_summary(router_name)
    logger.debug(f"{function_name}:\nRouter {router_name}: {router_summary}")
    return router_summary


def get_router_description(router_name: str) -> str:
    """Get the description text for a router.

    Public API function that retrieves the description from a router's
    associated tag configuration.

    Args:
        router_name: Name of the router to get description for

    Returns:
        Router description text

    Raises:
        AttributeError: If router_name or its tag does not exist
    """
    # noinspection PyUnresolvedReferences
    function_name = inspect.currentframe().f_code.co_name
    router_description = _get_app_config().get_router_description(router_name)
    logger.debug(f"{function_name}:\nRouter {router_name}: {router_description}")
    return router_description


def get_tosca_types() -> ToscaTypes:
    """Get the list of available TOSCA types.

    Public API function that retrieves all configured TOSCA type definitions
    for use in template validation and API generation.

    Returns:
        List of available TOSCA type names
    """
    # noinspection PyUnresolvedReferences
    function_name = inspect.currentframe().f_code.co_name
    tosca_types = _get_app_config().get_tosca_types()
    logger.debug(f"{function_name}:\n{json.dumps(tosca_types.model_dump(), indent=2)}")
    return tosca_types


def get_lifespan_config() -> Dict[str, str]:
    """Get configuration data for application lifespan management.

    Public API function that retrieves configuration needed during
    application startup and shutdown phases.

    Returns:
        Dictionary with application metadata and URL paths
    """
    # noinspection PyUnresolvedReferences
    function_name = inspect.currentframe().f_code.co_name
    lifespan_config = _get_app_config().get_lifespan_config()
    logger.debug(f"{function_name}:\n{json.dumps(lifespan_config, indent=2)}")
    return lifespan_config


def get_health_config() -> Dict[str, str]:
    """Get configuration data for health check endpoints.

    Public API function that retrieves service metadata needed
    for health check and monitoring endpoints.

    Returns:
        Dictionary with service name and version
    """
    # noinspection PyUnresolvedReferences
    function_name = inspect.currentframe().f_code.co_name
    health_config = _get_app_config().get_health_config()
    logger.debug(f"{function_name}:\n{json.dumps(health_config, indent=2)}")
    return health_config


def get_info_config() -> Dict[str, Any]:
    """Get configuration data for application info endpoints.

    Public API function that retrieves complete application metadata
    for info and root endpoints including documentation URLs.

    Returns:
        Dictionary with comprehensive application information
    """
    # noinspection PyUnresolvedReferences
    function_name = inspect.currentframe().f_code.co_name
    info_config = _get_app_config().get_info_config()
    logger.debug(f"{function_name}:\n{json.dumps(info_config, indent=2)}")
    return info_config


def get_validation_config() -> Dict[str, bool]:
    """Get validation feature flags configuration.

    Public API function that retrieves validation feature flags configuration
    based on templates and/or sardou.

    Returns:
        Dictionary with validation options enabling validation features
    """
    # noinspection PyUnresolvedReferences
    function_name = inspect.currentframe().f_code.co_name
    validation_config = _get_app_config().get_validation_config()
    logger.debug(f"{function_name}:\n{json.dumps(validation_config, indent=2)}")
    return validation_config
