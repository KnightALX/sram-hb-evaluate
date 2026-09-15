"""Analytical RC + L2 Elmore for the Hybrid-Bonding folded WL topology.

Paths
-----
A. Baseline: existing 30 um / 60 taps single-die M2 (re-run via extract_wl_rc).
B. HB lower-end: driver → 15 um M2 + 30 taps (local VIA0/VIA1 only).
C. HB upper-end: driver → full up-stack + HB + full down-stack (series) →
   15 um upper M2 + 30 taps.

Vertical stack (one climb): VIA2..VIA12 + RV. Round-trip = two climbs + one HB.
Metal stubs on the vertical path are neglected (via-dominated) — documented.
"""

from __future__ import annotations

from typing import Any

from gdsfactory import Component

from gf_layout_flow.cells.metal import HB_CLIMB_VIAS, STACK_MAP_NOTE
from gf_layout_flow.rc.electrical import extract_wl_rc, _sum_vias_by_class, _tap_via_lump
from gf_layout_flow.rc.elmore_ladder import (
    analyze_wl_l2,
    build_pi_ladder_from_wl_rc,
    elmore_delays,
    load_analysis_l2,
)
from gf_layout_flow.tech.rc_table import get_hb_rc, get_metal_rc, get_via_rc_for_layer


def climb_via_layers() -> tuple[str, ...]:
    """VIA2..VIA12 + RV — one of each per climb."""
    return tuple(HB_CLIMB_VIAS)


def vertical_climb_rc() -> dict[str, Any]:
    """Lumped R/C for one M2→AP climb (VIA2..VIA12 + RV)."""
    per_layer = {name: 1 for name in climb_via_layers()}
    summed = _sum_vias_by_class(per_layer)
    return {
        "n_vias": summed["n_vias"],
        "layers": list(climb_via_layers()),
        "r_ohm": float(summed["r_ohm"]),
        "c_ff": float(summed["c_ff"]),
        "c_plus_cc_ff": float(summed["c_plus_cc_ff"]),
        "per_layer": summed["per_layer"],
        "by_class": summed["by_class"],
        "note": (
            "One climb M2→…→M13→RV→AP. RV mapped to V10-V11 class "
            "(research; not in measured via table). Lateral metal stub R/C neglected."
        ),
    }


def vertical_roundtrip_rc(*, n_hb: int = 1) -> dict[str, Any]:
    """Two climbs + HB instance(s)."""
    climb = vertical_climb_rc()
    hb = get_hb_rc()
    n_hb_i = max(int(n_hb), 0)
    r_hb = n_hb_i * float(hb["r_ohm"])
    c_hb = n_hb_i * float(hb["c_ff"])
    c_hb_plus = n_hb_i * float(hb.get("c_plus_cc_ff", hb["c_ff"]))
    return {
        "n_climbs": 2,
        "n_hb": n_hb_i,
        "climb": climb,
        "hb": {
            "n_hb": n_hb_i,
            "r_ohm_each": float(hb["r_ohm"]),
            "c_ff_each": float(hb["c_ff"]),
            "c_plus_cc_ff_each": float(hb.get("c_plus_cc_ff", hb["c_ff"])),
            "r_ohm": r_hb,
            "c_ff": c_hb,
            "c_plus_cc_ff": c_hb_plus,
            "source": hb.get("source"),
            "size_um": hb.get("size_um"),
        },
        "r_ohm": 2.0 * float(climb["r_ohm"]) + r_hb,
        "c_ff": 2.0 * float(climb["c_ff"]) + c_hb,
        "c_plus_cc_ff": 2.0 * float(climb["c_plus_cc_ff"]) + c_hb_plus,
        "n_vias_total": 2 * int(climb["n_vias"]),
        "metal_stub_assumption": "neglected_via_dominated",
        "stack_map_note": STACK_MAP_NOTE,
    }


def _info(component: Component) -> dict[str, Any]:
    try:
        return dict(getattr(component, "info", {}) or {})
    except Exception:
        return {}


