"""SRAM long-WL RC/layout baseline (pre-Hybrid-Bonding).

Research-grade N5 sketches (not DRC-clean). Driver is a D10 inverter
(NMOS+PMOS each 3 nfin x 10 finger). Output net **WL** is an M2 (Mx)
trunk running in **Y** (SRAM convention); bitcell pass-gate loads tap
the trunk every tap_pitch and hang sideways in +X.

Tap placement (documented choice)
---------------------------------
n_bitcells = int(wl_length / tap_pitch)  # 30 / 0.5 = 60
Driver at y ~= 0; WL runs +y to wl_length.
Taps at y = tap_pitch, 2*tap_pitch, ..., n_bitcells*tap_pitch
  e.g. 0.5, 1.0, ..., 30.0 um
First tap is NOT at y=0 so the driver output is not shorted into a
bitcell sitting on top of the inverter.

Geometry constants (N5 DRM mins / PO_P57)
-----------------------------------------
- Fin/OD: W=0.034 um, S=0.078 um -> pitch=0.112 um
- nfin OD height ~= (nfin-1)*0.112 + 0.034
- PO Lg min = 0.006 um; multi-finger pitch CPP ~= 0.057 um (PO_P57)
- Via stack up to M2: VG/VD -> M0 -> VIA0 -> M1 -> VIA1 -> M2
"""

from __future__ import annotations

import gdsfactory as gf
from gdsfactory import Component

from gf_layout_flow.tech.pdk import activate_pdk
from gf_layout_flow.tech.layers import LAYER, METAL_LAYERS, VIA_LAYERS
from gf_layout_flow.tech.cross_sections import (
    DEFAULT_WIDTHS,
    DEFAULT_VIA_SIZES,
    DEFAULT_SPACING,
    FEOL_DEFAULT_WIDTHS,
    FEOL_VIA_SIZES,
)
from gf_layout_flow.cells.metal import metal_wire

activate_pdk()

# --- N5 research geometry (DRM mins; not DRC-clean) ---
FIN_WIDTH_UM = 0.034
FIN_SPACE_UM = 0.078
FIN_PITCH_UM = FIN_WIDTH_UM + FIN_SPACE_UM  # 0.112
LG_MIN_UM = 0.006
CPP_UM = 0.057  # contacted poly pitch, PO_P57 class
PO_OVERHANG_UM = 0.012
OD_SD_EXT_UM = 0.025
NW_ENCLOSURE_UM = 0.040
IMPLANT_ENCLOSURE_UM = 0.010

M2_MIN_W_UM = 0.020
M2_MIN_S_UM = 0.015

TAP_PLACEMENT_NOTE = (
    "Driver at y~=0; WL runs +y. Taps at y = k*tap_pitch for k=1..n_bitcells "
    "(first tap at tap_pitch, last at n_bitcells*tap_pitch). "
    "Example 30 um / 0.5 um -> 60 taps at 0.5, 1.0, ..., 30.0 um. "
    "Chosen so the driver is not shorted into a bitcell at y=0. "
    "PG loads hang off the vertical WL in +X."
)


def od_height_um(nfin: int, fin_pitch: float = FIN_PITCH_UM, fin_width: float = FIN_WIDTH_UM) -> float:
    """nfin OD height ~= (nfin-1)*fin_pitch + fin_width."""
    nfin = max(int(nfin), 1)
    return (nfin - 1) * fin_pitch + fin_width


def od_length_um(nfinger: int, l_gate: float = LG_MIN_UM, cpp: float = CPP_UM, sd_ext: float = OD_SD_EXT_UM) -> float:
    nfinger = max(int(nfinger), 1)
    return (nfinger - 1) * cpp + l_gate + 2 * sd_ext


def _rect(c: Component, x0: float, y0: float, x1: float, y1: float, layer) -> None:
    if x1 < x0:
        x0, x1 = x1, x0
    if y1 < y0:
        y0, y1 = y1, y0
    c.add_polygon([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], layer=layer)


