"""Application-wide access to the loaded profile."""
from pathlib import Path
from typing import Any, Tuple

from src.models.settings import get_profile_settings
from src.utils.logger import get_logger

from .fetcher import ensure_profile
from .resolver import Profile, load_profile

logger = get_logger()

_profile_instance: Profile | None = None
_profile_signature: Tuple[Any, ...] | None = None


def get_profile(force_refresh: bool = False) -> Profile:
    """Get the profile, re-reading it when the published copy has changed.

    Called on every request that builds a document. The cost of that is bounded
    twice over: the fetcher only contacts the network once per
    PROFILE__REFRESH_SECONDS, and an unchanged profile answers with a 304 per
    file. The parsed profile is only rebuilt when the files on disk differ, so a
    steady state costs a handful of stat calls.
    """
    global _profile_instance, _profile_signature

    settings = get_profile_settings()
    if settings.source.startswith(("http://", "https://")):
        directory = ensure_profile(
            settings.source,
            settings.cache_dir,
            0 if force_refresh else settings.refresh_seconds,
            settings.offline,
        )
    else:
        directory = Path(settings.source)

    signature = _signature(directory)
    if _profile_instance is not None and not force_refresh and signature == _profile_signature:
        return _profile_instance

    if _profile_instance is not None:
        logger.info("get_profile: profile changed on disk, reloading")
    _profile_instance = load_profile(directory)
    _profile_signature = signature
    return _profile_instance


def _signature(directory: Path) -> Tuple[Any, ...]:
    """Cheap fingerprint of the profile files, to detect a changed copy."""
    return tuple(sorted(
        (path.name, path.stat().st_mtime_ns, path.stat().st_size)
        for path in Path(directory).glob("*.yaml")
    ))
