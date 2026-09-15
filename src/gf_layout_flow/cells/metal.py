"""Metal wire / bus / via parametric cells (N5 1P13M defaults)."""

from __future__ import annotations

import gdsfactory as gf
from gdsfactory import Component

from gf_layout_flow.tech.pdk import activate_pdk
from gf_layout_flow.tech.layers import (
    METAL_LAYERS,
    VIA_LAYERS,
    VIA_BETWEEN,
    METAL_ORDER,
    VIA_BY_METAL_PAIR,
)
from gf_layout_flow.tech.cross_sections import DEFAULT_WIDTHS, DEFAULT_VIA_SIZES, DEFAULT_SPACING

activate_pdk()


def _rect(c: Component, x0: float, y0: float, x1: float, y1: float, layer) -> None:
    c.add_polygon([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], layer=layer)


@gf.cell
def metal_wire(
    length: float = 10.0,
    width: float | None = None,
    metal: str = "M1",
    orientation: str = "X",
) -> Component:
    """Straight metal wire along +X (default) or +Y, width-centered on the other axis (um)."""
    metal = metal.upper()
    if metal not in METAL_LAYERS:
        raise ValueError(f"Unknown metal {metal!r}; choose from {list(METAL_LAYERS)}")
    orientation = str(orientation).upper()
    if orientation not in {"X", "Y"}:
        raise ValueError("orientation must be 'X' or 'Y'")
    w = DEFAULT_WIDTHS[metal] if width is None else width
    c = gf.Component()
    if orientation == "Y":
        # Vertical: from y=0 to y=length, centered on x=0
        _rect(c, -w / 2, 0.0, w / 2, length, METAL_LAYERS[metal])
    else:
        # Horizontal: from x=0 to x=length, centered on y=0
        _rect(c, 0.0, -w / 2, length, w / 2, METAL_LAYERS[metal])
    c.info["metal"] = metal
    c.info["length_um"] = length
    c.info["width_um"] = w
    c.info["orientation"] = orientation
    return c


@gf.cell
def metal_bus(
    length: float = 20.0,
    width: float | None = None,
    metal: str = "M2",
    n_fingers: int = 4,
    pitch: float | None = None,
) -> Component:
    """Parallel metal fingers forming a bus (along +x, spaced in y)."""
    metal = metal.upper()
    w = DEFAULT_WIDTHS[metal] if width is None else width
    # Default pitch = min_w + min_s (DRM), with a small slack for demos
    if pitch is None:
        pitch = w + DEFAULT_SPACING.get(metal, w) + 0.01
    c = gf.Component()
    for i in range(n_fingers):
        wire = metal_wire(length=length, width=w, metal=metal)
        ref = c.add_ref(wire)
        ref.movey(i * pitch)
    c.info["metal"] = metal
    c.info["n_fingers"] = n_fingers
    c.info["pitch_um"] = pitch
    c.info["length_um"] = length
    c.info["width_um"] = w
    return c


@gf.cell
def via_array(
    via: str = "VIA1",
    size: float | None = None,
    rows: int = 2,
    cols: int = 2,
    pitch: float | None = None,
) -> Component:
    """Rectangular via array (square vias). Defaults = N5 DRM min sizes."""
    via = via.upper()
    if via not in VIA_LAYERS:
        raise ValueError(f"Unknown via {via!r}; choose from {list(VIA_LAYERS)}")
    sz = DEFAULT_VIA_SIZES.get(via, 0.05) if size is None else size
    if pitch is None:
        pitch = sz * 2.5
    layer = VIA_LAYERS[via]
    c = gf.Component()
    for r in range(rows):
        for col in range(cols):
            _rect(
                c,
                col * pitch,
                r * pitch,
                col * pitch + sz,
                r * pitch + sz,
                layer,
            )
    c.info["via"] = via
    c.info["size_um"] = sz
    c.info["rows"] = rows
    c.info["cols"] = cols
    c.info["pitch_um"] = pitch
    if via in VIA_BETWEEN:
        c.info["connects"] = list(VIA_BETWEEN[via])
    return c


@gf.cell
def stacked_via(
    bottom_metal: str = "M1",
    top_metal: str = "M2",
    via_size: float | None = None,
    enclosure: float | None = None,
) -> Component:
    """Single via stack between two adjacent metals with enclosure pads."""
    bottom_metal = bottom_metal.upper()
    top_metal = top_metal.upper()
    if bottom_metal not in METAL_ORDER or top_metal not in METAL_ORDER:
        raise ValueError(f"Metals must be in {METAL_ORDER}")
    bi = METAL_ORDER.index(bottom_metal)
    ti = METAL_ORDER.index(top_metal)
    if ti != bi + 1:
        raise ValueError("stacked_via only supports adjacent metals (e.g. M1→M2, M13→AP)")
    via_name = VIA_BY_METAL_PAIR[(bottom_metal, top_metal)]
    sz = DEFAULT_VIA_SIZES.get(via_name, 0.05) if via_size is None else via_size
    # Enclosure: use a fraction of via size, floored for tiny vias
    enc = max(sz * 0.25, 0.005) if enclosure is None else enclosure
    pad = sz + 2 * enc
    c = gf.Component()
    _rect(c, 0, 0, pad, pad, METAL_LAYERS[bottom_metal])
    _rect(
        c,
        enc,
        enc,
        enc + sz,
        enc + sz,
        VIA_LAYERS[via_name],
    )
    _rect(c, 0, 0, pad, pad, METAL_LAYERS[top_metal])
    c.info["bottom_metal"] = bottom_metal
    c.info["top_metal"] = top_metal
    c.info["via"] = via_name
    c.info["via_size_um"] = sz
    return c


