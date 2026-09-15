"""Analytical interconnect RC extraction from user measured lookup table.

Metal R/C use **per-um * length** (not Rsheet*L/W). Via / HB are lumped
per instance by via class. Intended for SPICE ladder sketches — not foundry
extraction.
"""

from __future__ import annotations

from typing import Any

from gdsfactory import Component

from gf_layout_flow.tech.layers import LAYER, LAYER_NAMES, layer_tuple
from gf_layout_flow.tech.rc_table import (
    get_hb_rc,
    get_metal_rc,
    get_via_rc,
    get_via_rc_for_layer,
    interpolation_notes,
)


# VIA layers typically used on the M0→M2 WL via stacks
_WL_VIA_LAYERS = ("VIA0", "VIA1")
_WL_TAP_VIA_LAYERS = ("VIA0", "VIA1")

_INTERP_SOURCES = frozenset(
    {
        "interpolated_from_user_measured",
        "interpolated_from_user_table",  # legacy alias
    }
)


def _info(component: Component) -> dict[str, Any]:
    try:
        return dict(getattr(component, "info", {}) or {})
    except Exception:
        return {}


def _count_via_polygons(component: Component, via_names: tuple[str, ...] = _WL_VIA_LAYERS) -> dict[str, Any]:
    """Count VIA* polygon instances on the (flattened) component.

    Prefers polygon count; returns method tag for the caller.
    """
    counts: dict[str, int] = {name: 0 for name in via_names}
    total = 0
    method = "polygon_count"
    try:
        flat = component.copy()
        try:
            flat.flatten()
        except Exception:
            flat = component
        get_polygons = getattr(flat, "get_polygons", None)
        if get_polygons is None:
            raise RuntimeError("no get_polygons")
        try:
            polys = get_polygons(by="tuple")
        except TypeError:
            try:
                polys = get_polygons(by_spec=True)
            except TypeError:
                polys = get_polygons()
        if not isinstance(polys, dict):
            raise RuntimeError("polygons not a dict")

        wanted = {layer_tuple(getattr(LAYER, name)): name for name in via_names if hasattr(LAYER, name)}
        # Also accept name-keyed dicts
        for layer, plist in polys.items():
            name = None
            if isinstance(layer, str) and layer in counts:
                name = layer
            else:
                try:
                    lt = layer_tuple(layer)
                except Exception:
                    lt = None
                if lt in wanted:
                    name = wanted[lt]
                elif lt is not None:
                    name = LAYER_NAMES.get(lt)
                    if name not in counts:
                        name = None
            if name is None:
                continue
            n = len(plist) if hasattr(plist, "__len__") else 0
            counts[name] = counts.get(name, 0) + int(n)
            total += int(n)
    except Exception:
        method = "unavailable"
        total = 0
        counts = {name: 0 for name in via_names}

    return {
        "n_vias": int(total),
        "per_layer": {k: int(v) for k, v in counts.items()},
        "method": method,
        "layers_counted": list(via_names),
    }


def _heuristic_wl_vias(n_bitcells: int) -> dict[str, Any]:
    """Driver stack VIA0+VIA1=2 plus each bitcell tap VIA0+VIA1=2."""
    n_bitcells = max(int(n_bitcells), 0)
    n_vias = 2 + 2 * n_bitcells
    return {
        "n_vias": n_vias,
        "per_layer": {"VIA0": 1 + n_bitcells, "VIA1": 1 + n_bitcells},
        "method": "heuristic_wl_longline_pattern",
        "layers_counted": list(_WL_VIA_LAYERS),
        "note": (
            "Driver contributes VIA0+VIA1=2; each bitcell tap contributes "
            "VIA0+VIA1=2 → n_vias = 2 + 2*n_bitcells"
        ),
    }


def count_wl_vias(component: Component, *, n_bitcells: int | None = None) -> dict[str, Any]:
    """Prefer VIA0/VIA1 polygon counts; fall back to WL heuristic."""
    poly = _count_via_polygons(component)
    if poly["n_vias"] > 0 and poly["method"] == "polygon_count":
        return poly
    info = _info(component)
    n_bc = n_bitcells if n_bitcells is not None else info.get("n_bitcells")
    if n_bc is None:
        n_bc = 0
    return _heuristic_wl_vias(int(n_bc))


