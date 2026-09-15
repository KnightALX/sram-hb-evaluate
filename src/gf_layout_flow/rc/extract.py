"""Extract RC-oriented geometry metrics from a gdsfactory Component.

This does NOT compute resistance/capacitance numerically. It extracts
interconnect geometry quantities that feed RC Pattern / BEOL analysis:
  - layers used
  - per-layer area, estimated wire length & mean width
  - hybrid-bonding pad area / pitch / count
"""

from __future__ import annotations

import math
from typing import Any

from gdsfactory import Component

from gf_layout_flow.tech.pdk import activate_pdk
from gf_layout_flow.tech.layers import LAYER_NAMES, METAL_LAYERS, layer_tuple
from gf_layout_flow.tech.stack import LAYER_STACK

activate_pdk()


def _poly_points_um(poly, dbu: float) -> list[tuple[float, float]]:
    """Convert a klayout Polygon to µm vertices."""
    if hasattr(poly, "each_point_hull"):
        return [(pt.x * dbu, pt.y * dbu) for pt in poly.each_point_hull()]
    # Fallback: sequence of points already in µm or dbu
    pts: list[tuple[float, float]] = []
    try:
        for p in poly:
            pts.append((float(p[0]), float(p[1])))
        # Heuristic: if values look like dbu integers for µm features, scale
        if pts and max(abs(x) for x, _ in pts) + max(abs(y) for _, y in pts) > 1000:
            pts = [(x * dbu, y * dbu) for x, y in pts]
        return pts
    except Exception:
        return []


def _polygon_area(pts: list[tuple[float, float]]) -> float:
    """Shoelace area (µm²)."""
    if len(pts) < 3:
        return 0.0
    area = 0.0
    n = len(pts)
    for i in range(n):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % n]
        area += x1 * y2 - x2 * y1
    return abs(area) / 2.0


def _bbox_wh(pts: list[tuple[float, float]]) -> tuple[float, float]:
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return max(xs) - min(xs), max(ys) - min(ys)


def _estimate_length_width(area: float, bbox_w: float, bbox_h: float) -> tuple[float, float]:
    """Heuristic: longer bbox edge ≈ length, area/length ≈ width."""
    if area <= 0:
        return 0.0, 0.0
    length = max(bbox_w, bbox_h)
    if length <= 0:
        side = math.sqrt(area)
        return side, side
    width = area / length
    return length, width


def _iter_polygons(component: Component):
    """Yield (layer_tuple, point_list_um) for all polygons including references."""
    try:
        flat = component.copy()
        flat.flatten()
    except Exception:
        flat = component

    dbu = float(getattr(getattr(flat, "kcl", None), "dbu", 0.001) or 0.001)

    get_polygons = getattr(flat, "get_polygons", None)
    if get_polygons is None:
        return

    try:
        polys = get_polygons(by="tuple")
    except TypeError:
        try:
            polys = get_polygons(by_spec=True)
        except TypeError:
            polys = get_polygons()

    if not isinstance(polys, dict):
        return

    for layer, plist in polys.items():
        lk = layer_tuple(layer)
        for poly in plist:
            pts = _poly_points_um(poly, dbu)
            if pts:
                yield lk, pts


def extract_rc_metrics(component: Component) -> dict[str, Any]:
    """Return structured metrics dict for interconnect / HB analysis."""
    per_layer: dict[str, dict[str, Any]] = {}
    layers_used: set[str] = set()

    area_by_layer: dict[str, float] = {}
    length_by_layer: dict[str, float] = {}
    width_samples: dict[str, list[float]] = {}
    poly_count: dict[str, int] = {}

    for layer_tup, pts in _iter_polygons(component):
        name = LAYER_NAMES.get(layer_tup, f"L{layer_tup[0]}_{layer_tup[1]}")
        layers_used.add(name)
        area = _polygon_area(pts)
        bw, bh = _bbox_wh(pts)
        length, width = _estimate_length_width(area, bw, bh)

        area_by_layer[name] = area_by_layer.get(name, 0.0) + area
        length_by_layer[name] = length_by_layer.get(name, 0.0) + length
        width_samples.setdefault(name, []).append(width)
        poly_count[name] = poly_count.get(name, 0) + 1

    for name in sorted(area_by_layer.keys()):
        widths = width_samples.get(name, [])
        mean_w = sum(widths) / len(widths) if widths else 0.0
        per_layer[name] = {
            "area_um2": round(area_by_layer[name], 6),
            "wire_length_um": round(length_by_layer.get(name, 0.0), 6),
            "mean_width_um": round(mean_w, 6),
            "polygon_count": poly_count.get(name, 0),
            "is_metal": name in METAL_LAYERS,
        }

    hb_pad_area = area_by_layer.get("HB_PAD", 0.0)
    hb_via_area = area_by_layer.get("HB_VIA", 0.0)
    hb_pad_count = poly_count.get("HB_PAD", 0)
    info = dict(getattr(component, "info", {}) or {})
    hb_pitch = info.get("pitch_um") if ("n_pads" in info or "pad_size_um" in info) else None

    thickness_um: dict[str, float] = {}
    try:
        for lname, level in LAYER_STACK.layers.items():
            thickness_um[lname] = float(level.thickness)
    except Exception:
        pass

    metrics: dict[str, Any] = {
        "component_name": getattr(component, "name", None) or component.__class__.__name__,
        "units": "um",
        "layers_used": sorted(layers_used),
        "per_layer": per_layer,
        "totals": {
            "metal_area_um2": round(
                sum(v["area_um2"] for k, v in per_layer.items() if v.get("is_metal")), 6
            ),
            "metal_wire_length_um": round(
                sum(v["wire_length_um"] for k, v in per_layer.items() if v.get("is_metal")), 6
            ),
            "total_area_um2": round(sum(v["area_um2"] for v in per_layer.values()), 6),
        },
        "hybrid_bonding": {
            "pad_count": int(info.get("n_pads", hb_pad_count)),
            "pad_area_um2": round(hb_pad_area, 6),
            "via_area_um2": round(hb_via_area, 6),
            "pitch_um": hb_pitch,
            "pad_size_um": info.get("pad_size_um"),
            "interface_area_um2": round(hb_pad_area, 6),
        },
        "layer_thickness_um": thickness_um,
        "component_info": {k: _jsonable(v) for k, v in info.items()},
        "notes": (
            "Geometry metrics only (N5 1P13M research tech; thicknesses are "
            "research_approx unless marked drm_ws). Map length/width/thickness "
            "to R ~ rho*L/(w*t) and C patterns offline — not a foundry extraction."
        ),
    }
    return metrics


def _jsonable(v: Any) -> Any:
    if isinstance(v, (str, int, float, bool)) or v is None:
        return v
    if isinstance(v, (list, tuple)):
        return [_jsonable(x) for x in v]
    if isinstance(v, dict):
        return {str(k): _jsonable(val) for k, val in v.items()}
    try:
        return float(v)
    except Exception:
        return str(v)


def metrics_to_jsonable(metrics: dict[str, Any]) -> dict[str, Any]:
    """Ensure metrics dict is JSON-serializable."""
    return _jsonable(metrics)  # type: ignore[return-value]
