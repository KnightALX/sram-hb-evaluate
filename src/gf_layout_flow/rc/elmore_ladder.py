"""L2 interconnect analysis: pi-ladder + Elmore delay.

User-approved primary model for GDS WL analysis (v0.6+).
Builds on extract_wl_rc / LUT; does NOT implement Palace (future L3).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from gdsfactory import Component

from gf_layout_flow.rc.electrical import extract_wl_rc
from gf_layout_flow.tech.rc_table import _yaml_path, get_via_rc

# Ohm * fF -> seconds = 1e-15; * 1e12 -> ps  =>  factor 1e-3
_RC_TO_PS = 1e-3


def load_analysis_l2(path: str | Path | None = None) -> dict[str, Any]:
    """Return ``analysis_l2`` mapping from tech yaml (defaults if missing)."""
    p = Path(path) if path else _yaml_path()
    with open(p, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    cfg = data.get("analysis_l2") or {}
    return {
        "model": cfg.get("model", "pi_ladder_elmore"),
        "seg_length_default_um": float(cfg.get("seg_length_default_um", 0.5)),
        "R_drv_ohm": float(cfg.get("R_drv_ohm", 200.0)),
        "R_drv_source": cfg.get("R_drv_source", "placeholder_unverified"),
        "R_drv_note": cfg.get("R_drv_note"),
        "C_drv_par_ff": float(cfg.get("C_drv_par_ff", 0.0)),
        "C_pg_ff_per_finger": float(cfg.get("C_pg_ff_per_finger", 0.3)),
        "C_pg_ff": float(cfg.get("C_pg_ff", 0.3)),
        "C_pg_source": cfg.get("C_pg_source", "user_rule_0p3fF_per_finger"),
        "C_pg_note": cfg.get("C_pg_note"),
        "n_pg_default": int(cfg.get("n_pg_default", 2)),
        "Vdd_V": float(cfg.get("Vdd_V", 0.75)),
        "Vdd_source": cfg.get("Vdd_source", "placeholder_unverified"),
        "Vdd_note": cfg.get("Vdd_note"),
        "via_c_from_ladder": bool(cfg.get("via_c_from_ladder", True)),
        "future_l3": cfg.get("future_l3"),
        "note_zh": cfg.get("note_zh"),
    }


def build_pi_ladder_from_wl_rc(
    wl_rc: dict[str, Any],
    *,
    C_pg_ff: float | None = None,
    n_pg: int | None = None,
    C_drv_par_ff: float | None = None,
    include_c_pg: bool = True,
    analysis_cfg: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a pi-ladder node/edge description from ``extract_wl_rc`` output.

    For each segment i=1..N (N = n_bitcells, seg_length = tap_pitch):
      R_seg = R' * seg_length, C_seg = C' * seg_length
      pi: C_seg/2 on each side of R_seg
      at tap node i: C_tap = C_via_at_tap + (n_pg * C_pg if include_c_pg else 0)

    Returns nodes C[0..N], series R between them, and metadata.
    """
    cfg = analysis_cfg if analysis_cfg is not None else load_analysis_l2()
    if C_pg_ff is None:
        C_pg_ff = float(cfg["C_pg_ff"])
    if n_pg is None:
        info = wl_rc.get("component_info") or {}
        n_pg = int(info.get("n_pg", cfg["n_pg_default"]))
    if C_drv_par_ff is None:
        C_drv_par_ff = float(cfg["C_drv_par_ff"])

    C_pg_ff = float(C_pg_ff)
    n_pg = int(n_pg)
    C_drv_par_ff = float(C_drv_par_ff)

    ladder_src = wl_rc.get("ladder") or {}
    segments = list(ladder_src.get("segments") or [])
    n_seg = int(ladder_src.get("n_seg") or len(segments) or 0)
    seg_length = ladder_src.get("seg_length_um")
    if seg_length is None:
        seg_length = wl_rc.get("tap_pitch_um") or cfg["seg_length_default_um"]
    seg_length = float(seg_length)

    mt = wl_rc.get("metal_table") or {}
    r_per_um = float(mt.get("r_ohm_per_um") or (wl_rc.get("metal_rc") or {}).get("r_ohm", 0) / max(float(wl_rc.get("length_um") or 1), 1e-30))
    c_per_um = float(mt.get("c_ff_per_um") or (wl_rc.get("metal_rc") or {}).get("c_ff", 0) / max(float(wl_rc.get("length_um") or 1), 1e-30))

    via_tbl = get_via_rc()
    vias_per_tap = int(ladder_src.get("vias_per_tap") or 2)
    default_c_via_tap = vias_per_tap * float(via_tbl["c_ff"])

    if n_seg <= 0:
        # Fallback: single segment spanning full length
        length = float(wl_rc.get("length_um") or seg_length)
        n_seg = 1
        segments = [
            {
                "index": 1,
                "y_um": length,
                "seg_length_um": length,
                "r_seg_ohm": r_per_um * length,
                "c_seg_ff": c_per_um * length,
                "via_lump_at_tap": {"n_vias": vias_per_tap, "c_ff": default_c_via_tap, "r_ohm": 0.0},
            }
        ]
        seg_length = length

    # Ensure we have n_seg segment dicts
    while len(segments) < n_seg:
        i = len(segments) + 1
        segments.append(
            {
                "index": i,
                "y_um": i * seg_length,
                "seg_length_um": seg_length,
                "r_seg_ohm": r_per_um * seg_length,
                "c_seg_ff": c_per_um * seg_length,
                "via_lump_at_tap": {"n_vias": vias_per_tap, "c_ff": default_c_via_tap, "r_ohm": 0.0},
            }
        )
    segments = segments[:n_seg]

    c_pg_load = (n_pg * C_pg_ff) if include_c_pg else 0.0

    r_series: list[float] = []  # length N: R between node i-1 and i
    c_nodes: list[float] = [0.0] * (n_seg + 1)  # length N+1
    c_via_taps: list[float] = []
    c_tap_loads: list[float] = []
    y_um: list[float | None] = [0.0]

    c_nodes[0] = C_drv_par_ff

    for i, seg in enumerate(segments):
        r_seg = float(seg.get("r_seg_ohm", r_per_um * float(seg.get("seg_length_um", seg_length))))
        c_seg = float(seg.get("c_seg_ff", c_per_um * float(seg.get("seg_length_um", seg_length))))
        via_lump = seg.get("via_lump_at_tap") or {}
        if cfg.get("via_c_from_ladder", True) and "c_ff" in via_lump:
            c_via = float(via_lump["c_ff"])
        else:
            c_via = default_c_via_tap
        c_tap = c_via + c_pg_load

        r_series.append(r_seg)
        # pi halves
        c_nodes[i] += c_seg / 2.0
        c_nodes[i + 1] += c_seg / 2.0
        # lumped at tap node (after segment)
        c_nodes[i + 1] += c_tap

        c_via_taps.append(c_via)
        c_tap_loads.append(c_tap)
        y_um.append(seg.get("y_um", (i + 1) * seg_length))

    return {
        "n_seg": n_seg,
        "n_nodes": n_seg + 1,
        "seg_length_um": seg_length,
        "r_ohm_per_um": r_per_um,
        "c_ff_per_um": c_per_um,
        "R_series_ohm": r_series,
        "C_nodes_ff": c_nodes,
        "C_via_at_tap_ff": c_via_taps,
        "C_tap_ff": c_tap_loads,
        "C_pg_ff": C_pg_ff,
        "n_pg": n_pg,
        "C_pg_load_ff": c_pg_load,
        "C_drv_par_ff": C_drv_par_ff,
        "include_c_pg": include_c_pg,
        "vias_per_tap": vias_per_tap,
        "y_um": y_um,
        "C_total_ff": float(sum(c_nodes)),
        "model": "pi_ladder",
        "note": (
            "pi: C_seg/2 on each side of R_seg; C_tap=C_via+n_pg*C_pg at each tap node; "
            "node0 = driver output (C_drv_par + first C_seg/2)"
        ),
    }


