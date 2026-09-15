# gf-layout-flow

面向半导体工艺版图 / **FEOL·MEOL·BEOL**·RC 研究的 **gdsfactory 版图工作流**（v0.6.0）：参数化单元（晶体管 finger / 多鳍多指 FinFET、SRAM 长 WL 基线、SRAM 风格互连条带、Hybrid Bonding 焊盘阵列）+ **TSMC N5 / N05 1P13M** 层栈配置（由用户提供的 DRM 摘录推导）+ RC 相关几何指标提取，并输出 GDS 与 JSON。

> **重要声明**：本仓库 `tech/` 中的层号、W/S、过孔尺寸等配置**仅来自用户提供的 N5 DRM 摘录**（T-N05-CL-DR-014），用于本地研究；**不是**官方 TSMC PDK，不可用于流片。厚度若不在所附 W/S 表中，一律标记为 **research_approx**。部分 FEOL 层（NW/DNW/OD2/CM0*）的 CAD 号在所附 DRM 中未给出，当前使用 **placeholder_unverified** 占位号，**必须对照 T-N05-CL-LE-001 核对**。请勿将 DRM 原文、表格或 PDF 放入本仓库或对外分发。

## N5 PDK 配置说明（FEOL + 1P13M）

| 项 | 值 |
|----|-----|
| PDK 名 | `n5_1p13m_beol` |
| Metallization option | `1P13M_M1+1x1xb1xe1ya1yb3y2yy2z` |
| FEOL（已确认） | OD / COD_* / PO / CPO / PP / NP / NT_N |
| MEOL（已确认） | MD / CMD / VG / VD / VDR / CB / CBD / CB2 / PM |
| 金属 | M0 + M1…M13 + AP（Al RDL） |
| 过孔 | VIA0…VIA12 + RV（M13–AP，CAD 85;0） |
| 研究叠加层 | `HB_PAD` (900;0)、`HB_VIA` (901;0) — **不在** N5 DRM 中 |
| **占位层（待核）** | NW / DNW / OD2 / CM0 / CM0A / CM0B — `placeholder_unverified` |
| 配置文件 | `src/gf_layout_flow/tech/n5_1p13m.yaml` |
| DBU | 推荐 **0.5 nm**（`dbu=0.0005` µm） |

### FEOL / MEOL 覆盖情况

| 状态 | 层 | 说明 |
|------|-----|------|
| ✅ 已入 LayerMap | OD, COD_H/V, COD_BLOCK, PO, CPO, PP, NP, NT_N | CAD 来自 DRM（T-N05-CL-DR-014） |
| ✅ 已入 LayerMap | MD, CMD, VG, VD, VDR, CB, CBD, CB2, PM | CAD 来自 DRM |
| ⚠️ **占位** | **NW, DNW, OD2, CM0, CM0A, CM0B** | CAD **未**在所附 DRM 写明；已注册占位号，**请用 LE-001 核对** |
| ✅ 已有 BEOL | M0–M13, VIA0–12, RV, AP, HB_*, LABEL, FLOORPLAN | 保持不变 |

### ⚠️ 占位 CAD 号一览（请用户核对 T-N05-CL-LE-001）

| Name | 占位 CAD;DT | source | verify_against |
|------|-------------|--------|----------------|
| **NW** | **1;0** | placeholder_unverified | T-N05-CL-LE-001 |
| **DNW** | **3;0** | placeholder_unverified | T-N05-CL-LE-001 |
| **OD2** (OD_12) | **8;0** | placeholder_unverified | T-N05-CL-LE-001 |
| **CM0** | **29;0** | placeholder_unverified | T-N05-CL-LE-001 |
| **CM0A** | **29;151** | placeholder_unverified | T-N05-CL-LE-001 |
| **CM0B** | **29;152** | placeholder_unverified | T-N05-CL-LE-001 |

占位号刻意避开已确认 CAD 段（5–6、11、17、25–26、30–47、50–66、74、76、82、85–86、169、177–179、900–901、990–991）。**拿到 LE-001 后请替换上述数字并更新 yaml/`layers.py`。**

