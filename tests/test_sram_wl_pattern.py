"""SRAM long-WL baseline pattern tests (D10 driver + M2 trunk + PG taps)."""

from __future__ import annotations

import json
from pathlib import Path

import gdsfactory as gf

from gf_layout_flow.tech.pdk import activate_pdk
from gf_layout_flow.cells import (
    finfet_device,
    inverter,
    inverter_d10,
    bitcell_pg_load,
    wl_longline_pattern,
    od_height_um,
    FIN_PITCH_UM,
    CPP_UM,
)
from gf_layout_flow.cells.sram_wl_pattern import FIN_WIDTH_UM, M2_MIN_W_UM, M2_MIN_S_UM
from gf_layout_flow.rc import extract_rc_metrics
from gf_layout_flow.cli import run_wl_pattern


def setup_module():
    activate_pdk()


def test_od_height_formula():
    assert abs(FIN_PITCH_UM - 0.112) < 1e-9
    assert abs(od_height_um(1) - FIN_WIDTH_UM) < 1e-12
    assert abs(od_height_um(3) - ((3 - 1) * 0.112 + 0.034)) < 1e-12
    assert abs(CPP_UM - 0.057) < 1e-12


def test_finfet_device_multi_fin_finger():
    d = finfet_device(nfin=3, nfinger=10, is_nmos=True)
    assert isinstance(d, gf.Component)
    assert d.info["device"] == "nmos"
    assert d.info["nfin"] == 3
    assert d.info["nfinger"] == 10
    assert abs(float(d.info["od_height_um"]) - od_height_um(3)) < 1e-12
    assert float(d.info["cpp_um"]) == CPP_UM
    p = finfet_device(nfin=2, nfinger=1, is_nmos=False)
    assert p.info["device"] == "pmos"
    assert p.info.get("nw_placeholder") is True


def test_inverter_d10():
    inv = inverter_d10()
    assert inv.info["driver_strength"] == "D10"
    assert inv.info["nfin_driver"] == 3
    assert inv.info["nfinger_driver"] == 10
    assert inv.info["net_name"] == "WL"
    inv2 = inverter(nfin=3, nfinger=10)
    assert inv2.info["driver_strength"] == "D10"


def test_bitcell_pg_load():
    bc = bitcell_pg_load()
    assert bc.info["pg_nfin"] == 2
    assert bc.info["pg_nfinger"] == 1
    assert bc.info["n_pg"] == 2
    assert bc.info["net_name"] == "WL"


def _m2_poly_bboxes(component):
    """Return list of (xmin, ymin, xmax, ymax, width, height) for M2 polygons."""
    import numpy as np
    from gf_layout_flow.tech.layers import LAYER, layer_tuple

    pts = component.get_polygons_points(by="tuple")
    arrs = pts[layer_tuple(LAYER.M2)]
    out = []
    for a in arrs:
        a = np.asarray(a)
        xmin, ymin = float(a[:, 0].min()), float(a[:, 1].min())
        xmax, ymax = float(a[:, 0].max()), float(a[:, 1].max())
        out.append((xmin, ymin, xmax, ymax, xmax - xmin, ymax - ymin))
    return out


def test_wl_pattern_small_four_taps():
    """length=2.0, pitch=0.5 -> 4 taps at y=0.5, 1.0, 1.5, 2.0."""
    p = wl_longline_pattern(wl_length=2.0, tap_pitch=0.5)
    assert p.info["n_bitcells"] == 4
    assert p.info["n_bitcells"] == int(2.0 / 0.5)
    assert abs(float(p.info["first_tap_um"]) - 0.5) < 1e-9
    assert abs(float(p.info["last_tap_um"]) - 2.0) < 1e-9
    assert p.info["net_name"] == "WL"
    assert p.info["wl_direction"] == "Y"
    assert p.info["baseline_for_hb"] is True
    assert p.info["driver_strength"] == "D10"
    assert p.info["nfin_driver"] == 3
    assert p.info["nfinger_driver"] == 10
    assert abs(float(p.info["m2_width_um"]) - M2_MIN_W_UM) < 1e-12
    assert abs(float(p.info["m2_space_um"]) - M2_MIN_S_UM) < 1e-12
    assert abs(float(p.info["tap_pitch_um"]) - 0.5) < 1e-12
    assert p.info["pg_nfin"] == 2
    assert p.info["pg_nfinger"] == 1
    assert p.info["with_shields"] is False
    # WL length along Y; driver below origin; PG loads hang +X
    assert float(p.dymax) >= 2.0 - 1e-6
    assert float(p.dymin) < 0.0
    assert (float(p.dymax) - float(p.dymin)) > (float(p.dxmax) - float(p.dxmin))
    assert float(p.dxmax) > 0.2  # PG array extends +X
    m = extract_rc_metrics(p)
    used = set(m["layers_used"])
    assert "M2" in used
    assert "OD" in used
    assert "PO" in used
    assert used & {"VG", "VD", "M0", "M1", "VIA0", "VIA1"}