def _sq(c: Component, cx: float, cy: float, size: float, layer) -> None:
    h = size / 2.0
    _rect(c, cx - h, cy - h, cx + h, cy + h, layer)


def _via_stack_m0_to_m2(c: Component, cx: float, cy: float, m2_width: float | None = None) -> None:
    """VG-path BEOL: M0 / VIA0 / M1 / VIA1 / M2 pads centered at (cx, cy)."""
    via0 = DEFAULT_VIA_SIZES["VIA0"]
    via1 = DEFAULT_VIA_SIZES["VIA1"]
    enc = 0.002
    m0s = max(DEFAULT_WIDTHS["M0"], via0 + 2 * enc)
    m1s = max(DEFAULT_WIDTHS["M1"], via0 + 2 * enc, via1 + 2 * enc)
    m2s = max(m2_width or DEFAULT_WIDTHS["M2"], via1 + 2 * enc)
    _sq(c, cx, cy, m0s, LAYER.M0)
    _sq(c, cx, cy, via0, LAYER.VIA0)
    _sq(c, cx, cy, m1s, LAYER.M1)
    _sq(c, cx, cy, via1, LAYER.VIA1)
    _sq(c, cx, cy, m2s, LAYER.M2)


def _copy_info(dst: Component, src: Component) -> None:
    try:
        mapping = dict(src.info)
    except Exception:
        mapping = {}
    for k, v in mapping.items():
        try:
            dst.info[k] = v
        except Exception:
            pass


