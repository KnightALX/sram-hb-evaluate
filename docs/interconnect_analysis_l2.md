# 互连分析模型 L0–L3（L2 = pi-ladder + Elmore）

本文档约定 **GDS / 版图侧** 如何做字线（WL）等互连延时与负载敏感度分析。  
**已批准主模型（L2）**：按 WL tap pitch 分段的 **pi-ladder + Elmore**。  
**不要**在未记录变更的情况下改动 L2 公式；Palace 等归入 **future L3**，本版本**不实现**。

ASCII 打印请用 `um` / `Ohm` / `fF` / `ps`（避免 µ 等非 ASCII 单位符号）。

---

## 层级总览

| 层级 | 名称 | 用途 | 本仓库状态 |
|------|------|------|------------|
| **L0** | 几何指标 | 层面积、线长/线宽估计、HB pad 计数 | `extract_rc_metrics` |
| **L1** | 解析 RC 查表 | Metal Ω/um·fF/um（**实测表**）；via 按类 / HB 集总；分段 ladder | `extract_wl_rc` + `n5_1p13m.yaml#interconnect_rc` |
| **L2** | **pi-ladder + Elmore** | **主延时估计**（GDS 全阵列扫描） | `analyze_wl_l2` / `elmore_ladder.py` |
| **L3** | EM 抽样校准 | Palace 等对局部段做场求解，校准 R'/C' | **future only — stub，未实现** |

**推荐用法**：版图 / GDS 分析默认跑 L1→L2；用 L2 的 `t_elmore_end`、per-tap 延时、`tau_wire_only` vs `tau_with_loads` 做比较与敏感度。L3 仅在有标定需求时对**抽样**段运行，再回写 LUT——**不要**用未校准的全 3D EM 替代 L2 全阵列扫描。

---

## 分析语境（本仓库基线）

- 方向：WL 沿 **Y** 的单根 **M2** 干线  
- 驱动： **D10** 反相器（占位 `R_drv`，非 SPICE 标定）  
- 负载： **60** 个 dual-PG tap（`n_bitcells=60`，`tap_pitch=0.5 um`，`wl_length=30 um`）  
- 网络名：`WL`；`baseline_for_hb=true`（Hybrid-Bonding 前基线）  
- L1/L2 共用同一套 Metal / via 表与 `extract_wl_rc` ladder，保证一致

---

## L2 约定（已批准，勿擅自更改）

对每个分段 `i = 1..N`（`N = n_bitcells`，`seg_length = tap_pitch`，默认 **0.5 um**）：

1. **导线**  
   - `R_seg = R' * seg_length`  
   - `C_seg = C' * seg_length`  
   - `R'` / `C'` 来自 M2 表 / `extract_wl_rc`（与 L1 一致）

2. **pi 模型**  
   - 在 `R_seg` 两侧各放 `C_seg/2`  
   - 节点 0 = 驱动输出端；节点 `k` = 第 k 个 tap

3. **Tap 集总电容**（每个分段之后的 tap 节点）  
   - `C_tap = C_via_at_tap + n_pg * C_pg`  
   - 默认每 tap **VIA0+VIA1**（类 V1-V2）→ `C_via = 2 * 0.1 fF = 0.2 fF`（或直接用 L1 ladder 的 `via_lump_at_tap.c_ff`）  
   - `C_pg`：yaml `analysis_l2.C_pg_ff_per_finger` 默认 **0.3 fF × nfinger_pg**，`source: user_rule_0p3fF_per_finger`
   - 默认 PG `nfinger_pg=1` → **0.3 fF / PG**；dual-PG：`n_pg=2` → **0.6 fF** PG 负载 / tap

4. **驱动**  
   - 串联 `R_drv` 后驱动 node0  
   - yaml `analysis_l2.R_drv_ohm` 默认 **200 Ohm**，`placeholder_unverified`（D10 未 SPICE 标定）  
   - 可选 `C_drv_par`（默认 0）并入 node0

5. **Elmore 延时**（到节点 k 及末端）  
   - `t_elmore(k) = sum_j R_upstream(j) * C_j`  
   - `R_upstream(0) = R_drv`；`R_upstream(j) = R_drv + sum_{i=1..j} R_seg_i`  
   - 单位：`Ohm * fF * 1e-3 = ps`  
   - 报告：`t_elmore_end`、`per_tap_delays` 数组、`tau_wire_only`（无 `C_pg`）vs `tau_with_loads`  
   - 可选能量代理：`0.5 * C_total * Vdd^2`（`Vdd` 默认 **0.75 V**，N5 core 占位；C 用 fF 时能量为 fJ）