def test_wl_pattern_full_30um_builds():
    p = wl_longline_pattern()
    assert p.info["n_bitcells"] == 60
    assert p.info["n_bitcells"] == int(30.0 / 0.5)
    assert abs(float(p.info["wl_length_um"]) - 30.0) < 1e-12
    assert abs(float(p.info["first_tap_um"]) - 0.5) < 1e-9
    assert abs(float(p.info["last_tap_um"]) - 30.0) < 1e-9
    assert p.info["baseline_for_hb"] is True
    assert p.info["tap_placement"] == "first_at_pitch_last_at_length"
    assert p.info["wl_direction"] == "Y"
    # driver at y~=0, WL extends to 30 um along +Y
    assert float(p.dymax) >= 30.0 - 1e-6
    assert float(p.dymin) < 0.0
    # overall bbox is tall (Y) rather than wide (X); shields+PGs widen X a bit
    assert (float(p.dymax) - float(p.dymin)) > (float(p.dxmax) - float(p.dxmin))
    m = extract_rc_metrics(p)
    assert "M2" in m["layers_used"]
    assert m["totals"]["total_area_um2"] > 0


def test_wl_m2_trunk_is_vertical():
    """M2 WL trunk bbox height ~= 30 um, width ~= 0.02 um, centered on x=0."""
    p = wl_longline_pattern()
    boxes = _m2_poly_bboxes(p)
    long_vert = [b for b in boxes if abs(b[5] - 30.0) < 0.05]
    assert long_vert, "expected M2 polygons spanning ~30 um in Y"
    # trunk is the one closest to x=0; shields sit at +/- (w+s)
    trunk = min(long_vert, key=lambda b: abs(0.5 * (b[0] + b[2])))
    xmin, ymin, xmax, ymax, w, h = trunk
    assert abs(w - M2_MIN_W_UM) < 1e-6
    assert abs(h - 30.0) < 1e-6
    assert abs(0.5 * (xmin + xmax)) < 1e-9
    assert abs(ymin) < 1e-9
    assert abs(ymax - 30.0) < 1e-9
    # default: single WL trunk only (no neighbor shields)
    assert len(long_vert) == 1
    assert abs(0.5 * (long_vert[0][0] + long_vert[0][2])) < 1e-9


def test_wl_taps_along_y():
    """VIA1 tap stacks sit at y = 0.5, 1.0, ... (and driver at y~=0)."""
    import numpy as np
    from gf_layout_flow.tech.layers import LAYER, layer_tuple

    p = wl_longline_pattern(wl_length=2.0, tap_pitch=0.5)
    pts = p.get_polygons_points(by="tuple")[layer_tuple(LAYER.VIA1)]
    ys = sorted({round(float(np.asarray(a)[:, 1].mean()), 6) for a in pts})
    xs = [round(float(np.asarray(a)[:, 0].mean()), 6) for a in pts]
    for ty in (0.5, 1.0, 1.5, 2.0):
        assert any(abs(y - ty) < 1e-6 for y in ys)
    # taps (and driver output) centered on the vertical WL at x~=0
    assert all(abs(x) < 0.02 for x in xs)
    # driver body below first tap
    assert float(p.dymin) < 0.25


def test_cli_wl_pattern_small(tmp_path: Path):
    result = run_wl_pattern(
        artifacts_dir=tmp_path,
        write_gds=True,
        wl_length=2.0,
        tap_pitch=0.5,
    )
    gds = Path(result["gds"])
    js = Path(result["metrics_json"])
    assert gds.exists() and gds.stat().st_size > 0
    assert js.exists()
    data = json.loads(js.read_text(encoding="utf-8"))
    assert "layers_used" in data
    assert data["component_info"]["n_bitcells"] == 4
    assert data["component_info"]["baseline_for_hb"] is True
    assert data["component_info"]["wl_direction"] == "Y"
    assert result["n_bitcells"] == 4
    assert result.get("wl_direction") == "Y"


def test_wl_shields_optional_when_enabled():
    """Shields remain available via with_shields=True but are off by default."""
    p = wl_longline_pattern(wl_length=2.0, tap_pitch=0.5, with_shields=True)
    assert p.info["with_shields"] is True
    boxes = _m2_poly_bboxes(p)
    long_vert = [b for b in boxes if abs(b[5] - 2.0) < 0.05]
    assert len(long_vert) >= 3
