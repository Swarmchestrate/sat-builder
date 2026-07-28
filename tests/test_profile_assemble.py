"""Tests for assembling a TOSCA document from database rows."""
import pytest
import yaml

from src.models.tosca.profile import assemble, load_profile

PROFILE = {
    "profile": "test:1.0",
    "metadata": {
        "gui_bindings": {
            "metadata.name": "cap.name",
            "description": "cap.description",
            "node_template.name": "flavour.name",
        }
    },
    "data_types": {
        "Rule": {
            "properties": {
                "to": {"type": "integer", "metadata": {"gui_name": "rule.port_to"}},
                "from": {"type": "integer", "metadata": {"gui_name": "rule.port_from"}},
            }
        }
    },
    "capability_types": {
        "HostCap": {
            "properties": {
                "num-cpus": {"type": "integer", "metadata": {"gui_name": "flavour.cpu"}},
                "speed": {"type": "float", "metadata": {"gui_name": "flavour.speed"}},
            }
        },
        "LocalityCap": {
            "properties": {"city": {"type": "string", "metadata": {"gui_name": "place.city"}}}
        },
        "QuotaCap": {
            "properties": {"total": {"type": "integer", "metadata": {"gui_name": "quota.total"}}}
        },
    },
    "node_types": {
        "Thing": {
            "properties": {
                "enabled": {"type": "boolean", "metadata": {"gui_name": "cap.enabled"}},
                "tags": {
                    "type": "list",
                    "entry_schema": "string",
                    "metadata": {"gui_name": "cap.tags"},
                },
                "ingress": {
                    "type": "list",
                    "entry_schema": "Rule",
                    "metadata": {"gui_name": "rule[direction=in]"},
                },
            },
            "capabilities": {"host": {"type": "HostCap"}, "locality": {"type": "LocalityCap"}},
        },
        # Exists only so quota.* is bound somewhere other than Thing.
        "Overall": {"capabilities": {"quota": {"type": "QuotaCap"}}},
    },
}

PAYLOAD = {
    "cap": {"name": "my-capacity", "description": "a capacity", "enabled": "true", "tags": ["a", "b"]},
    "place": {"city": "Budapest"},
    "flavour": [
        {"name": "big", "cpu": 8, "speed": "2.5"},
        {"name": "small", "cpu": 2},
    ],
    "rule": [
        {"direction": "in", "port_from": 22, "port_to": 22},
        {"direction": "out", "port_from": 1, "port_to": 65535},
    ],
}


@pytest.fixture
def profile(tmp_path):
    (tmp_path / "types.yaml").write_text(yaml.safe_dump(PROFILE), encoding="utf-8")
    return load_profile(tmp_path)


@pytest.fixture
def document(profile):
    doc, _ = assemble(profile, "Thing", PAYLOAD)
    return doc


def templates(document):
    return document["service_template"]["node_templates"]


def test_one_node_template_per_instance_row(document):
    assert set(templates(document)) == {"big", "small"}


def test_node_type_is_namespaced(document):
    assert templates(document)["big"]["type"] == "swch:Thing"


def test_per_row_values_differ(document):
    assert templates(document)["big"]["capabilities"]["host"]["properties"]["num-cpus"] == 8
    assert templates(document)["small"]["capabilities"]["host"]["properties"]["num-cpus"] == 2


def test_shared_values_are_copied_into_every_template(document):
    for name in ("big", "small"):
        locality = templates(document)[name]["capabilities"]["locality"]["properties"]
        assert locality["city"] == "Budapest"


def test_document_metadata_and_description_are_bound(document):
    assert document["metadata"]["name"] == "my-capacity"
    assert document["description"] == "a capacity"


def test_list_of_data_type_entries_is_filtered(document):
    # Only direction=in belongs to ingress.
    assert templates(document)["big"]["properties"]["ingress"] == [{"to": 22, "from": 22}]


def test_plain_list_column_passes_through(document):
    assert templates(document)["big"]["properties"]["tags"] == ["a", "b"]


def test_values_are_coerced_to_declared_types(document):
    assert templates(document)["big"]["properties"]["enabled"] is True
    assert templates(document)["big"]["capabilities"]["host"]["properties"]["speed"] == 2.5