### FEOL/MEOL 已确认层摘要

| Level | CAD | DT | min_w / min_s 或 size (µm) | 来源 |
|-------|-----|-----|---------------------------|------|
| OD | 6 | 0 | 0.034 / 0.078 | drm_ws |
| PO | 17 | 0 | 0.006 / 0.045 | drm_ws |
| PP / NP | 25 / 26 | 0 | — | drm_cad |
| NT_N | 11 | 0 | — | drm_cad |
| MD | 82 | 150 | 0.020 / 0.031 | drm_ws |
| VG | 178 | 150 | 0.012 / 0.039 | drm_ws |
| VD | 179 | 150 | 0.014 / 0.037 | drm_ws |
| VDR | 177 | 150 | — | drm_cad |

### BEOL 层映射摘要（CAD # / datatype）

| Level | Type | min_w / min_s (µm) | CAD | DT | 来源 |
|-------|------|-------------------|-----|-----|------|
| M0 | M0 | 0.014 / 0.014 | 30 | 151 | drm_ws |
| M1 | M1 (1.2X) | 0.020 / 0.014 | 31 | 171 | drm_ws |
| M2 | Mx (1.25X) | 0.020 / 0.015 | 32 | 151 | drm_ws |
| M3 | Mxb (1.5X) | 0.020 / 0.022 | 33 | 251 | drm_ws |
| M4 | Mxe (1.5X) | 0.020 / 0.022 | 34 | 401 | drm_ws |
| M5 | Mya (2.7X) | 0.038 / 0.038 | 35 | 950 | drm_ws |
| M6 | Myb (2.7X) | 0.038 / 0.038 | 36 | 800 | drm_ws |
| M7–M9 | My (2.7X) | 0.038 / 0.038 | 37–39 | 970 | drm_ws |
| M10–M11 | Myy (4.5X) | 0.062 / 0.064 | 40–41 | 90 | drm_ws |
| M12–M13 | Mz (26X) | 0.360 / 0.360 | 42–43 | 40 | drm_ws |
| AP | Al RDL | 1.8 / 1.8 | 74 | 0 | drm_ws |
| VIA0…VIA12 | — | 见 yaml | 50–62 | = upper metal DT | drm_ws |
| RV | Al via | 2.7 | 85 | 0 | drm_ws |
| HB_PAD / HB_VIA | research | — | 900 / 901 | 0 | research overlay |

### 厚度（LayerStack）

所附 DRM W/S 表**不含**精确 Cu / FEOL 厚度。`stack.py` / yaml 中厚度为 **research_approx**（FEOL 亦然）。NW/DNW/OD2 的 `info.source` 为 `placeholder_unverified`。

层栈顺序（自下而上）：**NW/DNW → OD/OD2 → PO → MD → VG/VD → M0 … M13 → RV → AP → HB**。

## 功能概览

1. **参数化 Cell**：FEOL 晶体管 finger / 多鳍多指 FinFET、SRAM 长 WL RC 基线、金属线/总线/过孔、Bitline/Wordline 条带、HB 焊盘阵列  
2. **层栈**：FEOL/MEOL + M0–M13、VIA0–VIA12、RV、AP、HB_*（单位 um）  
3. **RC 几何指标**：使用的层、每层面积/估算线长与线宽、HB 界面面积与 pitch  
4. **解析互连 RC（L1）**：用户查表（Metal Ω/µm·fF/µm；via/HB 集总）+ 未列表金属邻层折算；`extract_wl_rc`  
5. **L2 Elmore（主延时）**：pi-ladder 按 tap pitch 分段 + Elmore；见 `docs/interconnect_analysis_l2.md`；`analyze_wl_l2`  
6. **产物**：`artifacts/demo_top.gds` + `demo_feol.gds` + `wl_d10_m2_30um.gds` + `*_metrics.json` + `*_rc.json` + `*_l2.json`

## 环境要求

- Python **3.10+**（已在 3.13 验证）
- 依赖：`gdsfactory>=9.40,<10`

## 安装

