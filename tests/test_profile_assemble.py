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


def test_scalar_for_a_list_property_is_promoted(profile):
    # A list binding collects one value per row, so a lone scalar becomes a
    # single-item list rather than being dropped.
    payload = {**PAYLOAD, "cap": {**PAYLOAD["cap"], "tags": "just-one"}}
    doc, _ = assemble(profile, "Thing", payload)
    assert templates(doc)["big"]["properties"]["tags"] == ["just-one"]


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


# Free-form properties: the payload names the property it sets, rather than the
# profile fixing it at authoring time.

FREE_PROFILE = {
    "profile": "test:1.0",
    "metadata": {
        "gui_bindings": {
            "application": {
                "metadata.name": "app.name",
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
                "hostname": {"type": "string"},
            }
        }
    },
}

FREE_PAYLOAD = {
    "app": {"name": "my-app"},
    "service": [
        {"id": 1, "name": "web", "image": "nginx"},
        {"id": 2, "name": "worker", "image": "busybox"},
    ],
    "extra": [
        {"service_id": 1, "property_name": "replicas", "property_value": "3"},
        {"service_id": 2, "property_name": "hostname", "property_value": "worker-0"},
    ],
}


@pytest.fixture
def free_profile(tmp_path):
    (tmp_path / "types.yaml").write_text(yaml.safe_dump(FREE_PROFILE), encoding="utf-8")
    return load_profile(tmp_path)


def test_free_properties_land_on_their_own_node_template(free_profile):
    doc, _ = assemble(free_profile, "Service", FREE_PAYLOAD, bindings_group="application")
    nodes = templates(doc)
    assert nodes["web"]["properties"]["replicas"] == 3
    assert nodes["worker"]["properties"]["hostname"] == "worker-0"
    # Scoped by foreign key, so neither leaks into the other.
    assert "hostname" not in nodes["web"]["properties"]
    assert "replicas" not in nodes["worker"]["properties"]


def test_free_property_is_coerced_to_its_declared_type(free_profile):
    doc, _ = assemble(free_profile, "Service", FREE_PAYLOAD, bindings_group="application")
    assert templates(doc)["web"]["properties"]["replicas"] == 3


def test_unknown_free_property_is_dropped_with_a_warning(free_profile):
    payload = {
        **FREE_PAYLOAD,
        "extra": [{"service_id": 1, "property_name": "nonsense", "property_value": "x"}],
    }
    doc, warnings = assemble(free_profile, "Service", payload, bindings_group="application")
    assert "nonsense" not in templates(doc)["web"].get("properties", {})
    assert any("nonsense" in w.get("properties", "") for w in warnings)


def test_free_property_table_is_not_reported_as_unclaimed(free_profile):
    _, warnings = assemble(free_profile, "Service", FREE_PAYLOAD, bindings_group="application")
    assert not any("extra" in w.get("payload", "") for w in warnings)


def test_child_rows_without_a_foreign_key_are_shared(free_profile):
    """A child table not keyed to the instance applies to every node template."""
    payload = {
        **FREE_PAYLOAD,
        "extra": [{"property_name": "replicas", "property_value": "5"}],
    }
    doc, _ = assemble(free_profile, "Service", payload, bindings_group="application")
    nodes = templates(doc)
    assert nodes["web"]["properties"]["replicas"] == 5
    assert nodes["worker"]["properties"]["replicas"] == 5


def test_list_column_on_the_instance_table_is_per_row(tmp_path):
    """A list column on the instance table must not gather every row's value."""
    document = {
        "profile": "test:1.0",
        "metadata": {"gui_bindings": {"node_template.name": "service.name"}},
        "node_types": {
            "Service": {
                "properties": {
                    "command": {
                        "type": "list",
                        "entry_schema": "string",
                        "metadata": {"gui_name": "service.commands"},
                    }
                }
            }
        },
    }
    (tmp_path / "types.yaml").write_text(yaml.safe_dump(document), encoding="utf-8")
    payload = {
        "service": [
            {"id": 1, "name": "web", "commands": ["nginx"]},
            {"id": 2, "name": "worker"},
        ]
    }
    doc, _ = assemble(load_profile(tmp_path), "Service", payload)
    nodes = templates(doc)
    assert nodes["web"]["properties"]["command"] == ["nginx"]
    assert "command" not in nodes["worker"].get("properties", {})


