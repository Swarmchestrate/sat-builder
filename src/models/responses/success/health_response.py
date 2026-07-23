import time
from datetime import datetime, UTC
from typing import Optional

from pydantic import BaseModel, Field

from src.models.app import get_health_config

APP_START_TIME = time.time()

health_cfg = get_health_config()


def calculate_uptime() -> str:
    """Calculate uptime since application start."""
    uptime_seconds = int(time.time() - APP_START_TIME)

    days = uptime_seconds // 86400
    hours = (uptime_seconds % 86400) // 3600
    minutes = (uptime_seconds % 3600) // 60

    if days > 0:
        return f"{days}d {hours}h {minutes}m"
    elif hours > 0:
        return f"{hours}h {minutes}m"
    else:
        return f"{minutes}m"


class HealthResponse(BaseModel):
    """Health check response model."""

    service: str = Field(default_factory=lambda: health_cfg["service"], description="Service name")
    version: str = Field(default_factory=lambda: health_cfg["version"], description="API version")
    status: str = Field(default="healthy", description="Service health status")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Response timestamp")
    uptime: Optional[str] = Field(default_factory=calculate_uptime, description="Service uptime")

    model_config = {
        "json_schema_extra": {
            "example": {
                "service": "Swarmchestrate Application Template Builder API",
                "version": "1.0.0",
                "status": "healthy",
                "timestamp": "2024-01-01T12:00:00Z",
                "uptime": "2d 3h 45m"
            }
        }
    }