# Metals on the Hybrid-Bonding climb from WL M2 to AP (user "M2~M14" → AP)
HB_CLIMB_METALS: tuple[str, ...] = (
    "M2",
    "M3",
    "M4",
    "M5",
    "M6",
    "M7",
    "M8",
    "M9",
    "M10",
    "M11",
    "M12",
    "M13",
    "AP",
)

# VIA2..VIA12 + RV — one instance each per climb
HB_CLIMB_VIAS: tuple[str, ...] = tuple(
    VIA_BY_METAL_PAIR[(HB_CLIMB_METALS[i], HB_CLIMB_METALS[i + 1])]
    for i in range(len(HB_CLIMB_METALS) - 1)
)

STACK_MAP_NOTE = (
    "User said M2~M14 for the HB climb. This PDK is 1P13M: M0..M13 + AP "
    "(no M14 CAD layer). Research mapping: M14 ≈ AP / HB landing. "
    "Vertical stack = M2→M3→…→M13→RV→AP→HB_PAD/HB_VIA, then mirrored "
    "reverse on the upper die back to M2. VIA2..VIA12 + RV counted once "
    "per climb; round-trip = two climbs + one HB."
)


@gf.cell
def via_stack_multi(
    bottom_metal: str = "M2",
    top_metal: str = "AP",
    enclosure: float = 0.005,
    research_size_cap_um: float | None = 0.50,
) -> Component:
    """Multi-level via stack between non-adjacent metals (research sketch).

    Draws centered metal pads + vias for every step bottom→top along
    METAL_ORDER. Large DRM vias (e.g. RV 2.7 um) are optionally capped
    with ``research_size_cap_um`` for sketch visibility; info records both.
    """
    bottom_metal = bottom_metal.upper()
    top_metal = top_metal.upper()
    if bottom_metal not in METAL_ORDER or top_metal not in METAL_ORDER:
        raise ValueError(f"Metals must be in {METAL_ORDER}")
    bi = METAL_ORDER.index(bottom_metal)
    ti = METAL_ORDER.index(top_metal)
    if ti <= bi:
        raise ValueError("top_metal must be above bottom_metal in the stack")

    c = gf.Component()
    vias_drawn: list[str] = []
    metals_drawn: list[str] = []
    size_notes: list[dict] = []

    max_pad = 0.0
    for i in range(bi, ti):
        m_bot = METAL_ORDER[i]
        m_top = METAL_ORDER[i + 1]
        via_name = VIA_BY_METAL_PAIR[(m_bot, m_top)]
        drm_sz = float(DEFAULT_VIA_SIZES.get(via_name, 0.05))
        sz = drm_sz
        capped = False
        if research_size_cap_um is not None and sz > float(research_size_cap_um):
            sz = float(research_size_cap_um)
            capped = True
        enc = max(enclosure, sz * 0.15, 0.005)
        pad = sz + 2 * enc
        max_pad = max(max_pad, pad)
        half = pad / 2.0
        vh = sz / 2.0
        # Metal pads (both levels) + via, all centered at origin
        _rect(c, -half, -half, half, half, METAL_LAYERS[m_bot])
        _rect(c, -vh, -vh, vh, vh, VIA_LAYERS[via_name])
        _rect(c, -half, -half, half, half, METAL_LAYERS[m_top])
        vias_drawn.append(via_name)
        if m_bot not in metals_drawn:
            metals_drawn.append(m_bot)
        if m_top not in metals_drawn:
            metals_drawn.append(m_top)
        size_notes.append(
            {
                "via": via_name,
                "drm_min_size_um": drm_sz,
                "drawn_size_um": sz,
                "research_capped": capped,
            }
        )

    c.info["bottom_metal"] = bottom_metal
    c.info["top_metal"] = top_metal
    c.info["vias"] = list(vias_drawn)
    c.info["metals"] = list(metals_drawn)
    c.info["n_vias"] = len(vias_drawn)
    c.info["pad_size_um"] = float(max_pad)
    c.info["research_size_cap_um"] = (
        None if research_size_cap_um is None else float(research_size_cap_um)
    )
    c.info["via_size_notes"] = size_notes
    c.info["stack_map_note"] = STACK_MAP_NOTE
    return c


@gf.cell
def hb_climb_stack(
    research_size_cap_um: float | None = 0.50,
    hb_pad_size: float = 0.50,
    hb_via_size: float = 0.324,
    include_hb: bool = True,
) -> Component:
    """M2→…→M13→RV→AP climb plus optional HB_PAD/HB_VIA (one climb)."""
    from gf_layout_flow.cells.hb_pads import hb_pad

    c = gf.Component()
    stack = via_stack_multi(
        bottom_metal="M2",
        top_metal="AP",
        research_size_cap_um=research_size_cap_um,
    )
    c.add_ref(stack)
    if include_hb:
        pad = hb_pad(pad_size=hb_pad_size, via_size=hb_via_size, include_via=True)
        c.add_ref(pad)

    c.info["role"] = "hb_climb_stack"
    c.info["bottom_metal"] = "M2"
    c.info["top_metal"] = "AP"
    c.info["vias"] = list(HB_CLIMB_VIAS)
    c.info["n_vias"] = len(HB_CLIMB_VIAS)
    c.info["hb_pad_size_um"] = float(hb_pad_size) if include_hb else 0.0
    c.info["hb_via_size_um"] = float(hb_via_size) if include_hb else 0.0
    c.info["include_hb"] = bool(include_hb)
    c.info["stack_map_note"] = STACK_MAP_NOTE
    c.info["measured_hb_size_class_um"] = 0.324
    return c