def _sum_vias_by_class(
    per_layer: dict[str, int],
    *,
    via_r_ohm_override: float | None = None,
) -> dict[str, Any]:
    """Sum R/C using each VIA layer's class RC × count."""
    by_class: dict[str, dict[str, Any]] = {}
    per_layer_detail: dict[str, Any] = {}
    r_total = 0.0
    c_total = 0.0
    c_plus_total = 0.0
    n_total = 0

    for layer_name, count in per_layer.items():
        n = int(count)
        if n <= 0:
            continue
        info = get_via_rc_for_layer(layer_name)
        cls = str(info["class"])
        r_each = float(via_r_ohm_override) if via_r_ohm_override is not None else float(info["r_ohm"])
        c_each = float(info["c_ff"])
        c_plus_each = float(info.get("c_plus_cc_ff", c_each))
        r_layer = n * r_each
        c_layer = n * c_each
        c_plus_layer = n * c_plus_each
        r_total += r_layer
        c_total += c_layer
        c_plus_total += c_plus_layer
        n_total += n
        per_layer_detail[layer_name] = {
            "n": n,
            "class": cls,
            "r_ohm_each": r_each,
            "c_ff_each": c_each,
            "c_plus_cc_ff_each": c_plus_each,
            "r_ohm": r_layer,
            "c_ff": c_layer,
            "mapped": info.get("mapped", False),
            "source": info.get("source"),
            "size_um": info.get("size_um"),
            "note": info.get("note"),
        }
        bucket = by_class.setdefault(
            cls,
            {
                "n": 0,
                "r_ohm_each": r_each,
                "c_ff_each": c_each,
                "c_plus_cc_ff_each": c_plus_each,
                "r_ohm": 0.0,
                "c_ff": 0.0,
                "c_plus_cc_ff": 0.0,
                "layers": [],
                "source": info.get("source"),
                "size_um": info.get("size_um"),
            },
        )
        bucket["n"] += n
        bucket["r_ohm"] += r_layer
        bucket["c_ff"] += c_layer
        bucket["c_plus_cc_ff"] += c_plus_layer
        if layer_name not in bucket["layers"]:
            bucket["layers"].append(layer_name)

    return {
        "n_vias": n_total,
        "r_ohm": r_total,
        "c_ff": c_total,
        "c_plus_cc_ff": c_plus_total,
        "per_layer": per_layer_detail,
        "by_class": by_class,
    }


def _tap_via_lump(
    tap_layers: tuple[str, ...] = _WL_TAP_VIA_LAYERS,
    *,
    via_r_ohm_override: float | None = None,
) -> dict[str, Any]:
    """Lumped via stack at a WL tap (typically VIA0+VIA1)."""
    per_layer = {name: 1 for name in tap_layers}
    summed = _sum_vias_by_class(per_layer, via_r_ohm_override=via_r_ohm_override)
    return {
        "n_vias": summed["n_vias"],
        "r_ohm": summed["r_ohm"],
        "c_ff": summed["c_ff"],
        "c_plus_cc_ff": summed["c_plus_cc_ff"],
        "layers": list(tap_layers),
        "per_layer": summed["per_layer"],
        "by_class": summed["by_class"],
    }


