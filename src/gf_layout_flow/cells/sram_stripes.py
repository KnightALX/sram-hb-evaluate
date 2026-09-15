"""SRAM-ish bitline / wordline interconnect stripe arrays (placeholder geometry)."""

from __future__ import annotations

import gdsfactory as gf
from gdsfactory import Component

from gf_layout_flow.tech.pdk import activate_pdk
from gf_layout_flow.cells.metal import metal_wire
from gf_layout_flow.tech.cross_sections import DEFAULT_WIDTHS

activate_pdk()


@gf.cell
def bitline_stripes(
    n_bls: int = 8,
    length: float = 50.0,
    width: float | None = None,
    pitch: float = 0.10,
    metal: str = "M2",
) -> Component:
    """Bitlines as wires along +x, spaced by pitch in y (SRAM-ish)."""
    metal = metal.upper()
    w = DEFAULT_WIDTHS.get(metal, 0.06) if width is None else width
    c = gf.Component()
    for i in range(n_bls):
        wire = metal_wire(length=length, width=w, metal=metal)
        ref = c.add_ref(wire)
        ref.movey(i * pitch)
    c.info["role"] = "bitline"
    c.info["n_stripes"] = n_bls
    c.info["metal"] = metal
    c.info["length_um"] = length
    c.info["width_um"] = w
    c.info["pitch_um"] = pitch
    return c


@gf.cell
def wordline_stripes(
    n_wls: int = 8,
    length: float = 40.0,
    width: float | None = None,
    pitch: float = 0.10,
    metal: str = "M3",
) -> Component:
    """Wordlines as wires along +x, spaced in y (orthogonal metal vs BL by default)."""
    metal = metal.upper()
    w = DEFAULT_WIDTHS.get(metal, 0.07) if width is None else width
    c = gf.Component()
    for i in range(n_wls):
        wire = metal_wire(length=length, width=w, metal=metal)
        ref = c.add_ref(wire)
        ref.movey(i * pitch)
    c.info["role"] = "wordline"
    c.info["n_stripes"] = n_wls
    c.info["metal"] = metal
    c.info["length_um"] = length
    c.info["width_um"] = w
    c.info["pitch_um"] = pitch
    return c


@gf.cell
def sram_interconnect_block(
    n_bls: int = 8,
    n_wls: int = 8,
    bl_length: float = 50.0,
    wl_length: float = 40.0,
    bl_pitch: float = 0.10,
    wl_pitch: float = 0.10,
    bl_metal: str = "M2",
    wl_metal: str = "M3",
    bl_width: float | None = None,
    wl_width: float | None = None,
) -> Component:
    """Combined BL + WL stripe block for demo layouts / RC extraction."""
    c = gf.Component()
    bl = bitline_stripes(
        n_bls=n_bls,
        length=bl_length,
        width=bl_width,
        pitch=bl_pitch,
        metal=bl_metal,
    )
    wl = wordline_stripes(
        n_wls=n_wls,
        length=wl_length,
        width=wl_width,
        pitch=wl_pitch,
        metal=wl_metal,
    )
    c.add_ref(bl)
    wl_ref = c.add_ref(wl)
    wl_ref.movey(-wl_pitch * (n_wls + 1))
    c.info["n_bls"] = n_bls
    c.info["n_wls"] = n_wls
    c.info["bl_metal"] = bl_metal.upper()
    c.info["wl_metal"] = wl_metal.upper()
    return c