def elmore_delays(
    ladder: dict[str, Any],
    R_drv: float,
) -> dict[str, Any]:
    """Elmore delay from driver output to each node (and end).

    ``t_elmore(k) = sum_{j=0..k} R_upstream(j) * C_j``
    with ``R_upstream(0)=R_drv``, ``R_upstream(j)=R_drv + sum_{i=1..j} R_i``.

    Returns delays in **ps** (R in Ohm, C in fF).
    """
    R_drv = float(R_drv)
    r_series = [float(x) for x in ladder["R_series_ohm"]]
    c_nodes = [float(x) for x in ladder["C_nodes_ff"]]
    n = len(r_series)
    assert len(c_nodes) == n + 1

    r_up: list[float] = []
    acc = R_drv
    r_up.append(acc)  # node 0
    for r in r_series:
        acc += r
        r_up.append(acc)

    t_ps: list[float] = []
    running = 0.0
    for j in range(n + 1):
        running += r_up[j] * c_nodes[j] * _RC_TO_PS
        t_ps.append(running)

    # Per-tap = nodes 1..N (skip driver node0)
    per_tap_ps = t_ps[1:]

    return {
        "R_drv_ohm": R_drv,
        "R_upstream_ohm": r_up,
        "t_elmore_ps": t_ps,
        "t_elmore_node0_ps": t_ps[0],
        "t_elmore_end_ps": t_ps[-1],
        "per_tap_delays_ps": per_tap_ps,
        "units": {"delay": "ps", "R": "Ohm", "C": "fF"},
        "formula": "t(k)=sum_j R_up(j)*C_j with R_up including R_drv; ps = Ohm*fF*1e-3",
    }