@gf.cell
def finfet_device(
    nfin: int = 3,
    nfinger: int = 1,
    is_nmos: bool = True,
    l_gate: float = LG_MIN_UM,
    cpp: float = CPP_UM,
    fin_pitch: float = FIN_PITCH_UM,
    fin_width: float = FIN_WIDTH_UM,
    sd_ext: float = OD_SD_EXT_UM,
    include_nw: bool | None = None,
) -> Component:
    """Multi-fin multi-finger FinFET sketch (OD fins + PO fingers + MD/VG/VD/M0).

    Origin: left edge of OD, y=0 at the vertical center of the fin array.
    Even S/D regions (0, 2, ...) are source; odd regions are drain.
    """
    nfin = max(int(nfin), 1)
    nfinger = max(int(nfinger), 1)
    if include_nw is None:
        include_nw = not is_nmos

    c = gf.Component()
    od_h = od_height_um(nfin, fin_pitch=fin_pitch, fin_width=fin_width)
    od_len = od_length_um(nfinger, l_gate=l_gate, cpp=cpp, sd_ext=sd_ext)
    od_y0, od_y1 = -od_h / 2.0, od_h / 2.0

    if include_nw:
        enc = NW_ENCLOSURE_UM
        _rect(c, -enc, od_y0 - enc, od_len + enc, od_y1 + enc, LAYER.NW)
        c.info["nw_placeholder"] = True
        c.info["nw_source"] = "placeholder_unverified"

    # Individual fins (FinFET OD)
    for i in range(nfin):
        yc = (i - (nfin - 1) / 2.0) * fin_pitch
        _rect(c, 0.0, yc - fin_width / 2.0, od_len, yc + fin_width / 2.0, LAYER.OD)

    # Implant covering the fin array
    implant = LAYER.NP if is_nmos else LAYER.PP
    implant_name = "NP" if is_nmos else "PP"
    ie = IMPLANT_ENCLOSURE_UM
    _rect(c, -ie, od_y0 - ie, od_len + ie, od_y1 + ie, implant)

    md_w = FEOL_DEFAULT_WIDTHS["MD"]
    vd_sz = FEOL_VIA_SIZES["VD"]
    vg_sz = FEOL_VIA_SIZES["VG"]
    m0_w = DEFAULT_WIDTHS["M0"]

    gate_xs: list[float] = []
    po_over = PO_OVERHANG_UM
    for j in range(nfinger):
        gx0 = sd_ext + j * cpp
        gx1 = gx0 + l_gate
        _rect(c, gx0, od_y0 - po_over, gx1, od_y1 + po_over, LAYER.PO)
        gcx = 0.5 * (gx0 + gx1)
        gate_xs.append(gcx)
        # VG on PO overhang (top) + M0 landing
        vg_cy = od_y1 + po_over - vg_sz / 2.0
        _sq(c, gcx, vg_cy, vg_sz, LAYER.VG)
        _sq(c, gcx, vg_cy, max(m0_w, vg_sz), LAYER.M0)

    vg_y = od_y1 + po_over - vg_sz / 2.0
    if gate_xs:
        _rect(
            c,
            gate_xs[0] - m0_w / 2.0,
            vg_y - m0_w / 2.0,
            gate_xs[-1] + m0_w / 2.0,
            vg_y + m0_w / 2.0,
            LAYER.M0,
        )

    # S/D regions: nfinger+1. Even = source, odd = drain.
    source_xs: list[float] = []
    drain_xs: list[float] = []
    for k in range(nfinger + 1):
        if k == 0:
            x0, x1 = 0.0, sd_ext
        elif k == nfinger:
            x0, x1 = sd_ext + (nfinger - 1) * cpp + l_gate, od_len
        else:
            prev_g1 = sd_ext + (k - 1) * cpp + l_gate
            next_g0 = sd_ext + k * cpp
            x0, x1 = prev_g1, next_g0
        cx = 0.5 * (x0 + x1)
        half = min(md_w / 2.0, max((x1 - x0) / 2.0 - 0.001, 0.004))
        _rect(c, cx - half, od_y0, cx + half, od_y1, LAYER.MD)
        _sq(c, cx, 0.0, vd_sz, LAYER.VD)
        _sq(c, cx, 0.0, max(m0_w, vd_sz), LAYER.M0)
        if k % 2 == 0:
            source_xs.append(cx)
        else:
            drain_xs.append(cx)

    # Drain M0 strap along x (output pickup)
    if drain_xs:
        _rect(
            c,
            min(drain_xs) - m0_w / 2.0,
            -m0_w / 2.0,
            max(drain_xs) + m0_w / 2.0,
            m0_w / 2.0,
            LAYER.M0,
        )

    c.info["device"] = "nmos" if is_nmos else "pmos"
    c.info["nfin"] = nfin
    c.info["nfinger"] = nfinger
    c.info["l_gate_um"] = float(l_gate)
    c.info["cpp_um"] = float(cpp)
    c.info["fin_pitch_um"] = float(fin_pitch)
    c.info["fin_width_um"] = float(fin_width)
    c.info["od_height_um"] = float(od_h)
    c.info["od_length_um"] = float(od_len)
    c.info["implant"] = implant_name
    c.info["gate_x0_um"] = float(gate_xs[0]) if gate_xs else 0.0
    c.info["gate_x_last_um"] = float(gate_xs[-1]) if gate_xs else 0.0
    c.info["vg_y_um"] = float(vg_y)
    c.info["drain_x_right_um"] = float(drain_xs[-1]) if drain_xs else float(od_len)
    c.info["drain_x0_um"] = float(drain_xs[0]) if drain_xs else float(od_len / 2.0)
    c.info["source_x0_um"] = float(source_xs[0]) if source_xs else 0.0
    c.info["n_drain"] = len(drain_xs)
    c.info["n_source"] = len(source_xs)
    c.info["note"] = (
        "Sketch only; multi-fin/finger using N5 DRM mins + CPP=0.057 (PO_P57); "
        "not DRC-clean; NW CAD placeholder_unverified if present"
    )
    return c