def _die_wl_rc_dict(
    *,
    length_um: float,
    n_bitcells: int,
    tap_pitch_um: float,
    width_um: float,
    metal: str,
    n_local_vias: int,
    per_layer_local: dict[str, int],
    include_driver_vias: bool,
    net: str,
    component_info: dict[str, Any],
) -> dict[str, Any]:
    """Build an extract_wl_rc-compatible dict for one die's M2 ladder (no HB stack)."""
    metal_key = metal.upper()
    metal_rc = get_metal_rc(metal_key)
    if metal_rc is None or metal_rc.get("r_ohm_per_um") is None:
        raise ValueError(f"No RC table entry for metal={metal_key!r}")
    r_per_um = float(metal_rc["r_ohm_per_um"])
    c_per_um = float(metal_rc["c_ff_per_um"])
    r_metal = r_per_um * float(length_um)
    c_metal = c_per_um * float(length_um)

    via_sum = _sum_vias_by_class(per_layer_local)
    r_via = float(via_sum["r_ohm"])
    c_via = float(via_sum["c_ff"])
    tap_lump = _tap_via_lump()
    seg_length = float(tap_pitch_um)
    segments = []
    for i in range(int(n_bitcells)):
        segments.append(
            {
                "index": i + 1,
                "y_um": round((i + 1) * seg_length, 9),
                "seg_length_um": seg_length,
                "r_seg_ohm": r_per_um * seg_length,
                "c_seg_ff": c_per_um * seg_length,
                "via_lump_at_tap": {
                    "n_vias": tap_lump["n_vias"],
                    "r_ohm": tap_lump["r_ohm"],
                    "c_ff": tap_lump["c_ff"],
                    "c_plus_cc_ff": tap_lump["c_plus_cc_ff"],
                    "layers": tap_lump["layers"],
                },
            }
        )

    return {
        "net": net,
        "metal": metal_key,
        "length_um": float(length_um),
        "width_um": float(width_um),
        "n_bitcells": int(n_bitcells),
        "tap_pitch_um": float(tap_pitch_um),
        "metal_table": {
            "r_ohm_per_um": r_per_um,
            "c_ff_per_um": c_per_um,
            "source": metal_rc.get("source"),
            "parents": metal_rc.get("parents"),
        },
        "metal_rc": {"r_ohm": r_metal, "c_ff": c_metal, "formula": "per_um * length_um"},
        "via": {
            "n_vias": int(via_sum["n_vias"]),
            "r_ohm": r_via,
            "c_ff": c_via,
            "c_plus_cc_ff": float(via_sum["c_plus_cc_ff"]),
            "per_layer": via_sum["per_layer"],
            "by_class": via_sum["by_class"],
            "count_method": "hb_fold_local_heuristic",
            "include_driver_vias": include_driver_vias,
            "note": (
                "Local WL vias only (VIA0+VIA1). "
                + (
                    "Includes driver stack VIA0+VIA1=2. "
                    if include_driver_vias
                    else "Upper die: tap vias only (no second driver). "
                )
                + f"n_local={n_local_vias}."
            ),
        },
        "hb": {"n_hb": 0, "r_ohm": 0.0, "c_ff": 0.0},
        "totals": {
            "r_ohm": r_metal + r_via,
            "c_ff": c_metal + c_via,
            "r_metal_ohm": r_metal,
            "c_metal_ff": c_metal,
            "r_via_ohm": r_via,
            "c_via_ff": c_via,
            "r_hb_ohm": 0.0,
            "c_hb_ff": 0.0,
        },
        "ladder": {
            "n_seg": int(n_bitcells),
            "seg_length_um": seg_length,
            "vias_per_tap": int(tap_lump["n_vias"]),
            "tap_via_layers": list(tap_lump["layers"]),
            "segments": segments,
        },
        "component_info": dict(component_info),
    }


