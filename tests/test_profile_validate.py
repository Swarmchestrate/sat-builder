"""Tests for validating a payload against the profile."""
import pytest
import yaml

from src.models.tosca.profile import load_profile, validate

PROFILE = {
    "metadata": {
        "gui_bindings": {
            "metadata.name": "cap.name",
            "node_template.name": "flavour.name",
        }
    },
    "capability_types": {
        "HostCap": {
            "properties": {
                "num-cpus": {
                    "type": "integer", "required": True,
                    "metadata": {"gui_name": "flavour.cpu"},
                },
                "speed": {"type": "float", "metadata": {"gui_name": "flavour.speed"}},
            }
        },
        "LocalityCap": {
            "properties": {
                "city": {
                    "type": "string", "required": True,
                    "metadata": {"gui_name": "place.city"},
                }
            }
        },
        "QuotaCap": {
            "properties": {
                "total": {
                    "type": "integer", "required": True,
                    "metadata": {"gui_name": "quota.total"},
                }
            }
        },
    },
    "node_types": {
        "Thing": {
            "properties": {
                "enabled": {"type": "boolean", "metadata": {"gui_name": "cap.enabled"}},
                "port": {
                    "type": "integer", "required": True, "default": 22,
                    "metadata": {"gui_name": "cap.port"},
                },
                "tags": {"type": "list", "entry_schema": "string",
                         "metadata": {"gui_name": "cap.tags"}},
                "labels": {"type": "map", "metadata": {"gui_name": "cap.labels"}},
            },
            "capabilities": {"host": {"type": "HostCap"}, "locality": {"type": "LocalityCap"}},
        },
        "Overall": {"capabilities": {"quota": {"type": "QuotaCap"}}},
        "Unbindable": {
            "properties": {"orphan": {"type": "string", "required": True}},
        },
    },
}

VALID = {
    "cap": {"name": "c", "enabled": True, "tags": ["a"]},
    "place": {"city": "Budapest"},
    "flavour": [{"name": "big", "cpu": 8}],
}


@pytest.fixture
def profile(tmp_path):
    (tmp_path / "types.yaml").write_text(yaml.safe_dump(PROFILE), encoding="utf-8")
    return load_profile(tmp_path)


def kinds(errors):
    return {(e.kind, e.path) for e in errors}


def test_complete_payload_is_valid(profile):
    assert validate(profile, "Thing", VALID) == []


def test_missing_required_value_is_reported_against_its_column(profile):
    payload = {**VALID, "place": {}}
    errors = validate(profile, "Thing", payload)
    assert ("missing", "place.city") in kinds(errors)


def test_missing_required_per_row_value_locates_the_row(profile):
    payload = {**VALID, "flavour": [{"name": "a", "cpu": 1}, {"name": "b"}]}
    errors = validate(profile, "Thing", payload)
    assert ("missing", "flavour[1].cpu") in kinds(errors)
    assert ("missing", "flavour[0].cpu") not in kinds(errors)


def test_required_with_a_default_is_not_reported(profile):
    # port is required but the profile supplies a default.
    assert not any(e.path == "cap.port" for e in validate(profile, "Thing", VALID))


def test_wrong_type_is_reported(profile):
    payload = {**VALID, "flavour": [{"name": "big", "cpu": "four"}]}
    errors = validate(profile, "Thing", payload)
    assert ("type", "flavour[0].cpu") in kinds(errors)


@pytest.mark.parametrize("value", ["8", 8, 8.0])
def test_numeric_strings_are_accepted_for_integers(profile, value):
    payload = {**VALID, "flavour": [{"name": "big", "cpu": value}]}
    assert not any(e.kind == "type" for e in validate(profile, "Thing", payload))


@pytest.mark.parametrize("value", ["true", "no", True, False])
def test_boolean_forms_are_accepted(profile, value):
    payload = {**VALID, "cap": {**VALID["cap"], "enabled": value}}
    assert not any(e.kind == "type" for e in validate(profile, "Thing", payload))


def test_boolean_rejects_nonsense(profile):
    payload = {**VALID, "cap": {**VALID["cap"], "enabled": "banana"}}
    assert ("type", "cap.enabled") in kinds(validate(profile, "Thing", payload))


