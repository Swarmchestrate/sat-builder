"""FastAPI Application Factory and Configuration.

This module creates and configures the main FastAPI application instance with
all necessary middleware, routers, and settings. It serves as the entry point
for the web application and handles the complete application lifecycle.

The application includes:
- CORS middleware configuration
- Dynamic TOSCA router generation
- Health and info endpoints
- Comprehensive logging throughout the startup process for monitoring and debugging
"""
import inspect
import json
from typing import List, Tuple, cast, Any

from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware

from src.models.app import get_fastapi_config, get_swagger_config
from src.models.settings import get_cors_settings
from src.utils.logger import get_logger
from .lifespan import lifespan
from .routers import info_router, health_router, tosca_routers

logger = get_logger()


def _create_fastapi_app() -> FastAPI:
    """Create and configure the complete FastAPI application instance.

    This factory function orchestrates the entire application creation process through
    a series of well-defined steps. Each step is logged for monitoring and debugging
    purposes, ensuring full visibility into the application startup sequence.

    The creation process follows this sequence:
    1. Create the FastAPI instance
    2. Configure CORS middleware
    3. Register core application routers (health checks, info endpoints)
    4. Register dynamically generated TOSCA-related routers

    Returns:
        FastAPI: Fully configured FastAPI application instance ready for ASGI server
                deployment. The instance includes all middleware, routers, and
                lifecycle handlers configured according to application settings.

    Raises:
        RuntimeError: When required configuration sections are missing or invalid,
                     preventing proper application initialization.
        FileNotFoundError: When required, template or configuration files cannot
                          be found in the expected locations.
        ValidationError: When configuration values fail validation checks.
    """
    # noinspection PyUnresolvedReferences
    function_name = inspect.currentframe().f_code.co_name

    # Log application creation starts with visual separator for easy log parsing
    logger.info("=" * 60)
    logger.info("Starting FastAPI application creation process")
    logger.info("=" * 60)

    # Step 1: Create the core FastAPI application instance
    # Configuration is loaded internally within the function
    logger.debug(f"{function_name}: Beginning FastAPI instance creation phase")
    fastapi_app = _create_fastapi_instance()
    logger.debug(f"{function_name}: FastAPI instance creation phase completed successfully")

    # Step 2: Configure Cross-Origin Resource Sharing (CORS) middleware
    # CORS settings are loaded internally within the function
    logger.debug(f"{function_name}: Beginning CORS middleware configuration phase")
    _enable_cors(fastapi_app)
    logger.debug(f"{function_name}: CORS middleware configuration phase completed successfully")

    # Step 3: Register all application routers in an organized manner
    # Includes both static core routers and dynamically generated TOSCA routers
    logger.info("Registering application routers and their endpoints...")

    # Register essential core application routers (health checks, info endpoints)
    logger.debug(f"{function_name}: Starting core router registration")
    core_routers = _register_core_routers(fastapi_app)
    logger.debug(f"{function_name}: Core router registration completed - {len(core_routers)} routers registered")

    # Register dynamically generated TOSCA-related routers for domain-specific functionality
    logger.debug(f"{function_name}: Starting TOSCA router registration")
    _register_tosca_routers(fastapi_app)
    logger.debug(f"{function_name}: TOSCA router registration completed - {len(tosca_routers)} routers registered")

    # Step 4: Log a comprehensive final application state for deployment verification
    total_routers = len(core_routers) + len(tosca_routers)
    logger.info(f"Successfully registered {total_routers} routers")

    # Final success confirmation with visual separators for log readability
    logger.info("=" * 60)
    logger.info("FastAPI application creation completed successfully")
    logger.info("Application is ready for ASGI server deployment")
    logger.info("=" * 60)

    return fastapi_app


