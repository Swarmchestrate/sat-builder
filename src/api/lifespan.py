"""FastAPI application lifespan management.

Provides the context manager for handling FastAPI application startup and shutdown events.
Manages application lifecycle logging and displays key configuration information
during the startup phase.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.models.app import get_lifespan_config
from src.utils.logger import get_logger

logger = get_logger()


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Manage FastAPI application startup and shutdown events.
    
    Handles the application lifecycle by logging startup configuration details
    and shutdown confirmation. Displays application title, version, and
    documentation URLs during the startup phase.
    
    Args:
        _: FastAPI application instance (unused but required by FastAPI)
        
    Yields:
        None: Context manager yields control to application runtime
    """
    lifespan_cfg = get_lifespan_config()
    # Startup
    logger.info("=" * 80)
    logger.info(f"Starting {lifespan_cfg['title']}")
    logger.info(f"Version: {lifespan_cfg['version']}")
    logger.info(f"Swagger UI: {lifespan_cfg['docs_url']}")
    logger.info(f"ReDoc Documentation: {lifespan_cfg['redoc_url']}")
    logger.info(f"OpenAPI Schema: {lifespan_cfg['openapi_url']}")
    logger.info("=" * 80)

    yield

    # Shutdown
    logger.info("=" * 80)
    logger.info("Shutting down application")
    logger.info("=" * 80)
