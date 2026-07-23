"""Info router."""
from fastapi import APIRouter
from fastapi.responses import Response

from src.models.app import get_router_path, get_router_summary, get_router_description
from src.models.responses import InfoResponse
from src.models.settings import get_server_settings
from src.utils.logger import get_logger, log_api_calls, log_performance

logger = get_logger()

logger.info("="*60)
logger.info(f"Router configuration INFO initiated")

# Get config once at module level
info_path = get_router_path("info")
info_summary = get_router_summary("info")
info_description = get_router_description("info")
server_settings = get_server_settings()

# noinspection HttpUrlsUsage
# pylint: disable=consider-using-https-url
logger.info(f"Router configuration INFO: http://{server_settings.host}:{server_settings.port}{info_path}")
router = APIRouter()


@log_api_calls()
@log_performance()
@router.get(
    info_path,
    response_model=InfoResponse,
    summary=info_summary,
    description=info_description,
    tags=["info"]
)
async def info() -> InfoResponse:
    """Info endpoint with API information."""
    return InfoResponse()


@log_api_calls()
@log_performance()
@router.get("/favicon.ico", include_in_schema=False)
async def favicon() -> Response:
    """Return an empty favicon to stop browser requests."""
    return Response(status_code=204)  # No Content


logger.info(f"Router configuration INFO complete")
logger.info("="*60)