### 节点电容示意（等分段）

- `C_0 = C_drv_par + C_seg/2`  
- 中间 `C_k (1..N-1) = C_seg + C_tap`  
- `C_N = C_seg/2 + C_tap`

---

## 配置（yaml）

文件：`src/gf_layout_flow/tech/n5_1p13m.yaml` → 节 `analysis_l2:`

| 键 | 默认 | source | 说明 |
|----|------|--------|------|
| `R_drv_ohm` | 200 | placeholder_unverified | D10 Rout 占位 |
| `C_pg_ff_per_finger` | 0.3 | user_rule_0p3fF_per_finger | `C_pg = 0.3 fF × nfinger_pg` |
| `C_pg_ff` | 0.3 | user_rule_0p3fF_per_finger | 默认 1-finger PG 的每器件 C；dual-PG tap = 0.6 fF |
| `n_pg_default` | 2 | — | dual-PG |
| `C_drv_par_ff` | 0 | — | 驱动端寄生 |
| `Vdd_V` | 0.75 | placeholder_unverified | 能量代理用 |
| `seg_length_default_um` | 0.5 | — | 与 tap pitch 对齐 |

**用户需校准的占位**：`R_drv`（反相器 SPICE）、`Vdd`（实际核电压）。`C_pg` 已采用用户规则 **0.3 fF × finger**，不再是 placeholder。

---

## API / CLI

```python
from gf_layout_flow.rc import extract_wl_rc, analyze_wl_l2

wl_rc = extract_wl_rc(component)          # L1
l2 = analyze_wl_l2(wl_rc)                 # 或 analyze_wl_l2(component)
# l2["elmore"]["t_elmore_end_ps"]
# l2["elmore"]["per_tap_delays_ps"]
# l2["elmore"]["tau_wire_only_ps"] / tau_with_loads_ps
```

模块：`src/gf_layout_flow/rc/elmore_ladder.py`

- `build_pi_ladder_from_wl_rc(wl_rc_dict)`  
- `elmore_delays(ladder, R_drv)`  
- `analyze_wl_l2(component | wl_rc) -> dict`

CLI：`gf-wl-pattern` 额外写出  
`artifacts/wl_d10_m2_30um_l2.json`  
并打印：

```text
L2 Elmore: t_end=... ps  R_drv=...  C_pg=... (R_drv/Vdd placeholders)
```

---

## Future L3（占位说明，不实现）

> Palace（或同类 EM）仅用于对**抽样**分段做场求解，以校准 `R'`/`C'` 与 via 集总；  
> **在校准完成前，不要用 L3 替换 L2 全阵列扫描。**  
> 本版本 **不实现 Palace**、不引入 CloudAgent 场求解流水线。

---

## GDS 分析应如何使用本模型

1. 用 `wl_longline_pattern` / 实际 GDS 组件得到几何与 info（length、tap pitch、n_bitcells、n_pg）。  
2. 跑 `extract_wl_rc`（L1）得到与查表一致的 Metal/via 与 ladder。  
3. 跑 `analyze_wl_l2`（L2）得到 Elmore 末端延时、每 tap 延时、有/无 PG 负载对比、能量代理。  
4. 将 `*_l2.json` 与 `*_rc.json` 一并归档；对比 HB 前后可改 `n_hb` / 拓扑后再跑同一 L2。  
5. 标定：用 SPICE / 实测换 `R_drv`、`Vdd`；`C_pg` 按用户规则 **0.3 fF × finger** 使用。可选 L3 抽样后更新 `interconnect_rc` 表，再重跑 L1/L2。

---

## 版本

- L2 引入版本：**0.6.0**；用户 C_pg finger 规则更新于 **0.6.1**  
- **0.6.2**：L1 互连 RC 表刷新为用户**实测**表（`user_measured_lookup`）；via 按类（V1-V2…）查表，默认薄 via 30 Ω / 0.1 fF；HB 0.165 Ω / 1.0 fF；无 M13 实测行（M12/M13→M11）。L2 仍用同一 L1 ladder。  
- 配置与实现路径见上文；测试见 `tests/test_elmore_l2.py`


## Changelog note (0.7.0)

- **HB fold topology**: `wl_hb_fold_pattern` + `extract_hb_fold_rc` / `analyze_hb_fold_l2`.
- Stack mapping: user M14 → AP/HB landing; RV mapped to V10-V11 class (research).
- Upper path Elmore: series `R_stack` (2 climbs + HB) with `C_stack/2` on each side, then 15 um ladder.
- Compare report: `artifacts/wl_hb_vs_baseline_compare.json`, `docs/wl_hb_vs_baseline.md`.
