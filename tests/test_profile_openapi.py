"""Tests for deriving the request body schema from the bindings."""
import pytest
import yaml

from src.models.tosca.profile import load_profile, payload_schema

PROFILE = {
    "metadata": {
        "gui_bindings": {
            "metadata.name": "cap.name",
            "node_template.name": "flavour.name",
        }
    },
    "data_types": {
        "Rule": {
            "properties": {
                "to": {"type": "integer", "metadata": {"gui_name": "rule.port_to"}},
            }
        }
    },
    "capability_types": {
        "HostCap": {
            "properties": {
                "num-cpus": {
                    "type": "integer", "required": True,
                    "description": "Number of vCPUs",
                    "metadata": {"gui_name": "flavour.cpu"},
                },
                "speed": {"type": "float", "metadata": {"gui_name": "flavour.speed"}},
            }
        }
    },
    "node_types": {
        "Thing": {
            "properties": {
                "port": {
                    "type": "integer", "required": True, "default": 22,
                    "metadata": {"gui_name": "cap.port"},
                },
                "enabled": {"type": "boolean", "metadata": {"gui_name": "cap.enabled"}},
                "tags": {"type": "list", "entry_schema": "string",
                         "metadata": {"gui_name": "cap.tags"}},
                "ingress": {"type": "list", "entry_schema": "Rule",
                            "metadata": {"gui_name": "rule[direction=in]"}},
            },
            "capabilities": {"host": {"type": "HostCap"}},
        },
        "Unbound": {"properties": {"nothing": {"type": "string"}}},
    },
}


@pytest.fixture
def schema(tmp_path):
    (tmp_path / "types.yaml").write_text(yaml.safe_dump(PROFILE), encoding="utf-8")
    return payload_schema(load_profile(tmp_path))


def test_every_bound_table_is_documented(schema):
    assert set(schema["properties"]) == {"cap", "flavour", "rule"}


def test_unbound_types_contribute_nothing(schema):
    # Unbound has no gui_name bindings, so it adds no tables.
    assert "nothing" not in str(schema["properties"])


def test_instance_table_is_an_array(schema):
    assert schema["properties"]["flavour"]["type"] == "array"
    assert schema["properties"]["flavour"]["items"]["type"] == "object"


def test_single_row_table_is_an_object(schema):
    assert schema["properties"]["cap"]["type"] == "object"


def test_child_table_of_a_list_property_is_an_array(schema):
    assert schema["properties"]["rule"]["type"] == "array"


def test_declared_types_map_to_json_schema_types(schema):
    columns = schema["properties"]["flavour"]["items"]["properties"]
    assert columns["cpu"]["type"] == "integer"
    assert columns["speed"]["type"] == "number"
    assert schema["properties"]["cap"]["properties"]["enabled"]["type"] == "boolean"


def test_list_property_documents_its_item_type(schema):
    tags = schema["properties"]["cap"]["properties"]["tags"]
    assert tags["type"] == "array"
    assert tags["items"]["type"] == "string"


def test_required_without_a_default_is_marked_required(schema):
    assert "cpu" in schema["properties"]["flavour"]["items"]["required"]


def test_required_with_a_default_is_not_marked_required(schema):
    # port is required but the profile supplies a default.
    assert "port" not in schema["properties"]["cap"].get("required", [])


def test_filter_column_is_documented(schema):
    assert "direction" in schema["properties"]["rule"]["items"]["properties"]


def test_entry_schema_columns_are_documented(schema):
    assert "port_to" in schema["properties"]["rule"]["items"]["properties"]


def test_document_level_binding_columns_are_documented(schema):
    assert "name" in schema["properties"]["cap"]["properties"]
    assert "name" in schema["properties"]["flavour"]["items"]["properties"]


def test_profile_descriptions_are_carried_through(schema):
    description = schema["properties"]["flavour"]["items"]["properties"]["cpu"]["description"]
    assert "Number of vCPUs" in description


def test_restricting_the_types_narrows_the_schema(tmp_path):
    (tmp_path / "types.yaml").write_text(yaml.safe_dump(PROFILE), encoding="utf-8")
    narrowed = payload_schema(load_profile(tmp_path), ["Unbound"])
    # Only the document-level bindings remain.
    assert set(narrowed["properties"]) == {"cap", "flavour"}
