"""FEOL / MEOL parametric cells for full-custom transistor sketches.

Uses confirmed DRM CAD for OD/PO/MD/VG/VD/NP/PP and PLACEHOLDER NW
(source=placeholder_unverified — verify against T-N05-CL-LE-001).
"""

from __future__ import annotations

import gdsfactory as gf
from gdsfactory import Component

from gf_layout_flow.tech.pdk import activate_pdk
from gf_layout_flow.tech.layers import LAYER, layer_tuple
from gf_layout_flow.tech.cross_sections import (
    FEOL_DEFAULT_WIDTHS,
    FEOL_VIA_SIZES,
)

activate_pdk()


def _rect(c: Component, x0: float, y0: float, x1: float, y1: float, layer) -> None:
    c.add_polygon([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], layer=layer)


@gf.cell
def od_rect(
    width: float | None = None,
    length: float = 0.12,
) -> Component:
    """Active/diffusion rectangle (OD). width default = DRM OD.W.1 min."""
    w = FEOL_DEFAULT_WIDTHS["OD"] if width is None else width
    c = gf.Component()
    _rect(c, 0.0, -w / 2, length, w / 2, LAYER.OD)
    c.info["layer"] = "OD"
    c.info["width_um"] = w
    c.info["length_um"] = length
    return c


@gf.cell
def poly_gate(
    width: float | None = None,
    length: float = 0.10,
) -> Component:
    """Poly/gate strip (PO). width default = DRM PO.W.1 (Lg min)."""
    w = FEOL_DEFAULT_WIDTHS["PO"] if width is None else width
    c = gf.Component()
    _rect(c, 0.0, -w / 2, length, w / 2, LAYER.PO)
    c.info["layer"] = "PO"
    c.info["width_um"] = w
    c.info["length_um"] = length
    return c


@gf.cell
def md_strip(
    width: float | None = None,
    length: float = 0.08,
) -> Component:
    """MD local-interconnect strip."""
    w = FEOL_DEFAULT_WIDTHS["MD"] if width is None else width
    c = gf.Component()
    _rect(c, 0.0, -w / 2, length, w / 2, LAYER.MD)
    c.info["layer"] = "MD"
    c.info["width_um"] = w
    c.info["length_um"] = length
    return c


@gf.cell
def contact_vg(size: float | None = None) -> Component:
    """VG contact square (PO↔M0)."""
    sz = FEOL_VIA_SIZES["VG"] if size is None else size
    c = gf.Component()
    _rect(c, 0.0, 0.0, sz, sz, LAYER.VG)
    c.info["via"] = "VG"
    c.info["size_um"] = sz
    return c


@gf.cell
def contact_vd(size: float | None = None) -> Component:
    """VD contact square (MD↔M0)."""
    sz = FEOL_VIA_SIZES["VD"] if size is None else size
    c = gf.Component()
    _rect(c, 0.0, 0.0, sz, sz, LAYER.VD)
    c.info["via"] = "VD"
    c.info["size_um"] = sz
    return c


def _finger_core(
    *,
    is_nmos: bool,
    w_od: float,
    l_gate: float,
    od_extension: float,
    include_nw: bool,
) -> Component:
    """Shared OD+PO+implant+MD+VG/VD finger sketch.

    Geometry is illustrative (research), not DRC-clean.
    NW uses PLACEHOLDER CAD (1;0) — verify LE-001.
    """
    c = gf.Component()
    # OD length along x spans S/D + gate
    od_len = l_gate + 2 * od_extension
    od_y0, od_y1 = -w_od / 2, w_od / 2

    # Optional NW (PMOS required; NMOS may skip)
    if include_nw:
        # NW enclosure around OD (research slack)
        enc = 0.04
        _rect(c, -enc, od_y0 - enc, od_len + enc, od_y1 + enc, LAYER.NW)
        c.info["nw_placeholder"] = True
        c.info["nw_cad"] = list(layer_tuple(LAYER.NW))
        c.info["nw_source"] = "placeholder_unverified"

    _rect(c, 0.0, od_y0, od_len, od_y1, LAYER.OD)

    # Gate PO centered, runs across OD width with small overhang
    po_over = 0.01
    po_x0 = od_extension
    po_x1 = od_extension + l_gate
    _rect(c, po_x0, od_y0 - po_over, po_x1, od_y1 + po_over, LAYER.PO)

    # Implant covering OD (NP for NMOS, PP for PMOS)
    implant = LAYER.NP if is_nmos else LAYER.PP
    implant_name = "NP" if is_nmos else "PP"
    _rect(c, 0.0, od_y0, od_len, od_y1, implant)

    # MD strips on S/D regions + VD contacts
    md_w = FEOL_DEFAULT_WIDTHS["MD"]
    vd_sz = FEOL_VIA_SIZES["VD"]
    vg_sz = FEOL_VIA_SIZES["VG"]
    # Source MD (left)
    md_len = max(od_extension - 0.004, md_w)
    _rect(c, 0.002, -md_w / 2, md_len, md_w / 2, LAYER.MD)
    # Drain MD (right)
    _rect(c, od_len - md_len, -md_w / 2, od_len - 0.002, md_w / 2, LAYER.MD)
    # VD on S/D
    _rect(c, 0.004, -vd_sz / 2, 0.004 + vd_sz, vd_sz / 2, LAYER.VD)
    _rect(c, od_len - 0.004 - vd_sz, -vd_sz / 2, od_len - 0.004, vd_sz / 2, LAYER.VD)
    # VG on gate (center)
    gx = (po_x0 + po_x1) / 2 - vg_sz / 2
    _rect(c, gx, -vg_sz / 2, gx + vg_sz, vg_sz / 2, LAYER.VG)

    c.info["device"] = "nmos" if is_nmos else "pmos"
    c.info["w_od_um"] = w_od
    c.info["l_gate_um"] = l_gate
    c.info["implant"] = implant_name
    c.info["layers"] = [
        "OD",
        "PO",
        implant_name,
        "MD",
        "VG",
        "VD",
    ] + (["NW"] if include_nw else [])
    c.info["note"] = (
        "Sketch only; NW CAD is placeholder_unverified if present; "
        "not DRC-clean; verify LE-001 for NW/DNW/OD2/CM0"
    )
    return c


@gf.cell
def nmos_finger(
    w_od: float | None = None,
    l_gate: float | None = None,
    od_extension: float = 0.04,
    include_nw: bool = False,
) -> Component:
    """NMOS finger sketch: OD+PO+NP+MD+VG/VD. NW optional (default off)."""
    w = FEOL_DEFAULT_WIDTHS["OD"] * 2 if w_od is None else w_od
    lg = FEOL_DEFAULT_WIDTHS["PO"] if l_gate is None else l_gate
    return _finger_core(
        is_nmos=True, w_od=w, l_gate=lg, od_extension=od_extension, include_nw=include_nw
    )


@gf.cell
def pmos_finger(
    w_od: float | None = None,
    l_gate: float | None = None,
    od_extension: float = 0.04,
    include_nw: bool = True,
) -> Component:
    """PMOS finger sketch: OD+PO+PP+MD+VG/VD + NW (placeholder CAD).

    NW defaults ON because PMOS needs N-Well. CAD (1;0) is
    placeholder_unverified — verify against T-N05-CL-LE-001.
    """
    w = FEOL_DEFAULT_WIDTHS["OD"] * 2 if w_od is None else w_od
    lg = FEOL_DEFAULT_WIDTHS["PO"] if l_gate is None else l_gate
    return _finger_core(
        is_nmos=False, w_od=w, l_gate=lg, od_extension=od_extension, include_nw=include_nw
    )
