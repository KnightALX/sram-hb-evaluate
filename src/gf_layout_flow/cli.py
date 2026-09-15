"""Demo CLI: build sample N5 layouts (FEOL + BEOL), write GDS + RC metrics JSON."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import gdsfactory as gf

from gf_layout_flow import __version__
from gf_layout_flow.tech.pdk import activate_pdk, PDK_NAME, STACK_OPTION
from gf_layout_flow.cells import (
    sram_interconnect_block,
    hb_pad_array,
    metal_bus,
    metal_wire,
    stacked_via,
    nmos_finger,
    pmos_finger,
    wl_longline_pattern,
    wl_hb_fold_pattern,
)
from gf_layout_flow.rc import (
    extract_rc_metrics,
    metrics_to_jsonable,
    extract_wl_rc,
    format_wl_rc_summary,
    analyze_wl_l2,
    format_l2_summary,
    extract_hb_fold_rc,
    analyze_hb_fold_l2,
    compare_hb_vs_baseline,
    format_hb_compare_summary,
    write_hb_compare_markdown,
)

activate_pdk()


def _default_artifacts_dir() -> Path:
    here = Path(__file__).resolve()
    root = here.parents[2]
    candidate = root / "artifacts"
    if candidate.is_dir() or (root / "pyproject.toml").exists():
        candidate.mkdir(parents=True, exist_ok=True)
        return candidate
    out = Path.cwd() / "artifacts"
    out.mkdir(parents=True, exist_ok=True)
    return out


def build_demo_top() -> gf.Component:
    """Compose N5 FEOL transistors + metals + HB pad array demo."""
    activate_pdk()
    c = gf.Component()
    sram = sram_interconnect_block(
        n_bls=8,
        n_wls=8,
        bl_length=40.0,
        wl_length=30.0,
        bl_pitch=0.10,
        wl_pitch=0.10,
        bl_metal="M2",
        wl_metal="M3",
    )
    bus_m5 = metal_bus(length=25.0, metal="M5", n_fingers=4, pitch=0.12)
    wire_m12 = metal_wire(length=20.0, metal="M12")
    wire_m0 = metal_wire(length=15.0, metal="M0")
    wire_ap = metal_wire(length=12.0, metal="AP")
    via_m1m2 = stacked_via(bottom_metal="M1", top_metal="M2")
    via_rv = stacked_via(bottom_metal="M13", top_metal="AP")
    hb = hb_pad_array(rows=4, cols=4, pad_size=2.0, pitch=4.0, via_size=0.8)

    # FEOL transistor sketches
    nmos = nmos_finger()
    pmos = pmos_finger()  # includes NW placeholder

    r_sram = c.add_ref(sram)
    r_hb = c.add_ref(hb)
    r_bus = c.add_ref(bus_m5)
    r_m12 = c.add_ref(wire_m12)
    r_m0 = c.add_ref(wire_m0)
    r_ap = c.add_ref(wire_ap)
    r_via = c.add_ref(via_m1m2)
    r_rv = c.add_ref(via_rv)
    r_nmos = c.add_ref(nmos)
    r_pmos = c.add_ref(pmos)

    r_sram.move((0, 0))
    r_hb.move((60, 0))
    r_bus.move((0, 30))
    r_m12.move((0, 40))
    r_m0.move((25, 40))
    r_ap.move((45, 40))
    r_via.move((50, 35))
    r_rv.move((55, 42))
    r_nmos.move((0, 50))
    r_pmos.move((1.0, 50))

    c.info["demo"] = "n5_feol_nmos+pmos+sram+m5_bus+m12+m0+ap+hb+vias"
    c.info["pdk"] = PDK_NAME
    c.info["stack_option"] = STACK_OPTION
    c.info["version"] = __version__
    c.info["n_pads"] = hb.info.get("n_pads")
    c.info["pitch_um"] = hb.info.get("pitch_um")
    c.info["pad_size_um"] = hb.info.get("pad_size_um")
    c.info["nw_placeholder"] = True
    return c


def build_feol_demo() -> gf.Component:
    """Tiny FEOL-only transistor sketch (NMOS + PMOS side by side)."""
    activate_pdk()
    c = gf.Component()
    nmos = nmos_finger()
    pmos = pmos_finger()
    r_n = c.add_ref(nmos)
    r_p = c.add_ref(pmos)
    r_n.move((0, 0))
    r_p.move((0.5, 0))
    c.info["demo"] = "feol_nmos_pmos_finger"
    c.info["pdk"] = PDK_NAME
    c.info["version"] = __version__
    c.info["nw_placeholder"] = True
    c.info["nw_note"] = "PMOS NW CAD (1;0) is placeholder_unverified — verify T-N05-CL-LE-001"
    return c


def run_demo(artifacts_dir: Path | None = None, write_gds: bool = True) -> dict:
    activate_pdk()
    artifacts = artifacts_dir or _default_artifacts_dir()
    artifacts.mkdir(parents=True, exist_ok=True)

    top = build_demo_top()
    metrics = extract_rc_metrics(top)
    payload = metrics_to_jsonable(metrics)

    feol = build_feol_demo()
    feol_metrics = extract_rc_metrics(feol)
    feol_payload = metrics_to_jsonable(feol_metrics)

    gds_path = artifacts / "demo_top.gds"
    json_path = artifacts / "demo_top_metrics.json"
    feol_gds = artifacts / "demo_feol.gds"
    feol_json = artifacts / "demo_feol_metrics.json"

    if write_gds:
        top.write_gds(gds_path)
        feol.write_gds(feol_gds)

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
        f.write("\n")
    with open(feol_json, "w", encoding="utf-8") as f:
        json.dump(feol_payload, f, indent=2, ensure_ascii=False)
        f.write("\n")

    return {
        "gds": str(gds_path.resolve()) if write_gds else None,
        "metrics_json": str(json_path.resolve()),
        "metrics": payload,
        "feol_gds": str(feol_gds.resolve()) if write_gds else None,
        "feol_metrics_json": str(feol_json.resolve()),
        "feol_metrics": feol_payload,
    }



def _wl_gds_stem(wl_length: float) -> str:
    if float(wl_length) == int(wl_length):
        tag = str(int(wl_length))
    else:
        tag = str(wl_length).replace(".", "p")
    return f"wl_d10_m2_{tag}um"


def run_wl_pattern(
    artifacts_dir: Path | None = None,
    write_gds: bool = True,
    wl_length: float = 30.0,
    tap_pitch: float = 0.5,
    m2_width: float = 0.020,
    with_shields: bool = False,
) -> dict:
    """Build SRAM long-WL D10/M2 baseline, write GDS + geometry metrics + analytical RC."""
    activate_pdk()
    artifacts = artifacts_dir or _default_artifacts_dir()
    artifacts.mkdir(parents=True, exist_ok=True)

    top = wl_longline_pattern(
        wl_length=wl_length,
        tap_pitch=tap_pitch,
        m2_width=m2_width,
        with_shields=with_shields,
    )
    metrics = extract_rc_metrics(top)
    payload = metrics_to_jsonable(metrics)
    electrical = extract_wl_rc(top, net="WL", metal="M2")
    electrical_payload = metrics_to_jsonable(electrical)
    l2 = analyze_wl_l2(electrical)
    l2_payload = metrics_to_jsonable(l2)

    stem = _wl_gds_stem(wl_length)
    gds_path = artifacts / f"{stem}.gds"
    json_path = artifacts / f"{stem}_metrics.json"
    rc_json_path = artifacts / f"{stem}_rc.json"
    l2_json_path = artifacts / f"{stem}_l2.json"

    if write_gds:
        top.write_gds(gds_path)

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
        f.write("\n")
    with open(rc_json_path, "w", encoding="utf-8") as f:
        json.dump(electrical_payload, f, indent=2, ensure_ascii=False)
        f.write("\n")
    with open(l2_json_path, "w", encoding="utf-8") as f:
        json.dump(l2_payload, f, indent=2, ensure_ascii=False)
        f.write("\n")

    info = dict(getattr(top, "info", {}) or {})
    return {
        "gds": str(gds_path.resolve()) if write_gds else None,
        "metrics_json": str(json_path.resolve()),
        "rc_json": str(rc_json_path.resolve()),
        "l2_json": str(l2_json_path.resolve()),
        "metrics": payload,
        "electrical": electrical_payload,
        "l2": l2_payload,
        "n_bitcells": info.get("n_bitcells"),
        "wl_length_um": info.get("wl_length_um", wl_length),
        "tap_pitch_um": info.get("tap_pitch_um", tap_pitch),
        "m2_width_um": info.get("m2_width_um", m2_width),
        "m2_space_um": info.get("m2_space_um"),
        "first_tap_um": info.get("first_tap_um"),
        "last_tap_um": info.get("last_tap_um"),
        "driver_strength": info.get("driver_strength"),
        "net_name": info.get("net_name", "WL"),
        "wl_direction": info.get("wl_direction", "Y"),
        "with_shields": info.get("with_shields", with_shields),
        "baseline_for_hb": info.get("baseline_for_hb", True),
    }


def _print_wl_result(result: dict) -> None:
    # ASCII-only prints (Windows GBK: do not use mu)
    print(f"PDK:          {PDK_NAME} ({STACK_OPTION})")
    print(f"Version:      {__version__}")
    print(f"Pattern:      SRAM long-WL baseline (pre-Hybrid-Bonding)")
    print(
        f"Direction:    {result.get('wl_direction', 'Y')} "
        f"(WL along +Y, driver at y~=0, PG loads in +X)"
    )
    print(
        f"Driver:       {result.get('driver_strength')}  "
        f"net={result.get('net_name')}  "
        f"M2 width={result.get('m2_width_um')} um  "
        f"length={result.get('wl_length_um')} um"
    )
    print(
        f"Taps:         n_bitcells={result.get('n_bitcells')}  "
        f"pitch={result.get('tap_pitch_um')} um  "
        f"first_y={result.get('first_tap_um')} um  "
        f"last_y={result.get('last_tap_um')} um"
    )
    print(f"Shields:      {result.get('with_shields')}  baseline_for_hb={result.get('baseline_for_hb')}")
    print(f"Wrote metrics: {result['metrics_json']}")
    if result.get("rc_json"):
        print(f"Wrote RC JSON: {result['rc_json']}")
    if result.get("l2_json"):
        print(f"Wrote L2 JSON: {result['l2_json']}")
    if result.get("gds"):
        print(f"Wrote GDS:     {result['gds']}")
    layers = (result.get("metrics") or {}).get("layers_used", [])
    print(f"Layers used:   {', '.join(layers)}")
    elec = result.get("electrical")
    if elec:
        print(format_wl_rc_summary(elec))
    l2 = result.get("l2")
    if l2:
        print(format_l2_summary(l2))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="gf-layout-demo",
        description="Generate N5 FEOL+1P13M demo GDS + RC geometry metrics (gf_layout_flow)",
    )
    parser.add_argument(
        "-o",
        "--artifacts-dir",
        type=Path,
        default=None,
        help="Output directory (default: project artifacts/)",
    )
    parser.add_argument(
        "--no-gds",
        action="store_true",
        help="Skip writing GDS (metrics JSON only)",
    )
    parser.add_argument(
        "--wl-pattern",
        action="store_true",
        help="Write SRAM long-WL D10/M2 30 um baseline (artifacts/wl_d10_m2_30um.gds)",
    )
    parser.add_argument(
        "--hb-pattern",
        action="store_true",
        help="Write HB-folded WL (15 um x2) + compare vs 30 um baseline",
    )
    parser.add_argument(
        "--length",
        type=float,
        default=30.0,
        help="WL length in um (only with --wl-pattern; default 30)",
    )
    parser.add_argument(
        "--tap-pitch",
        type=float,
        default=0.5,
        help="Bitcell tap pitch in um (only with --wl-pattern; default 0.5)",
    )
    parser.add_argument(
        "--shields",
        action="store_true",
        help="Enable neighbor M2 shields (off by default; only with --wl-pattern)",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    args = parser.parse_args(argv)

    if args.hb_pattern:
        result = run_wl_hb_pattern(
            artifacts_dir=args.artifacts_dir,
            write_gds=not args.no_gds,
            with_shields=args.shields,
        )
        _print_hb_result(result)
        return 0

    if args.wl_pattern:
        result = run_wl_pattern(
            artifacts_dir=args.artifacts_dir,
            write_gds=not args.no_gds,
            wl_length=args.length,
            tap_pitch=args.tap_pitch,
            with_shields=args.shields,
        )
        _print_wl_result(result)
        return 0

    result = run_demo(artifacts_dir=args.artifacts_dir, write_gds=not args.no_gds)
    print(f"PDK:          {PDK_NAME} ({STACK_OPTION})")
    print(f"Version:      {__version__}")
    print(f"Wrote metrics: {result['metrics_json']}")
    if result["gds"]:
        print(f"Wrote GDS:     {result['gds']}")
    print(f"FEOL metrics:  {result['feol_metrics_json']}")
    if result["feol_gds"]:
        print(f"FEOL GDS:      {result['feol_gds']}")
    layers = result["metrics"].get("layers_used", [])
    print(f"Layers used:   {', '.join(layers)}")
    feol_layers = result["feol_metrics"].get("layers_used", [])
    print(f"FEOL layers:   {', '.join(feol_layers)}")
    hb = result["metrics"].get("hybrid_bonding", {})
    print(
        f"HB pads:       count={hb.get('pad_count')} "
        f"area={hb.get('pad_area_um2')} um^2 pitch={hb.get('pitch_um')} um"
    )
    print("NOTE: NW CAD (1;0) is placeholder_unverified - verify T-N05-CL-LE-001")
    return 0


def wl_pattern_main(argv: list[str] | None = None) -> int:
    """Entry point for gf-wl-pattern (ASCII prints only; use um not mu)."""
    parser = argparse.ArgumentParser(
        prog="gf-wl-pattern",
        description="Generate SRAM long-WL D10 + M2 baseline GDS + geometry metrics + analytical RC + L2 Elmore",
    )
    parser.add_argument(
        "-o",
        "--artifacts-dir",
        type=Path,
        default=None,
        help="Output directory (default: project artifacts/)",
    )
    parser.add_argument(
        "--no-gds",
        action="store_true",
        help="Skip writing GDS (metrics JSON only)",
    )
    parser.add_argument(
        "--length",
        type=float,
        default=30.0,
        help="WL length in um (default 30)",
    )
    parser.add_argument(
        "--tap-pitch",
        type=float,
        default=0.5,
        help="Bitcell tap pitch in um (default 0.5)",
    )
    parser.add_argument(
        "--m2-width",
        type=float,
        default=0.020,
        help="M2 WL width in um (default 0.020 = N5 M2 min_w)",
    )
    parser.add_argument(
        "--shields",
        action="store_true",
        help="Enable neighbor M2 dummy shields at min spacing (off by default)",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    args = parser.parse_args(argv)

    result = run_wl_pattern(
        artifacts_dir=args.artifacts_dir,
        write_gds=not args.no_gds,
        wl_length=args.length,
        tap_pitch=args.tap_pitch,
        m2_width=args.m2_width,
        with_shields=args.shields,
    )
    _print_wl_result(result)
    return 0



def run_wl_hb_pattern(
    artifacts_dir: Path | None = None,
    write_gds: bool = True,
    wl_length_per_die: float = 15.0,
    tap_pitch: float = 0.5,
    m2_width: float = 0.020,
    with_shields: bool = False,
    regenerate_baseline: bool = True,
) -> dict:
    """Build HB-folded WL pattern, write GDS/RC/L2 + vs-baseline compare artifacts."""
    activate_pdk()
    artifacts = artifacts_dir or _default_artifacts_dir()
    artifacts.mkdir(parents=True, exist_ok=True)
    docs_dir = artifacts.parent / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)

    baseline_result = None
    if regenerate_baseline:
        baseline_result = run_wl_pattern(
            artifacts_dir=artifacts,
            write_gds=write_gds,
            wl_length=30.0,
            tap_pitch=tap_pitch,
            m2_width=m2_width,
            with_shields=False,
        )

    top = wl_hb_fold_pattern(
        wl_length_per_die=wl_length_per_die,
        tap_pitch=tap_pitch,
        m2_width=m2_width,
        with_shields=with_shields,
    )
    metrics = extract_rc_metrics(top)
    payload = metrics_to_jsonable(metrics)
    hb_rc = extract_hb_fold_rc(top)
    hb_rc_payload = metrics_to_jsonable(hb_rc)
    l2 = analyze_hb_fold_l2(hb_rc)
    l2_payload = metrics_to_jsonable(l2)
    cmp = compare_hb_vs_baseline(hb_component=top)
    cmp_payload = metrics_to_jsonable(cmp)

    stem = "wl_d10_m2_hb_fold_15um"
    gds_path = artifacts / f"{stem}.gds"
    json_path = artifacts / f"{stem}_metrics.json"
    rc_json_path = artifacts / f"{stem}_rc.json"
    l2_json_path = artifacts / f"{stem}_l2.json"
    compare_json = artifacts / "wl_hb_vs_baseline_compare.json"
    compare_md = docs_dir / "wl_hb_vs_baseline.md"

    if write_gds:
        top.write_gds(gds_path)

    for path, data in (
        (json_path, payload),
        (rc_json_path, hb_rc_payload),
        (l2_json_path, l2_payload),
        (compare_json, cmp_payload),
    ):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")

    write_hb_compare_markdown(cmp, compare_md)

    info = dict(getattr(top, "info", {}) or {})
    return {
        "gds": str(gds_path.resolve()) if write_gds else None,
        "metrics_json": str(json_path.resolve()),
        "rc_json": str(rc_json_path.resolve()),
        "l2_json": str(l2_json_path.resolve()),
        "compare_json": str(compare_json.resolve()),
        "compare_md": str(compare_md.resolve()),
        "metrics": payload,
        "electrical": hb_rc_payload,
        "l2": l2_payload,
        "compare": cmp_payload,
        "baseline": baseline_result,
        "n_bitcells_lower": info.get("n_bitcells_lower"),
        "n_bitcells_upper": info.get("n_bitcells_upper"),
        "n_bitcells_total": info.get("n_bitcells_total"),
        "wl_length_lower_um": info.get("wl_length_lower_um"),
        "wl_length_upper_um": info.get("wl_length_upper_um"),
        "tap_pitch_um": info.get("tap_pitch_um", tap_pitch),
        "m2_width_um": info.get("m2_width_um", m2_width),
        "hb_count": info.get("hb_count"),
        "driver_strength": info.get("driver_strength"),
        "topology": info.get("topology"),
        "baseline_for_hb": info.get("baseline_for_hb", False),
        "compares_to": info.get("compares_to"),
        "stack_map_note": info.get("stack_map_note"),
        "with_shields": info.get("with_shields", with_shields),
    }


def _print_hb_result(result: dict) -> None:
    print(f"PDK:          {PDK_NAME} ({STACK_OPTION})")
    print(f"Version:      {__version__}")
    print(f"Pattern:      SRAM WL Hybrid-Bonding fold (D10)")
    print(
        f"Topology:     {result.get('topology')}  "
        f"compares_to={result.get('compares_to')}  "
        f"baseline_for_hb={result.get('baseline_for_hb')}"
    )
    print(
        f"Driver:       {result.get('driver_strength')}  "
        f"lower={result.get('wl_length_lower_um')} um / "
        f"{result.get('n_bitcells_lower')} taps; "
        f"upper={result.get('wl_length_upper_um')} um / "
        f"{result.get('n_bitcells_upper')} taps; "
        f"total_taps={result.get('n_bitcells_total')}  "
        f"hb_count={result.get('hb_count')}"
    )
    print(f"Shields:      {result.get('with_shields')}")
    print(f"Wrote metrics: {result['metrics_json']}")
    if result.get("rc_json"):
        print(f"Wrote RC JSON: {result['rc_json']}")
    if result.get("l2_json"):
        print(f"Wrote L2 JSON: {result['l2_json']}")
    if result.get("compare_json"):
        print(f"Wrote compare: {result['compare_json']}")
    if result.get("compare_md"):
        print(f"Wrote compare MD: {result['compare_md']}")
    if result.get("gds"):
        print(f"Wrote GDS:     {result['gds']}")
    if result.get("baseline") and result["baseline"].get("gds"):
        print(f"Baseline GDS:  {result['baseline']['gds']}")
    layers = (result.get("metrics") or {}).get("layers_used", [])
    print(f"Layers used:   {', '.join(layers)}")
    note = result.get("stack_map_note") or ""
    if note:
        print(f"Stack map:     {note[:120]}...")
    cmp = result.get("compare")
    if cmp:
        print(format_hb_compare_summary(cmp))


def wl_hb_pattern_main(argv: list[str] | None = None) -> int:
    """Entry point for gf-wl-hb-pattern."""
    parser = argparse.ArgumentParser(
        prog="gf-wl-hb-pattern",
        description=(
            "Generate HB-folded SRAM WL (15 um x2 + vertical M2..AP+HB) "
            "GDS + RC + L2 + vs-baseline compare"
        ),
    )
    parser.add_argument(
        "-o",
        "--artifacts-dir",
        type=Path,
        default=None,
        help="Output directory (default: project artifacts/)",
    )
    parser.add_argument("--no-gds", action="store_true", help="Skip writing GDS")
    parser.add_argument(
        "--length-per-die",
        type=float,
        default=15.0,
        help="WL length per die in um (default 15)",
    )
    parser.add_argument(
        "--tap-pitch",
        type=float,
        default=0.5,
        help="Bitcell tap pitch in um (default 0.5)",
    )
    parser.add_argument(
        "--m2-width",
        type=float,
        default=0.020,
        help="M2 WL width in um (default 0.020)",
    )
    parser.add_argument(
        "--shields",
        action="store_true",
        help="Enable neighbor M2 shields (off by default)",
    )
    parser.add_argument(
        "--no-baseline",
        action="store_true",
        help="Skip regenerating the 30 um baseline artifacts",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    args = parser.parse_args(argv)

    result = run_wl_hb_pattern(
        artifacts_dir=args.artifacts_dir,
        write_gds=not args.no_gds,
        wl_length_per_die=args.length_per_die,
        tap_pitch=args.tap_pitch,
        m2_width=args.m2_width,
        with_shields=args.shields,
        regenerate_baseline=not args.no_baseline,
    )
    _print_hb_result(result)
    return 0



if __name__ == "__main__":
    sys.exit(main())
