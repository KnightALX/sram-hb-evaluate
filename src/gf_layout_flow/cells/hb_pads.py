"""Hybrid-bonding pad and pad-array cells (placeholder geometry)."""

from __future__ import annotations

import gdsfactory as gf
from gdsfactory import Component

from gf_layout_flow.tech.pdk import activate_pdk
from gf_layout_flow.tech.layers import LAYER

activate_pdk()


@gf.cell
def hb_pad(
    pad_size: float = 2.0,
    via_size: float = 0.8,
    include_via: bool = True,
) -> Component:
    """Single hybrid-bonding pad with optional centered HB_VIA."""
    c = gf.Component()
    half = pad_size / 2
    c.add_polygon(
        [(-half, -half), (half, -half), (half, half), (-half, half)],
        layer=LAYER.HB_PAD,
    )
    if include_via:
        vh = via_size / 2
        c.add_polygon(
            [(-vh, -vh), (vh, -vh), (vh, vh), (-vh, vh)],
            layer=LAYER.HB_VIA,
        )
    c.info["pad_size_um"] = pad_size
    c.info["via_size_um"] = via_size if include_via else 0.0
    c.info["area_um2"] = pad_size * pad_size
    return c


@gf.cell
def hb_pad_array(
    rows: int = 4,
    cols: int = 4,
    pad_size: float = 2.0,
    pitch: float = 4.0,
    via_size: float = 0.8,
    include_via: bool = True,
) -> Component:
    """2D hybrid-bonding pad array for 3D stacking interface demos."""
    if pitch <= pad_size:
        raise ValueError(f"pitch ({pitch}) must be > pad_size ({pad_size})")
    c = gf.Component()
    pad = hb_pad(pad_size=pad_size, via_size=via_size, include_via=include_via)
    for r in range(rows):
        for col in range(cols):
            ref = c.add_ref(pad)
            ref.move((col * pitch, r * pitch))
    n = rows * cols
    c.info["rows"] = rows
    c.info["cols"] = cols
    c.info["n_pads"] = n
    c.info["pad_size_um"] = pad_size
    c.info["pitch_um"] = pitch
    c.info["via_size_um"] = via_size if include_via else 0.0
    c.info["total_pad_area_um2"] = n * pad_size * pad_size
    c.info["array_span_x_um"] = (cols - 1) * pitch + pad_size
    c.info["array_span_y_um"] = (rows - 1) * pitch + pad_size
    return c
