"""Health router."""
from fastapi import APIRouter

from src.models.app import get_router_path, get_router_summary, get_router_description
from src.models.responses import HealthResponse
from src.models.settings import get_server_settings
from src.utils.logger import get_logger, log_api_calls, log_performance

logger = get_logger()

logger.info("="*60)
logger.info(f"Router configuration HEALTH initiated")

# Get config once at module level
health_path = get_router_path("health")
health_summary = get_router_summary("health")
health_description = get_router_description("health")
server_settings = get_server_settings()

# noinspection HttpUrlsUsage
# pylint: disable=consider-using-https-url
logger.info(f"Router configuration HEALTH: http://{server_settings.host}:{server_settings.port}{health_path}")
router = APIRouter()


@log_api_calls()
@log_performance()
@router.get(
    health_path,
    response_model=HealthResponse,
    summary=health_summary,
    description=health_description,
    tags=["health"]
)
async def health_check() -> HealthResponse:
    """Health check endpoint to verify API is running."""
    return HealthResponse()


logger.info(f"Router configuration HEALTH complete")
logger.info("="*60)