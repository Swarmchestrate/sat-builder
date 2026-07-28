"""Profile fetching and local caching.

The profile is published as an index (profile.yaml) whose imports point at the
component files. All of them are mirrored into a local cache directory, which is
what the resolver actually reads. Refreshes use conditional GETs, so an unchanged
profile costs one 304 per file rather than a re-download.

The cache is also the offline fallback: if the network is unavailable at startup
the service runs on the last known good copy rather than failing to boot.
"""
import json
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import urlparse

import yaml

from src.utils.logger import get_logger

logger = get_logger()

META_FILENAME = ".cache-meta.json"
FETCH_TIMEOUT_SECONDS = 30


def ensure_profile(
        url: str,
        cache_dir: str | Path,
        refresh_seconds: int = 3600,
        offline: bool = False,
) -> Path:
    """Return a local directory holding the profile, refreshing it if stale.

    Args:
        url: URL of the profile index
        cache_dir: Directory to mirror the profile into
        refresh_seconds: Skip the update check if the cache is younger than this
        offline: Never touch the network; requires a populated cache

    Returns:
        Path to the cache directory

    Raises:
        FileNotFoundError: When the cache is empty and the profile cannot be fetched
    """
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    meta = _read_meta(cache_dir)

    if offline:
        _require_populated(cache_dir, reason="offline mode is enabled")
        logger.info(f"ensure_profile: offline, using cached profile in {cache_dir}")
        return cache_dir

    age = time.time() - meta.get("checked_at", 0)
    if meta.get("files") and age < refresh_seconds:
        logger.debug(f"ensure_profile: cache checked {int(age)}s ago, skipping update check")
        return cache_dir

    try:
        _refresh(url, cache_dir, meta)
    except (urllib.error.URLError, urllib.error.HTTPError, OSError) as error:
        # A failed refresh must not take the service down when a cache exists.
        _require_populated(cache_dir, reason=f"profile could not be fetched ({error})")
        logger.warning(f"ensure_profile: refresh failed ({error}), using cached profile")

    return cache_dir


def _refresh(index_url: str, cache_dir: Path, meta: Dict[str, Any]) -> None:
    """Fetch the index and every file it imports, updating only what changed."""
    files: Dict[str, Any] = meta.get("files", {})

    index_body, index_meta = _conditional_get(index_url, files.get(index_url, {}))
    if index_body is not None:
        _write(cache_dir, index_url, index_body)
        files[index_url] = index_meta
        index_document = yaml.safe_load(index_body) or {}
    else:
        index_document = yaml.safe_load(_read(cache_dir, index_url)) or {}

    changed = 0 if index_body is None else 1

    for import_url in _imported_urls(index_document, index_url):
        body, entry = _conditional_get(import_url, files.get(import_url, {}))
        if body is not None:
            _write(cache_dir, import_url, body)
            files[import_url] = entry
            changed += 1

    _write_meta(cache_dir, {"index": index_url, "files": files, "checked_at": time.time()})
    logger.info(
        f"ensure_profile: checked {len(files)} profile file(s), {changed} updated -> {cache_dir}"
    )


def _conditional_get(url: str, previous: Dict[str, Any]) -> tuple[bytes | None, Dict[str, Any]]:
    """GET a URL unless it is unchanged. Returns (body or None, cache entry)."""
    request = urllib.request.Request(url)
    if previous.get("etag"):
        request.add_header("If-None-Match", previous["etag"])
    if previous.get("last_modified"):
        request.add_header("If-Modified-Since", previous["last_modified"])

    try:
        with urllib.request.urlopen(request, timeout=FETCH_TIMEOUT_SECONDS) as response:
            if response.status == 304:
                return None, previous
            body = response.read()
            return body, {
                "etag": response.headers.get("ETag"),
                "last_modified": response.headers.get("Last-Modified"),
                "fetched_at": time.time(),
            }
    except urllib.error.HTTPError as error:
        if error.code == 304:
            logger.debug(f"_conditional_get: {url} unchanged")
            return None, previous
        raise


def _imported_urls(index_document: Dict[str, Any], index_url: str) -> List[str]:
    """URLs listed in the index's imports, validated before anything is fetched."""
    urls = []
    for entry in index_document.get("imports") or []:
        url = entry.get("url") if isinstance(entry, dict) else None
        if not url:
            logger.warning(f"_imported_urls: skipping non-URL import in {index_url}: {entry!r}")
            continue
        # Reject unsupported imports here rather than after downloading them.
        _filename_for(url)
        urls.append(url)
    return urls


def _filename_for(url: str) -> str:
    name = Path(urlparse(url).path).name
    if not name.endswith((".yaml", ".yml")):
        raise ValueError(f"Profile import is not a YAML file: {url}")
    return name


def _write(cache_dir: Path, url: str, body: bytes) -> None:
    (cache_dir / _filename_for(url)).write_bytes(body)


def _read(cache_dir: Path, url: str) -> bytes:
    return (cache_dir / _filename_for(url)).read_bytes()


def _read_meta(cache_dir: Path) -> Dict[str, Any]:
    path = cache_dir / META_FILENAME
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        logger.warning(f"_read_meta: unreadable cache metadata in {cache_dir}, refetching")
        return {}


def _write_meta(cache_dir: Path, meta: Dict[str, Any]) -> None:
    (cache_dir / META_FILENAME).write_text(json.dumps(meta, indent=2), encoding="utf-8")


def _require_populated(cache_dir: Path, reason: str) -> None:
    if not any(cache_dir.glob("*.yaml")):
        raise FileNotFoundError(
            f"No cached profile in {cache_dir} and {reason}. "
            f"Populate the cache with a successful fetch first."
        )
