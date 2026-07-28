"""Tests for profile loading and type resolution."""
import pytest
import yaml

from src.models.tosca.profile import load_profile, collect_bindings, parse_gui_name

PROFILE = {
    "profile": "test.profile:1.0",
    "metadata": {
        "gui_bindings": {"metadata.name": "thing.name"},
    },
    "capability_types": {
        "HostCap": {
            "properties": {
                "num-cpus": {"type": "integer", "metadata": {"gui_name": "flavour.cpu"}},
                "mem-size": {"type": "integer"},
            }
        },
        "ResourceCap": {
            "properties": {
                "type": {"type": "string"},
                "provider": {"type": "string", "metadata": {"gui_name": "thing.provider"}},
            }
        },
    },
    "node_types": {
        "Base": {
            "properties": {"ssh_port": {"type": "integer", "default": 22}},
            "capabilities": {
                "host": {"type": "HostCap"},
                "resource": {"type": "ResourceCap"},
            },
        },
        "Cloud": {
            "derived_from": "Base",
            "properties": {"cloud": {"type": "string"}},
            "capabilities": {"resource": {"properties": {"type": {"default": "cloud"}}}},
        },
        "AWS": {"derived_from": "Cloud"},
    },
}


@pytest.fixture
def profile(tmp_path):
    (tmp_path / "types.yaml").write_text(yaml.safe_dump(PROFILE), encoding="utf-8")
    return load_profile(tmp_path)


def test_loads_version_and_document_bindings(profile):
    assert profile.version == "test.profile:1.0"
    assert profile.gui_bindings == {"metadata.name": "thing.name"}


def test_inherited_properties_are_merged(profile):
    cloud = profile.resolve("Cloud")
    assert cloud.ancestry == ["Cloud", "Base"]
    assert set(cloud.properties) == {"ssh_port", "cloud"}
    assert cloud.properties["ssh_port"]["default"] == 22


def test_capability_types_are_expanded(profile):
    base = profile.resolve("Base")
    assert set(base.capabilities["host"]["properties"]) == {"num-cpus", "mem-size"}
    assert base.capabilities["host"]["type"] == "HostCap"


def test_subtype_overrides_inherited_capability_property(profile):
    # Cloud pins resource.type without restating the rest of ResourceCap.
    cloud = profile.resolve("Cloud")
    resource = cloud.capabilities["resource"]["properties"]
    assert resource["type"]["default"] == "cloud"
    assert resource["type"]["type"] == "string"
    assert "provider" in resource


def test_override_survives_a_further_subtype(profile):
    aws = profile.resolve("AWS")
    assert aws.ancestry == ["AWS", "Cloud", "Base"]
    assert aws.capabilities["resource"]["properties"]["type"]["default"] == "cloud"
    assert "ssh_port" in aws.properties


def test_derived_from_is_not_treated_as_a_property(profile):
    assert "derived_from" not in profile.resolve("Cloud").properties


def test_unknown_type_raises(profile):
    with pytest.raises(KeyError):
        profile.resolve("Nope")


def test_circular_inheritance_raises(tmp_path):
    doc = {"node_types": {"A": {"derived_from": "B"}, "B": {"derived_from": "A"}}}
    (tmp_path / "types.yaml").write_text(yaml.safe_dump(doc), encoding="utf-8")
    with pytest.raises(ValueError, match="Circular"):
        load_profile(tmp_path).resolve("A")


def test_bindings_carry_their_node_template_path(profile):
    by_path = {b.path: b for b in collect_bindings(profile.resolve("Cloud"))}
    assert by_path[("capabilities", "host", "properties", "num-cpus")].table == "flavour"
    assert by_path[("capabilities", "host", "properties", "num-cpus")].column == "cpu"
    assert by_path[("capabilities", "resource", "properties", "provider")].table == "thing"


@pytest.mark.parametrize(
    "reference,expected",
    [
        ("capacity_new.ssh_port", ("capacity_new", "ssh_port", {})),
        ("capacity_port_rule[direction=ingress]", ("capacity_port_rule", None, {"direction": "ingress"})),
        ("locality.city", ("locality", "city", {})),
    ],
)
def test_parse_gui_name(reference, expected):
    assert parse_gui_name(reference) == expected


def test_parse_gui_name_rejects_malformed():
    with pytest.raises(ValueError):
        parse_gui_name("not a reference!")