@gf.cell
def inverter(
    nfin: int = 3,
    nfinger: int = 10,
    l_gate: float = LG_MIN_UM,
    cpp: float = CPP_UM,
) -> Component:
    """CMOS inverter: NMOS+PMOS pair, shared drain via-stack up to M2 (net WL)."""
    c = gf.Component()
    nmos = finfet_device(nfin=nfin, nfinger=nfinger, is_nmos=True, l_gate=l_gate, cpp=cpp)
    pmos = finfet_device(nfin=nfin, nfinger=nfinger, is_nmos=False, l_gate=l_gate, cpp=cpp)
    od_h = float(nmos.info["od_height_um"])
    od_len = float(nmos.info["od_length_um"])
    sep = od_h / 2.0 + 0.080
    rn = c.add_ref(nmos)
    rp = c.add_ref(pmos)
    rn.move((0.0, -sep))
    rp.move((0.0, sep))

    dx = float(nmos.info["drain_x_right_um"])
    gx = float(nmos.info["gate_x0_um"])
    m0_w = DEFAULT_WIDTHS["M0"]
    m2_w = DEFAULT_WIDTHS["M2"]

    # Shared input (gates) at M0 only — not the WL
    _rect(c, gx - m0_w / 2.0, -sep, gx + m0_w / 2.0, sep, LAYER.M0)
    # Shared output (drains) M0 spine + via stack to M2
    _rect(c, dx - m0_w / 2.0, -sep, dx + m0_w / 2.0, sep, LAYER.M0)
    _via_stack_m0_to_m2(c, dx, 0.0, m2_width=m2_w)
    out_x = od_len + 0.020
    _rect(c, dx, -m2_w / 2.0, out_x, m2_w / 2.0, LAYER.M2)

    c.add_port(
        name="WL",
        center=(out_x, 0.0),
        width=m2_w,
        orientation=0,
        layer=LAYER.M2,
        port_type="electrical",
    )
    c.add_label(text="WL", position=(out_x, 0.040), layer=LAYER.LABEL)

    strength = f"D{nfinger}"
    c.info["driver_strength"] = strength
    c.info["nfin_driver"] = int(nfin)
    c.info["nfinger_driver"] = int(nfinger)
    c.info["net_name"] = "WL"
    c.info["out_x_um"] = float(out_x)
    c.info["out_y_um"] = 0.0
    c.info["od_length_um"] = float(od_len)
    c.info["od_height_um"] = float(od_h)
    c.info["cpp_um"] = float(cpp)
    c.info["l_gate_um"] = float(l_gate)
    return c


@gf.cell
def inverter_d10() -> Component:
    """D10 inverter: NMOS + PMOS each 3 nfin x 10 finger (WL driver)."""
    c = gf.Component()
    inv = inverter(nfin=3, nfinger=10)
    ref = c.add_ref(inv)
    try:
        c.add_ports(ref.ports)
    except Exception:
        pass
    _copy_info(c, inv)
    c.info["driver_strength"] = "D10"
    return c