def extract_hb_fold_rc(
    component: Component | None = None,
    *,
    wl_length_per_die: float | None = None,
    tap_pitch_um: float = 0.5,
    m2_width_um: float = 0.020,
    n_hb: int = 1,
    metal: str = "M2",
    net: str = "WL",
) -> dict[str, Any]:
    """Analytical RC for lower / upper HB-fold paths (+ vertical stack detail)."""
    info = _info(component) if component is not None else {}
    length = float(
        wl_length_per_die
        if wl_length_per_die is not None
        else info.get("wl_length_lower_um") or info.get("wl_length_um") or 15.0
    )
    pitch = float(info.get("tap_pitch_um") or tap_pitch_um)
    width = float(info.get("m2_width_um") or m2_width_um)
    n_die = int(info.get("n_bitcells_lower") or int(length / pitch))
    n_hb_i = int(info.get("hb_count") or n_hb)

    # Local vias: lower = driver + taps; upper = taps only
    per_lower = {"VIA0": 1 + n_die, "VIA1": 1 + n_die}
    per_upper = {"VIA0": n_die, "VIA1": n_die}
    n_local_lower = 2 + 2 * n_die
    n_local_upper = 2 * n_die

    common_info = {
        "driver_strength": info.get("driver_strength", "D10"),
        "n_pg": int(info.get("n_pg", 2)),
        "pg_nfinger": int(info.get("pg_nfinger", 1)),
        "topology": "hb_fold",
        "baseline_for_hb": False,
        "compares_to": info.get("compares_to", "wl_d10_m2_30um"),
        "net_name": info.get("net_name", net),
        "wl_direction": "Y",
    }

    lower = _die_wl_rc_dict(
        length_um=length,
        n_bitcells=n_die,
        tap_pitch_um=pitch,
        width_um=width,
        metal=metal,
        n_local_vias=n_local_lower,
        per_layer_local=per_lower,
        include_driver_vias=True,
        net=f"{net}_lower",
        component_info={**common_info, "die": "lower", "n_bitcells": n_die},
    )
    upper_local = _die_wl_rc_dict(
        length_um=length,
        n_bitcells=n_die,
        tap_pitch_um=pitch,
        width_um=width,
        metal=metal,
        n_local_vias=n_local_upper,
        per_layer_local=per_upper,
        include_driver_vias=False,
        net=f"{net}_upper",
        component_info={**common_info, "die": "upper", "n_bitcells": n_die},
    )

    stack = vertical_roundtrip_rc(n_hb=n_hb_i)

    # Upper path totals = local upper + vertical round-trip + HB
    upper_totals = {
        "r_ohm": float(upper_local["totals"]["r_ohm"]) + float(stack["r_ohm"]),
        "c_ff": float(upper_local["totals"]["c_ff"]) + float(stack["c_ff"]),
        "r_metal_ohm": float(upper_local["totals"]["r_metal_ohm"]),
        "c_metal_ff": float(upper_local["totals"]["c_metal_ff"]),
        "r_via_local_ohm": float(upper_local["totals"]["r_via_ohm"]),
        "c_via_local_ff": float(upper_local["totals"]["c_via_ff"]),
        "r_stack_ohm": float(stack["r_ohm"]),
        "c_stack_ff": float(stack["c_ff"]),
        "r_hb_ohm": float(stack["hb"]["r_ohm"]),
        "c_hb_ff": float(stack["hb"]["c_ff"]),
    }

    return {
        "topology": "hb_fold",
        "stack_map_note": STACK_MAP_NOTE,
        "wl_length_lower_um": length,
        "wl_length_upper_um": length,
        "n_bitcells_lower": n_die,
        "n_bitcells_upper": n_die,
        "n_bitcells_total": 2 * n_die,
        "tap_pitch_um": pitch,
        "m2_width_um": width,
        "hb_count": n_hb_i,
        "metal": metal.upper(),
        "vertical_stack": stack,
        "lower": lower,
        "upper_local": upper_local,
        "upper_path_totals": upper_totals,
        "lower_path_totals": dict(lower["totals"]),
        "assumptions": {
            "metal_stub_rc": "neglected_via_dominated",
            "rv_mapping": "V10-V11 class (research; DRM min_size 2.7 um)",
            "m14_mapping": "M14 ≈ AP / HB landing (no M14 CAD in 1P13M)",
            "upper_local_vias": "tap VIA0+VIA1 only (no second driver on upper die)",
            "R_drv": "placeholder_unverified (analysis_l2)",
        },
        "component_info": {
            k: info[k]
            for k in (
                "topology",
                "driver_strength",
                "wl_length_lower_um",
                "wl_length_upper_um",
                "n_bitcells_lower",
                "n_bitcells_upper",
                "n_bitcells_total",
                "hb_count",
                "stack_map_note",
                "baseline_for_hb",
                "compares_to",
                "n_pg",
                "pg_nfinger",
            )
            if k in info
        },
        "notes": (
            "HB-fold analytical RC from measured LUT. Vertical path = two climbs "
            "(VIA2..VIA12+RV each) + one HB. Lateral metal stubs neglected. "
            "Research sketch — not foundry extraction."
        ),
    }


