"""N5 FEOL/MEOL + 1P13M research tech (DRM excerpts + placeholder LE-001 layers)."""

from __future__ import annotations

from gf_layout_flow.tech.layers import (
    LAYER,
    LAYER_NAMES,
    METAL_LAYERS,
    VIA_LAYERS,
    VIA_BETWEEN,
    METAL_ORDER,
    FEOL_LAYERS,
    MEOL_LAYERS,
    PLACEHOLDER_LAYERS,
    layer_tuple,
)
from gf_layout_flow.tech.stack import get_layer_stack, LAYER_STACK
from gf_layout_flow.tech.cross_sections import (
    metal_xs,
    get_cross_section,
    feol_xs,
    DEFAULT_WIDTHS,
    DEFAULT_VIA_SIZES,
    FEOL_DEFAULT_WIDTHS,
    FEOL_VIA_SIZES,
)
from gf_layout_flow.tech.pdk import activate_pdk, get_pdk, PDK_NAME, STACK_OPTION
from gf_layout_flow.tech.layers_pending import PLACEHOLDER_CAD, ASK_USER_FOR
from gf_layout_flow.tech.rc_table import (
    get_metal_rc,
    get_via_rc,
    get_via_rc_for_layer,
    get_hb_rc,
    load_interconnect_rc,
)

activate_pdk()

__all__ = [
    "LAYER",
    "LAYER_NAMES",
    "METAL_LAYERS",
    "VIA_LAYERS",
    "VIA_BETWEEN",
    "METAL_ORDER",
    "FEOL_LAYERS",
    "MEOL_LAYERS",
    "PLACEHOLDER_LAYERS",
    "PLACEHOLDER_CAD",
    "ASK_USER_FOR",
    "layer_tuple",
    "LAYER_STACK",
    "get_layer_stack",
    "metal_xs",
    "feol_xs",
    "get_cross_section",
    "DEFAULT_WIDTHS",
    "DEFAULT_VIA_SIZES",
    "FEOL_DEFAULT_WIDTHS",
    "FEOL_VIA_SIZES",
    "activate_pdk",
    "get_pdk",
    "PDK_NAME",
    "STACK_OPTION",
    "get_metal_rc",
    "get_via_rc",
    "get_via_rc_for_layer",
    "get_hb_rc",
    "load_interconnect_rc",
]
