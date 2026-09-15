"""N5 / N05 1P13M LayerMap: FEOL/MEOL + BEOL (M0–M13/AP) + HB research overlays.

CAD layer numbers and datatypes from user-provided N5 DRM excerpts
(T-N05-CL-DR-014 Table / cross-section). NOT an official TSMC PDK.
HB_PAD / HB_VIA are research overlays (not in N5 DRM).

NW / DNW / OD2 / CM0* use PLACEHOLDER CAD numbers (source=placeholder_unverified).
User must verify against T-N05-CL-LE-001. See layers_pending.py + yaml placeholder_unverified.
"""

from __future__ import annotations

from gdsfactory.technology import LayerMap
from gdsfactory.typings import Layer


class LayerMapN5_1P13M(LayerMap):
    """N5 FEOL/MEOL + 1P13M_M1+1x1xb1xe1ya1yb3y2yy2z metals/vias + AP + HB."""

    # --- FEOL (confirmed CAD from DRM) ---
    OD: Layer = (6, 0)  # active/diffusion
    COD_H: Layer = (6, 60)  # horizontal cut-OD
    COD_V: Layer = (6, 61)  # vertical cut-OD
    COD_BLOCK: Layer = (6, 70)  # cut-OD blockage
    PO: Layer = (17, 0)  # poly/gate
    CPO: Layer = (17, 30)  # cut-poly
    PP: Layer = (25, 0)  # P+ implant
    NP: Layer = (26, 0)  # N+ implant
    NT_N: Layer = (11, 0)  # well implant blocking

    # --- PLACEHOLDER (unverified — verify against T-N05-CL-LE-001) ---
    # Chosen outside confirmed CAD ranges (not 5–6,11,17,25–26,30–47,50–66,74,76,82,85–86,169,177–179,900–901,990–991).
    NW: Layer = (1, 0)  # N-Well — PLACEHOLDER; verify LE-001
    DNW: Layer = (3, 0)  # Deep N-Well — PLACEHOLDER; verify LE-001
    OD2: Layer = (8, 0)  # thick oxide / OD_12 — PLACEHOLDER; verify LE-001
    CM0: Layer = (29, 0)  # cut-M0 — PLACEHOLDER; verify LE-001
    CM0A: Layer = (29, 151)  # cut-M0 variant A — PLACEHOLDER; verify LE-001
    CM0B: Layer = (29, 152)  # cut-M0 variant B — PLACEHOLDER; verify LE-001

    # --- MEOL (confirmed CAD from DRM) ---
    MD: Layer = (82, 150)  # local interconnect OD↔VD
    CMD: Layer = (82, 250)  # cut MD
    VG: Layer = (178, 150)  # via PO↔M0
    VD: Layer = (179, 150)  # via MD↔M0
    VDR: Layer = (177, 150)  # rail-type VD

    # --- Passivation / open (confirmed) ---
    CB: Layer = (76, 0)  # passivation open (wirebond)
    CBD: Layer = (169, 0)  # passivation-1 / CB-VD related
    CB2: Layer = (86, 0)  # passivation-2
    PM: Layer = (5, 0)  # polyimide open

    # --- Metals (CAD #, primary drawing datatype) ---
    M0: Layer = (30, 151)
    M1: Layer = (31, 171)
    M2: Layer = (32, 151)
    M3: Layer = (33, 251)
    M4: Layer = (34, 401)
    M5: Layer = (35, 950)
    M6: Layer = (36, 800)
    M7: Layer = (37, 970)
    M8: Layer = (38, 970)
    M9: Layer = (39, 970)
    M10: Layer = (40, 90)
    M11: Layer = (41, 90)
    M12: Layer = (42, 40)
    M13: Layer = (43, 40)
    AP: Layer = (74, 0)  # Al RDL

    # Vias — datatype = metal ABOVE the via (DRM)
    VIA0: Layer = (50, 150)  # M0–M1
    VIA1: Layer = (51, 150)  # M1–M2
    VIA2: Layer = (52, 250)  # M2–M3
    VIA3: Layer = (53, 400)  # M3–M4
    VIA4: Layer = (54, 950)  # M4–M5
    VIA5: Layer = (55, 800)  # M5–M6
    VIA6: Layer = (56, 970)  # M6–M7
    VIA7: Layer = (57, 970)  # M7–M8
    VIA8: Layer = (58, 970)  # M8–M9
    VIA9: Layer = (59, 90)  # M9–M10
    VIA10: Layer = (60, 90)  # M10–M11
    VIA11: Layer = (61, 40)  # M11–M12
    VIA12: Layer = (62, 40)  # M12–M13
    RV: Layer = (85, 0)  # M13–AP (Al via); CAD 85;0 from N5 userguide

    # Hybrid bonding — research overlays (unused high CAD #s; not in N5 DRM)
    HB_PAD: Layer = (900, 0)
    HB_VIA: Layer = (901, 0)

    # Utility / boundary (optional)
    Chip_Boundary: Layer = (108, 250)
    prBoundary: Layer = (108, 0)
    LABEL: Layer = (990, 0)
    FLOORPLAN: Layer = (991, 0)