# Placement constraints become clauses of a requirement's node_filter.

FILTER_PROFILE = {
    "profile": "test:1.0",
    "metadata": {
        "gui_bindings": {
            "application": {
                "node_template.name": "service.name",
                "node_filter": {
                    "gui_name": "constraint",
                    "requirement": "host",
                    "target_type": "Host",
                },
            }
        }
    },
    "capability_types": {
        "HostCap": {"properties": {"num-cpus": {"type": "integer"}}},
        "NetworkCap": {
            "properties": {"tcp-allow": {"type": "list", "entry_schema": "string"}}
        },
    },
    "node_types": {
        "Host": {"capabilities": {"host": {"type": "HostCap"},
                                  "network": {"type": "NetworkCap"}}},
        "Service": {"properties": {"image": {"type": "string",
                                             "metadata": {"gui_name": "service.image"}}}},
    },
}


@pytest.fixture
def filter_profile(tmp_path):
    (tmp_path / "types.yaml").write_text(yaml.safe_dump(FILTER_PROFILE), encoding="utf-8")
    return load_profile(tmp_path)


def build_with(profile, rows):
    payload = {
        "service": [
            {"id": 1, "name": "web", "image": "nginx"},
            {"id": 2, "name": "worker", "image": "busybox"},
        ],
        "constraint": rows,
    }
    doc, warnings = assemble(profile, "Service", payload, bindings_group="application")
    return templates(doc), warnings


def test_constraints_become_a_node_filter(filter_profile):
    nodes, _ = build_with(filter_profile, [
        {"service_id": 1, "target": "host.num-cpus", "operator": "$greater_or_equal", "value": 2},
    ])
    assert nodes["web"]["requirements"] == [{
        "host": {"node_filter": {"$and": [
            {"$greater_or_equal": [
                {"$get_property": ["SELF", "TARGET", "CAPABILITY", "host", "num-cpus"]}, 2,
            ]}
        ]}}
    }]


def test_constraints_are_scoped_to_their_own_microservice(filter_profile):
    nodes, _ = build_with(filter_profile, [
        {"service_id": 1, "target": "host.num-cpus", "operator": "$greater_or_equal", "value": 2},
    ])
    assert "requirements" not in nodes["worker"]


def test_range_emits_both_bounds(filter_profile):
    nodes, _ = build_with(filter_profile, [
        {"service_id": 1, "target": "host.num-cpus", "operator": "$in_range",
         "value": "1", "value_max": "4"},
    ])
    clause = nodes["web"]["requirements"][0]["host"]["node_filter"]["$and"][0]
    # Coerced to the property's declared type, not left as text.
    assert clause["$in_range"][1] == [1, 4]


def test_has_any_entry_takes_a_list_of_entries(filter_profile):
    nodes, _ = build_with(filter_profile, [
        {"service_id": 1, "target": "network.tcp-allow",
         "operator": "$has_any_entry", "value": "ALL, 80"},
    ])
    clause = nodes["web"]["requirements"][0]["host"]["node_filter"]["$and"][0]
    assert clause["$has_any_entry"][1] == ["ALL", "80"]


def test_no_constraints_means_no_requirements_block(filter_profile):
    nodes, _ = build_with(filter_profile, [])
    assert "requirements" not in nodes["web"]


def test_constraint_table_is_not_reported_as_unclaimed(filter_profile):
    _, warnings = build_with(filter_profile, [
        {"service_id": 1, "target": "host.num-cpus", "operator": "$equal", "value": 2},
    ])
    assert not any("constraint" in w.get("payload", "") for w in warnings)