```bash
cd gdsfactory-layout-workflow   # 或 D:\workspace\project\BEOL
python3 -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate
pip install -U pip setuptools wheel
pip install -e ".[dev]"
```

## 快速演示

```bash
gf-layout-demo
# 或
python -m gf_layout_flow.cli
```

默认生成：
- `artifacts/demo_top.gds` + `demo_top_metrics.json`（FEOL finger + BEOL + HB）
- `artifacts/demo_feol.gds` + `demo_feol_metrics.json`（NMOS/PMOS finger 草图）

SRAM 长 WL 基线（D10 + M2 30 um，Hybrid Bonding 实验前）：

```bash
gf-wl-pattern / gf-wl-hb-pattern
# 或
gf-layout-demo --wl-pattern
```

生成 `artifacts/wl_d10_m2_30um.gds` + `wl_d10_m2_30um_metrics.json` + `wl_d10_m2_30um_rc.json`。

## 运行测试

```bash
pytest -q
```

## 包结构

```
src/gf_layout_flow/
  tech/     # LayerMap、LayerStack、cross-sections、n5_1p13m.yaml、PDK、layers_pending
  cells/    # feol / metal / SRAM stripes / SRAM long-WL / HB pads
  rc/       # 几何指标 + 解析互连 RC（electrical.py）→ dict / JSON
  cli.py    # 演示入口
```

## 内置 Cells

| Cell | 模块 | 说明 |
|------|------|------|
| `od_rect` / `poly_gate` / `md_strip` | `cells.feol` | OD / PO / MD 基本图形 |
| `contact_vg` / `contact_vd` | `cells.feol` | VG / VD 接触 |
| `nmos_finger` / `pmos_finger` | `cells.feol` | 晶体管 finger 草图（PMOS 默认含 **NW 占位**） |
| `finfet_device` / `inverter` / `inverter_d10` | `cells.sram_wl_pattern` | 多鳍多指 FinFET；D10 反相器（3 nfin x 10 finger） |
| `bitcell_pg_load` / `wl_longline_pattern` | `cells.sram_wl_pattern` | 双 PG 负载 + 30 um **Y 向** M2 长 WL 基线（60 taps） |
| `metal_wire` / `metal_bus` | `cells.metal` | 金属线 / 总线 |
| `via_array` / `stacked_via` | `cells.metal` | 过孔阵列 / 邻层堆叠 |
| `bitline_stripes` / `wordline_stripes` / `sram_interconnect_block` | `cells.sram_stripes` | SRAM 风格互连 |
| `hb_pad` / `hb_pad_array` | `cells.hb_pads` | Hybrid Bonding（研究层） |

## API 速查

```python
from gf_layout_flow.cells import nmos_finger, pmos_finger, sram_interconnect_block
from gf_layout_flow.cells import inverter_d10, wl_longline_pattern
from gf_layout_flow.rc import extract_rc_metrics, extract_wl_rc

nmos = nmos_finger()
pmos = pmos_finger()  # includes NW placeholder (1;0)
metrics = extract_rc_metrics(pmos)
pmos.write_gds("artifacts/pmos.gds")

wl = wl_longline_pattern()  # D10 + M2 30 um Y-direction + 60 PG taps
rc = extract_wl_rc(wl)      # analytical R/C from user lookup table
```


## SRAM 长 WL RC 基线（v0.6.0，Hybrid Bonding 实验前）

本基线用于 **SRAM 长 wordline 互连 RC** 研究，是接入 Hybrid Bonding 对照实验**之前**的参考版图。全部参数化，便于后续改 driver 强度、线宽、tap 间距或叠 HB。

**v0.4.1**：WL 按 SRAM 惯例改为 **Y 方向**（竖线）；driver 在 y~=0，taps 沿 +Y，PG 负载向 +X 侧挂。

**v0.6.0**：接入用户提供的互连 RC 查表 + `extract_wl_rc` 解析提取（输出 `*_rc.json`）。

### 规格