def analyze_hb_fold_l2(
    component_or_rc: Component | dict[str, Any] | None = None,
    *,
    R_drv: float | None = None,
    baseline_component: Component | None = None,
) -> dict[str, Any]:
    """L2 Elmore for baseline / HB-lower / HB-upper paths.

    Upper path: vertical+HB modeled as one prepended pi segment
    (series R_stack with C_stack/2 on each side) before the upper WL ladder.
    """
    cfg = load_analysis_l2()
    if R_drv is None:
        R_drv = float(cfg["R_drv_ohm"])
    R_drv = float(R_drv)

    if isinstance(component_or_rc, dict) and "vertical_stack" in component_or_rc:
        hb_rc = component_or_rc
    else:
        hb_rc = extract_hb_fold_rc(component_or_rc)  # type: ignore[arg-type]

    # Lower path: standard L2 on lower die wl_rc
    l2_lower = analyze_wl_l2(hb_rc["lower"], R_drv=R_drv)

    # Upper path: prepend stack as pi segment then Elmore
    stack = hb_rc["vertical_stack"]
    r_stack = float(stack["r_ohm"])
    c_stack = float(stack["c_ff"])
    ladder_u = build_pi_ladder_from_wl_rc(hb_rc["upper_local"], analysis_cfg=cfg)
    # Prepend: C0' = C_drv_par + C_stack/2; R_stack; then original nodes with
    # C0_metal_half absorbed into node after stack.
    c_drv = float(ladder_u["C_drv_par_ff"])
    c_nodes_orig = [float(x) for x in ladder_u["C_nodes_ff"]]
    r_series_orig = [float(x) for x in ladder_u["R_series_ohm"]]
    # Remove C_drv from orig[0] before merging (we'll put C_drv on new node0)
    c0_rest = c_nodes_orig[0] - c_drv
    c_nodes = [c_drv + c_stack / 2.0, c_stack / 2.0 + c0_rest] + c_nodes_orig[1:]
    r_series = [r_stack] + r_series_orig
    ladder_upper = {
        "n_seg": len(r_series),
        "n_nodes": len(c_nodes),
        "R_series_ohm": r_series,
        "C_nodes_ff": c_nodes,
        "C_total_ff": float(sum(c_nodes)),
        "seg_length_um": ladder_u["seg_length_um"],
        "model": "pi_ladder_with_series_hb_stack",
        "stack_r_ohm": r_stack,
        "stack_c_ff": c_stack,
        "stack_c_distribution": "C_stack/2 at driver-side node0 and C_stack/2 at upper-WL start",
        "note": (
            "Vertical round-trip+HB prepended as one pi segment (R_stack, C_stack/2 "
            "each side) before the upper 15 um / 30-tap M2 ladder."
        ),
    }
    elmore_upper = elmore_delays(ladder_upper, R_drv)

    # Wire-only upper (no PG) for sensitivity
    ladder_u_wire = build_pi_ladder_from_wl_rc(
        hb_rc["upper_local"], include_c_pg=False, analysis_cfg=cfg
    )
    c_nodes_w = [float(x) for x in ladder_u_wire["C_nodes_ff"]]
    c_drv_w = float(ladder_u_wire["C_drv_par_ff"])
    c0_rest_w = c_nodes_w[0] - c_drv_w
    c_nodes_wire = [c_drv_w + c_stack / 2.0, c_stack / 2.0 + c0_rest_w] + c_nodes_w[1:]
    r_series_wire = [r_stack] + [float(x) for x in ladder_u_wire["R_series_ohm"]]
    elmore_upper_wire = elmore_delays(
        {"R_series_ohm": r_series_wire, "C_nodes_ff": c_nodes_wire}, R_drv
    )

    # Baseline (30 um) if provided or build default
    if baseline_component is not None:
        l2_base = analyze_wl_l2(baseline_component, R_drv=R_drv)
        rc_base = extract_wl_rc(baseline_component)
    else:
        from gf_layout_flow.cells.sram_wl_pattern import wl_longline_pattern

        base = wl_longline_pattern(wl_length=30.0, tap_pitch=0.5)
        l2_base = analyze_wl_l2(base, R_drv=R_drv)
        rc_base = extract_wl_rc(base)

    t_base = float(l2_base["elmore"]["t_elmore_end_ps"])
    t_lower = float(l2_lower["elmore"]["t_elmore_end_ps"])
    t_upper = float(elmore_upper["t_elmore_end_ps"])

    def _delta(t: float) -> dict[str, float]:
        return {
            "t_elmore_end_ps": t,
            "delta_ps": t - t_base,
            "ratio_vs_baseline": t / t_base if t_base else float("nan"),
        }

    critical = "upper" if t_upper >= t_lower else "lower"
    # HB fold "wins" when critical end is faster than baseline
    t_critical = max(t_lower, t_upper)
    wins = t_critical < t_base

    return {
        "level": "L2",
        "model": "pi_ladder_elmore_hb_fold",
        "topology": "hb_fold",
        "stack_map_note": STACK_MAP_NOTE,
        "R_drv_ohm": R_drv,
        "R_drv_source": cfg.get("R_drv_source"),
        "C_pg_ff": l2_lower.get("C_pg_ff"),
        "C_pg_load_ff": l2_lower.get("C_pg_load_ff"),
        "n_pg": l2_lower.get("n_pg"),
        "vertical_stack": stack,
        "baseline": {
            "name": "wl_d10_m2_30um",
            "length_um": rc_base.get("length_um"),
            "n_bitcells": rc_base.get("n_bitcells"),
            "totals": rc_base.get("totals"),
            "l2": {
                "t_elmore_end_ps": t_base,
                "C_total_ff": l2_base["ladder"]["C_total_ff"],
                "tau_wire_only_ps": l2_base["elmore"]["tau_wire_only_ps"],
            },
        },
        "hb_lower": {
            "length_um": hb_rc["wl_length_lower_um"],
            "n_bitcells": hb_rc["n_bitcells_lower"],
            "totals": hb_rc["lower_path_totals"],
            "l2": {
                "t_elmore_end_ps": t_lower,
                "C_total_ff": l2_lower["ladder"]["C_total_ff"],
                "tau_wire_only_ps": l2_lower["elmore"]["tau_wire_only_ps"],
                "per_tap_delays_ps": l2_lower["elmore"]["per_tap_delays_ps"],
            },
            "vs_baseline": _delta(t_lower),
        },
        "hb_upper": {
            "length_um": hb_rc["wl_length_upper_um"],
            "n_bitcells": hb_rc["n_bitcells_upper"],
            "totals": hb_rc["upper_path_totals"],
            "ladder_note": ladder_upper["note"],
            "stack_c_distribution": ladder_upper["stack_c_distribution"],
            "l2": {
                "t_elmore_end_ps": t_upper,
                "C_total_ff": ladder_upper["C_total_ff"],
                "tau_wire_only_ps": elmore_upper_wire["t_elmore_end_ps"],
                "t_elmore_node0_ps": elmore_upper["t_elmore_node0_ps"],
                "per_tap_delays_ps": elmore_upper["per_tap_delays_ps"][1:],  # skip stack node
                "n_nodes": ladder_upper["n_nodes"],
            },
            "vs_baseline": _delta(t_upper),
        },
        "comparison": {
            "critical_end": critical,
            "t_elmore_end_baseline_ps": t_base,
            "t_elmore_end_lower_ps": t_lower,
            "t_elmore_end_upper_ps": t_upper,
            "t_elmore_end_critical_ps": t_critical,
            "delta_critical_vs_baseline_ps": t_critical - t_base,
            "ratio_critical_vs_baseline": t_critical / t_base if t_base else float("nan"),
            "hb_fold_wins_vs_baseline": wins,
            "qualitative": (
                f"Critical end is the {critical} die "
                f"(t_end={t_critical:.4f} ps vs baseline {t_base:.4f} ps). "
                + (
                    "HB fold wins on end delay (critical < baseline)."
                    if wins
                    else "HB fold does not win on end delay (critical >= baseline); "
                    "stack R/C and/or still-loaded ends dominate."
                )
                + " Assumptions: M14→AP, RV→V10-V11, metal stubs neglected, "
                "R_drv placeholder, C_stack split half/half across series R_stack."
            ),
        },
        "assumptions": hb_rc.get("assumptions"),
        "notes": (
            "L2 Elmore: lower = standard 15 um pi-ladder; upper = R_stack series "
            "pi-prepend + 15 um ladder. C_pg = 0.3 fF × finger; dual-PG → 0.6 fF/tap."
        ),
    }


