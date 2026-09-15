"""L2 pi-ladder + Elmore delay tests (analytic sanity + 30 um baseline)."""

from __future__ import annotations

import json
import math
from pathlib import Path

from gf_layout_flow.tech.pdk import activate_pdk
from gf_layout_flow.tech.rc_table import get_metal_rc, get_via_rc
from gf_layout_flow.cells import wl_longline_pattern
from gf_layout_flow.rc import (
    extract_wl_rc,
    load_analysis_l2,
    build_pi_ladder_from_wl_rc,
    elmore_delays,
    analyze_wl_l2,
    format_l2_summary,
)
from gf_layout_flow.cli import run_wl_pattern
from gf_layout_flow import __version__


def setup_module():
    activate_pdk()


def test_version_0_7_0():
    assert __version__ == "0.7.0"


def test_analysis_l2_yaml_defaults():
    cfg = load_analysis_l2()
    assert cfg["R_drv_ohm"] == 200.0
    assert cfg["C_pg_ff_per_finger"] == 0.3
    assert cfg["C_pg_ff"] == 0.3
    assert cfg["n_pg_default"] == 2
    assert cfg["Vdd_V"] == 0.75
    assert cfg["R_drv_source"] == "placeholder_unverified"
    assert cfg["C_pg_source"] == "user_rule_0p3fF_per_finger"
    assert cfg["model"] == "pi_ladder_elmore"


def test_small_ladder_analytic_2seg():
    """Hand-checked 2-segment pi + Elmore (Ohm, fF -> ps)."""
    # Synthetic wl_rc-like ladder: 2 segs, R_seg=10, C_seg=2, C_via=4
    wl_rc = {
        "net": "WL",
        "metal": "M2",
        "length_um": 1.0,
        "n_bitcells": 2,
        "tap_pitch_um": 0.5,
        "metal_table": {"r_ohm_per_um": 20.0, "c_ff_per_um": 4.0, "source": "test"},
        "metal_rc": {"r_ohm": 20.0, "c_ff": 4.0},
        "via": {"n_vias": 4, "table": {"c_ff": 2.0, "source": "test"}},
        "totals": {},
        "component_info": {"n_pg": 2},
        "ladder": {
            "n_seg": 2,
            "seg_length_um": 0.5,
            "vias_per_tap": 2,
            "segments": [
                {
                    "index": 1,
                    "y_um": 0.5,
                    "seg_length_um": 0.5,
                    "r_seg_ohm": 10.0,
                    "c_seg_ff": 2.0,
                    "via_lump_at_tap": {"n_vias": 2, "c_ff": 4.0, "r_ohm": 25.0},
                },
                {
                    "index": 2,
                    "y_um": 1.0,
                    "seg_length_um": 0.5,
                    "r_seg_ohm": 10.0,
                    "c_seg_ff": 2.0,
                    "via_lump_at_tap": {"n_vias": 2, "c_ff": 4.0, "r_ohm": 25.0},
                },
            ],
        },
    }
    # include_c_pg=False so C_tap = 4 only
    ladder = build_pi_ladder_from_wl_rc(
        wl_rc, C_pg_ff=1.0, n_pg=2, C_drv_par_ff=0.0, include_c_pg=False
    )
    # C0 = 0 + 1 = 1; C1 = 1+1+4 = 6; C2 = 1+4 = 5
    assert abs(ladder["C_nodes_ff"][0] - 1.0) < 1e-12
    assert abs(ladder["C_nodes_ff"][1] - 6.0) < 1e-12
    assert abs(ladder["C_nodes_ff"][2] - 5.0) < 1e-12
    assert ladder["R_series_ohm"] == [10.0, 10.0]

    R_drv = 200.0
    el = elmore_delays(ladder, R_drv)
    # t0 = 200*1*1e-3 = 0.2
    # t1 = 0.2 + 210*6*1e-3 = 0.2 + 1.26 = 1.46
    # t2 = 1.46 + 220*5*1e-3 = 1.46 + 1.1 = 2.56
    assert abs(el["t_elmore_node0_ps"] - 0.2) < 1e-9
    assert abs(el["per_tap_delays_ps"][0] - 1.46) < 1e-9
    assert abs(el["t_elmore_end_ps"] - 2.56) < 1e-9


