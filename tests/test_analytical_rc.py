"""Analytical interconnect RC table + extract_wl_rc tests."""

from __future__ import annotations

import json
import math
from pathlib import Path

from gf_layout_flow.tech.pdk import activate_pdk
from gf_layout_flow.tech.rc_table import (
    get_metal_rc,
    get_via_rc,
    get_via_rc_for_layer,
    get_hb_rc,
    load_interconnect_rc,
)
from gf_layout_flow.cells import wl_longline_pattern
from gf_layout_flow.rc import extract_wl_rc
from gf_layout_flow.cli import run_wl_pattern


def setup_module():
    activate_pdk()


def test_rc_table_m1_exact():
    m1 = get_metal_rc("M1")
    assert m1 is not None
    assert m1["r_ohm_per_um"] == 60.0
    assert m1["c_ff_per_um"] == 0.22
    assert m1["source"] == "user_measured_lookup"
    assert m1["width_um"] == 0.021
    assert m1["Cc"] == 0.0857


def test_rc_table_m2_interpolated():
    m2 = get_metal_rc("M2")
    assert m2 is not None
    assert m2["source"] == "interpolated_from_user_measured"
    assert m2["parents"] == ["M1", "M3"]
    expected_r = math.sqrt(60.0 * 18.0)
    expected_c = (0.22 + 0.21) / 2.0
    assert abs(m2["r_ohm_per_um"] - expected_r) < 1e-9
    assert abs(m2["c_ff_per_um"] - expected_c) < 1e-12
    # Expected range sanity
    assert 18.0 < m2["r_ohm_per_um"] < 60.0
    assert 0.21 <= m2["c_ff_per_um"] <= 0.22


def test_rc_table_m13_mapped_to_m11():
    m13 = get_metal_rc("M13")
    assert m13 is not None
    assert m13["mapped_to"] == "M11"
    assert abs(m13["r_ohm_per_um"] - 0.76) < 1e-12
    assert abs(m13["c_ff_per_um"] - 0.068) < 1e-12
    assert m13["source"] == "extrapolated"


def test_rc_table_via_and_hb():
    via = get_via_rc()
    assert via["r_ohm_default_use"] == 30.0
    assert via["c_ff"] == 0.1
    assert via["c_plus_cc_ff"] == 0.1
    assert via["class"] == "V1-V2"
    assert "classes" in via
    assert "V1-V2" in via["classes"]
    assert "V10-V11" in via["classes"]
    assert via["classes"]["V5-V9"]["r_ohm"] == 9.0
    # Named lookup
    v0 = get_via_rc("VIA0")
    assert v0["class"] == "V1-V2"
    assert v0["r_ohm"] == 30.0
    assert v0["c_ff"] == 0.1
    assert v0["mapped"] is True
    v1 = get_via_rc_for_layer("VIA1")
    assert v1["class"] == "V1-V2"
    assert v1["r_ohm"] == 30.0
    hb = get_hb_rc()
    assert hb["r_ohm"] == 0.165
    assert hb["c_ff"] == 1.0
    assert hb["c_plus_cc_ff"] == 1.3


def test_rc_table_ap_null():
    assert get_metal_rc("AP") is None


def test_yaml_has_interconnect_rc():
    rc = load_interconnect_rc()
    assert "metals_per_um" in rc
    assert "lumped" in rc
    assert "interpolation_notes" in rc
    assert "M1" in rc["metals_per_um"]
    assert "M2" in rc["metals_per_um"]
    assert "via_classes" in rc["lumped"]
    assert "viaX" not in rc["lumped"]
    assert rc["metals_per_um"]["M13"]["mapped_to"] == "M11"


def test_extract_wl_rc_30um_baseline():
    c = wl_longline_pattern(wl_length=30.0)
    rc = extract_wl_rc(c)
    m2 = get_metal_rc("M2")
    assert m2 is not None
    r_metal = m2["r_ohm_per_um"] * 30.0
    c_metal = m2["c_ff_per_um"] * 30.0
    assert abs(rc["metal_rc"]["r_ohm"] - r_metal) < 1e-6
    assert abs(rc["metal_rc"]["c_ff"] - c_metal) < 1e-9
    assert abs(rc["metal_rc"]["r_ohm"] - 32.863353450309965 * 30) < 1e-6
    assert abs(rc["metal_rc"]["c_ff"] - 0.215 * 30) < 1e-9
    assert rc["via"]["n_vias"] > 0
    # VIA0+VIA1 both V1-V2: 30 Ohm / 0.1 fF → n≈122 → R≈3660, C≈12.2
    assert rc["via"]["n_vias"] == 122
    assert abs(rc["via"]["r_ohm"] - 122 * 30.0) < 1e-6
    assert abs(rc["via"]["c_ff"] - 122 * 0.1) < 1e-9
    assert "per_layer" in rc["via"]
    assert "by_class" in rc["via"]
    assert "VIA0" in rc["via"]["per_layer"]
    assert "VIA1" in rc["via"]["per_layer"]
    assert "V1-V2" in rc["via"]["by_class"]
    assert rc["totals"]["r_ohm"] > rc["metal_rc"]["r_ohm"]
    assert rc["totals"]["c_ff"] > rc["metal_rc"]["c_ff"]
    assert rc["ladder"]["n_seg"] == 60
    assert rc["metal_table"]["source"] == "interpolated_from_user_measured"
    # Tap lump: VIA0+VIA1 → 60 Ohm / 0.2 fF
    tap = rc["ladder"]["segments"][0]["via_lump_at_tap"]
    assert tap["n_vias"] == 2
    assert abs(tap["r_ohm"] - 60.0) < 1e-9
    assert abs(tap["c_ff"] - 0.2) < 1e-12
    # JSON serializable
    raw = json.dumps(rc)
    assert "R_total" not in raw  # keys use totals.r_ohm
    assert "r_ohm" in raw


def test_extract_wl_rc_small_pattern_via_count():
    c = wl_longline_pattern(wl_length=2.0, tap_pitch=0.5)
    rc = extract_wl_rc(c)
    assert c.info["n_bitcells"] == 4
    assert rc["via"]["n_vias"] > 0
    # Prefer polygon count when available
    assert rc["via"]["count_method"] in ("polygon_count", "heuristic_wl_longline_pattern")
    if rc["via"]["count_method"] == "heuristic_wl_longline_pattern":
        assert rc["via"]["n_vias"] == 2 + 2 * 4


def test_cli_writes_rc_json(tmp_path: Path):
    result = run_wl_pattern(
        artifacts_dir=tmp_path,
        write_gds=True,
        wl_length=30.0,
        tap_pitch=0.5,
    )
    rc_path = Path(result["rc_json"])
    assert rc_path.exists()
    assert rc_path.name == "wl_d10_m2_30um_rc.json"
    data = json.loads(rc_path.read_text(encoding="utf-8"))
    assert abs(data["metal_rc"]["r_ohm"] - 32.863353450309965 * 30) < 1e-6
    assert data["via"]["n_vias"] > 0
    assert "totals" in data
    assert abs(data["via"]["c_ff"] - data["via"]["n_vias"] * 0.1) < 1e-9