def compare_hb_vs_baseline(
    *,
    hb_component: Component | None = None,
    baseline_component: Component | None = None,
    R_drv: float | None = None,
) -> dict[str, Any]:
    """Full comparison payload for JSON / markdown report."""
    from gf_layout_flow.cells.sram_wl_pattern import wl_hb_fold_pattern, wl_longline_pattern
    from gf_layout_flow import __version__

    base = baseline_component or wl_longline_pattern(wl_length=30.0, tap_pitch=0.5)
    hb = hb_component or wl_hb_fold_pattern()
    hb_rc = extract_hb_fold_rc(hb)
    l2 = analyze_hb_fold_l2(hb_rc, R_drv=R_drv, baseline_component=base)
    rc_base = extract_wl_rc(base)

    climb = hb_rc["vertical_stack"]["climb"]
    return {
        "version": __version__,
        "topology_baseline": "single_die_m2_30um_60taps",
        "topology_hb": "hb_fold_15um_30taps_x2",
        "stack_map_note": STACK_MAP_NOTE,
        "vertical_stack": {
            "one_climb_n_vias": climb["n_vias"],
            "one_climb_layers": climb["layers"],
            "one_climb_r_ohm": climb["r_ohm"],
            "one_climb_c_ff": climb["c_ff"],
            "roundtrip_n_vias": hb_rc["vertical_stack"]["n_vias_total"],
            "roundtrip_n_hb": hb_rc["vertical_stack"]["n_hb"],
            "roundtrip_r_ohm": hb_rc["vertical_stack"]["r_ohm"],
            "roundtrip_c_ff": hb_rc["vertical_stack"]["c_ff"],
            "hb_r_ohm": hb_rc["vertical_stack"]["hb"]["r_ohm"],
            "hb_c_ff": hb_rc["vertical_stack"]["hb"]["c_ff"],
            "metal_stub_assumption": "neglected_via_dominated",
        },
        "baseline": {
            "length_um": 30.0,
            "n_bitcells": 60,
            "n_pg_loads": 60,
            "r_total_ohm": rc_base["totals"]["r_ohm"],
            "c_total_ff": rc_base["totals"]["c_ff"],
            "r_metal_ohm": rc_base["totals"]["r_metal_ohm"],
            "c_metal_ff": rc_base["totals"]["c_metal_ff"],
            "r_via_ohm": rc_base["totals"]["r_via_ohm"],
            "c_via_ff": rc_base["totals"]["c_via_ff"],
            "n_vias_local": rc_base["via"]["n_vias"],
            "t_elmore_end_ps": l2["baseline"]["l2"]["t_elmore_end_ps"],
        },
        "hb_lower": {
            "length_um": 15.0,
            "n_bitcells": 30,
            "n_pg_loads": 30,
            "r_total_ohm": hb_rc["lower_path_totals"]["r_ohm"],
            "c_total_ff": hb_rc["lower_path_totals"]["c_ff"],
            "r_metal_ohm": hb_rc["lower_path_totals"]["r_metal_ohm"],
            "c_metal_ff": hb_rc["lower_path_totals"]["c_metal_ff"],
            "r_via_ohm": hb_rc["lower_path_totals"]["r_via_ohm"],
            "c_via_ff": hb_rc["lower_path_totals"]["c_via_ff"],
            "t_elmore_end_ps": l2["hb_lower"]["l2"]["t_elmore_end_ps"],
            "vs_baseline": l2["hb_lower"]["vs_baseline"],
        },
        "hb_upper": {
            "length_um": 15.0,
            "n_bitcells": 30,
            "n_pg_loads": 30,
            "r_total_ohm": hb_rc["upper_path_totals"]["r_ohm"],
            "c_total_ff": hb_rc["upper_path_totals"]["c_ff"],
            "r_metal_ohm": hb_rc["upper_path_totals"]["r_metal_ohm"],
            "c_metal_ff": hb_rc["upper_path_totals"]["c_metal_ff"],
            "r_via_local_ohm": hb_rc["upper_path_totals"]["r_via_local_ohm"],
            "c_via_local_ff": hb_rc["upper_path_totals"]["c_via_local_ff"],
            "r_stack_ohm": hb_rc["upper_path_totals"]["r_stack_ohm"],
            "c_stack_ff": hb_rc["upper_path_totals"]["c_stack_ff"],
            "t_elmore_end_ps": l2["hb_upper"]["l2"]["t_elmore_end_ps"],
            "vs_baseline": l2["hb_upper"]["vs_baseline"],
            "stack_c_distribution": l2["hb_upper"]["stack_c_distribution"],
        },
        "comparison": l2["comparison"],
        "assumptions": hb_rc["assumptions"],
        "l2_detail": l2,
        "hb_rc": hb_rc,
    }