def test_absent_values_are_omitted_entirely(document):
    # small has no speed, and the key must not appear as null.
    assert "speed" not in templates(document)["small"]["capabilities"]["host"]["properties"]


def test_description_argument_overrides_the_bound_value(profile):
    doc, _ = assemble(profile, "Thing", PAYLOAD, description="explicit")
    assert doc["description"] == "explicit"


def test_unbound_column_is_reported(profile):
    payload = {**PAYLOAD, "cap": {**PAYLOAD["cap"], "mystery": "value"}}
    _, warnings = assemble(profile, "Thing", payload)
    assert any("mystery" in w["payload"] and "no gui_name binding anywhere" in w["payload"]
               for w in warnings)


def test_column_bound_on_another_type_is_reported_separately(profile):
    payload = {**PAYLOAD, "quota": {"total": 100}}
    _, warnings = assemble(profile, "Thing", payload)
    assert any("bound on another node type" in w["payload"] and "total" in w["payload"]
               for w in warnings)


def test_filter_and_entry_columns_are_not_reported_as_unused(profile):
    _, warnings = assemble(profile, "Thing", PAYLOAD)
    assert not any("rule" in w["payload"] for w in warnings)


def test_keys_and_timestamps_are_not_reported(profile):
    payload = {**PAYLOAD, "place": {"locality_id": 3, "id": 1, "created_at": "x", "city": "Budapest"}}
    _, warnings = assemble(profile, "Thing", payload)
    assert not any("place" in w["payload"] for w in warnings)


def test_missing_instance_rows_warns_and_produces_nothing(profile):
    payload = {**PAYLOAD, "flavour": []}
    doc, warnings = assemble(profile, "Thing", payload)
    assert templates(doc) == {}
    assert any("no node templates" in w["payload"] for w in warnings)


def test_row_without_a_name_gets_a_fallback(profile):
    payload = {**PAYLOAD, "flavour": [{"cpu": 1}]}
    doc, warnings = assemble(profile, "Thing", payload)
    assert "thing-1" in templates(doc)
    assert any("has no name" in w["node_template"] for w in warnings)


def test_duplicate_names_are_reported(profile):
    payload = {**PAYLOAD, "flavour": [{"name": "same", "cpu": 1}, {"name": "same", "cpu": 2}]}
    doc, warnings = assemble(profile, "Thing", payload)
    assert len(templates(doc)) == 1
    assert any("Duplicate" in w.get("node_template", "") for w in warnings)


def test_totals_type_adds_one_template_beside_the_per_row_ones(profile):
    payload = {**PAYLOAD, "quota": {"total": 100}}
    doc, _ = assemble(profile, ["Thing", "Overall"], payload)
    assert set(templates(doc)) == {"big", "small", "my-capacity"}
    assert templates(doc)["my-capacity"]["type"] == "swch:Overall"
    assert templates(doc)["my-capacity"]["capabilities"]["quota"]["properties"]["total"] == 100


def test_totals_type_is_omitted_when_the_payload_has_no_data_for_it(profile):
    doc, _ = assemble(profile, ["Thing", "Overall"], PAYLOAD)
    assert set(templates(doc)) == {"big", "small"}


def test_requesting_the_totals_type_claims_its_columns(profile):
    payload = {**PAYLOAD, "quota": {"total": 100}}
    _, warnings = assemble(profile, ["Thing", "Overall"], payload)
    assert not any("quota" in w.get("payload", "") for w in warnings)


def test_totals_template_name_falls_back_when_taken(profile):
    payload = {
        **PAYLOAD,
        "quota": {"total": 100},
        "flavour": [{"name": "my-capacity", "cpu": 1}],
    }
    doc, _ = assemble(profile, ["Thing", "Overall"], payload)
    assert set(templates(doc)) == {"my-capacity", "my-capacity-overall"}


def test_profile_without_node_template_binding_raises(tmp_path):
    document = {**PROFILE, "metadata": {"gui_bindings": {"metadata.name": "cap.name"}}}
    (tmp_path / "types.yaml").write_text(yaml.safe_dump(document), encoding="utf-8")
    with pytest.raises(ValueError, match="node_template.name"):
        assemble(load_profile(tmp_path), "Thing", PAYLOAD)
