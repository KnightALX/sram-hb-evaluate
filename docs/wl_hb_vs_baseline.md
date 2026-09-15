# HB-folded WL vs 30 um baseline

Version: **0.7.0**

## Stack mapping (M14)

User said M2~M14 for the HB climb. This PDK is 1P13M: M0..M13 + AP (no M14 CAD layer). Research mapping: M14 ≈ AP / HB landing. Vertical stack = M2→M3→…→M13→RV→AP→HB_PAD/HB_VIA, then mirrored reverse on the upper die back to M2. VIA2..VIA12 + RV counted once per climb; round-trip = two climbs + one HB.

## Vertical path (measured LUT)

| Item | n | R (Ohm) | C (fF) |
|------|---|---------|--------|
| One climb (VIA2..VIA12 + RV) | 12 vias | 136.2000 | 2.9000 |
| Round-trip (2 climbs) | 24 vias | 272.4000 | 5.8000 |
| HB | 1 | 0.1650 | 1.0000 |
| **Round-trip + HB** | | **272.5650** | **6.8000** |

Climb layers: `VIA2 VIA3 VIA4 VIA5 VIA6 VIA7 VIA8 VIA9 VIA10 VIA11 VIA12 RV`

Metal stubs on the vertical path: **neglected** (via-dominated).

## Path comparison

| Path | Length (um) | n_taps | R_total (Ohm) | C_total (fF) | t_elmore_end (ps) | ratio vs baseline |
|------|-------------|--------|---------------|--------------|-------------------|-------------------|
| Baseline (single M2) | 30.0 | 60 | 4645.9006 | 18.6500 | 38.1255 | 1.000 |
| HB lower | 15.0 | 30 | 2352.9503 | 9.4250 | 12.3525 | 0.3240 |
| HB upper (+ stack) | 15.0 | 30 | 2565.5153 | 16.0250 | 22.0598 | 0.5786 |

### Metal / via detail

| Path | R_metal | C_metal | R_via (local) | C_via (local) | R_stack | C_stack |
|------|---------|---------|---------------|---------------|---------|---------|
| Baseline | 985.9006 | 6.4500 | 3660.0000 | 12.2000 | — | — |
| HB lower | 492.9503 | 3.2250 | 1860.0000 | 6.2000 | — | — |
| HB upper | 492.9503 | 3.2250 | 1800.0000 | 6.0000 | 272.5650 | 6.8000 |

## Qualitative

- Critical end: **upper** (`t_end=22.0598` ps)
- Delta vs baseline: **-16.0657** ps
- HB fold wins: **True**
- Critical end is the upper die (t_end=22.0598 ps vs baseline 38.1255 ps). HB fold wins on end delay (critical < baseline). Assumptions: M14→AP, RV→V10-V11, metal stubs neglected, R_drv placeholder, C_stack split half/half across series R_stack.

### Assumptions

- M14 → AP / HB landing (1P13M has no M14 CAD)
- RV → V10-V11 class (research mapping)
- Vertical metal stub R/C neglected
- `R_drv=200 Ohm` placeholder_unverified
- Upper stack C: half at driver-side node, half at upper-WL start (`C_stack/2 at driver-side node0 and C_stack/2 at upper-WL start`)
- C_pg = 0.3 fF × finger; dual-PG → 0.6 fF/tap
