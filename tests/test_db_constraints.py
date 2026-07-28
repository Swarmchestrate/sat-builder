"""Tests for deriving NOT NULL constraints from the profile."""
import pytest
import yaml

from src.models.tosca.profile import load_profile
from src.tools.db_constraints import compare, required_columns, to_ddl

PROFILE = {
    "metadata": {"gui_bindings": {"node_template.name": "flavour.name"}},
    "data_types": {
        "Rule": {
            "properties": {
                "to": {"type": "integer", "required": True,
                       "metadata": {"gui_name": "rule.port_to"}},
                "source": {"type": "string", "required": False,
                           "metadata": {"gui_name": "rule.source"}},
            }
        }
    },
    "capability_types": {
        "HostCap": {
            "properties": {
                "num-cpus": {"type": "integer", "required": True,
                             "metadata": {"gui_name": "flavour.cpu"}},
                "speed": {"type": "float", "metadata": {"gui_name": "flavour.speed"}},
            }
        }
    },
    "node_types": {
        "Thing": {
            "properties": {
                "port": {"type": "integer", "required": True, "default": 22,
                         "metadata": {"gui_name": "cap.port"}},
                "owner": {"type": "string", "required": True,
                          "metadata": {"gui_name": "cap.owner"}},
                "ingress": {"type": "list", "entry_schema": "Rule", "required": False,
                            "metadata": {"gui_name": "rule[direction=in]"}},
            },
            "capabilities": {"host": {"type": "HostCap"}},
        }
    },
}


@pytest.fixture
def required(tmp_path):
    (tmp_path / "types.yaml").write_text(yaml.safe_dump(PROFILE), encoding="utf-8")
    return required_columns(load_profile(tmp_path))


def test_required_property_yields_its_column(required):
    assert required["cap"] == {"owner"}
    assert "cpu" in required["flavour"]


def test_optional_property_is_not_required(required):
    assert "speed" not in required["flavour"]


def test_required_with_a_default_is_not_required(required):
    # The profile supplies port, so the column may be null.
    assert "port" not in required.get("cap", set())


def test_entry_properties_of_a_list_are_required_on_the_child_table(required):
    # ingress itself is optional, but a row that exists must be complete.
    assert required["rule"] == {"port_to"}


def test_optional_entry_property_is_not_required(required):
    assert "source" not in required["rule"]


def test_ddl_is_transactional_and_sorted(required):
    ddl = to_ddl(required)
    assert ddl.index("BEGIN;") < ddl.index("ALTER TABLE") < ddl.index("COMMIT;")
    assert "ALTER TABLE cap ALTER COLUMN owner SET NOT NULL;" in ddl


def test_compare_reports_columns_the_database_does_not_enforce():
    missing, extra = compare({"t": {"a", "b"}}, {"t": {"a"}})
    assert missing == ["t.b"]
    assert extra == []


def test_compare_reports_columns_the_profile_does_not_require():
    missing, extra = compare({"t": {"a"}}, {"t": {"a", "c"}})
    assert missing == []
    assert extra == ["t.c"]


def test_compare_ignores_keys():
    _, extra = compare({}, {"t": {"id", "other_id"}})
    assert extra == []


def test_compare_is_quiet_when_in_step():
    assert compare({"t": {"a"}}, {"t": {"a"}}) == ([], [])
