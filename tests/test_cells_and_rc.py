"""Basic tests: N5 1P13M cells and RC geometry metrics."""

from __future__ import annotations

import json
from pathlib import Path

import gdsfactory as gf

from gf_layout_flow.tech.pdk import activate_pdk, PDK_NAME, N5_DBU_UM
from gf_layout_flow.tech.layers import LAYER, METAL_LAYERS, VIA_LAYERS, layer_tuple
from gf_layout_flow.tech import LAYER_STACK, metal_xs, DEFAULT_WIDTHS
from gf_layout_flow.cells import (
    metal_wire,
    metal_bus,
    via_array,
    stacked_via,
    bitline_stripes,
    wordline_stripes,
    sram_interconnect_block,
    hb_pad,
    hb_pad_array,
)
from gf_layout_flow.rc import extract_rc_metrics, metrics_to_jsonable
from gf_layout_flow.cli import build_demo_top, run_demo


def setup_module():
    activate_pdk()


def test_layer_map_and_stack():
    assert layer_tuple(LAYER.M0) == (30, 151)
    assert layer_tuple(LAYER.M1) == (31, 171)
    assert layer_tuple(LAYER.M13) == (43, 40)
    assert layer_tuple(LAYER.AP) == (74, 0)
    assert layer_tuple(LAYER.VIA0) == (50, 150)
    assert layer_tuple(LAYER.RV) == (85, 0)
    assert layer_tuple(LAYER.HB_PAD) == (900, 0)
    assert layer_tuple(LAYER.HB_VIA) == (901, 0)
    assert "M0" in LAYER_STACK.layers
    assert "M13" in LAYER_STACK.layers
    assert "AP" in LAYER_STACK.layers
    assert "RV" in LAYER_STACK.layers
    assert "HB_PAD" in LAYER_STACK.layers
    assert len(METAL_LAYERS) == 15  # M0–M13 + AP
    assert "VIA12" in VIA_LAYERS
    # Cumulative stack: AP above M13
    assert LAYER_STACK.layers["AP"].zmin > LAYER_STACK.layers["M13"].zmin


def test_pdk_name_and_dbu():
    pdk = activate_pdk()
    assert pdk.name == PDK_NAME
    assert PDK_NAME == "n5_1p13m_beol"
    assert N5_DBU_UM == 0.0005
    assert abs(float(pdk.dbu) - 0.0005) < 1e-12


def test_default_widths_drm_min():
    assert DEFAULT_WIDTHS["M0"] == 0.014
    assert DEFAULT_WIDTHS["M1"] == 0.020
    assert DEFAULT_WIDTHS["M5"] == 0.038
    assert DEFAULT_WIDTHS["M12"] == 0.360
    assert DEFAULT_WIDTHS["AP"] == 1.8


def test_metal_xs():
    xs = metal_xs("M2", width=0.08)
    assert xs.width == 0.08
    xs_default = metal_xs("M12")
    assert xs_default.width == 0.360


def test_metal_wire_and_bus():
    w = metal_wire(length=5.0, width=0.05, metal="M1")
    assert isinstance(w, gf.Component)
    assert w.info["length_um"] == 5.0
    assert w.info.get("orientation", "X") == "X"
    b = metal_bus(length=10.0, metal="M2", n_fingers=3, pitch=0.1)
    assert b.info["n_fingers"] == 3
    m0 = metal_wire(length=2.0, metal="M0")
    assert m0.info["width_um"] == 0.014
    vy = metal_wire(length=30.0, width=0.020, metal="M2", orientation="Y")
    assert vy.info["orientation"] == "Y"
    assert abs(float(vy.dymax) - 30.0) < 1e-9
    assert abs(float(vy.dymin)) < 1e-12
    assert abs(float(vy.dxmax - vy.dxmin) - 0.020) < 1e-9
    assert abs(0.5 * (float(vy.dxmin) + float(vy.dxmax))) < 1e-12


def test_via_cells():
    v = via_array(via="VIA1", rows=2, cols=2)
    assert v.info["via"] == "VIA1"
    assert v.info["size_um"] == 0.016
    s = stacked_via(bottom_metal="M1", top_metal="M2")
    assert s.info["via"] == "VIA1"
    s0 = stacked_via(bottom_metal="M0", top_metal="M1")
    assert s0.info["via"] == "VIA0"
    srv = stacked_via(bottom_metal="M13", top_metal="AP")
    assert srv.info["via"] == "RV"


def test_sram_stripes():
    bl = bitline_stripes(n_bls=4, length=10.0, metal="M2")
    assert bl.info["n_stripes"] == 4
    wl = wordline_stripes(n_wls=4, length=8.0, metal="M3")
    assert wl.info["role"] == "wordline"
    block = sram_interconnect_block(n_bls=4, n_wls=4, bl_length=10.0, wl_length=8.0)
    assert block.info["n_bls"] == 4


def test_hb_pad_array():
    pad = hb_pad(pad_size=1.5, via_size=0.5)
    assert pad.info["area_um2"] == 1.5 * 1.5
    arr = hb_pad_array(rows=2, cols=3, pad_size=1.0, pitch=2.5)
    assert arr.info["n_pads"] == 6
    assert arr.info["pitch_um"] == 2.5