def test_small_ladder_with_pg_loads():
    wl_rc = {
        "net": "WL",
        "metal": "M2",
        "length_um": 2.0,
        "n_bitcells": 4,
        "tap_pitch_um": 0.5,
        "metal_table": {"r_ohm_per_um": 32.863353450309965, "c_ff_per_um": 0.215},
        "metal_rc": {"r_ohm": 65.7267, "c_ff": 0.43},
        "via": {"n_vias": 10, "table": {"c_ff": 2.0}},
        "totals": {},
        "component_info": {"n_pg": 2},
        "ladder": {
            "n_seg": 4,
            "seg_length_um": 0.5,
            "vias_per_tap": 2,
            "segments": [
                {
                    "index": i + 1,
                    "y_um": (i + 1) * 0.5,
                    "seg_length_um": 0.5,
                    "r_seg_ohm": 32.863353450309965 * 0.5,
                    "c_seg_ff": 0.215 * 0.5,
                    "via_lump_at_tap": {"n_vias": 2, "c_ff": 4.0, "r_ohm": 25.0},
                }
                for i in range(4)
            ],
        },
    }
    ladder_w = build_pi_ladder_from_wl_rc(wl_rc, include_c_pg=True, C_pg_ff=1.0, n_pg=2)
    ladder_o = build_pi_ladder_from_wl_rc(wl_rc, include_c_pg=False, C_pg_ff=1.0, n_pg=2)
    # Each tap: C_via=4 + 2*1 = 6 with PG; 4 without
    assert abs(ladder_w["C_tap_ff"][0] - 6.0) < 1e-12
    assert abs(ladder_o["C_tap_ff"][0] - 4.0) < 1e-12
    assert ladder_w["C_total_ff"] > ladder_o["C_total_ff"]

    el_w = elmore_delays(ladder_w, 200.0)
    el_o = elmore_delays(ladder_o, 200.0)
    assert el_w["t_elmore_end_ps"] > el_o["t_elmore_end_ps"]
    assert len(el_w["per_tap_delays_ps"]) == 4
    # Monotonic increasing tap delays
    taps = el_w["per_tap_delays_ps"]
    assert all(taps[i] <= taps[i + 1] for i in range(len(taps) - 1))


def test_analyze_wl_l2_30um_baseline():
    c = wl_longline_pattern(wl_length=30.0, tap_pitch=0.5)
    l2 = analyze_wl_l2(c)
    assert l2["level"] == "L2"
    assert l2["model"] == "pi_ladder_elmore"
    assert l2["R_drv_ohm"] == 200.0
    assert l2["C_pg_ff"] == 0.3
    assert l2["C_pg_ff_per_finger"] == 0.3
    assert l2["C_pg_load_ff"] == 0.6
    assert l2["C_pg_rule"] == "user_rule_0p3fF_per_finger"
    assert l2["pg_nfinger"] == 1
    assert l2["n_pg"] == 2
    assert l2["ladder"]["n_seg"] == 60
    assert abs(l2["ladder"]["seg_length_um"] - 0.5) < 1e-12
    assert len(l2["elmore"]["per_tap_delays_ps"]) == 60
    t_end = l2["elmore"]["t_elmore_end_ps"]
    assert t_end > 0
    assert l2["elmore"]["tau_with_loads_ps"] >= l2["elmore"]["tau_wire_only_ps"]
    assert "R_drv_ohm" in l2["placeholders"]
    assert "C_pg_ff" not in l2["placeholders"]
    # Energy proxy positive
    assert l2["energy_proxy"]["E_fj"] > 0
    # Consistent with L1 M2 numbers
    m2 = get_metal_rc("M2")
    assert m2 is not None
    assert abs(l2["ladder"]["r_ohm_per_um"] - m2["r_ohm_per_um"]) < 1e-9
    assert abs(l2["ladder"]["c_ff_per_um"] - m2["c_ff_per_um"]) < 1e-12
    # Via C at tap = 0.2 fF (VIA0+VIA1, each 0.1 fF)
    via = get_via_rc()
    assert via["c_ff"] == 0.1
    assert abs(l2["ladder"]["C_via_at_tap_ff"] - 2 * via["c_ff"]) < 1e-12
    assert abs(l2["ladder"]["C_via_at_tap_ff"] - 0.2) < 1e-12


def test_analyze_wl_l2_from_wl_rc_dict():
    c = wl_longline_pattern(wl_length=2.0, tap_pitch=0.5)
    wl_rc = extract_wl_rc(c)
    l2 = analyze_wl_l2(wl_rc)
    assert l2["ladder"]["n_seg"] == 4
    assert l2["elmore"]["t_elmore_end_ps"] > 0


def test_format_l2_summary_ascii():
    c = wl_longline_pattern(wl_length=2.0)
    l2 = analyze_wl_l2(c)
    s = format_l2_summary(l2)
    assert s.startswith("L2 Elmore:")
    assert "t_end=" in s
    assert "ps" in s
    assert "R_drv=" in s
    assert "C_pg=" in s
    # No micro sign
    assert "\u00b5" not in s
    assert "µ" not in s


def test_cli_writes_l2_json(tmp_path: Path):
    result = run_wl_pattern(
        artifacts_dir=tmp_path,
        write_gds=False,
        wl_length=30.0,
        tap_pitch=0.5,
    )
    l2_path = Path(result["l2_json"])
    assert l2_path.exists()
    assert l2_path.name == "wl_d10_m2_30um_l2.json"
    data = json.loads(l2_path.read_text(encoding="utf-8"))
    assert data["level"] == "L2"
    assert data["R_drv_ohm"] == 200.0
    assert data["C_pg_ff"] == 0.3
    assert data["elmore"]["t_elmore_end_ps"] > 0
    assert "l2" in result
    assert abs(result["l2"]["elmore"]["t_elmore_end_ps"] - data["elmore"]["t_elmore_end_ps"]) < 1e-9


def test_elmore_scales_with_r_drv():
    c = wl_longline_pattern(wl_length=5.0)
    a = analyze_wl_l2(c, R_drv=100.0)
    b = analyze_wl_l2(c, R_drv=400.0)
    assert b["elmore"]["t_elmore_end_ps"] > a["elmore"]["t_elmore_end_ps"]
