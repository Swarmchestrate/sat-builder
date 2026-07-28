"""Application-wide access to the loaded profile."""
from src.models.settings import get_profile_settings
from src.utils.logger import get_logger

from .resolver import Profile, load_profile

logger = get_logger()

_profile_instance: Profile | None = None


def get_profile(force_refresh: bool = False) -> Profile:
    """Get the profile, loading it from the configured source on first use.

    The underlying loader throttles its own update checks, so calling this on
    every request is cheap; force_refresh bypasses the cached instance when the
    profile needs re-reading immediately.
    """
    global _profile_instance
    if _profile_instance is not None and not force_refresh:
        return _profile_instance

    settings = get_profile_settings()
    _profile_instance = load_profile(
        settings.source,
        cache_dir=settings.cache_dir,
        refresh_seconds=settings.refresh_seconds,
        offline=settings.offline,
    )
    return _profile_instance
