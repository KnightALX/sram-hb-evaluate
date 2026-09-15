"""Activate N5 FEOL/MEOL + 1P13M research PDK for gdsfactory 9+."""

from __future__ import annotations

from functools import partial

from gdsfactory.pdk import Pdk

from gf_layout_flow.tech.layers import LAYER, METAL_LAYERS
from gf_layout_flow.tech.stack import LAYER_STACK
from gf_layout_flow.tech.cross_sections import metal_xs, feol_xs

# DRM recommends 0.5 nm DBU when streaming GDS
N5_DBU_UM = 0.0005

PDK_NAME = "n5_1p13m_beol"
STACK_OPTION = "1P13M_M1+1x1xb1xe1ya1yb3y2yy2z"


def get_pdk() -> Pdk:
    """Return (and register) the N5 FEOL/MEOL + 1P13M research PDK."""
    cross_sections = {name: partial(metal_xs, metal=name) for name in METAL_LAYERS}
    cross_sections["metal"] = metal_xs
    for feol_name in ("OD", "PO", "MD"):
        cross_sections[feol_name] = partial(feol_xs, name=feol_name)
    return Pdk(
        name=PDK_NAME,
        version="0.4.0",
        layers=LAYER,
        layer_stack=LAYER_STACK,
        cross_sections=cross_sections,
        cells={},
        dbu=N5_DBU_UM,
    )


_PDK: Pdk | None = None


def activate_pdk() -> Pdk:
    """Activate N5 1P13M PDK (idempotent)."""
    global _PDK
    if _PDK is None:
        _PDK = get_pdk()
    _PDK.activate()
    return _PDK
