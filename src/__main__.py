"""Application Server Entry Point and Configuration.

This module serves as the main entry point for the FastAPI application server.
It handles server initialization, configuration loading, and uvicorn server startup.

The module provides:
- Server configuration loading from application settings
- Service identification and metadata logging
- Uvicorn ASGI server initialization and startup
- Comprehensive startup process logging for monitoring and debugging

Usage:
    python -m src # Start server with default settings
"""
import inspect
import json
import sys
from typing import Dict, Any

import uvicorn

from src.api import app
from src.models.settings import get_server_settings, get_service_settings
from src.utils.logger import get_logger

logger = get_logger()


# noinspection PyUnresolvedReferences
def _load_and_validate_settings() -> tuple[str, Dict[str, Any]]:
    """Load and validate all required server and service settings.
    
    Returns:
        tuple: (service_name, uvicorn_cfg) for uvicorn startup
        
    Raises:
        RuntimeError: When required configuration sections are missing or invalid.
        ValueError: When server settings contain invalid values.
    """
    function_name = inspect.currentframe().f_code.co_name

    logger.info("Loading application settings...")

    # Load service metadata for identification and logging
    service = get_service_settings()
    logger.debug(f"{function_name}: service settings\n{json.dumps(service.model_dump(), indent=2)}")
    service_name = service.name

    # Load server configuration for uvicorn startup
    server = get_server_settings()
    logger.debug(f"{function_name}: server settings\n{json.dumps(server.model_dump(), indent=2)}")
    logger.info(f"Uvicorn - Host: {server.host}")
    logger.info(f"Uvicorn - Port: {server.port}")
    logger.info(f"Uvicorn - Reload: {server.reload}")
    logger.info(f"Uvicorn - Log Level: {server.log_level}")

    # Build uvicorn configuration dictionary
    uvicorn_cfg = {
        "app": "src.api:app" if server.reload else app,  # FastAPI application module path
        "host": server.host,  # Server bind address
        "port": server.port,  # Server listen port
        "reload": server.reload,  # Auto-reload on code changes (development)
        "log_level": server.log_level  # Uvicorn logging verbosity
    }

    # Log config without the app object for JSON serialization
    debug_config = {k: v for k, v in uvicorn_cfg.items() if k != "app"}
    debug_config["app"] = f"{type(app).__name__} instance"
    logger.debug(f"{function_name}: uvicorn configuration\n{json.dumps(debug_config, indent=2)}")

    return service_name, uvicorn_cfg


def _log_startup_banner(service_name: str, uvicorn_cfg: Dict[str, Any]) -> None:
    """Log formatted startup banner.
    
    Args:
        service_name: Name of the service being started
        uvicorn_cfg: Uvicorn server configuration dictionary
    """
    logger.info("=" * 80)
    logger.info("FASTAPI APPLICATION SERVER STARTUP")
    logger.info("=" * 80)
    logger.info(f"Service Name: {service_name}")
    # noinspection HttpUrlsUsage
    # pylint: disable=consider-using-https-url
    logger.info(f"Service URL: http://{uvicorn_cfg['host']}:{uvicorn_cfg['port']}")
    logger.warning("Security: HTTP only - use HTTPS proxy for public deployment")
    logger.info(f"Application type: {type(uvicorn_cfg['app']).__name__}")
    logger.info(f"Development Mode: {'Enabled' if uvicorn_cfg['reload'] else 'Disabled'}")
    logger.info(f"Uvicorn Log Level: {uvicorn_cfg['log_level'].upper()}")
    logger.info("=" * 80)


def init_app() -> None:
    """Initialize and start the FastAPI application server.
    
    This function serves as the main entry point for the application, handling:
    - Configuration loading and validation
    - Service identification and logging
    - Server startup parameter preparation  
    - Uvicorn ASGI server initialization and execution
    
    The function will not return during normal operation as uvicorn.run()
    blocks until the server is shut down.
    
    Raises:
        RuntimeError: When uvicorn configuration is invalid or missing.
        SystemExit: When uvicorn server fails to start or encounters fatal errors.
    """
    # Load and validate all required configuration settings
    service_name, uvicorn_cfg = _load_and_validate_settings()

    # Display a formatted startup information banner
    _log_startup_banner(service_name, uvicorn_cfg)

    # Initialize and start the uvicorn ASGI server
    logger.info("Starting uvicorn ASGI server...")
    logger.info("Note: Uvicorn includes its own logs alongside application logs")
    logger.info("=" * 80)

    # Start uvicorn server
    try:
        uvicorn.run(**uvicorn_cfg)
    except KeyboardInterrupt:
        logger.info("Server shutdown requested by user (Ctrl+C)")
        logger.info("Uvicorn server shutdown complete, exiting application.")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error during server startup: {e}")
        logger.error("Uvicorn server startup failed - check configuration and try again")
        logger.debug("Server startup traceback:", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    init_app()