LAYER = LayerMapN5_1P13M


def layer_tuple(layer) -> tuple[int, int]:
    """Normalize LayerEnum / tuple to (layer, datatype)."""
    if isinstance(layer, tuple):
        return (int(layer[0]), int(layer[1]))
    return (int(tuple(layer)[0]), int(tuple(layer)[1]))


# Human-readable names used by RC extractors (keys are plain tuples)
LAYER_NAMES: dict[tuple[int, int], str] = {
    layer_tuple(LAYER.OD): "OD",
    layer_tuple(LAYER.COD_H): "COD_H",
    layer_tuple(LAYER.COD_V): "COD_V",
    layer_tuple(LAYER.COD_BLOCK): "COD_BLOCK",
    layer_tuple(LAYER.PO): "PO",
    layer_tuple(LAYER.CPO): "CPO",
    layer_tuple(LAYER.PP): "PP",
    layer_tuple(LAYER.NP): "NP",
    layer_tuple(LAYER.NT_N): "NT_N",
    layer_tuple(LAYER.NW): "NW",
    layer_tuple(LAYER.DNW): "DNW",
    layer_tuple(LAYER.OD2): "OD2",
    layer_tuple(LAYER.CM0): "CM0",
    layer_tuple(LAYER.CM0A): "CM0A",
    layer_tuple(LAYER.CM0B): "CM0B",
    layer_tuple(LAYER.MD): "MD",
    layer_tuple(LAYER.CMD): "CMD",
    layer_tuple(LAYER.VG): "VG",
    layer_tuple(LAYER.VD): "VD",
    layer_tuple(LAYER.VDR): "VDR",
    layer_tuple(LAYER.CB): "CB",
    layer_tuple(LAYER.CBD): "CBD",
    layer_tuple(LAYER.CB2): "CB2",
    layer_tuple(LAYER.PM): "PM",
    layer_tuple(LAYER.M0): "M0",
    layer_tuple(LAYER.M1): "M1",
    layer_tuple(LAYER.M2): "M2",
    layer_tuple(LAYER.M3): "M3",
    layer_tuple(LAYER.M4): "M4",
    layer_tuple(LAYER.M5): "M5",
    layer_tuple(LAYER.M6): "M6",
    layer_tuple(LAYER.M7): "M7",
    layer_tuple(LAYER.M8): "M8",
    layer_tuple(LAYER.M9): "M9",
    layer_tuple(LAYER.M10): "M10",
    layer_tuple(LAYER.M11): "M11",
    layer_tuple(LAYER.M12): "M12",
    layer_tuple(LAYER.M13): "M13",
    layer_tuple(LAYER.AP): "AP",
    layer_tuple(LAYER.VIA0): "VIA0",
    layer_tuple(LAYER.VIA1): "VIA1",
    layer_tuple(LAYER.VIA2): "VIA2",
    layer_tuple(LAYER.VIA3): "VIA3",
    layer_tuple(LAYER.VIA4): "VIA4",
    layer_tuple(LAYER.VIA5): "VIA5",
    layer_tuple(LAYER.VIA6): "VIA6",
    layer_tuple(LAYER.VIA7): "VIA7",
    layer_tuple(LAYER.VIA8): "VIA8",
    layer_tuple(LAYER.VIA9): "VIA9",
    layer_tuple(LAYER.VIA10): "VIA10",
    layer_tuple(LAYER.VIA11): "VIA11",
    layer_tuple(LAYER.VIA12): "VIA12",
    layer_tuple(LAYER.RV): "RV",
    layer_tuple(LAYER.HB_PAD): "HB_PAD",
    layer_tuple(LAYER.HB_VIA): "HB_VIA",
    layer_tuple(LAYER.Chip_Boundary): "Chip_Boundary",
    layer_tuple(LAYER.prBoundary): "prBoundary",
    layer_tuple(LAYER.LABEL): "LABEL",
    layer_tuple(LAYER.FLOORPLAN): "FLOORPLAN",
}

FEOL_LAYERS: dict[str, tuple[int, int]] = {
    "OD": layer_tuple(LAYER.OD),
    "COD_H": layer_tuple(LAYER.COD_H),
    "COD_V": layer_tuple(LAYER.COD_V),
    "COD_BLOCK": layer_tuple(LAYER.COD_BLOCK),
    "PO": layer_tuple(LAYER.PO),
    "CPO": layer_tuple(LAYER.CPO),
    "PP": layer_tuple(LAYER.PP),
    "NP": layer_tuple(LAYER.NP),
    "NT_N": layer_tuple(LAYER.NT_N),
    "NW": layer_tuple(LAYER.NW),
    "DNW": layer_tuple(LAYER.DNW),
    "OD2": layer_tuple(LAYER.OD2),
}

