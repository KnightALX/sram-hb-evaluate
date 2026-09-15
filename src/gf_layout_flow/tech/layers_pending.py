"""Placeholder FEOL layers — CAD# NOT confirmed in T-N05-CL-DR-014.

These ARE registered in the active LayerMap so full-custom sketches work, but
every CAD number is ``placeholder_unverified``. Replace with values from
**T-N05-CL-LE-001** when the user provides that document.

Placeholder map (must not collide with confirmed DRM layers):
  NW    (1;0)   — N-Well
  DNW   (3;0)   — Deep N-Well
  OD2   (8;0)   — thick oxide (OD_12 alias)
  CM0   (29;0)  — cut-M0
  CM0A  (29;151)
  CM0B  (29;152)
"""

from __future__ import annotations

from gf_layout_flow.tech.layers import PLACEHOLDER_LAYERS, layer_tuple, LAYER

# Name → (cad, dt) placeholders currently active
PLACEHOLDER_CAD: dict[str, tuple[int, int]] = dict(PLACEHOLDER_LAYERS)
PLACEHOLDER_CAD["OD_12"] = layer_tuple(LAYER.OD2)  # alias

PLACEHOLDER_NOTES: dict[str, str] = {
    "NW": "N-Well — PLACEHOLDER (1;0); verify T-N05-CL-LE-001",
    "DNW": "Deep N-Well — PLACEHOLDER (3;0); verify T-N05-CL-LE-001",
    "OD2": "Thick oxide — PLACEHOLDER (8;0); verify T-N05-CL-LE-001",
    "OD_12": "Alias of OD2 — PLACEHOLDER (8;0); verify T-N05-CL-LE-001",
    "CM0": "Cut-M0 — PLACEHOLDER (29;0); verify T-N05-CL-LE-001",
    "CM0A": "Cut-M0 A — PLACEHOLDER (29;151); verify T-N05-CL-LE-001",
    "CM0B": "Cut-M0 B — PLACEHOLDER (29;152); verify T-N05-CL-LE-001",
}

ASK_USER_FOR = "T-N05-CL-LE-001 (replace placeholder CAD;datatype for NW/DNW/OD2/CM0*)"
SOURCE = "placeholder_unverified"