| 项 | 值 |
|----|-----|
| Driver | inverter **D10** = NMOS + PMOS 各 **3 nfin x 10 finger** |
| 输出网络名 | **WL** |
| 线层 | Metal2（M2 / Mx） |
| 方向 | **Y**（竖 WL；SRAM 惯例） |
| 线长 | **30 um** |
| 线宽 | **0.020 um**（N5 yaml M2 min_w） |
| 邻线间距 | **0.015 um**（N5 yaml M2 min_s）；默认两侧 M2 shield/dummy |
| Tap 间距 | **0.5 um** 接一个 bitcell |
| Bitcell 负载 | 两个 PG 管，各 **2 nfin x 1 finger**；栅极都接到 WL tap |
| Tap 数量 | `n_bitcells = int(wl_length / tap_pitch) = 30/0.5 = **60**` |
| `baseline_for_hb` | `True` |

### Tap 位置选择（请后续 HB 实验保持一致或显式改参数）

Driver 放在 **y ~= 0**；WL 沿 **+Y** 铺到 30 um（`info["wl_direction"] = "Y"`）。

**第一拍在 y=0.5 um，最后一拍在 y=30.0 um**（60 taps：0.5, 1.0, …, 30.0）。

不在 y=0 放 bitcell，避免 driver 输出在原点被第一颗 cell 直接短路。Bitcell PG 负载从 WL **向 +X 侧挂**（不是沿 Y 继续延伸）。`wl_longline_pattern` 的 `info["tap_placement"]` = `first_at_pitch_last_at_length`，`info["tap_placement_note"]` 有同样说明。

### 几何约定（研究级，非 DRC-clean；用 N5 DRM 最小值）

- Fin / OD：fin 宽 0.034 um，fin pitch 0.112 um（OD W/S 0.034/0.078）
- `nfin` OD 高度 ≈ `(nfin - 1) * 0.112 + 0.034`
- PO Lg min = 0.006 um；多 finger 间距 **CPP ≈ 0.057 um**（PO_P57 class）
- 过孔栈（反相器输出与 PG 栅到 M2 WL）：**VG/VD → M0 → VIA0 → M1 → VIA1 → M2**
- PG 的源/漏保持本地 MD stub（负载电容几何），不做完整 6T bitcell
- 可选 M2 shield/dummy（`with_shields=True` 默认开启），与 WL 平行（同 Y 长），在 X 方向两侧各一条，间距 0.015 um，便于后续邻线 RC

连通意图（版图级示意，非 LVS）：

1. 反相器输出节点 → via stack → M2 WL 干线
2. 每个 tap：M2 stub / via 下到 PG 栅极 poly（VG 路径）；两个 PG 栅同接 WL
3. 邻 M2 shield 与 WL 同宽、同长，电学上不短接到 WL

### API / CLI

```python
from gf_layout_flow.cells import (
    finfet_device, inverter, inverter_d10,
    bitcell_pg_load, wl_longline_pattern,
)

dev = finfet_device(nfin=3, nfinger=10, is_nmos=True)
inv = inverter_d10()                 # == inverter(nfin=3, nfinger=10)
pg  = bitcell_pg_load()              # two PG, 2 nfin x 1 finger
top = wl_longline_pattern()          # 30 um, 60 taps, D10, shields on
# 小规模：wl_longline_pattern(wl_length=2.0, tap_pitch=0.5)  -> 4 taps
```

```bash
gf-wl-pattern
gf-layout-demo --wl-pattern
# 产物
#   artifacts/wl_d10_m2_30um.gds
#   artifacts/wl_d10_m2_30um_metrics.json
#   artifacts/wl_d10_m2_30um_rc.json
```

Windows 控制台请用 `um` 而不是微米符号（CLI 打印已避免非 ASCII 单位符号）。


## 互连 RC 查表（v0.7.0，用户实测）

配置键：`src/gf_layout_flow/tech/n5_1p13m.yaml` → `interconnect_rc:`（`metals_per_um` / `lumped` / `interpolation_notes`）。