def extract_net_rc(
    component: Component,
    *,
    net: str = "WL",
    metal: str = "M2",
    length_um: float | None = None,
    width_um: float | None = None,
    n_vias: int | None = None,
    n_hb: int = 0,
    via_r_ohm: float | None = None,
    n_bitcells: int | None = None,
    tap_pitch_um: float | None = None,
) -> dict[str, Any]:
    """General analytical RC for a named interconnect net.

    Metal contribution uses table **per-um * length** (not sheet*L/W).
    Width is recorded for documentation only unless a future sheet mode is added.
    Via R/C are summed **per layer class** (not a single flat viaX).
    """
    info = _info(component)
    net_name = str(info.get("net_name") or net)

    if length_um is None:
        length_um = info.get("wl_length_um")
    if length_um is None:
        length_um = info.get("length_um")
    if length_um is None:
        raise ValueError("length_um required (or component.info['wl_length_um'])")
    length_um = float(length_um)

    if width_um is None:
        width_um = info.get("m2_width_um") or info.get("width_um")
    width_um = float(width_um) if width_um is not None else None

    if n_bitcells is None:
        n_bitcells = info.get("n_bitcells")
    n_bitcells_i = int(n_bitcells) if n_bitcells is not None else 0

    if tap_pitch_um is None:
        tap_pitch_um = info.get("tap_pitch_um")
    tap_pitch = float(tap_pitch_um) if tap_pitch_um is not None else None

    metal_key = str(metal).upper()
    metal_rc = get_metal_rc(metal_key)
    if metal_rc is None or metal_rc.get("r_ohm_per_um") is None:
        raise ValueError(f"No RC table entry for metal={metal_key!r} (null/skip or missing)")

    r_per_um = float(metal_rc["r_ohm_per_um"])
    c_per_um = float(metal_rc["c_ff_per_um"])
    r_metal = r_per_um * length_um
    c_metal = c_per_um * length_um

    via_tbl = get_via_rc()
    default_via_r = float(via_tbl["r_ohm_default_use"])
    default_via_c = float(via_tbl["c_ff"])

    via_count_info: dict[str, Any]
    if n_vias is not None:
        via_count_info = {
            "n_vias": int(n_vias),
            "method": "caller_override",
            "per_layer": {},
            "layers_counted": [],
        }
    else:
        via_count_info = count_wl_vias(component, n_bitcells=n_bitcells_i)
    n_vias_i = int(via_count_info["n_vias"])
    per_layer_counts = dict(via_count_info.get("per_layer") or {})

    if per_layer_counts:
        via_sum = _sum_vias_by_class(per_layer_counts, via_r_ohm_override=via_r_ohm)
        # If polygon/heuristic count total differs from sum of layers, trust layers
        n_vias_i = int(via_sum["n_vias"]) if via_sum["n_vias"] else n_vias_i
        r_via = float(via_sum["r_ohm"])
        c_via = float(via_sum["c_ff"])
        c_via_plus = float(via_sum["c_plus_cc_ff"])
        via_per_layer = via_sum["per_layer"]
        via_by_class = via_sum["by_class"]
    else:
        # Flat default thin via × n (caller override without per_layer)
        via_r = float(via_r_ohm) if via_r_ohm is not None else default_via_r
        via_c = default_via_c
        r_via = n_vias_i * via_r
        c_via = n_vias_i * via_c
        c_via_plus = n_vias_i * float(via_tbl.get("c_plus_cc_ff", via_c))
        via_per_layer = {}
        via_by_class = {
            via_tbl["class"]: {
                "n": n_vias_i,
                "r_ohm_each": via_r,
                "c_ff_each": via_c,
                "r_ohm": r_via,
                "c_ff": c_via,
                "source": via_tbl.get("source"),
            }
        }

    # Representative "each" for summary when homogeneous; else None
    unique_r = {v["r_ohm_each"] for v in via_by_class.values()} if via_by_class else {default_via_r}
    unique_c = {v["c_ff_each"] for v in via_by_class.values()} if via_by_class else {default_via_c}
    r_ohm_each = float(next(iter(unique_r))) if len(unique_r) == 1 else None
    c_ff_each = float(next(iter(unique_c))) if len(unique_c) == 1 else None

    hb_tbl = get_hb_rc()
    n_hb_i = max(int(n_hb), 0)
    r_hb = n_hb_i * float(hb_tbl["r_ohm"])
    c_hb = n_hb_i * float(hb_tbl["c_ff"])

    r_total = r_metal + r_via + r_hb
    c_total = c_metal + c_via + c_hb

    # Segmented ladder for taps (useful for SPICE later)
    n_seg = n_bitcells_i
    seg_length = tap_pitch if tap_pitch is not None else (length_um / n_seg if n_seg > 0 else length_um)
    tap_lump = _tap_via_lump(_WL_TAP_VIA_LAYERS, via_r_ohm_override=via_r_ohm)
    vias_per_tap = int(tap_lump["n_vias"])
    if via_count_info.get("method") == "polygon_count" and n_bitcells_i > 0:
        rem = max(n_vias_i - 2, 0)
        approx = max(int(round(rem / n_bitcells_i)), 1) if n_bitcells_i else vias_per_tap
        # Prefer actual VIA0+VIA1 tap stack when count matches typical 2
        if approx != vias_per_tap and approx > 0:
            # Keep measured per-type tap when typical; only note divergence
            pass

    segments: list[dict[str, Any]] = []
    if n_seg > 0 and seg_length is not None:
        r_seg = r_per_um * float(seg_length)
        c_seg = c_per_um * float(seg_length)
        for i in range(n_seg):
            segments.append(
                {
                    "index": i + 1,
                    "y_um": round((i + 1) * float(seg_length), 9) if tap_pitch is not None else None,
                    "seg_length_um": float(seg_length),
                    "r_seg_ohm": r_seg,
                    "c_seg_ff": c_seg,
                    "via_lump_at_tap": {
                        "n_vias": vias_per_tap,
                        "r_ohm": tap_lump["r_ohm"],
                        "c_ff": tap_lump["c_ff"],
                        "c_plus_cc_ff": tap_lump["c_plus_cc_ff"],
                        "layers": tap_lump["layers"],
                        "by_class": {
                            k: {"n": v["n"], "r_ohm": v["r_ohm"], "c_ff": v["c_ff"]}
                            for k, v in tap_lump["by_class"].items()
                        },
                    },
                }
            )

    interp = interpolation_notes()
    metal_note = None
    src = metal_rc.get("source")
    if src in _INTERP_SOURCES:
        parents = metal_rc.get("parents") or []
        metal_note = (
            f"{metal_key} interpolated from {'-'.join(parents)} "
            f"(R=sqrt, C=avg) source={src}"
        )
    elif src == "extrapolated":
        metal_note = metal_rc.get("note") or f"{metal_key} extrapolated/mapped"

    metal_table: dict[str, Any] = {
        "r_ohm_per_um": r_per_um,
        "c_ff_per_um": c_per_um,
        "source": metal_rc.get("source"),
        "parents": metal_rc.get("parents"),
        "mapped_to": metal_rc.get("mapped_to"),
        "note": metal_rc.get("note"),
        "interpolation_note": metal_note,
    }
    for k in ("width_um", "space_um", "Cc", "Cbottom", "Ctop"):
        if k in metal_rc:
            metal_table[k] = metal_rc[k]

    result: dict[str, Any] = {
        "net": net_name,
        "metal": metal_key,
        "units": {
            "r": "Ohm",
            "c": "fF",
            "length": "um",
            "r_per_um": "Ohm/um",
            "c_per_um": "fF/um",
        },
        "length_um": length_um,
        "width_um": width_um,
        "width_note": (
            "Table is per-length (Ohm/um, fF/um); width is recorded only. "
            "Do not divide by width unless using an optional sheet mode."
        ),
        "n_bitcells": n_bitcells_i,
        "tap_pitch_um": tap_pitch,
        "metal_table": metal_table,
        "metal_rc": {
            "r_ohm": r_metal,
            "c_ff": c_metal,
            "formula": "per_um * length_um",
        },
        "via": {
            "n_vias": n_vias_i,
            "r_ohm_each": r_ohm_each,
            "c_ff_each": c_ff_each,
            "r_ohm": r_via,
            "c_ff": c_via,
            "c_plus_cc_ff": c_via_plus,
            "count_method": via_count_info.get("method"),
            "count_detail": via_count_info,
            "per_layer": via_per_layer,
            "by_class": via_by_class,
            "table": {
                "r_ohm_default_use": default_via_r,
                "c_ff": default_via_c,
                "c_plus_cc_ff": float(via_tbl.get("c_plus_cc_ff", default_via_c)),
                "default_via_class": via_tbl.get("class") or via_tbl.get("default_via_class"),
                "classes": via_tbl.get("classes"),
                "layer_map": via_tbl.get("layer_map"),
                "source": via_tbl.get("source"),
                "note": via_tbl.get("note"),
            },
        },
        "hb": {
            "n_hb": n_hb_i,
            "r_ohm_each": float(hb_tbl["r_ohm"]),
            "c_ff_each": float(hb_tbl["c_ff"]),
            "c_plus_cc_ff_each": float(hb_tbl.get("c_plus_cc_ff", hb_tbl["c_ff"])),
            "r_ohm": r_hb,
            "c_ff": c_hb,
            "source": hb_tbl["source"],
            "size_um": hb_tbl.get("size_um"),
        },
        "totals": {
            "r_ohm": r_total,
            "c_ff": c_total,
            "r_metal_ohm": r_metal,
            "c_metal_ff": c_metal,
            "r_via_ohm": r_via,
            "c_via_ff": c_via,
            "r_hb_ohm": r_hb,
            "c_hb_ff": c_hb,
        },
        "ladder": {
            "n_seg": n_seg,
            "seg_length_um": float(seg_length) if seg_length is not None else None,
            "vias_per_tap": vias_per_tap,
            "tap_via_layers": list(_WL_TAP_VIA_LAYERS),
            "segments": segments,
            "note": (
                "Distributed metal segments between taps with via lump at each tap "
                "(VIA0+VIA1 class V1-V2); for SPICE ladder later. "
                "Driver via stack is included in totals n_vias."
            ),
        },
        "interpolation_notes": interp,
        "sources": {
            "table": "src/gf_layout_flow/tech/n5_1p13m.yaml#interconnect_rc",
            "metal": metal_rc.get("source"),
            "via": via_tbl.get("source"),
            "hb": hb_tbl["source"],
            "via_count": via_count_info.get("method"),
        },
        "component_info": {
            k: info[k]
            for k in (
                "driver_strength",
                "wl_length_um",
                "m2_width_um",
                "n_bitcells",
                "tap_pitch_um",
                "net_name",
                "wl_direction",
                "baseline_for_hb",
                "n_pg",
                "pg_nfinger",
            )
            if k in info
        },
        "notes": (
            "Analytical RC from user measured lookup table. Metal uses per-um * length "
            "(not Rsheet*L/W). Via/HB are lumped per instance by via class; analysis "
            "capacitance uses C (not C+cc). Research sketch — not a foundry parasitic extraction."
        ),
    }
    return result