def _create_fastapi_instance() -> FastAPI:
    """Create the core FastAPI application instance.

    Loads FastAPI and Swagger UI configuration internally and creates a new FastAPI
    application instance. This function handles the low-level FastAPI instantiation
    with custom Swagger UI parameters and application lifecycle handlers.

    Returns:
        FastAPI: Configured FastAPI application instance with:
                - Custom application metadata from the loaded configuration
                - Swagger UI parameters from loaded configuration
                - Lifespan event handlers for startup/shutdown

    Raises:
        TypeError: When configuration dictionaries contain invalid parameter types
        ValueError: When required configuration keys are missing
        FileNotFoundError: When required configuration files cannot be found
    """
    # noinspection PyUnresolvedReferences
    function_name = inspect.currentframe().f_code.co_name
    logger.info("Creating FastAPI application instance with Swagger UI integration and startup/shutdown handlers...")

    # Load FastAPI core configuration (title, version, description, etc.)
    logger.debug(f"{function_name}: Loading FastAPI core configuration settings")
    fastapi_cfg = get_fastapi_config()
    logger.debug(f"{function_name}: FastAPI configuration loaded\n'{json.dumps(fastapi_cfg, indent=2)}'")

    # Load Swagger UI customization parameters for API documentation
    logger.debug(f"{function_name}: Loading Swagger UI configuration parameters")
    swagger_cfg = get_swagger_config()
    logger.debug(f"{function_name}: Swagger UI configuration loaded\n'{json.dumps(swagger_cfg, indent=2)}'")

    # Log configuration details being applied for debugging
    logger.debug(f"{function_name}: Applying FastAPI configuration - {len(fastapi_cfg)} parameters")
    logger.debug(f"{function_name}: Applying Swagger UI configuration - {len(swagger_cfg)} parameters")
    logger.debug(f"{function_name}: Attaching lifespan event handlers for application lifecycle management")

    # Create the FastAPI instance with all configuration parameters
    fastapi_app = FastAPI(
        **fastapi_cfg,  # Includes title, version, description, etc.
        swagger_ui_parameters=swagger_cfg,  # Custom Swagger UI settings for documentation
        lifespan=lifespan  # Application startup/shutdown event handlers
    )
    logger.info(f"{fastapi_cfg['title']} v{fastapi_cfg['version']}")

    logger.info("FastAPI application instance created successfully")

    return fastapi_app


def _enable_cors(fastapi_app: FastAPI):
    """Configure CORS (Cross-Origin Resource Sharing) middleware for the application.

    Loads CORS settings internally and conditionally adds CORS middleware to the
    FastAPI application. When enabled, configures allowed origins, methods, headers,
    and credential handling according to the security requirements.

    CORS middleware is essential for web applications that need to serve requests
    from different origins (domains, protocols, or ports). This function provides
    centralized CORS configuration management.

    Args:
        fastapi_app: FastAPI application instance to configure with CORS middleware

    Returns:
        None: Function modifies the FastAPI app in-place by adding middleware

    Side Effects:
        - Adds CORSMiddleware to the FastAPI application when CORS is enabled
        - Logs the CORS configuration status for monitoring

    Raises:
        FileNotFoundError: When CORS configuration files cannot be found
        ValidationError: When CORS configuration contains invalid values
    """
    # noinspection PyUnresolvedReferences
    function_name = inspect.currentframe().f_code.co_name
    logger.info("Configuring CORS (Cross-Origin Resource Sharing) middleware...")

    # Load CORS settings for cross-origin request handling
    logger.debug(f"{function_name}: Loading CORS (Cross-Origin Resource Sharing) settings")
    cors_settings = get_cors_settings()

    # Debug log CORS settings with formatted JSON for easy troubleshooting
    logger.debug(
        f"{function_name}: CORS settings loaded and validated\n{json.dumps(cors_settings.model_dump(), indent=2)}")

    # Check if CORS is enabled in the configuration
    if cors_settings.enabled:
        logger.debug(f"{function_name}: CORS is enabled - configuring middleware with security settings")

        # Build a comprehensive CORS configuration dictionary from validated settings
        cors_cfg = {
            "allow_origins": cors_settings.origins_list,  # Permitted request origins
            "allow_credentials": cors_settings.allow_credentials,  # Cookie/auth handling
            "allow_methods": cors_settings.methods_list,  # Allowed HTTP methods
            "allow_headers": cors_settings.headers_list,  # Permitted request headers
        }

        # Log detailed CORS configuration for security auditing
        logger.debug(f"{function_name}: CORS configuration details:")
        logger.debug(f"{function_name}:   - Allow origins: {cors_settings.origins_list}")
        logger.debug(f"{function_name}:   - Allow credentials: {cors_settings.allow_credentials}")
        logger.debug(f"{function_name}:   - Allow methods: {cors_settings.methods_list}")
        logger.debug(f"{function_name}:   - Allow headers: {cors_settings.headers_list}")

        # Add CORS middleware to the FastAPI application with configured settings
        fastapi_app.add_middleware(cast(Any, CORSMiddleware), **cors_cfg)

        logger.info(f"CORS middleware enabled for origins: {cors_settings.origins_list}")
    else:
        # CORS is disabled - log for security awareness
        logger.info("CORS middleware disabled by configuration")
        logger.debug(f"{function_name}: Cross-origin requests will be blocked by default browser security")


