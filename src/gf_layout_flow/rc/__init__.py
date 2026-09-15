"""RC-related extractors: geometry metrics + analytical interconnect RC + L2 Elmore."""

from __future__ import annotations

from gf_layout_flow.rc.extract import extract_rc_metrics, metrics_to_jsonable
from gf_layout_flow.rc.electrical import (
    extract_wl_rc,
    extract_net_rc,
    count_wl_vias,
    format_wl_rc_summary,
)
from gf_layout_flow.rc.elmore_ladder import (
    load_analysis_l2,
    build_pi_ladder_from_wl_rc,
    elmore_delays,
    analyze_wl_l2,
    format_l2_summary,
)
from gf_layout_flow.rc.hb_fold import (
    climb_via_layers,
    vertical_climb_rc,
    vertical_roundtrip_rc,
    extract_hb_fold_rc,
    analyze_hb_fold_l2,
    compare_hb_vs_baseline,
    format_hb_compare_summary,
    write_hb_compare_markdown,
)

__all__ = [
    "extract_rc_metrics",
    "metrics_to_jsonable",
    "extract_wl_rc",
    "extract_net_rc",
    "count_wl_vias",
    "format_wl_rc_summary",
    "load_analysis_l2",
    "build_pi_ladder_from_wl_rc",
    "elmore_delays",
    "analyze_wl_l2",
    "format_l2_summary",
    "climb_via_layers",
    "vertical_climb_rc",
    "vertical_roundtrip_rc",
    "extract_hb_fold_rc",
    "analyze_hb_fold_l2",
    "compare_hb_vs_baseline",
    "format_hb_compare_summary",
    "write_hb_compare_markdown",
]