def analyze_wl_l2(
    component_or_wl_rc: Component | dict[str, Any],
    *,
    R_drv: float | None = None,
    C_pg_ff: float | None = None,
    n_pg: int | None = None,
    C_drv_par_ff: float | None = None,
    Vdd: float | None = None,
    net: str = "WL",
    metal: str = "M2",
) -> dict[str, Any]:
    """Full L2 analysis: pi-ladder Elmore + sensitivity (wire-only vs with loads).

    Accepts either a gdsfactory Component (runs ``extract_wl_rc``) or an
    existing ``extract_wl_rc`` dict.
    """
    cfg = load_analysis_l2()
    if R_drv is None:
        R_drv = float(cfg["R_drv_ohm"])
    if Vdd is None:
        Vdd = float(cfg["Vdd_V"])
    R_drv = float(R_drv)
    Vdd = float(Vdd)

    if isinstance(component_or_wl_rc, dict) and "ladder" in component_or_wl_rc:
        wl_rc = component_or_wl_rc
    elif isinstance(component_or_wl_rc, dict) and "metal_rc" in component_or_wl_rc:
        wl_rc = component_or_wl_rc
    else:
        wl_rc = extract_wl_rc(component_or_wl_rc, net=net, metal=metal)  # type: ignore[arg-type]

    # Infer PG count/finger count from pattern metadata when present.
    info = wl_rc.get("component_info") or {}
    if n_pg is None:
        n_pg = int(info.get("n_pg", cfg["n_pg_default"]))
    pg_nfinger_raw = info.get("pg_nfinger")
    pg_nfinger = int(pg_nfinger_raw) if pg_nfinger_raw is not None else None

    # The user rule is per PG finger. An explicit C_pg_ff API argument remains
    # authoritative for synthetic ladders and calibration sweeps.
    c_pg_ff_per_finger = float(cfg["C_pg_ff_per_finger"])
    if C_pg_ff is None and pg_nfinger is not None:
        c_pg_used = c_pg_ff_per_finger * pg_nfinger
        c_pg_rule = cfg.get("C_pg_source", "user_rule_0p3fF_per_finger")
    elif C_pg_ff is None:
        c_pg_used = float(cfg["C_pg_ff"])
        c_pg_rule = "config_C_pg_ff"
    else:
        c_pg_used = float(C_pg_ff)
        c_pg_rule = "explicit_override"

    ladder_loads = build_pi_ladder_from_wl_rc(
        wl_rc,
        C_pg_ff=c_pg_used,
        n_pg=n_pg,
        C_drv_par_ff=C_drv_par_ff,
        include_c_pg=True,
        analysis_cfg=cfg,
    )
    ladder_wire = build_pi_ladder_from_wl_rc(
        wl_rc,
        C_pg_ff=c_pg_used,
        n_pg=n_pg,
        C_drv_par_ff=C_drv_par_ff,
        include_c_pg=False,
        analysis_cfg=cfg,
    )

    elmore_loads = elmore_delays(ladder_loads, R_drv)
    elmore_wire = elmore_delays(ladder_wire, R_drv)

    c_total = float(ladder_loads["C_total_ff"])
    # Energy in fJ when C in fF and V in V: 0.5 * C_fF * V^2
    energy_fj = 0.5 * c_total * (Vdd ** 2)

    placeholders = []
    if cfg.get("R_drv_source") == "placeholder_unverified":
        placeholders.append("R_drv_ohm")
    if cfg.get("C_pg_source") == "placeholder_unverified":
        placeholders.append("C_pg_ff")
    if cfg.get("Vdd_source") == "placeholder_unverified":
        placeholders.append("Vdd_V")

    result: dict[str, Any] = {
        "level": "L2",
        "model": "pi_ladder_elmore",
        "net": wl_rc.get("net", net),
        "metal": wl_rc.get("metal", metal),
        "length_um": wl_rc.get("length_um"),
        "n_bitcells": wl_rc.get("n_bitcells"),
        "tap_pitch_um": wl_rc.get("tap_pitch_um"),
        "R_drv_ohm": R_drv,
        "R_drv_source": cfg.get("R_drv_source"),
        "C_pg_ff": c_pg_used,
        "C_pg_ff_per_finger": c_pg_ff_per_finger,
        "C_pg_source": cfg.get("C_pg_source"),
        "C_pg_rule": c_pg_rule,
        "pg_nfinger": pg_nfinger,
        "C_pg_load_ff": float(ladder_loads["C_pg_load_ff"]),
        "n_pg": int(n_pg),
        "C_drv_par_ff": float(C_drv_par_ff if C_drv_par_ff is not None else cfg["C_drv_par_ff"]),
        "Vdd_V": Vdd,
        "Vdd_source": cfg.get("Vdd_source"),
        "placeholders": placeholders,
        "ladder": {
            "n_seg": ladder_loads["n_seg"],
            "seg_length_um": ladder_loads["seg_length_um"],
            "r_ohm_per_um": ladder_loads["r_ohm_per_um"],
            "c_ff_per_um": ladder_loads["c_ff_per_um"],
            "vias_per_tap": ladder_loads["vias_per_tap"],
            "C_via_at_tap_ff": ladder_loads["C_via_at_tap_ff"][:1][0] if ladder_loads["C_via_at_tap_ff"] else None,
            "C_tap_ff_with_pg": ladder_loads["C_tap_ff"][:1][0] if ladder_loads["C_tap_ff"] else None,
            "C_pg_load_ff": float(ladder_loads["C_pg_load_ff"]),
            "C_total_ff": c_total,
            "C_total_wire_only_ff": float(ladder_wire["C_total_ff"]),
            "note": ladder_loads["note"],
        },
        "elmore": {
            "t_elmore_end_ps": elmore_loads["t_elmore_end_ps"],
            "per_tap_delays_ps": elmore_loads["per_tap_delays_ps"],
            "t_elmore_node0_ps": elmore_loads["t_elmore_node0_ps"],
            "tau_with_loads_ps": elmore_loads["t_elmore_end_ps"],
            "tau_wire_only_ps": elmore_wire["t_elmore_end_ps"],
            "formula": elmore_loads["formula"],
        },
        "energy_proxy": {
            "E_fj": energy_fj,
            "formula": "0.5 * C_total_ff * Vdd_V^2  (fJ)",
            "Vdd_V": Vdd,
            "C_total_ff": c_total,
            "source": cfg.get("Vdd_source"),
        },
        "l1_totals": wl_rc.get("totals"),
        "sources": {
            "l1": "extract_wl_rc / interconnect_rc LUT",
            "l2_params": "n5_1p13m.yaml#analysis_l2",
            "metal": (wl_rc.get("metal_table") or {}).get("source"),
            "via": (wl_rc.get("via") or {}).get("table", {}).get("source"),
        },
        "future_l3": (
            "Palace (or similar EM) sampling for R'/C' calibration only — "
            "not implemented in this release."
        ),
        "notes": (
            "L2 Elmore on pi-ladder segmented at WL tap pitch. "
            "R_drv / Vdd remain placeholder_unverified; C_pg uses the user rule "
            "C_pg = 0.3 fF × nfinger_pg. Consistent with L1 extract_wl_rc metal/via numbers."
        ),
    }
    return result


def format_l2_summary(l2: dict[str, Any]) -> str:
    """ASCII-only one-liner for CLI (no non-ASCII unit symbols)."""
    el = l2.get("elmore") or {}
    t_end = el.get("t_elmore_end_ps")
    r_drv = l2.get("R_drv_ohm")
    c_pg = l2.get("C_pg_ff")
    c_pg_rule = l2.get("C_pg_rule")
    ph = l2.get("placeholders") or []
    rule_tag = f" [{c_pg_rule}]" if c_pg_rule else ""
    ph_tag = f" (placeholders: {','.join(ph)})" if ph else ""
    t_str = f"{t_end:.4f}" if isinstance(t_end, (int, float)) else str(t_end)
    return (
        f"L2 Elmore: t_end={t_str} ps  R_drv={r_drv}  C_pg={c_pg}{rule_tag}{ph_tag}"
    )


__all__ = [
    "load_analysis_l2",
    "build_pi_ladder_from_wl_rc",
    "elmore_delays",
    "analyze_wl_l2",
    "format_l2_summary",
]
