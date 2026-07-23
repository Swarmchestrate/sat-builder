"""Application Configuration Settings

Individual configuration modules using singleton pattern for consistent
environment-based configuration across the application.
"""

from .cors import get_cors_settings
from .logger import get_logger_settings
from .server import get_server_settings
from .service import get_service_settings

__all__ = [
    "get_server_settings",
    "get_cors_settings",
    "get_logger_settings",
    "get_service_settings"
]
