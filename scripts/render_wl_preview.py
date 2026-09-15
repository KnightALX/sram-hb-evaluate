#!/usr/bin/env python3
"""Render a zoomed bottom-end preview of the Y-direction SRAM long-WL GDS."""

from __future__ import annotations

import argparse
from pathlib import Path

import klayout.db as kdb
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MplPolygon
from matplotlib.collections import PatchCollection
from matplotlib.patches import Patch

LAYER_COLORS: dict[tuple[int, int], tuple[str, str, int]] = {
    # name, color, zorder (NW under FEOL; M2 on top)
    (1, 0): ("NW (1;0)", "#f4d6c1", 1),
    (25, 0): ("PP (25;0)", "#f4a261", 2),
    (26, 0): ("NP (26;0)", "#8d99ae", 2),
    (6, 0): ("OD (6;0)", "#2a9d8f", 3),
    (17, 0): ("PO (17;0)", "#e9c46a", 4),
    (82, 150): ("MD (82;150)", "#90be6d", 5),
    (178, 150): ("VG (178;150)", "#9b5de5", 6),
    (179, 150): ("VD (179;150)", "#00b4d8", 6),
    (30, 151): ("M0 (30;151)", "#457b9d", 7),
    (50, 150): ("VIA0 (50;150)", "#ff006e", 8),
    (31, 171): ("M1 (31;171)", "#1d3557", 9),
    (51, 150): ("VIA1 (51;150)", "#fb5607", 10),
    (32, 151): ("M2 (32;151)", "#e63946", 11),
}


def render_preview(
    gds_path: Path,
    out_png: Path,
    xlim: tuple[float, float] = (-0.55, 0.70),
    ylim: tuple[float, float] = (-0.80, 2.55),
) -> Path:
    ly = kdb.Layout()
    ly.read(str(gds_path))
    dbu = ly.dbu
    cell = ly.top_cell()
    flat = ly.create_cell("_wl_preview_flat")
    flat.copy_tree(cell)
    flat.flatten(-1)

    fig, ax = plt.subplots(figsize=(7.2, 12.4), dpi=140)
    legend_handles: list[Patch] = []
    for li in ly.layer_indexes():
        info = ly.get_info(li)
        key = (int(info.layer), int(info.datatype))
        if key not in LAYER_COLORS:
            continue
        name, color, z = LAYER_COLORS[key]
        patches: list[MplPolygon] = []
        for sh in flat.shapes(li).each():
            poly = sh.polygon
            if poly is None:
                if sh.is_box():
                    b = sh.box
                    pts = [
                        (b.left * dbu, b.bottom * dbu),
                        (b.right * dbu, b.bottom * dbu),
                        (b.right * dbu, b.top * dbu),
                        (b.left * dbu, b.top * dbu),
                    ]
                else:
                    continue
            else:
                pts = [(p.x * dbu, p.y * dbu) for p in poly.each_point_hull()]
            if len(pts) < 3:
                continue
            xs = [p[0] for p in pts]
            ys = [p[1] for p in pts]
            if max(xs) < xlim[0] or min(xs) > xlim[1] or max(ys) < ylim[0] or min(ys) > ylim[1]:
                continue
            patches.append(MplPolygon(pts, closed=True))
        if not patches:
            continue
        ax.add_collection(
            PatchCollection(
                patches,
                facecolor=color,
                edgecolor="#222222",
                linewidths=0.15,
                alpha=0.88,
                zorder=z,
            )
        )
        legend_handles.append(Patch(facecolor=color, edgecolor="#222222", label=name))

    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    ax.set_aspect("equal")
    ax.set_xlabel("x (um)")
    ax.set_ylabel("y (um)")
    ax.set_title(
        "SRAM long-WL baseline (D10 + M2 30 um, Y-direction) — bottom end: "
        "driver + first Y-taps (0.5 um pitch)"
    )
    ax.grid(True, alpha=0.28, zorder=0)
    if legend_handles:
        ax.legend(handles=legend_handles, loc="upper right", fontsize=7, framealpha=0.92, ncol=2)
    fig.tight_layout()
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=140)
    plt.close(fig)
    return out_png


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="render_wl_preview")
    parser.add_argument(
        "--gds",
        type=Path,
        default=None,
        help="Input GDS (default: artifacts/wl_d10_m2_30um.gds)",
    )
    parser.add_argument(
        "-o",
        "--out",
        type=Path,
        default=Path("/workspace/wl_pattern_preview.png"),
        help="Output PNG path",
    )
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[1]
    gds = args.gds or (root / "artifacts" / "wl_d10_m2_30um.gds")
    if not gds.exists():
        raise SystemExit(f"GDS not found: {gds}")
    out = render_preview(gds, args.out)
    print(f"Wrote preview: {out}")  # um, no mu
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