def test_extract_rc_metrics_on_tiny_cell():
    c = metal_wire(length=10.0, width=0.1, metal="M1")
    m = extract_rc_metrics(c)
    assert "layers_used" in m
    assert "M1" in m["layers_used"]
    assert m["per_layer"]["M1"]["area_um2"] > 0
    assert m["per_layer"]["M1"]["wire_length_um"] > 0
    assert m["units"] == "um"
    raw = json.dumps(metrics_to_jsonable(m))
    assert "M1" in raw


def test_extract_hb_metrics():
    arr = hb_pad_array(rows=2, cols=2, pad_size=2.0, pitch=4.0)
    m = extract_rc_metrics(arr)
    assert "HB_PAD" in m["layers_used"]
    hb = m["hybrid_bonding"]
    assert hb["pad_count"] == 4
    assert hb["pad_area_um2"] > 0
    assert hb["pitch_um"] == 4.0


def test_demo_build_and_run(tmp_path: Path):
    top = build_demo_top()
    assert isinstance(top, gf.Component)
    result = run_demo(artifacts_dir=tmp_path, write_gds=True)
    gds = Path(result["gds"])
    js = Path(result["metrics_json"])
    assert gds.exists() and gds.stat().st_size > 0
    assert js.exists()
    data = json.loads(js.read_text(encoding="utf-8"))
    assert "layers_used" in data
    assert data["totals"]["total_area_um2"] > 0
    assert data["hybrid_bonding"]["pitch_um"] == 4.0
    # Demo should touch several N5 metals + HB
    used = set(data["layers_used"])
    assert "HB_PAD" in used
    assert used & {"M0", "M2", "M5", "M12", "AP"}


def test_feol_layers_present():
    from gf_layout_flow.tech.layers import FEOL_LAYERS, MEOL_LAYERS, PLACEHOLDER_LAYERS

    assert layer_tuple(LAYER.OD) == (6, 0)
    assert layer_tuple(LAYER.PO) == (17, 0)
    assert layer_tuple(LAYER.MD) == (82, 150)
    assert layer_tuple(LAYER.VG) == (178, 150)
    assert layer_tuple(LAYER.VD) == (179, 150)
    assert layer_tuple(LAYER.NP) == (26, 0)
    assert layer_tuple(LAYER.PP) == (25, 0)
    # Placeholders
    assert layer_tuple(LAYER.NW) == (1, 0)
    assert layer_tuple(LAYER.DNW) == (3, 0)
    assert layer_tuple(LAYER.OD2) == (8, 0)
    assert layer_tuple(LAYER.CM0) == (29, 0)
    assert layer_tuple(LAYER.CM0A) == (29, 151)
    assert layer_tuple(LAYER.CM0B) == (29, 152)
    assert "OD" in FEOL_LAYERS and "NW" in FEOL_LAYERS
    assert "MD" in MEOL_LAYERS and "VG" in MEOL_LAYERS
    assert set(PLACEHOLDER_LAYERS) >= {"NW", "DNW", "OD2", "CM0", "CM0A", "CM0B"}
    assert "OD" in LAYER_STACK.layers
    assert "PO" in LAYER_STACK.layers
    assert "MD" in LAYER_STACK.layers
    assert "NW" in LAYER_STACK.layers
    # FEOL below M0
    assert LAYER_STACK.layers["OD"].zmin < LAYER_STACK.layers["M0"].zmin
    assert LAYER_STACK.layers["PO"].zmin < LAYER_STACK.layers["M0"].zmin


def test_feol_cells_build():
    from gf_layout_flow.cells import (
        od_rect,
        poly_gate,
        md_strip,
        contact_vg,
        contact_vd,
        nmos_finger,
        pmos_finger,
    )

    assert od_rect().info["layer"] == "OD"
    assert poly_gate().info["width_um"] == 0.006
    assert md_strip().info["layer"] == "MD"
    assert contact_vg().info["via"] == "VG"
    assert contact_vd().info["size_um"] == 0.014
    nmos = nmos_finger()
    assert nmos.info["device"] == "nmos"
    assert "NP" in nmos.info["layers"]
    assert "NW" not in nmos.info["layers"]
    pmos = pmos_finger()
    assert pmos.info["device"] == "pmos"
    assert "PP" in pmos.info["layers"]
    assert "NW" in pmos.info["layers"]
    assert pmos.info.get("nw_placeholder") is True
    assert pmos.info.get("nw_source") == "placeholder_unverified"


def test_feol_demo_artifacts(tmp_path: Path):
    from gf_layout_flow.cli import build_feol_demo, run_demo

    feol = build_feol_demo()
    assert isinstance(feol, gf.Component)
    result = run_demo(artifacts_dir=tmp_path, write_gds=True)
    assert Path(result["feol_gds"]).exists()
    data = json.loads(Path(result["feol_metrics_json"]).read_text(encoding="utf-8"))
    used = set(data["layers_used"])
    assert used & {"OD", "PO", "MD", "VG", "VD"}
    assert "NW" in used  # from pmos_finger