def format_hb_compare_summary(cmp: dict[str, Any]) -> str:
    """ASCII CLI summary for HB vs baseline."""
    b = cmp["baseline"]
    lo = cmp["hb_lower"]
    up = cmp["hb_upper"]
    vs = cmp["vertical_stack"]
    c = cmp["comparison"]
    lines = [
        "=== HB fold vs baseline (L1/L2) ===",
        f"Stack: 1 climb n_vias={vs['one_climb_n_vias']} "
        f"R={vs['one_climb_r_ohm']:.4f} Ohm C={vs['one_climb_c_ff']:.4f} fF; "
        f"round-trip R={vs['roundtrip_r_ohm']:.4f} C={vs['roundtrip_c_ff']:.4f} "
        f"(HB R={vs['hb_r_ohm']} C={vs['hb_c_ff']})",
        f"Baseline 30 um / 60 taps: R={b['r_total_ohm']:.4f} C={b['c_total_ff']:.4f} "
        f"t_end={b['t_elmore_end_ps']:.4f} ps",
        f"HB lower 15 um / 30 taps: R={lo['r_total_ohm']:.4f} C={lo['c_total_ff']:.4f} "
        f"t_end={lo['t_elmore_end_ps']:.4f} ps "
        f"(ratio={lo['vs_baseline']['ratio_vs_baseline']:.4f})",
        f"HB upper 15 um / 30 taps + stack: R={up['r_total_ohm']:.4f} "
        f"C={up['c_total_ff']:.4f} t_end={up['t_elmore_end_ps']:.4f} ps "
        f"(ratio={up['vs_baseline']['ratio_vs_baseline']:.4f})",
        f"Critical end: {c['critical_end']}  "
        f"delta_vs_baseline={c['delta_critical_vs_baseline_ps']:.4f} ps  "
        f"hb_fold_wins={c['hb_fold_wins_vs_baseline']}",
        c["qualitative"],
    ]
    return "\n".join(lines)