def test_map_type_rejects_a_scalar(profile):
    payload = {**VALID, "cap": {**VALID["cap"], "labels": "not-a-map"}}
    assert ("type", "cap.labels") in kinds(validate(profile, "Thing", payload))


def test_scalar_for_a_list_property_is_promoted_not_rejected(profile):
    # A list binding collects one value per row, so a lone scalar is a
    # single-item list rather than a type error.
    payload = {**VALID, "cap": {**VALID["cap"], "tags": "just-one"}}
    assert not any(e.kind == "type" for e in validate(profile, "Thing", payload))


def test_shared_values_are_reported_once_not_once_per_row(profile):
    payload = {**VALID, "place": {}, "flavour": [{"name": "a", "cpu": 1}, {"name": "b", "cpu": 2}]}
    errors = [e for e in validate(profile, "Thing", payload) if e.path == "place.city"]
    assert len(errors) == 1


def test_required_property_without_a_binding_is_reported_as_unbindable(profile):
    errors = validate(profile, "Unbindable", VALID)
    assert any(e.kind == "unbindable" and "orphan" in e.message for e in errors)


def test_totals_type_is_skipped_when_absent_from_the_payload(profile):
    assert validate(profile, ["Thing", "Overall"], VALID) == []


def test_totals_type_is_checked_once_present(profile):
    payload = {**VALID, "quota": {"total": "lots"}}
    assert ("type", "quota.total") in kinds(validate(profile, ["Thing", "Overall"], payload))


def test_errors_serialise_for_an_api_response(profile):
    payload = {**VALID, "place": {}}
    error = validate(profile, "Thing", payload)[0].as_dict()
    assert set(error) == {"path", "message", "kind"}


def test_profile_without_node_template_binding_raises(tmp_path):
    document = {**PROFILE, "metadata": {"gui_bindings": {}}}
    (tmp_path / "types.yaml").write_text(yaml.safe_dump(document), encoding="utf-8")
    with pytest.raises(ValueError, match="node_template.name"):
        validate(load_profile(tmp_path), "Thing", VALID)


# Free-form properties: the profile is what says whether a name the user typed
# exists, and what type its value should be.

FREE_PROFILE = {
    "profile": "test:1.0",
    "metadata": {
        "gui_bindings": {
            "application": {
                "node_template.name": "service.name",
                "node_template.properties": "extra{property_name: property_value}",
            }
        }
    },
    "node_types": {
        "Service": {
            "properties": {
                "image": {"type": "string", "metadata": {"gui_name": "service.image"}},
                "replicas": {"type": "integer"},
            }
        }
    },
}


@pytest.fixture
def free_profile(tmp_path):
    (tmp_path / "types.yaml").write_text(yaml.safe_dump(FREE_PROFILE), encoding="utf-8")
    return load_profile(tmp_path)


def free_payload(rows):
    return {
        "service": [{"id": 1, "name": "web", "image": "nginx"}],
        "extra": rows,
    }


def test_known_free_property_of_the_right_type_passes(free_profile):
    payload = free_payload([{"service_id": 1, "property_name": "replicas", "property_value": "3"}])
    assert validate(free_profile, "Service", payload, bindings_group="application") == []


def test_unknown_free_property_is_reported(free_profile):
    payload = free_payload([{"service_id": 1, "property_name": "nonsense", "property_value": "x"}])
    errors = validate(free_profile, "Service", payload, bindings_group="application")
    assert [e.kind for e in errors] == ["unknown_property"]
    assert "nonsense" in errors[0].message
    assert "Service" in errors[0].message


def test_free_property_of_the_wrong_type_is_reported(free_profile):
    payload = free_payload([
        {"service_id": 1, "property_name": "replicas", "property_value": "lots"},
    ])
    errors = validate(free_profile, "Service", payload, bindings_group="application")
    assert [e.kind for e in errors] == ["type"]
    assert errors[0].path == "extra[0].property_value"


def test_free_property_without_a_name_is_reported(free_profile):
    payload = free_payload([{"service_id": 1, "property_value": "3"}])
    errors = validate(free_profile, "Service", payload, bindings_group="application")
    assert [e.kind for e in errors] == ["missing"]
