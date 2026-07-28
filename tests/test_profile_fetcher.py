"""Tests for profile fetching and caching. No network access."""
import json
import urllib.error
from pathlib import Path

import pytest

from src.models.tosca.profile import fetcher
from src.models.tosca.profile.fetcher import META_FILENAME, ensure_profile

INDEX_URL = "https://example.test/profiles/eu.swarmchestrate/profile.yaml"
CHILD_URL = "https://example.test/profiles/eu.swarmchestrate/capacity.yaml"

INDEX_BODY = f"""
profile: test:1.0
imports:
- url: {CHILD_URL}
""".encode()

CHILD_BODY = b"node_types:\n  Thing: {}\n"


class FakeResponse:
    def __init__(self, status, body=b"", headers=None):
        self.status = status
        self._body = body
        self.headers = headers or {}

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


@pytest.fixture
def transport(monkeypatch):
    """Records requests and serves canned responses."""
    state = {"calls": [], "responses": {}, "fail": False}

    def fake_urlopen(request, timeout=None):
        if state["fail"]:
            raise urllib.error.URLError("network down")
        url = request.full_url
        state["calls"].append((url, dict(request.headers)))
        return state["responses"][url]()

    monkeypatch.setattr(fetcher.urllib.request, "urlopen", fake_urlopen)
    state["responses"] = {
        INDEX_URL: lambda: FakeResponse(200, INDEX_BODY, {"ETag": "idx-v1"}),
        CHILD_URL: lambda: FakeResponse(200, CHILD_BODY, {"ETag": "child-v1"}),
    }
    return state


def test_cold_fetch_mirrors_index_and_imports(transport, tmp_path):
    ensure_profile(INDEX_URL, tmp_path, refresh_seconds=0)

    assert (tmp_path / "profile.yaml").read_bytes() == INDEX_BODY
    assert (tmp_path / "capacity.yaml").read_bytes() == CHILD_BODY
    meta = json.loads((tmp_path / META_FILENAME).read_text())
    assert meta["files"][INDEX_URL]["etag"] == "idx-v1"


def test_refresh_sends_conditional_headers(transport, tmp_path):
    ensure_profile(INDEX_URL, tmp_path, refresh_seconds=0)
    transport["calls"].clear()
    transport["responses"] = {
        INDEX_URL: lambda: FakeResponse(304),
        CHILD_URL: lambda: FakeResponse(304),
    }

    ensure_profile(INDEX_URL, tmp_path, refresh_seconds=0)

    headers = dict(transport["calls"])[INDEX_URL]
    assert headers.get("If-none-match") == "idx-v1"
    # A 304 must leave the cached copy in place.
    assert (tmp_path / "profile.yaml").read_bytes() == INDEX_BODY


def test_unchanged_profile_is_not_rewritten(transport, tmp_path):
    ensure_profile(INDEX_URL, tmp_path, refresh_seconds=0)
    before = (tmp_path / "capacity.yaml").stat().st_mtime_ns
    transport["responses"] = {
        INDEX_URL: lambda: FakeResponse(304),
        CHILD_URL: lambda: FakeResponse(304),
    }

    ensure_profile(INDEX_URL, tmp_path, refresh_seconds=0)

    assert (tmp_path / "capacity.yaml").stat().st_mtime_ns == before


def test_changed_file_is_updated(transport, tmp_path):
    ensure_profile(INDEX_URL, tmp_path, refresh_seconds=0)
    transport["responses"] = {
        INDEX_URL: lambda: FakeResponse(304),
        CHILD_URL: lambda: FakeResponse(200, b"node_types:\n  Thing2: {}\n", {"ETag": "child-v2"}),
    }

    ensure_profile(INDEX_URL, tmp_path, refresh_seconds=0)

    assert b"Thing2" in (tmp_path / "capacity.yaml").read_bytes()
    meta = json.loads((tmp_path / META_FILENAME).read_text())
    assert meta["files"][CHILD_URL]["etag"] == "child-v2"


def test_within_ttl_skips_the_network(transport, tmp_path):
    ensure_profile(INDEX_URL, tmp_path, refresh_seconds=0)
    transport["calls"].clear()

    ensure_profile(INDEX_URL, tmp_path, refresh_seconds=3600)

    assert transport["calls"] == []


def test_failed_refresh_falls_back_to_cache(transport, tmp_path):
    ensure_profile(INDEX_URL, tmp_path, refresh_seconds=0)
    transport["fail"] = True

    ensure_profile(INDEX_URL, tmp_path, refresh_seconds=0)

    assert (tmp_path / "capacity.yaml").read_bytes() == CHILD_BODY


def test_failed_fetch_without_cache_raises(transport, tmp_path):
    transport["fail"] = True

    with pytest.raises(FileNotFoundError, match="could not be fetched"):
        ensure_profile(INDEX_URL, tmp_path, refresh_seconds=0)


def test_offline_uses_cache_without_network(transport, tmp_path):
    ensure_profile(INDEX_URL, tmp_path, refresh_seconds=0)
    transport["calls"].clear()

    ensure_profile(INDEX_URL, tmp_path, offline=True)

    assert transport["calls"] == []


def test_offline_without_cache_raises(transport, tmp_path):
    with pytest.raises(FileNotFoundError, match="offline"):
        ensure_profile(INDEX_URL, tmp_path, offline=True)


def test_non_yaml_import_is_rejected(transport, tmp_path):
    transport["responses"][INDEX_URL] = lambda: FakeResponse(
        200, b"imports:\n- url: https://example.test/thing.tar.gz\n", {"ETag": "x"}
    )

    with pytest.raises(ValueError, match="not a YAML file"):
        ensure_profile(INDEX_URL, tmp_path, refresh_seconds=0)


def test_corrupt_metadata_is_recovered(transport, tmp_path):
    ensure_profile(INDEX_URL, tmp_path, refresh_seconds=0)
    (tmp_path / META_FILENAME).write_text("{not json", encoding="utf-8")

    ensure_profile(INDEX_URL, tmp_path, refresh_seconds=0)

    assert json.loads((tmp_path / META_FILENAME).read_text())["files"]
