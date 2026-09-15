"""Metal cross-sections for routing cells (width in µm).

Default widths = DRM min_w per metal (source: drm_ws). AP included.
"""

from __future__ import annotations

from functools import partial

import gdsfactory as gf
from gdsfactory.cross_section import CrossSection

from gf_layout_flow.tech.layers import METAL_LAYERS, FEOL_LAYERS, MEOL_LAYERS, LAYER, layer_tuple

# Default metal widths (µm) — N5 DRM min_w from Table 2.5.1 / cross-section
DEFAULT_WIDTHS: dict[str, float] = {
    "M0": 0.014,
    "M1": 0.020,
    "M2": 0.020,
    "M3": 0.020,
    "M4": 0.020,
    "M5": 0.038,
    "M6": 0.038,
    "M7": 0.038,
    "M8": 0.038,
    "M9": 0.038,
    "M10": 0.062,
    "M11": 0.062,
    "M12": 0.360,
    "M13": 0.360,
    "AP": 1.8,
}

# Min spacing (µm) — DRM min_s (for documentation / pitch helpers)
DEFAULT_SPACING: dict[str, float] = {
    "M0": 0.014,
    "M1": 0.014,
    "M2": 0.015,
    "M3": 0.022,
    "M4": 0.022,
    "M5": 0.038,
    "M6": 0.038,
    "M7": 0.038,
    "M8": 0.038,
    "M9": 0.038,
    "M10": 0.064,
    "M11": 0.064,
    "M12": 0.360,
    "M13": 0.360,
    "AP": 1.8,
}

# Via min square size (µm) — DRM Table 2.5.2
DEFAULT_VIA_SIZES: dict[str, float] = {
    "VIA0": 0.014,
    "VIA1": 0.016,
    "VIA2": 0.016,
    "VIA3": 0.020,
    "VIA4": 0.020,
    "VIA5": 0.038,
    "VIA6": 0.038,
    "VIA7": 0.038,
    "VIA8": 0.038,
    "VIA9": 0.062,
    "VIA10": 0.062,
    "VIA11": 0.324,
    "VIA12": 0.324,
    "RV": 2.7,
}


def metal_xs(metal: str = "M1", width: float | None = None) -> CrossSection:
    """Return a rectangular metal CrossSection for the given metal name."""
    metal = metal.upper()
    if metal not in METAL_LAYERS:
        raise ValueError(f"Unknown metal {metal!r}; choose from {list(METAL_LAYERS)}")
    w = DEFAULT_WIDTHS[metal] if width is None else width
    return gf.cross_section.cross_section(width=w, layer=METAL_LAYERS[metal])


def get_cross_section(name: str, width: float | None = None) -> CrossSection:
    """Alias: get metal cross-section by name (e.g. 'M2')."""
    return metal_xs(name, width=width)


def min_pitch(metal: str) -> float:
    """Minimum center-to-center pitch = min_w + min_s (µm)."""
    metal = metal.upper()
    return DEFAULT_WIDTHS[metal] + DEFAULT_SPACING[metal]


xs_m0 = partial(metal_xs, metal="M0")
xs_m1 = partial(metal_xs, metal="M1")
xs_m2 = partial(metal_xs, metal="M2")
xs_m3 = partial(metal_xs, metal="M3")
xs_m4 = partial(metal_xs, metal="M4")
xs_m5 = partial(metal_xs, metal="M5")
xs_m6 = partial(metal_xs, metal="M6")
xs_m7 = partial(metal_xs, metal="M7")
xs_m8 = partial(metal_xs, metal="M8")
xs_m9 = partial(metal_xs, metal="M9")
xs_m10 = partial(metal_xs, metal="M10")
xs_m11 = partial(metal_xs, metal="M11")
xs_m12 = partial(metal_xs, metal="M12")
xs_m13 = partial(metal_xs, metal="M13")
xs_ap = partial(metal_xs, metal="AP")


# FEOL / MEOL default widths & via sizes (µm) — DRM min geom where known
FEOL_DEFAULT_WIDTHS: dict[str, float] = {
    "OD": 0.034,
    "PO": 0.006,
    "MD": 0.020,
}

FEOL_DEFAULT_SPACING: dict[str, float] = {
    "OD": 0.078,
    "PO": 0.045,
    "MD": 0.031,
}

FEOL_VIA_SIZES: dict[str, float] = {
    "VG": 0.012,
    "VD": 0.014,
    "VDR": 0.014,
}


def feol_xs(name: str = "OD", width: float | None = None):
    """Cross-section for OD / PO / MD drawing layers."""
    name = name.upper()
    layer_map = {**{k: FEOL_LAYERS[k] for k in ("OD", "PO") if k in FEOL_LAYERS}, **{"MD": MEOL_LAYERS["MD"]}}
    if name not in layer_map:
        raise ValueError(f"Unknown FEOL xs {name!r}; choose from {list(layer_map)}")
    import gdsfactory as gf
    w = FEOL_DEFAULT_WIDTHS[name] if width is None else width
    return gf.cross_section.cross_section(width=w, layer=layer_map[name])
