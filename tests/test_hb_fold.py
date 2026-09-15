"""HB-folded SRAM WL pattern + RC/L2 vs baseline tests."""

from __future__ import annotations

import json
from pathlib import Path

import gdsfactory as gf

from gf_layout_flow import __version__
from gf_layout_flow.tech.pdk import activate_pdk
from gf_layout_flow.tech.rc_table import clear_rc_cache, get_via_rc_for_layer, get_hb_rc
from gf_layout_flow.cells import wl_hb_fold_pattern, wl_longline_pattern, hb_climb_stack
from gf_layout_flow.rc import (
    extract_rc_metrics,
    extract_wl_rc,
    extract_hb_fold_rc,
    analyze_hb_fold_l2,
    compare_hb_vs_baseline,
    vertical_climb_rc,
    vertical_roundtrip_rc,
    climb_via_layers,
)
from gf_layout_flow.cli import run_wl_hb_pattern


def setup_module():
    activate_pdk()
    clear_rc_cache()


def test_version_0_7_0():
    assert __version__ == "0.7.0"


def test_rv_mapped_to_v10_v11():
    clear_rc_cache()
    rv = get_via_rc_for_layer("RV")
    assert rv["class"] == "V10-V11"
    assert rv["r_ohm"] == 0.3
    assert rv["c_ff"] == 0.4
    assert rv["mapped"] is True


def test_climb_via_layers_and_rc():
    layers = climb_via_layers()
    assert layers[0] == "VIA2"
    assert layers[-1] == "RV"
    assert "VIA12" in layers
    assert len(layers) == 12  # VIA2..VIA12 (11) + RV
    climb = vertical_climb_rc()
    assert climb["n_vias"] == 12
    assert abs(climb["r_ohm"] - 136.2) < 1e-9
    assert abs(climb["c_ff"] - 2.9) < 1e-12
    rt = vertical_roundtrip_rc(n_hb=1)
    assert rt["n_climbs"] == 2
    assert rt["n_hb"] == 1
    hb = get_hb_rc()
    assert abs(rt["r_ohm"] - (2 * 136.2 + hb["r_ohm"])) < 1e-9
    assert abs(rt["c_ff"] - (2 * 2.9 + hb["c_ff"])) < 1e-12


def test_hb_climb_stack_cell():
    s = hb_climb_stack()
    assert isinstance(s, gf.Component)
    assert s.info["n_vias"] == 12
    assert s.info["include_hb"] is True
    m = extract_rc_metrics(s)
    used = set(m["layers_used"])
    assert "HB_PAD" in used
    assert "AP" in used
    assert "M2" in used
    assert "VIA2" in used or "VIA12" in used or "RV" in used


def test_wl_hb_fold_pattern_geometry():
    p = wl_hb_fold_pattern()
    assert p.info["topology"] == "hb_fold"
    assert p.info["baseline_for_hb"] is False
    assert p.info["compares_to"] == "wl_d10_m2_30um"
    assert p.info["n_bitcells_lower"] == 30
    assert p.info["n_bitcells_upper"] == 30
    assert p.info["n_bitcells_total"] == 60
    assert abs(float(p.info["wl_length_lower_um"]) - 15.0) < 1e-12
    assert abs(float(p.info["wl_length_upper_um"]) - 15.0) < 1e-12
    assert p.info["hb_count"] >= 1
    assert "M14" in p.info["stack_map_note"] or "AP" in p.info["stack_map_note"]
    assert p.info["driver_strength"] == "D10"
    assert abs(float(p.info["first_tap_um"]) - 0.5) < 1e-9
    assert abs(float(p.info["last_tap_um"]) - 15.0) < 1e-9
    assert float(p.dymax) >= 15.0 - 1e-6
    m = extract_rc_metrics(p)
    used = set(m["layers_used"])
    assert "M2" in used
    assert "HB_PAD" in used
    assert "AP" in used or "M13" in used
    # High metals present
    assert used & {"M10", "M11", "M12", "M13", "AP"}


def test_hb_fold_rc_paths():
    p = wl_hb_fold_pattern()
    rc = extract_hb_fold_rc(p)
    assert rc["n_bitcells_lower"] == 30
    assert rc["n_bitcells_upper"] == 30
    assert rc["hb_count"] == 1
    # Lower shorter than baseline 30 um
    base = extract_wl_rc(wl_longline_pattern(wl_length=30.0))
    assert rc["lower_path_totals"]["r_ohm"] < base["totals"]["r_ohm"]
    assert rc["wl_length_lower_um"] < base["length_um"]
    # Upper path includes HB + many vias
    assert rc["upper_path_totals"]["r_stack_ohm"] > 200.0
    assert rc["upper_path_totals"]["r_ohm"] > rc["lower_path_totals"]["r_ohm"]
    assert rc["vertical_stack"]["hb"]["r_ohm"] == get_hb_rc()["r_ohm"]
    assert rc["vertical_stack"]["n_vias_total"] == 24


def test_hb_fold_l2_delays():
    p = wl_hb_fold_pattern()
    l2 = analyze_hb_fold_l2(p)
    t_lo = l2["hb_lower"]["l2"]["t_elmore_end_ps"]
    t_up = l2["hb_upper"]["l2"]["t_elmore_end_ps"]
    t_base = l2["baseline"]["l2"]["t_elmore_end_ps"]
    assert t_up > t_lo  # typically upper > lower
    assert t_base > 0 and t_lo > 0 and t_up > 0
    assert l2["comparison"]["critical_end"] == "upper"
    # Lower should be faster than baseline (half length / half taps)
    assert t_lo < t_base


def test_compare_hb_vs_baseline_payload():
    cmp = compare_hb_vs_baseline()
    assert cmp["baseline"]["n_bitcells"] == 60
    assert cmp["hb_lower"]["n_bitcells"] == 30
    assert cmp["hb_upper"]["n_bitcells"] == 30
    assert "stack_map_note" in cmp
    assert cmp["vertical_stack"]["one_climb_n_vias"] == 12


def test_cli_hb_pattern(tmp_path: Path):
    result = run_wl_hb_pattern(
        artifacts_dir=tmp_path,
        write_gds=True,
        regenerate_baseline=True,
    )
    gds = Path(result["gds"])
    assert gds.exists() and gds.stat().st_size > 0
    assert gds.name == "wl_d10_m2_hb_fold_15um.gds"
    for key in ("metrics_json", "rc_json", "l2_json", "compare_json"):
        path = Path(result[key])
        assert path.exists(), key
        json.loads(path.read_text(encoding="utf-8"))
    assert Path(result["compare_md"]).exists()
    assert result["n_bitcells_total"] == 60
    assert result["topology"] == "hb_fold"
    # baseline regenerated
    assert result["baseline"] is not None
    assert Path(result["baseline"]["gds"]).exists()