def write_hb_compare_markdown(cmp: dict[str, Any], path) -> None:
    """Write a short markdown comparison report."""
    from pathlib import Path

    b = cmp["baseline"]
    lo = cmp["hb_lower"]
    up = cmp["hb_upper"]
    vs = cmp["vertical_stack"]
    c = cmp["comparison"]
    text = f"""# HB-folded WL vs 30 um baseline

Version: **{cmp.get('version')}**

## Stack mapping (M14)

{cmp['stack_map_note']}

## Vertical path (measured LUT)

| Item | n | R (Ohm) | C (fF) |
|------|---|---------|--------|
| One climb (VIA2..VIA12 + RV) | {vs['one_climb_n_vias']} vias | {vs['one_climb_r_ohm']:.4f} | {vs['one_climb_c_ff']:.4f} |
| Round-trip (2 climbs) | {vs['roundtrip_n_vias']} vias | {2*vs['one_climb_r_ohm']:.4f} | {2*vs['one_climb_c_ff']:.4f} |
| HB | {vs['roundtrip_n_hb']} | {vs['hb_r_ohm']:.4f} | {vs['hb_c_ff']:.4f} |
| **Round-trip + HB** | | **{vs['roundtrip_r_ohm']:.4f}** | **{vs['roundtrip_c_ff']:.4f}** |

Climb layers: `{' '.join(vs['one_climb_layers'])}`

Metal stubs on the vertical path: **neglected** (via-dominated).

## Path comparison

| Path | Length (um) | n_taps | R_total (Ohm) | C_total (fF) | t_elmore_end (ps) | ratio vs baseline |
|------|-------------|--------|---------------|--------------|-------------------|-------------------|
| Baseline (single M2) | {b['length_um']} | {b['n_bitcells']} | {b['r_total_ohm']:.4f} | {b['c_total_ff']:.4f} | {b['t_elmore_end_ps']:.4f} | 1.000 |
| HB lower | {lo['length_um']} | {lo['n_bitcells']} | {lo['r_total_ohm']:.4f} | {lo['c_total_ff']:.4f} | {lo['t_elmore_end_ps']:.4f} | {lo['vs_baseline']['ratio_vs_baseline']:.4f} |
| HB upper (+ stack) | {up['length_um']} | {up['n_bitcells']} | {up['r_total_ohm']:.4f} | {up['c_total_ff']:.4f} | {up['t_elmore_end_ps']:.4f} | {up['vs_baseline']['ratio_vs_baseline']:.4f} |

### Metal / via detail

| Path | R_metal | C_metal | R_via (local) | C_via (local) | R_stack | C_stack |
|------|---------|---------|---------------|---------------|---------|---------|
| Baseline | {b['r_metal_ohm']:.4f} | {b['c_metal_ff']:.4f} | {b['r_via_ohm']:.4f} | {b['c_via_ff']:.4f} | — | — |
| HB lower | {lo['r_metal_ohm']:.4f} | {lo['c_metal_ff']:.4f} | {lo['r_via_ohm']:.4f} | {lo['c_via_ff']:.4f} | — | — |
| HB upper | {up['r_metal_ohm']:.4f} | {up['c_metal_ff']:.4f} | {up['r_via_local_ohm']:.4f} | {up['c_via_local_ff']:.4f} | {up['r_stack_ohm']:.4f} | {up['c_stack_ff']:.4f} |

## Qualitative

- Critical end: **{c['critical_end']}** (`t_end={c['t_elmore_end_critical_ps']:.4f}` ps)
- Delta vs baseline: **{c['delta_critical_vs_baseline_ps']:.4f}** ps
- HB fold wins: **{c['hb_fold_wins_vs_baseline']}**
- {c['qualitative']}

### Assumptions

- M14 → AP / HB landing (1P13M has no M14 CAD)
- RV → V10-V11 class (research mapping)
- Vertical metal stub R/C neglected
- `R_drv=200 Ohm` placeholder_unverified
- Upper stack C: half at driver-side node, half at upper-WL start (`{up['stack_c_distribution']}`)
- C_pg = 0.3 fF × finger; dual-PG → 0.6 fF/tap
"""
    Path(path).write_text(text, encoding="utf-8")


__all__ = [
    "climb_via_layers",
    "vertical_climb_rc",
    "vertical_roundtrip_rc",
    "extract_hb_fold_rc",
    "analyze_hb_fold_l2",
    "compare_hb_vs_baseline",
    "format_hb_compare_summary",
    "write_hb_compare_markdown",
]
