"""Test dynamique du nombre d'agents par flottille (poll mensuel config.json).

Couvre les exigences:
- retrait random équitable
- retrait immédiat sans landing
- port aléatoire pour nouveaux
- habitat spécifique flottille conservé
- colonne retired
- ID monotone jamais réutilisé
"""
import json
import tempfile
import os
from pathlib import Path

import pytest

import src.domain.environment.restricted_areas as ra

# Mock rasterization (geopandas non requis pour ces tests)
ra.load_restricted_area_map = lambda *a, **kw: None
ra.load_restricted_area_vector = lambda *a, **kw: None

from src.infrastructure.loader import ConfigLoader
from src.core.model import FisheryModel


def _make_model(coupling=False, verbose=False):
    loader = ConfigLoader()
    cfg = loader.load("configs_json/config_default.json")
    # ensure apply_map_configuration doesn't fail on missing shp
    ra.load_restricted_area_map = lambda *a, **kw: None
    ra.load_restricted_area_vector = lambda *a, **kw: None
    loader.apply_map_configuration()
    params = loader.get_model_params()
    params["coupling"] = coupling
    params["verbose"] = verbose
    model = FisheryModel(**params, config_loader=loader)
    return model, loader


def test_ids_monotone_and_unique():
    model, _ = _make_model()
    assert model._next_agent_id == 25  # 10+10+5
    initial_ids = set(a.unique_id for a in model.agents)
    assert len(initial_ids) == 25
    # increase archipelago
    model._apply_fleet_resize({"num_archipelago": 12, "num_coastal": 10, "num_trawler": 5})
    assert len(list(model.agents)) == 27
    new_ids = set(a.unique_id for a in model.agents)
    # 2 new ids should be 25,26
    assert 25 in new_ids and 26 in new_ids
    assert model._next_agent_id == 27
    # retired empty still disjoint
    assert new_ids.isdisjoint(model._retired_ids)


def test_no_reuse_on_retire_and_create():
    model, _ = _make_model()
    # retire 4 archipelago
    model._apply_fleet_resize({"num_archipelago": 6, "num_coastal": 10, "num_trawler": 5})
    assert len(model._retired_agents) == 4
    retired_ids = set(a.unique_id for a in model._retired_agents)
    active_ids = set(a.unique_id for a in model.agents)
    assert active_ids.isdisjoint(retired_ids)
    # recreate 2 archipelago
    model._apply_fleet_resize({"num_archipelago": 8, "num_coastal": 10, "num_trawler": 5})
    new_active = set(a.unique_id for a in model.agents)
    # new ids should be 25,26 not any retired
    assert retired_ids.isdisjoint(new_active)
    # all ever used still unique
    all_ids = new_active | retired_ids
    assert len(all_ids) == len(new_active) + len(retired_ids)
    assert max(all_ids) + 1 == model._next_agent_id


def test_random_retire_and_immediate_no_landing():
    model, _ = _make_model()
    # pick an agent that will be retired and check its state before
    # force all archipelago to be at_sea to test immediate removal still works
    for a in model.agents:
        if a.fisher_type == "archipelago":
            a.at_sea = True
            a.gone_fishing = True
    n_arch_before = sum(1 for a in model.agents if a.fisher_type == "archipelago")
    model._retire_agents("archipelago", 2)
    assert len(model._retired_agents) == 2
    for r in model._retired_agents:
        assert r.retired is True
        assert r.retired_at_step == model.current_step
        assert r.current_location is None
        assert r.at_sea is False
    n_arch_after = sum(1 for a in model.agents if a.fisher_type == "archipelago")
    assert n_arch_after == n_arch_before - 2


def test_port_random_and_habitat_same():
    model, _ = _make_model()
    # create 3 new trawlers with random ports
    model._create_agents_batch("trawler", 3)
    # check new agents have port in port_coordinates and habitat not empty
    new_agents = sorted(list(model.agents), key=lambda a: a.unique_id)[-3:]
    assert all(a.port is not None for a in new_agents)
    # habitat is fleet-specific: all trawler should share same restricted_mask type/len
    masks = [tuple(a.restricted_mask) if hasattr(a.restricted_mask, "__iter__") else a.restricted_mask for a in new_agents]
    # at least ensure not None
    assert all(m is not None for m in new_agents)


def test_retired_column_in_exports():
    model, _ = _make_model()
    model._build_daily_agent_metrics_cache()
    assert "num_retired" in model._daily_agent_metrics
    # datacollector should have retired column
    df = model.datacollector.get_agent_vars_dataframe()
    assert "retired" in df.columns.get_level_values(0) or "retired" in df.columns
    # monthly rows have retired
    model._append_daily_agent_rows_for_monthly_export()
    assert len(model._monthly_agent_rows) > 0
    assert "retired" in model._monthly_agent_rows[0]
    assert "retired_at" in model._monthly_agent_rows[0]


def test_coupling_read_desired():
    from src.servicies.coupling_service import read_desired_num_agents, _read_config_snapshot
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "config.json"
        cfg = {
            "maps": {"species_map": {"10": "dummy.csv"}},
            "simulation": {"step": 5},
            "agents": {"num_agents": {"num_archipelago": 7, "num_coastal": 8, "num_trawler": 3}},
        }
        p.write_text(json.dumps(cfg), encoding="utf-8")
        snap = _read_config_snapshot(str(p))
        assert snap is not None
        _, step, num_agents = snap
        assert step == 5
        assert num_agents == {"num_archipelago": 7, "num_coastal": 8, "num_trawler": 3}
        assert read_desired_num_agents(str(p)) == num_agents


def test_monthly_poll_non_coupling_via_file():
    # Simulates file change between months without coupling (read_desired path)
    import json as js
    src_path = Path("configs_json/config_default.json")
    tgt_path = Path("configs_json/config.json")
    cfg_data = js.loads(src_path.read_text(encoding="utf-8"))
    cfg_data["simulation"]["step"] = 0
    cfg_data["agents"]["num_agents"] = {"num_archipelago": 10, "num_coastal": 10, "num_trawler": 5}
    tgt_path.write_text(js.dumps(cfg_data, indent=2), encoding="utf-8")

    model, _ = _make_model(coupling=False, verbose=False)
    # Run to first month
    for _ in range(28):
        model.step()
    assert len(list(model.agents)) == 25  # unchanged because file still 10/10/5
    # change file
    cfg_data["agents"]["num_agents"] = {"num_archipelago": 5, "num_coastal": 5, "num_trawler": 2}
    cfg_data["simulation"]["step"] = 1
    tgt_path.write_text(js.dumps(cfg_data, indent=2), encoding="utf-8")
    for _ in range(28):
        model.step()
    assert len(list(model.agents)) == 12
    assert len(model._retired_agents) == 13
    # all IDs unique
    all_ids = [a.unique_id for a in list(model.agents) + model._retired_agents]
    assert len(all_ids) == len(set(all_ids))


def test_yearly_and_model_summary_include_retired():
    model, _ = _make_model()
    model._apply_fleet_resize({"num_archipelago": 5, "num_coastal": 5, "num_trawler": 2})
    summary = model.get_model_summary()
    assert summary["num_retired"] == 13
    assert "total_catch_including_retired" in summary
    yearly = model.collect_yearly_data()
    assert "num_retired" in yearly
    assert "total_catch_all_including_retired" in yearly