def _register_core_routers(fastapi_app: FastAPI) -> list[tuple[str, APIRouter]]:
    """Register essential core application routers with the FastAPI instance.

    Adds fundamental application routers that provide basic functionality
    required by all deployments. These routers handle system-level endpoints
    such as health checks and application information.

    Core routers include:
    - INFO router: Provides application metadata and version information
    - HEALTH router: Implements health check endpoints for monitoring

    Args:
        fastapi_app: FastAPI application instance to register routers with

    Returns:
        list[tuple[str, APIRouter]]: List of tuples containing router names
                                    and their corresponding APIRouter instances.
                                    Used for logging and router count tracking.

    Side Effects:
        - Modifies the FastAPI app by including core routers
        - Logs each router registration for monitoring
    """
    # noinspection PyUnresolvedReferences
    function_name = inspect.currentframe().f_code.co_name
    logger.debug(f"{function_name}: Preparing core application routers for registration")

    # Define essential core routers required for basic application functionality
    core_routers: List[Tuple[str, APIRouter]] = [
        ("INFO", info_router),  # Application information and metadata endpoints
        ("HEALTH", health_router),  # Health check and status monitoring endpoints
    ]

    logger.debug(f"{function_name}: {len(core_routers)} core routers prepared for registration")

    # Register each core router with detailed logging for monitoring
    for router_name, router in core_routers:
        logger.info(f"Registering core router: {router_name}")

        # Log router details for debugging
        router_routes = len(router.routes) if hasattr(router, 'routes') else 0
        logger.debug(f"{function_name}: Router '{router_name}' contains {router_routes} routes")

        # Include the router in the FastAPI application
        fastapi_app.include_router(router)

        logger.debug(f"{function_name}: Core router '{router_name}' registered successfully")

    logger.info(f"All {len(core_routers)} core routers registered successfully")
    return core_routers


def _register_tosca_routers(fastapi_app: FastAPI):
    """Register dynamically generated TOSCA-related routers with the FastAPI instance.

    Adds domain-specific routers that handle TOSCA (Topology and Orchestration
    Specification for Cloud Applications) related functionality. These routers
    are generated dynamically based on TOSCA templates and provide endpoints
    for orchestration, deployment, and management operations.

    TOSCA routers handle:
    - Template validation and processing
    - Service orchestration endpoints
    - Deployment management APIs
    - Resource lifecycle operations

    Args:
        fastapi_app: FastAPI application instance to register TOSCA routers with

    Returns:
        None: Function modifies the FastAPI app in-place by including routers

    Side Effects:
        - Modifies the FastAPI app by including dynamically generated routers
        - Logs each TOSCA router registration with type information

    Global Dependencies:
        - tosca_routers: Module-level list of generated TOSCA router instances
    """
    # noinspection PyUnresolvedReferences
    function_name = inspect.currentframe().f_code.co_name
    logger.info("Registering dynamically generated TOSCA-related routers...")

    # Log the number of TOSCA routers available for registration
    logger.debug(f"{function_name}: {len(tosca_routers)} TOSCA routers available for registration")

    # Register each dynamically generated TOSCA router
    for tosca_type, router in tosca_routers:
        logger.info(f"Registering TOSCA router: {tosca_type.upper()}")

        # Log additional router details for debugging and monitoring
        router_routes = len(router.routes) if hasattr(router, 'routes') else 0
        logger.debug(f"{function_name}: TOSCA router '{tosca_type}' contains {router_routes} routes")

        # Include the TOSCA router in the FastAPI application
        fastapi_app.include_router(router)

        logger.debug(f"{function_name}: TOSCA router '{tosca_type.upper()}' registered successfully")

    logger.info(f"All {len(tosca_routers)} TOSCA routers registered successfully")


# Global application instance creation for ASGI server deployment
# This instance is created at module import time and can be imported directly
# by ASGI servers such as uvicorn, gunicorn, or hypercorn for production deployment
logger.info("=" * 60)
logger.info("FastAPI - creating global application instance...")

# Create the production-ready FastAPI application instance
# This instance includes all configured middleware, routers, and lifecycle handlers
app: FastAPI = _create_fastapi_app()

logger.info("FastAPI - global application instance ready for ASGI server")
logger.info("=" * 60)