@gf.cell
def bitcell_pg_load(
    pg_nfin: int = 2,
    pg_nfinger: int = 1,
    net_name: str = "WL",
    m2_width: float = M2_MIN_W_UM,
) -> Component:
    """Two PG FETs (default 2 nfin x 1 finger), gates tied to a WL M2 tap.

    Local origin: M2 tap / via stack at (0, 0) so the parent can place the
    cell at each WL tap coordinate. Drawn hanging in -Y; wl_longline_pattern
    rotates +90 deg so loads hang in +X off a vertical (Y) WL. PG
    drains/sources stay as local MD stubs (load capacitance geometry —
    not a full 6T bitcell).
    """
    c = gf.Component()
    pg = finfet_device(nfin=pg_nfin, nfinger=pg_nfinger, is_nmos=True)
    od_h = float(pg.info["od_height_um"])
    gx = float(pg.info["gate_x0_um"])
    vg_y = float(pg.info["vg_y_um"])

    y_upper = -0.16
    y_lower = y_upper - od_h - 0.060
    r_u = c.add_ref(pg)
    r_l = c.add_ref(pg)
    r_u.move((-gx, y_upper))
    r_l.move((-gx, y_lower))

    vg_u = y_upper + vg_y
    vg_l = y_lower + vg_y
    m0_w = max(DEFAULT_WIDTHS["M0"], 0.014)
    m1_w = DEFAULT_WIDTHS["M1"]
    y_bot = min(vg_u, vg_l) - m0_w / 2.0

    # M0/M1 strap from WL tap (y=0) down to both PG gate contacts
    _rect(c, -m0_w / 2.0, y_bot, m0_w / 2.0, m0_w / 2.0, LAYER.M0)
    _rect(c, -m1_w / 2.0, y_bot, m1_w / 2.0, m1_w / 2.0, LAYER.M1)

    # M2 stub toward the PG array + via stack onto the WL trunk
    stub_len = 0.040
    _rect(c, -m2_width / 2.0, -stub_len, m2_width / 2.0, m2_width / 2.0, LAYER.M2)
    _via_stack_m0_to_m2(c, 0.0, 0.0, m2_width=m2_width)

    c.add_port(
        name=net_name,
        center=(0.0, 0.0),
        width=m2_width,
        orientation=90,
        layer=LAYER.M2,
        port_type="electrical",
    )
    c.add_label(text=net_name, position=(0.0, 0.030), layer=LAYER.LABEL)

    c.info["pg_nfin"] = int(pg_nfin)
    c.info["pg_nfinger"] = int(pg_nfinger)
    c.info["n_pg"] = 2
    c.info["net_name"] = net_name
    c.info["m2_width_um"] = float(m2_width)
    c.info["role"] = "bitcell_pg_load"
    return c


def _tap_ys(wl_length: float, tap_pitch: float) -> list[float]:
    """Tap coordinates along +Y: pitch, 2*pitch, ..., n*pitch."""
    n = int(wl_length / tap_pitch)
    return [round((i + 1) * tap_pitch, 9) for i in range(n)]


