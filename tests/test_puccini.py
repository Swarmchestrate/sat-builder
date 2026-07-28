"""Tests for TOSCA document validation via Sardou. No Puccini binary required."""
import builtins

import pytest

from src.models.tosca import puccini

DOCUMENT = "tosca_definitions_version: tosca_2_0\n"


def _fake_sardou(monkeypatch, behaviour):
    """Install a fake Sardou whose constructor runs `behaviour`."""
    class FakeSardou:
        def __init__(self, path=None, content=None):
            behaviour(content)

    module = type("m", (), {"Sardou": FakeSardou})
    monkeypatch.setitem(__import__("sys").modules, "sardou", module)


def test_valid_document_reports_no_problems(monkeypatch):
    _fake_sardou(monkeypatch, lambda content: None)
    problems, available = puccini.validate_document(DOCUMENT)
    assert problems == []
    assert available is True


def test_document_is_passed_through_as_content(monkeypatch):
    seen = {}
    _fake_sardou(monkeypatch, lambda content: seen.update(content=content))
    puccini.validate_document(DOCUMENT)
    assert seen["content"] == DOCUMENT


def test_missing_processor_is_reported_as_unavailable_not_a_problem(monkeypatch):
    def missing(content):
        raise FileNotFoundError("Puccini not found at /usr/bin/puccini-tosca")

    _fake_sardou(monkeypatch, missing)
    problems, available = puccini.validate_document(DOCUMENT)
    # An absent processor must not look like an invalid document.
    assert problems == []
    assert available is False


def test_validation_failure_is_reported_as_a_problem(monkeypatch):
    def invalid(content):
        raise ValueError("node template 'x' has no type")

    _fake_sardou(monkeypatch, invalid)
    problems, available = puccini.validate_document(DOCUMENT)
    assert available is True
    assert "no type" in problems[0]["tosca_validation"]


def test_uninstalled_sardou_is_reported_as_unavailable(monkeypatch):
    real_import = builtins.__import__

    def no_sardou(name, *args, **kwargs):
        if name == "sardou":
            raise ImportError("No module named 'sardou'")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", no_sardou)
    problems, available = puccini.validate_document(DOCUMENT)
    assert problems == []
    assert available is False
