"""API routers package."""
from .health_router import router as health_router
from .info_router import router as info_router
from .capacity_router import capacity_router

__all__ = ["health_router", "info_router", "capacity_router"]