@gf.cell
def wl_longline_pattern(
    wl_length: float = 30.0,
    tap_pitch: float = 0.5,
    m2_width: float = M2_MIN_W_UM,
    m2_space: float = M2_MIN_S_UM,
    with_shields: bool = False,
    nfin_driver: int = 3,
    nfinger_driver: int = 10,
    pg_nfin: int = 2,
    pg_nfinger: int = 1,
    net_name: str = "WL",
) -> Component:
    """D10 (or parametric) inverter + vertical M2 WL trunk + bitcell PG taps.

    SRAM convention: WL runs along +Y. Driver at y~=0 feeds the trunk
    upward. PG loads hang off the trunk in +X. Baseline before Hybrid
    Bonding experiments. Keep parametric.
    """
    if tap_pitch <= 0 or wl_length <= 0:
        raise ValueError("wl_length and tap_pitch must be positive")

    c = gf.Component()
    n_bitcells = int(wl_length / tap_pitch)
    tap_ys = _tap_ys(wl_length, tap_pitch)
    first_tap = tap_ys[0] if tap_ys else 0.0
    last_tap = tap_ys[-1] if tap_ys else 0.0

    inv = inverter(nfin=nfin_driver, nfinger=nfinger_driver)
    iref = c.add_ref(inv)
    out_x = float(inv.info["out_x_um"])
    out_y = float(inv.info["out_y_um"])
    # +90 deg: native +X WL stub faces +Y. Then park the output at origin
    # so the driver body sits at y<=0 and does not overlap the first tap.
    iref.rotate(90)
    iref.move((-out_y, -out_x))

    wl = metal_wire(length=wl_length, width=m2_width, metal="M2", orientation="Y")
    c.add_ref(wl)

    if with_shields:
        pitch = m2_width + m2_space
        sh = metal_wire(length=wl_length, width=m2_width, metal="M2", orientation="Y")
        c.add_ref(sh).movex(pitch)
        c.add_ref(sh).movex(-pitch)

    pg = bitcell_pg_load(
        pg_nfin=pg_nfin,
        pg_nfinger=pg_nfinger,
        net_name=net_name,
        m2_width=m2_width,
    )
    for ty in tap_ys:
        pref = c.add_ref(pg)
        # Local PG hang is -Y; +90 deg makes the array hang in +X (sideways).
        pref.rotate(90)
        pref.move((0.0, ty))

    c.add_port(
        name=net_name,
        center=(0.0, 0.0),
        width=m2_width,
        orientation=270,
        layer=LAYER.M2,
        port_type="electrical",
    )
    c.add_port(
        name=f"{net_name}_end",
        center=(0.0, wl_length),
        width=m2_width,
        orientation=90,
        layer=LAYER.M2,
        port_type="electrical",
    )
    c.add_label(text=net_name, position=(0.080, 0.0), layer=LAYER.LABEL)
    c.add_label(text=net_name, position=(0.080, wl_length), layer=LAYER.LABEL)

    c.info["driver_strength"] = f"D{nfinger_driver}"
    c.info["nfin_driver"] = int(nfin_driver)
    c.info["nfinger_driver"] = int(nfinger_driver)
    c.info["wl_length_um"] = float(wl_length)
    c.info["wl_direction"] = "Y"
    c.info["tap_pitch_um"] = float(tap_pitch)
    c.info["n_bitcells"] = int(n_bitcells)
    c.info["m2_width_um"] = float(m2_width)
    c.info["m2_space_um"] = float(m2_space)
    c.info["pg_nfin"] = int(pg_nfin)
    c.info["pg_nfinger"] = int(pg_nfinger)
    c.info["net_name"] = net_name
    c.info["baseline_for_hb"] = True
    c.info["with_shields"] = bool(with_shields)
    c.info["first_tap_um"] = float(first_tap)
    c.info["last_tap_um"] = float(last_tap)
    c.info["cpp_um"] = float(CPP_UM)
    c.info["fin_pitch_um"] = float(FIN_PITCH_UM)
    c.info["tap_placement"] = "first_at_pitch_last_at_length"
    c.info["tap_placement_note"] = TAP_PLACEMENT_NOTE
    c.info["via_stack"] = "VG/VD-M0-VIA0-M1-VIA1-M2"
    return c


# ---------------------------------------------------------------------------
# Hybrid-Bonding fold pattern (half array on upper die)
# ---------------------------------------------------------------------------

HB_STACK_MAP_NOTE = (
    "User said M2~M14 for the HB climb. This PDK is 1P13M: M0..M13 + AP "
    "(no M14 CAD layer). Research mapping: M14 ≈ AP / HB landing. "
    "Vertical path = M2→M3→…→M13→RV→AP→HB_PAD/HB_VIA, mirrored reverse on "
    "the upper die back to M2. Count VIA2..VIA12 + RV once per climb; "
    "round-trip = two climbs + one HB instance."
)