**说明（中文）**：下表为用户**实测** Metal **每微米** R / Ctotal（另存 width/space/Cc/Cbottom/Ctop）与 Via 类 / HB **按实例**集总值；**不要自行编造表中数字**。分析默认电容用 **C**（非 C+cc）。表中未列的 Metal（含 M2、M0、M4…）在相邻已给层之间折算：

- **R**：对数平均 `R = sqrt(R_lo * R_hi)`（例：M2 ≈ `sqrt(60*18)` ≈ **32.863 Ohm/um**）
- **C**：算术平均 `C = (C_lo + C_hi)/2`（例：M2 = **0.215 fF/um**）
- **M0**：无更密邻层 → 映射为 M1（`source: extrapolated`）
- **M12 / M13**：实测表止于 M11 → 映射为 M11
- **AP**：无邻层可折算 → 留空 / skip
- 实测行：`source: user_measured_lookup`；折算项：`interpolated_from_user_measured` + `parents`

| Layer | w/s (um) | R (Ohm/um) | Ctotal (fF/um) | source |
|-------|----------|------------|----------------|--------|
| M1 | 0.021/0.021 | 60 | 0.22 | user_measured_lookup |
| M3 | 0.021/0.021 | 18 | 0.21 | user_measured_lookup |
| M5 | 0.04/0.04 | 7 | 0.16 | user_measured_lookup |
| M7 | 0.04/0.04 | 4.2 | 0.14 | user_measured_lookup |
| M9 | 0.04/0.04 | 2.3 | 0.106 | user_measured_lookup |
| M11 | 0.36/0.36 | 0.76 | 0.068 | user_measured_lookup |
| M2 等偶数层 | — | 邻层折算 | 邻层折算 | interpolated_from_user_measured |
| M12/M13 | — | =M11 | =M11 | extrapolated / mapped_to M11 |

Via 类（按个；默认电容用 C）：

| Class | Size | R (Ohm) | C (fF) | C+cc (fF) |
|-------|------|---------|--------|-----------|
| V1-V2 | 0.021^2 | 30 | 0.1 | 0.1 |
| V3-V4 | 0.021^2 | 30 | 0.1 | 0.1 |
| V5-V9 | 0.040^2 | 9 | 0.2 | 0.2 |
| V10-V11 | 0.324^2 | 0.3 | 0.4 | 0.5 |
| HB | 0.324^2 | 0.165 | 1.0 | 1.3 |

PDK 映射：VIA0→V1-V2（mapped）；VIA1–2→V1-V2；VIA3–4→V3-V4；VIA5–9→V5-V9；VIA10–11→V10-V11；VIA12→V10-V11（mapped）。

Python：`tech/rc_table.py` → `get_metal_rc` / `get_via_rc` / `get_via_rc_for_layer` / `get_hb_rc`；`rc/electrical.py` → `extract_wl_rc` / `extract_net_rc`。Metal 贡献为 **per_um × length**。Via 按层类累加 R/C；优先统计 VIA0/VIA1 polygon，否则启发式 `2 + 2*n_bitcells`。

## 仍需用户提供

请提供 **T-N05-CL-LE-001** 中 NW / DNW / OD2(OD_12) / CM0* 的正式 **CAD;datatype**，以便把占位号换成真实层号。

## License

MIT（示例代码；工艺层号/W/S 来自用户 DRM 摘录的派生配置；占位层与厚度为研究近似，非官方 PDK）


## HB-folded WL (v0.7.0)

Hybrid-Bonding fold splits the 60-tap / 30 um baseline into **15 um / 30 taps** on the lower die and **15 um / 30 taps** on the upper die, linked at the D10 driver by a vertical climb:

`M2 → … → M13 → RV → AP → HB` (user "M14" ≈ AP / HB landing; 1P13M has no M14 CAD).

```bash
gf-wl-hb-pattern
# artifacts/wl_d10_m2_hb_fold_15um.gds (+ *_metrics/rc/l2.json)
# artifacts/wl_hb_vs_baseline_compare.json
# docs/wl_hb_vs_baseline.md
```

See `docs/wl_hb_vs_baseline.md` for L1/L2 numbers vs the non-HB 30 um baseline.