def extract_wl_rc(
    component: Component,
    *,
    net: str = "WL",
    metal: str = "M2",
    length_um: float | None = None,
    width_um: float | None = None,
    n_vias: int | None = None,
    n_hb: int = 0,
    via_r_ohm: float | None = None,
) -> dict[str, Any]:
    """Analytical RC for the SRAM long-WL baseline (wrapper around extract_net_rc)."""
    return extract_net_rc(
        component,
        net=net,
        metal=metal,
        length_um=length_um,
        width_um=width_um,
        n_vias=n_vias,
        n_hb=n_hb,
        via_r_ohm=via_r_ohm,
    )


def format_wl_rc_summary(rc: dict[str, Any]) -> str:
    """Short ASCII summary lines for CLI (no non-ASCII unit symbols)."""
    totals = rc.get("totals") or {}
    metal = rc.get("metal_rc") or {}
    via = rc.get("via") or {}
    mt = rc.get("metal_table") or {}
    metal_name = rc.get("metal", "M2")
    interp = mt.get("interpolation_note") or mt.get("source") or ""
    lines = [
        (
            f"WL RC (analytical): R_metal={metal.get('r_ohm')} Ohm  "
            f"C_metal={metal.get('c_ff')} fF  n_vias={via.get('n_vias')}  "
            f"R_total={totals.get('r_ohm')}  C_total={totals.get('c_ff')}"
        ),
        f"{metal_name} table: {interp}",
    ]
    return "\n".join(lines)


__all__ = [
    "extract_wl_rc",
    "extract_net_rc",
    "count_wl_vias",
    "format_wl_rc_summary",
]