@gf.cell
def wl_hb_fold_pattern(
    wl_length_per_die: float = 15.0,
    tap_pitch: float = 0.5,
    m2_width: float = M2_MIN_W_UM,
    m2_space: float = M2_MIN_S_UM,
    with_shields: bool = False,
    nfin_driver: int = 3,
    nfinger_driver: int = 10,
    pg_nfin: int = 2,
    pg_nfinger: int = 1,
    net_name: str = "WL",
    upper_x_offset: float = -1.50,
    hb_pad_size: float = 0.50,
    hb_via_size: float = 0.324,
    draw_upper_descend_stack: bool = True,
) -> Component:
    """D10 driver + HB-folded WL: 15 um / 30 taps lower + 15 um / 30 taps upper.

    Lower die: like ``wl_longline_pattern`` with length=15, n_bitcells=30,
    shields off. At the driver (y≈0) a vertical via climb M2…AP + HB pad
    connects conceptually to the upper die. Upper die is drawn as a second
    M2 trunk offset in X (``upper_x_offset``, default negative X) with the
    other 30 taps; optional mirrored descend stack at the upper WL start
    for visual completeness. Research sketch — not DRC-clean.
    """
    from gf_layout_flow.cells.metal import hb_climb_stack, HB_CLIMB_VIAS

    if tap_pitch <= 0 or wl_length_per_die <= 0:
        raise ValueError("wl_length_per_die and tap_pitch must be positive")

    c = gf.Component()
    n_bitcells_die = int(wl_length_per_die / tap_pitch)
    tap_ys = _tap_ys(wl_length_per_die, tap_pitch)
    first_tap = tap_ys[0] if tap_ys else 0.0
    last_tap = tap_ys[-1] if tap_ys else 0.0

    # --- Driver (same placement as wl_longline_pattern) ---
    inv = inverter(nfin=nfin_driver, nfinger=nfinger_driver)
    iref = c.add_ref(inv)
    out_x = float(inv.info["out_x_um"])
    out_y = float(inv.info["out_y_um"])
    iref.rotate(90)
    iref.move((-out_y, -out_x))

    # --- Lower die M2 trunk + PG taps (+X) ---
    wl_lower = metal_wire(
        length=wl_length_per_die, width=m2_width, metal="M2", orientation="Y"
    )
    c.add_ref(wl_lower)

    if with_shields:
        pitch = m2_width + m2_space
        sh = metal_wire(
            length=wl_length_per_die, width=m2_width, metal="M2", orientation="Y"
        )
        c.add_ref(sh).movex(pitch)
        c.add_ref(sh).movex(-pitch)

    pg = bitcell_pg_load(
        pg_nfin=pg_nfin,
        pg_nfinger=pg_nfinger,
        net_name=net_name,
        m2_width=m2_width,
    )
    for ty in tap_ys:
        pref = c.add_ref(pg)
        pref.rotate(90)
        pref.move((0.0, ty))

    # --- HB climb at driver column (y≈0) ---
    climb = hb_climb_stack(
        hb_pad_size=hb_pad_size,
        hb_via_size=hb_via_size,
        include_hb=True,
    )
    c.add_ref(climb)  # centered at (0, 0)

    # --- Upper die M2 trunk (offset in X) + PG taps ---
    wl_upper = metal_wire(
        length=wl_length_per_die, width=m2_width, metal="M2", orientation="Y"
    )
    c.add_ref(wl_upper).movex(upper_x_offset)

    # Short M2 stub conceptually tying HB column to upper trunk start
    stub_len = abs(float(upper_x_offset))
    if stub_len > 1e-6:
        # Horizontal M2 from x=0 to upper_x_offset at y=0 (research stub; RC neglects)
        x0, x1 = (upper_x_offset, 0.0) if upper_x_offset < 0 else (0.0, upper_x_offset)
        _rect(c, x0, -m2_width / 2.0, x1, m2_width / 2.0, LAYER.M2)

    for ty in tap_ys:
        pref = c.add_ref(pg)
        pref.rotate(90)
        # Hang +X from upper trunk: place tap at (upper_x_offset, ty)
        pref.move((upper_x_offset, ty))

    if draw_upper_descend_stack:
        # Visual descend stack near upper WL start (no second HB pad)
        descend = hb_climb_stack(
            hb_pad_size=hb_pad_size,
            hb_via_size=hb_via_size,
            include_hb=False,
        )
        c.add_ref(descend).move((upper_x_offset, 0.0))

    # Ports
    c.add_port(
        name=f"{net_name}_lower",
        center=(0.0, 0.0),
        width=m2_width,
        orientation=270,
        layer=LAYER.M2,
        port_type="electrical",
    )
    c.add_port(
        name=f"{net_name}_lower_end",
        center=(0.0, wl_length_per_die),
        width=m2_width,
        orientation=90,
        layer=LAYER.M2,
        port_type="electrical",
    )
    c.add_port(
        name=f"{net_name}_upper",
        center=(upper_x_offset, 0.0),
        width=m2_width,
        orientation=270,
        layer=LAYER.M2,
        port_type="electrical",
    )
    c.add_port(
        name=f"{net_name}_upper_end",
        center=(upper_x_offset, wl_length_per_die),
        width=m2_width,
        orientation=90,
        layer=LAYER.M2,
        port_type="electrical",
    )

    c.add_label(text=f"{net_name}_lower", position=(0.080, 0.0), layer=LAYER.LABEL)
    c.add_label(
        text=f"{net_name}_lower",
        position=(0.080, wl_length_per_die),
        layer=LAYER.LABEL,
    )
    c.add_label(
        text=f"{net_name}_upper",
        position=(upper_x_offset - 0.080, 0.0),
        layer=LAYER.LABEL,
    )
    c.add_label(text="die=lower", position=(0.20, wl_length_per_die / 2.0), layer=LAYER.LABEL)
    c.add_label(
        text="die=upper",
        position=(upper_x_offset - 0.20, wl_length_per_die / 2.0),
        layer=LAYER.LABEL,
    )
    c.add_label(text="HB", position=(0.0, -0.40), layer=LAYER.LABEL)

    c.info["topology"] = "hb_fold"
    c.info["driver_strength"] = f"D{nfinger_driver}"
    c.info["nfin_driver"] = int(nfin_driver)
    c.info["nfinger_driver"] = int(nfinger_driver)
    c.info["wl_length_um"] = float(wl_length_per_die)  # per-die (compat)
    c.info["wl_length_lower_um"] = float(wl_length_per_die)
    c.info["wl_length_upper_um"] = float(wl_length_per_die)
    c.info["wl_direction"] = "Y"
    c.info["tap_pitch_um"] = float(tap_pitch)
    c.info["n_bitcells"] = int(n_bitcells_die)  # per-die (compat)
    c.info["n_bitcells_lower"] = int(n_bitcells_die)
    c.info["n_bitcells_upper"] = int(n_bitcells_die)
    c.info["n_bitcells_total"] = int(2 * n_bitcells_die)
    c.info["m2_width_um"] = float(m2_width)
    c.info["m2_space_um"] = float(m2_space)
    c.info["pg_nfin"] = int(pg_nfin)
    c.info["pg_nfinger"] = int(pg_nfinger)
    c.info["n_pg"] = 2
    c.info["net_name"] = net_name
    c.info["baseline_for_hb"] = False
    c.info["compares_to"] = "wl_d10_m2_30um"
    c.info["with_shields"] = bool(with_shields)
    c.info["first_tap_um"] = float(first_tap)
    c.info["last_tap_um"] = float(last_tap)
    c.info["cpp_um"] = float(CPP_UM)
    c.info["fin_pitch_um"] = float(FIN_PITCH_UM)
    c.info["tap_placement"] = "first_at_pitch_last_at_length"
    c.info["tap_placement_note"] = TAP_PLACEMENT_NOTE
    c.info["via_stack"] = "VG/VD-M0-VIA0-M1-VIA1-M2 (local); M2..AP+HB (vertical)"
    c.info["hb_count"] = 1
    c.info["hb_pad_size_um"] = float(hb_pad_size)
    c.info["hb_via_size_um"] = float(hb_via_size)
    c.info["upper_x_offset_um"] = float(upper_x_offset)
    c.info["climb_vias"] = list(HB_CLIMB_VIAS)
    c.info["n_climb_vias"] = len(HB_CLIMB_VIAS)
    c.info["stack_map_note"] = HB_STACK_MAP_NOTE
    c.info["metal_stub_rc"] = "neglected_via_dominated"
    c.info["draw_upper_descend_stack"] = bool(draw_upper_descend_stack)
    return c