# Application-wide policies, declared by the profile and filled from the payload.

POLICY_PROFILE = {
    "profile": "test:1.0",
    "metadata": {
        "gui_bindings": {
            "application": {
                "metadata.name": "app.name",
                "metadata.author": "app.author",
                "node_template.name": "service.name",
                "policies": {
                    "energy": {
                        "type": "EnergyBudget",
                        "properties": {
                            "priority": "app.energy_priority",
                            "target": "app.energy_target",
                        },
                    },
                    "cost": {
                        "type": "CostBudget",
                        "properties": {"target": "app.cost_target"},
                    },
                },
            }
        }
    },
    "policy_types": {
        "QoS": {"properties": {"priority": {"type": "float"}, "target": {"type": "integer"}}},
        "EnergyBudget": {"derived_from": "QoS"},
        "CostBudget": {"derived_from": "QoS"},
    },
    "node_types": {
        "Service": {"properties": {"image": {"type": "string",
                                             "metadata": {"gui_name": "service.image"}}}}
    },
}


@pytest.fixture
def policy_profile(tmp_path):
    # sort_keys=False so the fixture keeps the declared policy order, which is
    # the order the document is expected to carry.
    (tmp_path / "types.yaml").write_text(
        yaml.safe_dump(POLICY_PROFILE, sort_keys=False), encoding="utf-8"
    )
    return load_profile(tmp_path)


def policy_doc(profile, app):
    payload = {"app": app, "service": [{"id": 1, "name": "web", "image": "nginx"}]}
    doc, _ = assemble(profile, "Service", payload, bindings_group="application")
    return doc


def test_policies_are_built_from_the_payload(policy_profile):
    doc = policy_doc(policy_profile, {
        "name": "app", "energy_priority": "0.5", "energy_target": "40", "cost_target": 2,
    })
    assert doc["service_template"]["policies"] == [
        {"energy": {"type": "swch:EnergyBudget",
                    "properties": {"priority": 0.5, "target": 40}}},
        {"cost": {"type": "swch:CostBudget", "properties": {"target": 2}}},
    ]


def test_a_policy_with_no_values_is_not_emitted(policy_profile):
    doc = policy_doc(policy_profile, {"name": "app", "energy_target": 40})
    assert [next(iter(p)) for p in doc["service_template"]["policies"]] == ["energy"]


def test_no_policies_means_no_policies_key(policy_profile):
    doc = policy_doc(policy_profile, {"name": "app"})
    assert "policies" not in doc["service_template"]


def test_any_metadata_binding_populates_that_key(policy_profile):
    doc = policy_doc(policy_profile, {"name": "app", "author": "you"})
    assert doc["metadata"] == {"name": "app", "author": "you"}


def test_count_comes_from_the_instance_row(tmp_path):
    """count belongs to the requirement, so it is per microservice."""
    document = dict(FILTER_PROFILE)
    document["metadata"] = {"gui_bindings": {"application": {
        "node_template.name": "service.name",
        "node_filter": {
            "gui_name": "constraint",
            "requirement": "host",
            "target_type": "Host",
            "count": "service.instances",
        },
    }}}
    (tmp_path / "types.yaml").write_text(yaml.safe_dump(document), encoding="utf-8")
    payload = {
        "service": [{"id": 1, "name": "web", "image": "nginx", "instances": "3"}],
        "constraint": [{"service_id": 1, "target": "host.num-cpus",
                        "operator": "$equal", "value": 2}],
    }
    doc, _ = assemble(load_profile(tmp_path), "Service", payload, bindings_group="application")
    host = templates(doc)["web"]["requirements"][0]["host"]
    assert host["count"] == 3
    assert "$and" in host["node_filter"]