# Alias: OD_12 == OD2 (placeholder)
OD12_ALIAS = "OD2"

PLACEHOLDER_LAYERS: dict[str, tuple[int, int]] = {
    "NW": layer_tuple(LAYER.NW),
    "DNW": layer_tuple(LAYER.DNW),
    "OD2": layer_tuple(LAYER.OD2),
    "CM0": layer_tuple(LAYER.CM0),
    "CM0A": layer_tuple(LAYER.CM0A),
    "CM0B": layer_tuple(LAYER.CM0B),
}

CUT_M0_LAYERS: dict[str, tuple[int, int]] = {
    "CM0": layer_tuple(LAYER.CM0),
    "CM0A": layer_tuple(LAYER.CM0A),
    "CM0B": layer_tuple(LAYER.CM0B),
}


MEOL_LAYERS: dict[str, tuple[int, int]] = {
    "MD": layer_tuple(LAYER.MD),
    "CMD": layer_tuple(LAYER.CMD),
    "VG": layer_tuple(LAYER.VG),
    "VD": layer_tuple(LAYER.VD),
    "VDR": layer_tuple(LAYER.VDR),
    "CB": layer_tuple(LAYER.CB),
    "CBD": layer_tuple(LAYER.CBD),
    "CB2": layer_tuple(LAYER.CB2),
    "PM": layer_tuple(LAYER.PM),
}

METAL_LAYERS: dict[str, tuple[int, int]] = {
    "M0": layer_tuple(LAYER.M0),
    "M1": layer_tuple(LAYER.M1),
    "M2": layer_tuple(LAYER.M2),
    "M3": layer_tuple(LAYER.M3),
    "M4": layer_tuple(LAYER.M4),
    "M5": layer_tuple(LAYER.M5),
    "M6": layer_tuple(LAYER.M6),
    "M7": layer_tuple(LAYER.M7),
    "M8": layer_tuple(LAYER.M8),
    "M9": layer_tuple(LAYER.M9),
    "M10": layer_tuple(LAYER.M10),
    "M11": layer_tuple(LAYER.M11),
    "M12": layer_tuple(LAYER.M12),
    "M13": layer_tuple(LAYER.M13),
    "AP": layer_tuple(LAYER.AP),
}

VIA_LAYERS: dict[str, tuple[int, int]] = {
    "VIA0": layer_tuple(LAYER.VIA0),
    "VIA1": layer_tuple(LAYER.VIA1),
    "VIA2": layer_tuple(LAYER.VIA2),
    "VIA3": layer_tuple(LAYER.VIA3),
    "VIA4": layer_tuple(LAYER.VIA4),
    "VIA5": layer_tuple(LAYER.VIA5),
    "VIA6": layer_tuple(LAYER.VIA6),
    "VIA7": layer_tuple(LAYER.VIA7),
    "VIA8": layer_tuple(LAYER.VIA8),
    "VIA9": layer_tuple(LAYER.VIA9),
    "VIA10": layer_tuple(LAYER.VIA10),
    "VIA11": layer_tuple(LAYER.VIA11),
    "VIA12": layer_tuple(LAYER.VIA12),
    "RV": layer_tuple(LAYER.RV),
    "VG": layer_tuple(LAYER.VG),
    "VD": layer_tuple(LAYER.VD),
    "VDR": layer_tuple(LAYER.VDR),
}

# Which via sits between which metals (bottom, top) — BEOL only
VIA_BETWEEN: dict[str, tuple[str, str]] = {
    "VIA0": ("M0", "M1"),
    "VIA1": ("M1", "M2"),
    "VIA2": ("M2", "M3"),
    "VIA3": ("M3", "M4"),
    "VIA4": ("M4", "M5"),
    "VIA5": ("M5", "M6"),
    "VIA6": ("M6", "M7"),
    "VIA7": ("M7", "M8"),
    "VIA8": ("M8", "M9"),
    "VIA9": ("M9", "M10"),
    "VIA10": ("M10", "M11"),
    "VIA11": ("M11", "M12"),
    "VIA12": ("M12", "M13"),
    "RV": ("M13", "AP"),
}

# Ordered metal stack bottom→top (for stacked_via adjacency)
METAL_ORDER: list[str] = [
    "M0",
    "M1",
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
]

# Via name connecting METAL_ORDER[i] → METAL_ORDER[i+1]
VIA_BY_METAL_PAIR: dict[tuple[str, str], str] = {
    pair: name for name, pair in VIA_BETWEEN.items()
}
