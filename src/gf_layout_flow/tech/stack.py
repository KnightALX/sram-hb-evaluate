"""N5 FEOL/MEOL + 1P13M LayerStack with research-approx thicknesses (µm).

Exact Cu / FEOL thickness is NOT in the attached DRM W/S tables.
Thicknesses are research approximations. NW/DNW/OD2/CM0 CAD# are
placeholder_unverified (verify T-N05-CL-LE-001).
"""

from __future__ import annotations

from gdsfactory.technology import LayerLevel, LayerStack

from gf_layout_flow.tech.layers import LAYER

# Research-approx FEOL / MEOL thicknesses (µm)
_FEOL_T: dict[str, float] = {
    "NW": 0.200,  # well implant depth placeholder
    "DNW": 0.400,
    "OD": 0.050,
    "OD2": 0.070,
    "PO": 0.040,
    "MD": 0.030,
    "VG": 0.035,
    "VD": 0.035,
}

_METAL_T: dict[str, float] = {
    "M0": 0.036,
    "M1": 0.043,
    "M2": 0.045,
    "M3": 0.054,
    "M4": 0.054,
    "M5": 0.097,
    "M6": 0.097,
    "M7": 0.097,
    "M8": 0.097,
    "M9": 0.097,
    "M10": 0.162,
    "M11": 0.162,
    "M12": 0.936,
    "M13": 0.936,
    "AP": 1.450,
}

_VIA_T: dict[str, float] = {
    "VIA0": 0.040,
    "VIA1": 0.045,
    "VIA2": 0.050,
    "VIA3": 0.055,
    "VIA4": 0.080,
    "VIA5": 0.090,
    "VIA6": 0.090,
    "VIA7": 0.090,
    "VIA8": 0.090,
    "VIA9": 0.140,
    "VIA10": 0.140,
    "VIA11": 0.800,
    "VIA12": 0.800,
    "RV": 1.000,
}

_HB_VIA_T = 0.500
_HB_PAD_T = 0.800

# Bottom→top: FEOL → MEOL → BEOL metals/vias → AP → HB
# Each entry: (name, kind, layer_ref, thickness_dict_key_or_None)
_STACK_SEQ: list[tuple[str, str, object]] = [
    ("NW", "feol", LAYER.NW),
    ("DNW", "feol", LAYER.DNW),
    ("OD", "feol", LAYER.OD),
    ("OD2", "feol", LAYER.OD2),
    ("PO", "feol", LAYER.PO),
    ("MD", "meol", LAYER.MD),
    ("VG", "meol_via", LAYER.VG),
    ("VD", "meol_via", LAYER.VD),
    ("M0", "metal", LAYER.M0),
    ("VIA0", "via", LAYER.VIA0),
    ("M1", "metal", LAYER.M1),
    ("VIA1", "via", LAYER.VIA1),
    ("M2", "metal", LAYER.M2),
    ("VIA2", "via", LAYER.VIA2),
    ("M3", "metal", LAYER.M3),
    ("VIA3", "via", LAYER.VIA3),
    ("M4", "metal", LAYER.M4),
    ("VIA4", "via", LAYER.VIA4),
    ("M5", "metal", LAYER.M5),
    ("VIA5", "via", LAYER.VIA5),
    ("M6", "metal", LAYER.M6),
    ("VIA6", "via", LAYER.VIA6),
    ("M7", "metal", LAYER.M7),
    ("VIA7", "via", LAYER.VIA7),
    ("M8", "metal", LAYER.M8),
    ("VIA8", "via", LAYER.VIA8),
    ("M9", "metal", LAYER.M9),
    ("VIA9", "via", LAYER.VIA9),
    ("M10", "metal", LAYER.M10),
    ("VIA10", "via", LAYER.VIA10),
    ("M11", "metal", LAYER.M11),
    ("VIA11", "via", LAYER.VIA11),
    ("M12", "metal", LAYER.M12),
    ("VIA12", "via", LAYER.VIA12),
    ("M13", "metal", LAYER.M13),
    ("RV", "via", LAYER.RV),
    ("AP", "metal", LAYER.AP),
]


def get_layer_stack(z0: float = 0.0) -> LayerStack:
    """Return FEOL/MEOL + 1P13M + AP + HB LayerStack (µm).

    Parameters
    ----------
    z0 :
        Starting zmin for bottom FEOL (µm). Default 0.0.
    """
    layers: dict[str, LayerLevel] = {}
    z = z0
    # Well layers share a low z band (implant / substrate markers)
    well_z = z0
    for name, kind, lyr in _STACK_SEQ:
        if name in ("NW", "DNW"):
            t = _FEOL_T[name]
            layers[name] = LayerLevel(
                layer=lyr,
                thickness=t,
                zmin=well_z,
                material="si",
                mesh_order=3,
                info={
                    "source": "placeholder_unverified",
                    "verify_against": "T-N05-CL-LE-001",
                },
            )
            continue
        if kind == "feol":
            t = _FEOL_T[name]
            material = "poly" if name == "PO" else "si"
            mesh_order = 1
            src = (
                "placeholder_unverified"
                if name == "OD2"
                else "research_approx"
            )
            info = {"source": src}
            if name == "OD2":
                info["verify_against"] = "T-N05-CL-LE-001"
        elif kind == "meol":
            t = _FEOL_T[name]
            material = "w"  # local interconnect research placeholder
            mesh_order = 1
            info = {"source": "research_approx"}
        elif kind == "meol_via":
            t = _FEOL_T[name]
            material = "w"
            mesh_order = 2
            info = {"source": "research_approx"}
        elif kind == "metal":
            t = _METAL_T[name]
            material = "al" if name == "AP" else "cu"
            mesh_order = 1
            info = {"source": "research_approx"}
        else:  # via
            t = _VIA_T[name]
            material = "al" if name == "RV" else "cu"
            mesh_order = 2
            info = {"source": "research_approx"}

        layers[name] = LayerLevel(
            layer=lyr,
            thickness=t,
            zmin=z,
            material=material,
            mesh_order=mesh_order,
            info=info,
        )
        z = z + t

    layers["HB_VIA"] = LayerLevel(
        layer=LAYER.HB_VIA,
        thickness=_HB_VIA_T,
        zmin=z,
        material="cu",
        mesh_order=2,
        info={"source": "research_approx", "note": "HB research overlay"},
    )
    z = z + _HB_VIA_T
    layers["HB_PAD"] = LayerLevel(
        layer=LAYER.HB_PAD,
        thickness=_HB_PAD_T,
        zmin=z,
        material="cu",
        mesh_order=1,
        info={"source": "research_approx", "note": "HB research overlay"},
    )
    return LayerStack(layers=layers)


LAYER_STACK = get_layer_stack()