def test_count_alone_still_produces_a_requirement(tmp_path):
    document = dict(FILTER_PROFILE)
    document["metadata"] = {"gui_bindings": {"application": {
        "node_template.name": "service.name",
        "node_filter": {
            "gui_name": "constraint",
            "requirement": "host",
            "target_type": "Host",
            "count": "service.instances",
        },
    }}}
    (tmp_path / "types.yaml").write_text(yaml.safe_dump(document), encoding="utf-8")
    payload = {"service": [{"id": 1, "name": "web", "image": "nginx", "instances": 1}]}
    doc, _ = assemble(load_profile(tmp_path), "Service", payload, bindings_group="application")
    assert templates(doc)["web"]["requirements"] == [{"host": {"count": 1}}]


# Grouped policies: rows link node templates, and each connected group becomes
# one policy rather than one policy per row.

GROUPED_PROFILE = {
    "profile": "test:1.0",
    "metadata": {
        "gui_bindings": {
            "application": {
                "node_template.name": "service.name",
                "grouped_policies": {
                    "colocation": {
                        "type": "Colocation",
                        "gui_name": "coloc",
                        "links": "target",
                    }
                },
            }
        }
    },
    "policy_types": {"Colocation": {}},
    "node_types": {
        "Service": {"properties": {"image": {"type": "string",
                                             "metadata": {"gui_name": "service.image"}}}}
    },
}

GROUPED_SERVICES = [
    {"id": 1, "name": "web", "image": "x"},
    {"id": 2, "name": "worker", "image": "x"},
    {"id": 3, "name": "cache", "image": "x"},
    {"id": 4, "name": "api", "image": "x"},
    {"id": 5, "name": "db", "image": "x"},
]


@pytest.fixture
def grouped_profile(tmp_path):
    (tmp_path / "types.yaml").write_text(yaml.safe_dump(GROUPED_PROFILE), encoding="utf-8")
    return load_profile(tmp_path)


def grouped_policies(profile, coloc_rows):
    payload = {"service": GROUPED_SERVICES, "coloc": coloc_rows}
    doc, warnings = assemble(profile, "Service", payload, bindings_group="application")
    return doc["service_template"].get("policies", []), warnings


def test_linked_rows_merge_into_one_policy(grouped_profile):
    """web-worker and worker-cache is one group of three, not two pairs."""
    policies, _ = grouped_policies(grouped_profile, [
        {"service_id": 1, "target": "worker"},
        {"service_id": 2, "target": "cache"},
    ])
    assert policies == [{
        "web_worker_cache_colocation": {
            "type": "swch:Colocation",
            "targets": ["web", "worker", "cache"],
        }
    }]


def test_separate_groups_become_separate_policies(grouped_profile):
    policies, _ = grouped_policies(grouped_profile, [
        {"service_id": 1, "target": "worker"},
        {"service_id": 4, "target": "db"},
    ])
    assert [next(iter(p)) for p in policies] == [
        "web_worker_colocation", "api_db_colocation",
    ]


def test_a_link_joining_two_existing_groups_merges_them(grouped_profile):
    policies, _ = grouped_policies(grouped_profile, [
        {"service_id": 1, "target": "worker"},
        {"service_id": 3, "target": "api"},
        # This one bridges the two groups above.
        {"service_id": 2, "target": "cache"},
    ])
    assert len(policies) == 1
    assert policies[0]["web_worker_cache_api_colocation"]["targets"] == [
        "web", "worker", "cache", "api",
    ]


def test_members_are_ordered_as_the_payload_gives_them(grouped_profile):
    """Creation order reads better than alphabetical, and is deterministic."""
    policies, _ = grouped_policies(grouped_profile, [{"service_id": 3, "target": "web"}])
    assert policies[0]["web_cache_colocation"]["targets"] == ["web", "cache"]


def test_no_links_means_no_policies(grouped_profile):
    policies, _ = grouped_policies(grouped_profile, [])
    assert policies == []


def test_link_to_an_unknown_name_is_reported_and_skipped(grouped_profile):
    policies, warnings = grouped_policies(grouped_profile, [
        {"service_id": 1, "target": "ghost"},
    ])
    assert policies == []
    assert any("ghost" in w.get("policies", "") for w in warnings)
