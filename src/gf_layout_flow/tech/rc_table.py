"""Load analytical interconnect RC lookup from n5_1p13m.yaml.

User-measured table values are authoritative. Metals not in the table are
interpolated between nearest tabulated neighbors (R = sqrt product, C = mean)
or mapped (M0 -> M1; M12/M13 -> M11). AP is null / skip.

Via lumps are per class (V1-V2 / V3-V4 / V5-V9 / V10-V11); PDK VIA* names
map to classes. Analysis uses C (not C+cc); c_plus_cc_ff is stored.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

_YAML_PATH = Path(__file__).resolve().parent / "n5_1p13m.yaml"

_DEFAULT_VIA_CLASS = "V1-V2"

_METAL_EXTRA_KEYS = (
    "width_um",
    "space_um",
    "Cc",
    "Cbottom",
    "Ctop",
)


def _yaml_path() -> Path:
    return _YAML_PATH


@lru_cache(maxsize=1)
def load_interconnect_rc(path: str | Path | None = None) -> dict[str, Any]:
    """Return the ``interconnect_rc`` mapping from the tech yaml."""
    p = Path(path) if path else _yaml_path()
    with open(p, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    rc = data.get("interconnect_rc")
    if not isinstance(rc, dict):
        raise KeyError(f"interconnect_rc missing in {p}")
    return rc


def clear_rc_cache() -> None:
    """Drop cached yaml (for tests that rewrite the table)."""
    load_interconnect_rc.cache_clear()


def get_metal_rc(layer_name: str, *, path: str | Path | None = None) -> dict[str, Any] | None:
    """Return metal per-um RC: ``{r_ohm_per_um, c_ff_per_um, source, ...}``.

    Also forwards optional measured fields (width_um, space_um, Cc, Cbottom, Ctop)
    when present. Returns ``None`` when the layer is marked null/skip (e.g. AP)
    or unknown.
    """
    rc = load_interconnect_rc(path)
    metals = rc.get("metals_per_um") or {}
    key = str(layer_name).strip().upper()
    entry = metals.get(key) or metals.get(layer_name)
    if entry is None:
        return None
    r = entry.get("r_ohm_per_um")
    c = entry.get("c_ff_per_um")
    if r is None and c is None:
        return None
    out: dict[str, Any] = {
        "r_ohm_per_um": None if r is None else float(r),
        "c_ff_per_um": None if c is None else float(c),
        "source": entry.get("source"),
    }
    if "parents" in entry:
        out["parents"] = list(entry["parents"])
    if "mapped_to" in entry:
        out["mapped_to"] = entry["mapped_to"]
    if "note" in entry:
        out["note"] = entry["note"]
    for k in _METAL_EXTRA_KEYS:
        if k in entry and entry[k] is not None:
            out[k] = float(entry[k]) if isinstance(entry[k], (int, float)) else entry[k]
    return out


def _via_classes(rc: dict[str, Any]) -> dict[str, Any]:
    lumped = rc.get("lumped") or {}
    classes = lumped.get("via_classes") or {}
    return dict(classes)


def _via_layer_map(rc: dict[str, Any]) -> dict[str, Any]:
    lumped = rc.get("lumped") or {}
    return dict(lumped.get("via_layer_map") or {})


def _default_via_class_name(rc: dict[str, Any]) -> str:
    lumped = rc.get("lumped") or {}
    return str(lumped.get("default_via_class") or _DEFAULT_VIA_CLASS)


def _normalize_via_name(name: str) -> str:
    key = str(name).strip().upper()
    if key.startswith("VIA") or key in ("RV", "HB"):
        return key
    # Allow class names like V1-V2
    return str(name).strip()


def resolve_via_class(via_name: str, *, path: str | Path | None = None) -> dict[str, Any]:
    """Resolve a PDK VIA* (or class) name to class metadata + RC fields."""
    rc = load_interconnect_rc(path)
    classes = _via_classes(rc)
    layer_map = _via_layer_map(rc)
    key = _normalize_via_name(via_name)

    mapped = False
    map_note = None
    class_name: str | None = None

    if key in classes:
        class_name = key
    elif key in layer_map:
        entry = layer_map[key] or {}
        class_name = entry.get("class")
        mapped = bool(entry.get("mapped", False))
        map_note = entry.get("note")
    else:
        # Fallback: treat unknown as default thin via
        class_name = _default_via_class_name(rc)
        mapped = True
        map_note = f"Unknown via {key!r}; using default class {class_name}"

    if class_name not in classes:
        raise KeyError(f"via class {class_name!r} missing for {via_name!r}")

    cls = classes[class_name]
    out: dict[str, Any] = {
        "r_ohm": float(cls.get("r_ohm", 30.0)),
        "c_ff": float(cls.get("c_ff", 0.1)),
        "c_plus_cc_ff": float(cls.get("c_plus_cc_ff", cls.get("c_ff", 0.1))),
        "class": class_name,
        "size_um": float(cls["size_um"]) if cls.get("size_um") is not None else None,
        "source": cls.get("source", "user_measured_lookup"),
        "per": cls.get("per", "instance"),
        "via_name": key if key.startswith("VIA") or key == "RV" else None,
        "mapped": mapped,
    }
    if map_note:
        out["note"] = map_note
    elif cls.get("note"):
        out["note"] = cls["note"]
    return out


def get_via_rc_for_layer(name: str, *, path: str | Path | None = None) -> dict[str, Any]:
    """Return lumped RC for a PDK via layer name (e.g. VIA0, VIA1)."""
    return resolve_via_class(name, path=path)


def get_via_rc(
    via_name: str | None = None,
    *,
    path: str | Path | None = None,
) -> dict[str, Any]:
    """Return via RC.

    - If ``via_name`` is given: resolve class and return
      ``{r_ohm, c_ff, c_plus_cc_ff, class, size_um, source, per, ...}``.
    - If ``via_name`` is None: return default thin via (V1-V2) fields for
      backward compatibility (``r_ohm_default_use``, ``c_ff``, …) plus the
      full ``classes`` and ``layer_map`` dicts.
    """
    rc = load_interconnect_rc(path)
    classes = _via_classes(rc)
    layer_map = _via_layer_map(rc)
    default_name = _default_via_class_name(rc)

    if via_name is not None:
        return resolve_via_class(via_name, path=path)

    thin = classes.get(default_name) or {}
    r_default = float(thin.get("r_ohm", 30.0))
    c_default = float(thin.get("c_ff", 0.1))
    c_plus = float(thin.get("c_plus_cc_ff", c_default))
    size = float(thin["size_um"]) if thin.get("size_um") is not None else 0.021

    # Serialize classes for JSON / callers
    classes_out: dict[str, Any] = {}
    for cname, centry in classes.items():
        classes_out[cname] = {
            "size_um": float(centry["size_um"]) if centry.get("size_um") is not None else None,
            "r_ohm": float(centry.get("r_ohm", 0.0)),
            "c_ff": float(centry.get("c_ff", 0.0)),
            "c_plus_cc_ff": float(centry.get("c_plus_cc_ff", centry.get("c_ff", 0.0))),
            "source": centry.get("source", "user_measured_lookup"),
            "per": centry.get("per", "instance"),
        }

    return {
        "r_ohm": r_default,
        "r_ohm_default_use": r_default,
        "c_ff": c_default,
        "c_plus_cc_ff": c_plus,
        "class": default_name,
        "size_um": size,
        "source": thin.get("source", "user_measured_lookup"),
        "per": thin.get("per", "instance"),
        "default_via_class": default_name,
        "classes": classes_out,
        "layer_map": {k: dict(v) if isinstance(v, dict) else v for k, v in layer_map.items()},
        "note": (
            f"Default thin via = {default_name}; "
            "pass via_name / use get_via_rc_for_layer for per-layer class lookup. "
            "Analysis capacitance uses c_ff (not c_plus_cc_ff)."
        ),
    }


def get_hb_rc(*, path: str | Path | None = None) -> dict[str, Any]:
    """Return HB pad lumped RC per instance (analysis uses C, not C+cc)."""
    rc = load_interconnect_rc(path)
    hb = (rc.get("lumped") or {}).get("HB") or {}
    c_ff = float(hb.get("c_ff", 1.0))
    return {
        "r_ohm": float(hb.get("r_ohm", 0.165)),
        "c_ff": c_ff,
        "c_plus_cc_ff": float(hb.get("c_plus_cc_ff", c_ff)),
        "size_um": float(hb["size_um"]) if hb.get("size_um") is not None else None,
        "source": hb.get("source", "user_measured_lookup"),
        "per": hb.get("per", "instance"),
        "note": hb.get("note"),
    }


def interpolation_notes(*, path: str | Path | None = None) -> dict[str, Any]:
    rc = load_interconnect_rc(path)
    return dict(rc.get("interpolation_notes") or {})


__all__ = [
    "load_interconnect_rc",
    "clear_rc_cache",
    "get_metal_rc",
    "get_via_rc",
    "get_via_rc_for_layer",
    "resolve_via_class",
    "get_hb_rc",
    "interpolation_notes",
]
