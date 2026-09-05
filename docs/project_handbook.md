# DK1 Short-Term Power Market Research

**项目手册 / Project Handbook**

**文档版本 / Document version:** 1.0 · 2026-09-03
**设计基线 / Design baseline:** MVP Blueprint — Freeze Candidate v1.1，随后由项目所有者明确冻结 / subsequently frozen by the project owner.
**仓库名称 / Repository:** `dk1-power-market-research`
**使用位置 / Intended location:** `docs/project_handbook.md`

> **先看进度，再看地图。/ Start with status, then use the map.**
> 每次开工先打开 [project_status.md](project_status.md)，只推进其中的当前步骤；忘记“为什么”时回到本手册，设计发生变化时查看 [decision_log.md](decision_log.md)。
> Open the status board at the start of every session. Work on its current step; use this handbook for context and the decision log for the reasons behind design choices.

这份手册把已冻结的 31 节 Blueprint 整理成可执行的参考文档，没有重新开放 MVP 范围。编号步骤、完成证据、交接模板和待核实登记是执行层补充，不代表新增的研究结论。文档生成不等于数据验证、测试完成或达到 Level A。

This handbook operationalizes the frozen 31-section Blueprint without reopening MVP scope. Step IDs, evidence requirements, handover templates and verification items are execution aids, not new research findings. Creating these documents does not establish data validity, complete a hypothesis test or achieve Level A.

## 导航 / Navigation

- [01 · 项目定位 / Mission and scope](#s01)
- [02 · 目标变量 / Target definition](#s02)
- [03 · 时间窗口与留出期 / Periods and holdout](#s03)
- [04 · 时点完整性 / Point-in-time integrity](#s04)
- [05 · H1 / H2 / H3](#s05)
- [06 · 数据层与首次核验 / Data and source validation](#s06)
- [07 · 特征与市场状态 / Features and regimes](#s07)
- [08 · 研究与评估 / Research and evaluation](#s08)
- [09 · 信号、置信度与决策 / Signal, confidence and decision](#s09)
- [10 · 风险、状态卡与日志 / Risk, state card and journal](#s10)
- [11 · Level A / B / C 完成标准 / Acceptance gates](#s11)
- [12 · 编号执行路线 / Numbered execution route](#s12)
- [13 · 仓库结构 / Repository structure](#s13)
- [14 · 十条原则 / Ten principles](#s14)
- [15 · 每次开工与收工 / Session protocol](#s15)
- [16 · 公开表述与面试 / Public positioning and interview](#s16)
- [17 · 尚待核实的实施细节 / Implementation items to verify](#s17)
- [18 · 来源对应表与术语 / Source crosswalk and glossary](#s18)

<a id="s01"></a>
## 01 · 项目定位 / Mission and scope

**使命 / Mission**

如何把 DK1 电力市场中在决策时点可获得的信息，转化为明确的市场假设、概率性的方向判断，以及考虑风险的决策？

How can point-in-time information from the DK1 power market be transformed into explicit market hypotheses, probabilistic directional views and risk-aware decisions?

**冻结的研究问题 / Frozen research question**

可再生能源预报修正和可观察的系统基本面，是否包含关于 DK1 短期平衡压力的信息？这种关系在什么条件下失效？

Do renewable forecast revisions and observable system fundamentals contain information about short-term balancing pressure in DK1, and under what conditions does that relationship break down?

**研究链 / Research chain**

信息 → 市场机制 → 假设 → 证据 → 方向判断 → 概率 / 置信度 → 决策 → 风险 / 失效条件 → 历史评估 → 复盘。

Information → Market mechanism → Hypothesis → Evidence → Directional view → Probability / Confidence → Decision → Risk / Invalidation → Historical evaluation → Post-mortem.

| 边界 / Boundary | 冻结内容 / Frozen specification |
|---|---|
| 地区 / Geography | DK1 — Western Denmark / 丹麦西部，一个 bidding zone / one bidding zone |
| 粒度 / Resolution | 单小时交割段 / One hourly delivery period |
| 公开名称 / Public name | **DK1 Short-Term Power Market Research** |
| 研究性质 / Nature | 独立、历史市场研究 / Independent historical market research |
| 当前重点 / Priority | 市场机制、真实预报修正、可解释判断与风险 / Mechanism, real forecast revisions, interpretable views and risk |
| 未来范围 / Future scope | R01 方法成熟后才考虑 DK2、德国、挪威、瑞典及 Nordic umbrella / Extend only after R01 methodology matures |
| 当前不开展 / Outside current scope | 实盘、可执行日内 P&L、订单簿重建、2025+ 的市场设计研究、复杂 ML 与 dashboard / Live trading, executable intraday P&L, order-book reconstruction, 2025+ market-design research, complex ML and dashboards |

“Nordic Power Trading Research Lab”仅是未来可能的长期容器名称；当前项目不以区域广度或模型复杂度作为成果。

“Nordic Power Trading Research Lab” is a possible future umbrella name. The current project earns its value through a defensible study of one zone, not geographic breadth or model complexity.

<a id="s02"></a>
## 02 · 目标变量 / Target definition

### 2.1 测什么、比什么、哪个小时？ / What is measured and compared?

对同一个 DK1 小时交割段 `t`：

For the same DK1 hourly delivery period `t`:

```text
Spread_t = P_Balancing,t - P_DayAhead,t
```

- `P_DayAhead,t`：该交割小时的 DK1 day-ahead spot price，作为参考价格。/ DK1 day-ahead spot price for that delivery hour; the reference price.
- `P_Balancing,t`：该交割小时的 DK1 balancing/regulating price，作为事后结果。/ DK1 balancing/regulating price for that delivery hour; the realized outcome.
- 两个价格必须使用相同币种和单位（EUR/MWh），同一小时、同一区域。/ Both prices must share currency and unit (EUR/MWh), delivery hour and zone.

**实施待核实：** 冻结版没有锁定具体 balancing API 字段。P1.3 必须明确历史数据中的目标字段及含义；若同时存在 up/down 或其他价格字段，不可自行平均、择优或按结果挑选。把字段映射与理由登记后才能构造目标。

**Implementation item:** The frozen Blueprint does not name the exact balancing API field. P1.3 must establish its historical meaning and mapping. If several price fields exist, do not average them or select one by results. Record the mapping and rationale before building targets.

### 2.2 三分类和边界 / Three classes and boundaries

```text
UP       if Spread_t >  delta
DOWN     if Spread_t < -delta
NEUTRAL  if abs(Spread_t) <= delta
```

| 标签 / Label | 含义 / Meaning |
|---|---|
| UP | Balancing price 显著高于日前参考价 / Balancing price materially above the day-ahead reference |
| DOWN | Balancing price 显著低于日前参考价 / Balancing price materially below the day-ahead reference |
| NEUTRAL | Spread 落入中性带，含正负边界和零 / Spread within the neutral band, including both boundaries and zero |

`NEUTRAL` 是事后目标类别；`No Trade` 是决策动作。低置信度、缺失信息或信号冲突也可以导致 No Trade，即使后来真实标签是 UP 或 DOWN。

`NEUTRAL` is an outcome label; `No Trade` is an action. Low confidence, missing information or conflicting signals can justify No Trade even when the eventual outcome is UP or DOWN.

### 2.3 中性带 δ / Neutral-band threshold

**冻结的主规格 / Frozen primary specification:**

```text
delta = Q25(abs(Spread_t) | abs(Spread_t) > 0, t in development period)
development period = 2022-01-01 through 2024-06-30
```

只用开发期内**非零绝对 spread** 的第 25 百分位数。不是带符号 spread 的分位数，不是相邻小时价格变化的分位数，也不包含 holdout。

Use the 25th percentile of **nonzero absolute spreads** in the development period. This is not a quantile of signed spreads or adjacent-hour price changes, and it excludes the holdout.

P3.2 计算后立即把数值、单位、样本日期、样本数、分位数算法和来源版本写入 `config/research_config.yaml` 并冻结。目前数值为 **TBD — 尚未计算**；空值或缺失价格不能当零，若没有有效非零样本则停止并记录问题。

At P3.2, immediately freeze the value, unit, sample dates, sample count, quantile method and source version in the research config. The value is currently **TBD — not computed**. Missing prices are not zeros; stop and record a blocker if no valid nonzero observations exist.

Q20 / Q30 仅可作为 Level C 的次要敏感性分析，必须单独标注；Q25 始终是主规格。不能因为 holdout 表现更好就替换主规格。

Q20 / Q30 may be secondary Level C sensitivity analyses, reported separately. Q25 remains the primary specification and cannot be replaced because an alternative performs better on holdout.

### 2.4 为什么不用相邻小时日前价变化？ / Why not adjacent-hour day-ahead changes?

市场逻辑是：日前价格确定 → 短期预报更新 → 系统预期变化 → 实际平衡结果。5h / 1h 修正是在日前出清之后形成的信息，因此不能回头预测已经确定的日前价格。`P_DA,t - P_DA,t-1` 可以做描述性研究，但不是 H2 的主目标。

The causal ordering is day-ahead clearing → short-term forecast updates → revised system expectations → realized balancing outcome. Information arriving after day-ahead clearing cannot be treated as a predictor of the already-cleared price. Adjacent-hour day-ahead changes may be descriptive analysis, but are not H2's primary outcome.

<a id="s03"></a>
## 03 · 时间窗口与留出期 / Periods and holdout

| 数据区间 / Period | 冻结日期 / Frozen dates | 用途 / Permitted use |
|---|---|---|
| Development | **2022-01-01 → 2024-06-30** | EDA、特征、δ、规则、模型开发和开发期内验证 / EDA, features, delta, rule and model development, internal validation |
| Locked holdout | **2024-07-01 → 2024-12-31** | 仅 Level C 解锁后的最终样本外评估 / Final out-of-sample evaluation after the Level C unlock gate |
| 2025+ | 当前不纳入 / Excluded from v1 | 后续研究新的 imbalance design / 15-minute MTU / Future research on later market design and resolution |

选取该历史窗口是为了保持 hourly resolution，并避开冻结版指出的后续市场设计变化。并不据此假定 2022–2024 内所有字段和规则天然完全一致；P1 仍需核实历史覆盖和语义。

This historical window preserves the intended hourly study and avoids the later market-design changes identified by the Blueprint. It does not establish that every field or rule was constant during 2022–2024; P1 must still verify historical coverage and semantics.

**Level A / B 的默认做法：不抓取 holdout。** 不做 holdout EDA、相关性、标签分布、表现评估；不据其修改特征、阈值或假设。日期约束应先写入配置，所有常规读取限定 development。

**Default for Levels A and B: do not fetch the holdout.** Do not inspect its distributions, correlations, labels or performance, or use it to revise features, thresholds or hypotheses. Record the dates first and restrict routine reads to development data.

**Level C 解锁前的检查 / Before unlocking at Level C:**

1. 完成 Level B；固定目标字段、δ、特征资格、规则、基准、模型及校准方案。/ Complete Level B and freeze the target field, delta, feature eligibility, rules, baselines, model and calibration plan.
2. 模型选择和校准只用开发期内按时间排序的训练 / 验证安排，并预先记录。/ Use and record time-ordered development-only training and validation for model selection and calibration.
3. 保存配置 / 代码版本，预先写明主指标、样本筛选、时间边界和 holdout 报告格式。/ Save config and code versions; specify primary metrics, row selection, time boundaries and the holdout report format in advance.
4. 在 decision log 登记解锁日期、冻结版本、测试计划和此前未使用 holdout 的证据，然后解锁。/ Log the unlock date, frozen versions, test plan and evidence of prior non-use, then unlock.
5. 报告主规格与两个基准；保留负面结果。之后依据 holdout 修改的研究必须标记为探索性，并使用未来新的未见数据验证。/ Report the primary specification and both baselines, retaining negative results. Changes informed by holdout are exploratory and require new unseen data for fresh confirmation.

这些是执行已冻结 holdout 协议的操作检查。初始三件套不会创建实际的数据锁、配置或模型；“LOCKED”表示研究协议状态，技术约束在 P0.2 / P2 落地。

These checks implement the frozen holdout protocol. This document package does not create a technical data lock, research config or model; “LOCKED” describes the protocol state until controls are implemented at P0.2 / P2.

日期边界按 UTC 还是丹麦本地交割日解释，原 Blueprint 未明确。P1 必须先确定并登记；内部 join 使用 UTC，保留本地时间用于解释，不能把夏令时重复小时合并成一行。

The Blueprint does not specify whether date boundaries refer to UTC dates or Danish local delivery dates. Resolve and log this before ingestion. Use UTC for internal joins and retain local time for interpretation; do not collapse repeated daylight-saving hours into one row.

<a id="s04"></a>
## 04 · 时点完整性 / Point-in-time integrity

> **No variable may enter a simulated decision unless it was reasonably available at the simulated decision time.**

任何变量只有在模拟决策时点已经合理可得，才允许用于该次决策。历史 API 今天能返回它，不代表历史上当时能看到它。

A value returned by today's historical API is not automatically a value that was available at the historical decision time.

| 分类 / Classification | 用途 / Use | 示例与条件 / Examples and conditions |
|---|---|---|
| `decision_eligible` | 可进入模拟决策 / May enter simulated decisions | ForecastDayAhead / Forecast5Hour / Forecast1Hour、已公布 schedule / capacity、lagged values；均须验证发布时间与版本 / All require timing and version verification |
| `diagnostic_only` | 解释事后机制 / Explain realized mechanisms | Final actual wind / solar / consumption，事前不可知的 realized physical flow / Realized flows unavailable before the decision |
| `outcome` | 目标与评估结果 / Targets and evaluation | Final balancing price、realized balancing spread / Realized balancing spread |

分类要落到字段及其实际使用方式。相同变量的历史滞后值若已发布，可以经核验后获得资格；未经核验的候选字段先隔离，不默认赋予 `decision_eligible`。

Classification applies to each field and its actual use. A lagged historical value may become eligible if its publication is verified. Quarantine unverified candidates; do not default them to decision eligible.

**每个候选字段至少记录 / Record at least:**

`source_dataset`, `source_field`, `definition`, `unit`, `zone`, `delivery_start_utc`, `publication_time` or documented availability rule, `retrieved_at`, revision/version semantics, classification, eligibility evidence, missing-data treatment.

此外每次决策必须记录 `decision_time_utc`。抓取时间、交割时间、预报生成时间、市场可获得时间是不同概念；不能仅凭 `TimestampUTC` 这个名字认定其含义。最终字段命名由 P1 形成的数据字典确定。

Each decision also needs `decision_time_utc`. Retrieval, delivery, forecast creation and market availability are distinct times. Do not infer a field's meaning from the name `TimestampUTC`; P1 establishes the actual data contract.

**H2 的资格条件：** 同一交割小时、同一地区和能源类型的 5h 与 1h 预报均须在所设决策时点可用。决策时点的具体偏移尚未冻结；先验证发布时间，再登记明确的 cutoff，不能把“1h”自动解释为恰好交割前一小时即可获得。

**H2 eligibility:** Both the 5h and 1h forecasts for the same delivery hour, zone and production type must be available by the chosen decision time. Its exact offset is not yet fixed. Verify publication timing and log an explicit cutoff; a “1h” label alone does not prove availability exactly one hour before delivery.

**滞后项和 persistence：** `y_t-1` 或上一小时 spread 可能尚未发布。冻结的 persistence 公式仍须报告，但若 `y_t-1` 在决策时点不可知，应标为事后参考基准，并另外报告按发布时间构造的可用滞后基准。任何补充基准需先登记，不能悄悄替换原公式或把事后基准称为可交易信号。

**Lags and persistence:** The preceding hour's label or spread may not yet be published. Retain the frozen persistence formula, but label it an ex-post reference when unavailable at the decision cutoff and also report an availability-correct lagged benchmark. Register additions before evaluation; do not silently replace the formula or claim the ex-post benchmark is tradable.

<a id="s05"></a>
## 05 · 三个研究假设 / H1, H2 and H3

### H1 · Residual Load / System Tightness

**定位 / Role:** Fundamental baseline hypothesis / 基本面基准假设。

更高 residual load 意味着更紧的物理系统，在部分条件下应与更强的上行压力相关。这是待检验的机制，不是已得出的结果。

Higher residual load implies a tighter physical system and should, under some conditions, be associated with upward pressure. This is a hypothesis to test, not an established project result.

```text
RL_actual,t = Demand_actual,t - Wind_actual,t - Solar_actual,t
RL_known,t  = point-in-time forecast / scheduled / lag-based residual-load estimate
```

- **H1-A — Ex-post mechanism research：** 用 actual residual load 解释真实发生的物理系统条件，输出机制图和结论；仅为 diagnostic。/ Use actual residual load to understand realized physical conditions, producing a mechanism chart and conclusion; diagnostic only.
- **H1-B — Decision-eligible version：** 只有确认可靠且在当时可得的负荷与可再生能源信息，才将 `RL_known` 纳入信号。/ Admit `RL_known` to the signal only after reliable contemporaneously available load and renewable inputs are established.

若没有可信的 consumption forecast，H1-A 仍可完成，H1-B 保持待核实或不可用。不得用 actual demand 填补缺口以赶 Level A。

If a reliable consumption forecast is unavailable, H1-A can still be completed while H1-B remains pending or unavailable. Do not substitute actual demand to accelerate Level A.

### H2 · Renewable Forecast Revision

**定位 / Role:** MVP 的核心 hypothesis / The core MVP hypothesis.

```text
WindRevision_5h_to_1h,t  = WindForecast_1h,t  - WindForecast_5h,t
SolarRevision_5h_to_1h,t = SolarForecast_1h,t - SolarForecast_5h,t
```

必须比较**同一交割小时**的不同 horizon；不能误用相邻行或相邻交割小时的差值。若需要汇总风电类型，应先确认类别定义和可加性，避免重复计算。

Compare different horizons for the **same delivery hour**. Do not difference adjacent rows or delivery hours. If wind categories need aggregation, first establish their definitions and additivity to avoid double counting.

**预期方向 / Expected mechanism:** 正向 wind revision → 预期供给更充裕 → 其他条件不变时 DOWN balancing pressure 的概率更高。Solar revision 采用相同“新信息改变供需预期”的机制进行检验。

A positive wind revision implies a looser expected system and, other things equal, a higher probability of DOWN balancing pressure. Test solar revision through the same mechanism of new information changing expected supply conditions.

研究必须回答：什么 regime 下成立？cross-border 条件会抵消吗？revision 多大才有信息？市场是否已经吸收？记录无效和相反方向的结果。

Ask when the relationship holds, whether cross-border conditions offset it, how large a revision must be to carry information, and whether the information may already be absorbed. Retain null and contrary results.

**Forecast vintage honesty rule / 预报版本诚实规则**

冻结版以 `Forecasts_Hour` 存在多个 horizon 为 H2 的数据依据；本次文档交付仅继承这一设计依据，尚未重新核验 live API 或 2022–2024 的历史可用性。

The frozen Blueprint bases H2 on multiple horizons in `Forecasts_Hour`. This documentation delivery carries forward that design basis; it has not independently revalidated the live API or historical availability in 2022–2024.

P1.1 检查同一交割小时是否有多条 publication timestamp 记录、`TimestampUTC` 的含义、`ForecastCurrent` / `ForecastIntraday` 的定义，以及每次更新是否留存。多 horizon 不等于完整 tick-by-tick vintage history。

At P1.1, check whether a delivery hour has multiple publication-timestamp rows, what `TimestampUTC` means, how `ForecastCurrent` / `ForecastIntraday` are defined and whether every update is retained. Multiple horizons do not establish complete tick-by-tick vintage history.

`ForecastIntraday - ForecastDayAhead` 仅在历史语义和可用时点核实后加入。未验证的 Current / Intraday 不进入信号。如果证据否定已冻结的数据假设，记录冲突并暂停受影响路径；不可伪造 vintage 或静默降低 H2 完成标准。

Add `ForecastIntraday - ForecastDayAhead` only after historical semantics and availability are verified. Keep unverified Current / Intraday values out of signals. If evidence contradicts the frozen data assumption, log the conflict and pause the affected path; do not fabricate vintages or silently lower H2's acceptance criteria.

### H3 · Cross-Border & System Conditions

**定位 / Role:** 条件性研究 / Conditioning hypothesis。

预报修正的影响可能受跨境输电及系统条件增强、削弱或抵消。它首先是检验 H2 是否有条件成立，不意味着凭相关性确定因果关系。

Cross-border and system conditions may amplify, weaken or offset a revision's relationship with pressure. H3 first tests whether H2 is conditional; correlation alone does not establish causality.

- **Eligible candidates：** 已公布 scheduled exchanges、announced countertrade、available capacity、当时可观察的 system information；需逐字段验证。/ Published exchanges, countertrade, capacity and observable system information, each requiring field-level verification.
- **Diagnostic only：** 决策时未知的 realized physical flow。/ Realized physical flow unavailable at decision time.

H3 输出条件分层的结果、样本数、解释与失效条件；若只能取得事后流量，就清楚标注 diagnostic conditioning，不能宣称它提高了可实施预测能力。

H3 produces conditional results, sample counts, interpretation and failure conditions. If only realized flows are available, label the work diagnostic conditioning and do not claim improved deployable prediction.

<a id="s06"></a>
## 06 · 数据层与首次核验 / Data and source validation

优先数据来源为 **Energinet Energi Data Service**。下面是冻结的逻辑数据层，具体 dataset ID、字段、发布时间和历史适用区间均由 P1 验证后写入 `data/data_dictionary.md`。

The primary source is **Energinet Energi Data Service**. These are the frozen logical layers; P1 must establish exact dataset IDs, fields, publication timing and historical coverage in `data/data_dictionary.md`.

| 数据层 / Layer | 预期内容 / Intended content | 主要用途 / Main use |
|---|---|---|
| Day-ahead reference | DK1 Elspot / day-ahead price | `Spread` 参考价 / Reference |
| Short-term outcome | DK1 balancing / regulating price | `outcome` |
| Renewable forecast | Day-ahead / 5h / 1h wind and solar | 经核验后 `decision_eligible` / Eligible after verification |
| Actual fundamentals | Wind / solar / demand | H1-A，`diagnostic_only` |
| Cross-border | Scheduled / known exchanges and realized flows | 按可用时点分开 eligible 与 diagnostic / Split by availability |
| System | Balancing / regulating variables | 逐字段分类；已发布历史滞后值可另核资格 / Classify each field and verify lag eligibility |

未来再考虑 weather、ENTSO-E、Nord Pool intraday 和 order / trade data；不为扩大数据量推迟 MVP 核心验证。

Weather, ENTSO-E, Nord Pool intraday and order/trade data are future extensions. They must not delay verification of the MVP's core data.

**P1.1 的唯一目标 / The sole objective of P1.1:** 建立 `Forecasts_Hour` 的有证据数据契约，判断 5h→1h H2 能否按时点完整性实施。/ Establish an evidenced `Forecasts_Hour` contract and determine whether 5h→1h H2 can be implemented point in time.

完成时应能回答 / Completion must answer:

1. Dataset ID、字段名称、单位、DK1 及 wind / solar 类别如何识别？/ Which dataset, fields, units and zone/production-type selectors apply?
2. Delivery time、发布时间、horizon、抓取时间分别是什么？/ Which fields represent delivery, publication, horizon and retrieval?
3. 2022–2024 development 区间的历史覆盖、缺失与重复版本怎样？/ What historical coverage, gaps and version multiplicity exist within development?
4. 5h 与 1h 是否属于同一小时且确实先后可得？/ Are the two horizons for the same hour and demonstrably available in sequence?
5. Current / Intraday 是否覆盖旧值或保存版本？/ Do Current / Intraday overwrite values or retain history?
6. 哪些字段可以进入 signal，哪些仍待核实？/ Which fields qualify for signals and which remain unverified?

证据包括官方说明的位置、检索日期、限定 development 的小样本、字段映射和未解决项。样本请求必须显式限制日期，不能使用默认“最新数据”来替代历史核验。

Evidence includes the location of official documentation, retrieval date, a development-restricted sample, field mappings and unresolved items. Sample requests must explicitly bound dates; a default latest-data response is not historical verification.

**管道最低检查 / Minimum pipeline checks:** 唯一键、小时对齐、单位和正负方向、UTC / DST、缺失、重复、连接行数、范围过滤、字段资格、原始数据来源和版本。先保存原始响应再转换；不要把缺失值自动解释成零或正常市场状态。

Check unique keys, aligned hours, units and signs, UTC/DST, missing values, duplicates, join cardinality, date filters, field eligibility and raw-data provenance/versioning. Preserve raw responses before transformation. Missing values are not automatically zeros or normal system states.

<a id="s07"></a>
## 07 · 特征与市场状态 / Features and regimes

每个特征先回答：**Why might a trader care?** 再解释发布时间、机制和适用条件。

For each feature, first answer **“Why might a trader care?”**, then document availability, mechanism and applicable conditions.

| 特征组 / Group | 候选项 / Candidates | 限制 / Constraint |
|---|---|---|
| Information revision | Wind / solar 5h→1h revision | 同一交割小时、两个 horizon 均可得 / Same hour; both horizons available |
| Fundamental state | Forecast renewable level / share, residual-load proxy | 分母与组成项也须符合 PIT / Denominators and components must also be PIT eligible |
| Lagged information | Previous balancing state / spread / price | 滞后不自动等于已发布 / Lagged does not automatically mean published |
| Time context | Hour-of-day, weekday, season | 保留本地时间语义与 DST / Preserve local-time and DST semantics |
| Cross-border context | Known exchange / capacity / system measures | 只用合格信息 / Eligible information only |

第一版 regime 保持简单：`Tight / Normal / Loose`，或 `High / Normal / Low renewable`。具体变量与分箱边界是待登记的实施项，只在 development 上确定。使用 actual 构造的 regime 只能支持 diagnostic 分层，不能回填成当时已知状态。

Keep first-version regimes simple: `Tight / Normal / Loose`, or `High / Normal / Low renewable`. Register the variables and bin boundaries using development data only. Regimes built from actual outcomes support diagnostic stratification, not reconstructed prior knowledge.

目的：检验信号是否依赖条件，并报告每组样本量与不确定性；不急着做复杂 clustering。

The purpose is to test conditional signal behavior with group sizes and uncertainty, without complex clustering.

<a id="s08"></a>
## 08 · 研究与评估 / Research and evaluation

### 8.1 统一研究流程 / Research protocol

Observation → Hypothesis → Mechanism → Eligible information → Test → Result → Trading implication → Failure condition.

每次测试前在 `research/hypotheses.md` 写明：假设 ID、预期方向、机制、数据资格、开发期样本、测试方式、分组规则和失败标准。完成后写样本数、图表、基准比较、局限及结论，不只保留“好看的结果”。

Before testing, record the hypothesis ID, expected direction, mechanism, information eligibility, development sample, test method, grouping and failure criterion. Afterwards record sample counts, charts, baseline comparisons, limitations and conclusions, retaining unfavorable results.

允许且必须区分三种结论 / Use three valid conclusion types:

- **Supported / 支持：** 本次指定测试支持关系，仍受数据与设计局限约束。/ The specified test supports the relationship within its limitations.
- **Conditionally supported / 条件性支持：** 仅在明确 regime 或条件下成立。/ Supported only under specified conditions or regimes.
- **Rejected / Null / 拒绝或无证据：** 未获得支持，或者未证明增量信息。/ No support or no demonstrated incremental information.

相关关系不自动等于因果效应；漂亮的机制图也不等于已证实的可决策信号。

Association does not establish causality, and a compelling mechanism chart does not establish a decision-eligible signal.

### 8.2 两个强制基准 / Two mandatory baselines

**Majority class:** 在训练样本上确定最多的类别，此后始终预测该类。最终 holdout 的 majority 只能来自 development，不能从 holdout 的类分布反推。若开发期做内部验证，每个验证段的 majority 只能来自其训练段。

Determine the most common class from training observations and always predict it. The final holdout majority comes from development, never holdout labels. For internal validation, estimate the majority from the corresponding training portion only.

**Persistence:**

```text
y_hat_t = y_(t-1)
```

上一小时的 market-pressure class 作为本小时预测。它延续的是本项目 spread 标签，不是相邻小时 DA 价格涨跌。无前一小时、时间断档或发布时间不合格的处理要事前固定并报告，参见 [时点规则](#s04)。

Predict the previous hour's market-pressure class. This means the project's spread label, not adjacent-hour day-ahead price direction. Predefine and report treatment of missing predecessors, time gaps and publication availability; see the point-in-time rules.

**只有稳定优于这些 naive baselines，才讨论 incremental information。** 如果未超过，结论写“本次规格未证明超越基准的 edge”；不能用单个高准确率代替比较。

Discuss incremental information only when results consistently outperform the naive baselines. If they do not, report that this specification has not demonstrated an edge beyond the benchmarks. A standalone accuracy number is insufficient.

### 8.3 最低报告表 / Minimum scorecard

| 指标 / Metric | 执行定义与报告要求 / Reporting requirement |
|---|---|
| Class distribution | UP / DOWN / NEUTRAL 数量和占比，注明区间 / Counts, shares and period |
| Directional accuracy | 明示标签、预测及分母；三分类正确率和 active-view 子集分别报告 / Define labels and denominator; distinguish full three-class accuracy from active-view accuracy |
| Balanced accuracy | 三个类别 recall 的平均值；缺类时明确标记 / Mean class recall, with missing-class handling stated |
| Macro F1 | 三类 F1 等权平均，注明无法计算项的规则 / Equal-weight class F1, with undefined-case handling stated |
| Confusion matrix | 固定标签顺序并说明行是真值还是预测 / Fix class order and identify true/predicted axes |
| Class-specific hit rate | 本项目报告为按预测类别计算的命中率，即 precision；同时给每类 recall / Report precision by predicted class, alongside each class's recall |
| Performance by regime | 各 regime 的样本数、类分布、指标及两个基准 / Group sizes, distributions, metrics and both baselines |
| Coverage / No Trade | 作为执行补充，报告 active views、No Trade、缺失或被排除样本数 / Operational supplement: report active views, No Trade and missing/excluded rows |

所有方法使用可比样本、同一目标和指标。若 No Trade 过滤了难例，同时给全样本结果和覆盖率，不能只报筛选后的 hit rate。非方向性机制测试可以报告机制证据，但不能由此声称胜过方向预测基准。

Compare methods on comparable rows with the same target and metrics. If No Trade filters difficult cases, report full-sample results and coverage alongside selected hit rate. Mechanism tests may report mechanism evidence, but cannot claim superiority to directional baselines without the corresponding evaluation.

概率模型后增加 calibration、Brier score、probability buckets；说明多分类 Brier 的计算 convention。校准只在 development 内拟合，holdout 用于评估而非拟合校准器。

After probability modelling, add calibration, Brier score and probability buckets, stating the multiclass Brier convention. Fit calibration within development; evaluate it on holdout without fitting on holdout outcomes.

开发期内的描述性统计必须标为 exploratory / in-sample。冻结版 δ 使用完整 development 估计；如果内部回测也沿用这一 δ，要注明该限制，不把它称为全流程严格未见样本测试。最终 locked holdout 使用固定 development δ，不受此问题影响。

Label development descriptive results exploratory / in-sample. The frozen delta uses all development data; internal backtests that reuse it must disclose this limitation rather than claim a fully unseen end-to-end test. The final locked holdout uses the fixed development delta and remains separate.

<a id="s09"></a>
## 09 · 信号、置信度与决策 / Signal, confidence and decision

**冻结的建模顺序 / Frozen modelling order:**

| Stage | 工作 / Work |
|---|---|
| 0 | Market mechanism / 先理解市场机制 |
| 1 | Descriptive / conditional statistics / 描述性与条件统计 |
| 2 | Transparent rule-based signal / 透明规则信号 |
| 3 | Logistic Regression / 逻辑回归基准 |
| 4+ | Tree models / boosting / probabilistic models / time series / ML，后续再评估 / Later extensions |

复杂度必须通过样本外超越简单基准来证明价值。MVP 先形成 `UP PRESSURE / DOWN PRESSURE / NO TRADE or NEUTRAL` 的透明规则输出，再进入 Logistic Regression。

Complexity must earn its place by beating a simpler baseline out of sample. Start with transparent `UP PRESSURE / DOWN PRESSURE / NO TRADE or NEUTRAL` outputs, then introduce Logistic Regression.

Level A / early Level B 的 confidence 用 `Low / Medium / High`，并说明判断依据。统计基准后才报告 `P(UP | I_t)`、`P(DOWN | I_t)`、`P(NEUTRAL | I_t)`，三者总和为 1，并评估校准。不要把主观 High 转换成未经验证的百分比。

Use `Low / Medium / High` confidence in Level A / early Level B, explaining the basis. After statistical modelling, report the three conditional probabilities, summing to one, and assess calibration. Do not convert a subjective High rating into an unvalidated percentage.

**Decision / 决策：** `Bullish / Bearish / No Trade`。这表示研究判断，不是实际成交指令。Signal ≠ Trade；信号冲突、edge 太小、关键信息缺失或 regime 未知时，No Trade 是正式选择。

Decisions are `Bullish / Bearish / No Trade`: research judgments, not execution instructions. Signal ≠ Trade. Conflicting signals, insufficient edge, missing key information or an unknown regime justify No Trade.

“强修正”、规则阈值、置信度映射和 No Trade 的实施条件要在 development 中定义并登记，冻结版没有提供具体数值；不得编造已经锁定的参数。

Define and log “strong revision”, rule thresholds, confidence mapping and No Trade conditions using development only. The Blueprint does not supply their numerical values; do not invent frozen parameters.

<a id="s10"></a>
## 10 · 风险、状态卡与日志 / Risk, state card and journal

每条观点必须包含 primary driver、counterargument、key risk、invalidation、no-trade condition。Invalidation 要具体回答：什么新信息出现后，这个观点应撤回？

Every view requires a primary driver, counterargument, key risk, invalidation and no-trade condition. Invalidation must identify the new information that would require withdrawing the view.

### Market State Card 模板 / Template

下列字段是待填写模板，不是已完成的市场观察。决策部分先记录；结果公布后才填写 Outcome / Post-Mortem，保留前后记录。

This is a blank template, not a completed observation. Record the decision first; add Outcome / Post-Mortem only after publication, preserving the earlier record.

```text
DK1 MARKET STATE
Card ID / 卡片编号:
Delivery Hour / 交割小时 (UTC + local):
Decision Time / 决策时点 (UTC):
Information Snapshot / 当时信息快照与来源版本:
Renewable Revision / 可再生能源预报修正:
System Condition / 系统状态:
Directional View / 方向判断: UP / DOWN / NEUTRAL
Confidence / 置信度: Low / Medium / High
Primary Driver / 主要依据:
Counterargument / 最强反方:
Key Risk / 关键风险:
Invalidation / 失效条件:
No-Trade Condition / 不参与条件:
Decision / 决策: Bullish / Bearish / No Trade
Outcome / 结果 (fill later):
Post-Mortem / 复盘 (fill later):
```

### Market Journal 模板 / Template

```text
Journal ID / 日志编号:
Related Card / 对应状态卡:
Observed Information / 观察到的信息:
Hypothesis / 假设:
Expected Direction / 预期方向:
Confidence / 置信度:
Market Mechanism / 市场机制:
Counterargument / 反方论证:
Risk / 风险:
Invalidation / 失效条件:
Actual Outcome / 实际结果:
What I Got Right / 判断正确之处:
What I Missed / 遗漏之处:
What Changes Next Time / 下次要改变什么:
Related Decision ID / 如涉及设计变更，关联决策编号:
```

失败假设与错误判断保留。复盘形成的新规则仍须经 development 测试和记录，不能根据 holdout 的单个案例重写主规格。

Retain failed hypotheses and incorrect views. New rules from post-mortems still need development testing and logging; do not rewrite the primary specification around a holdout example.

### No Fake P&L / 不虚构交易收益

**Balancing pressure is used as a short-term market-outcome proxy, not as executable intraday P&L.**

本项目用 balancing pressure 作为短期市场结果的代理变量。缺少完整可执行的历史日内成交、订单簿、成本和流动性数据时，不能把分类准确率或 spread 变化包装成交易收益。

Without reliable executable historical intraday transactions, order books, costs and liquidity, classification accuracy or spread movements cannot be presented as trading profits.

未来得到可靠交易数据后，可以沿用研究链，把 outcome layer 扩展到 intraday price change、spread、execution、transaction cost 和 liquidity；这不是当前 MVP 的已完成功能。

With reliable transaction data later, the research process can extend its outcome layer to intraday price changes, spreads, execution, costs and liquidity. These are not completed MVP capabilities.

<a id="s11"></a>
## 11 · Level A / B / C 完成标准 / Acceptance gates

本节是稳定的验收标准；实时完成状态只记在 [project_status.md](project_status.md)。每项 DONE 必须有文件 / 结果证据，不按投入时间或“已开始”判定。

These are stable acceptance criteria; live completion belongs in the status board. Each DONE item requires file or result evidence, not elapsed effort or work merely started.

### Level A — CV-safe

1. Repo 建立。/ Repository created.
2. Professional README 完成。/ Professional README completed.
3. Project Charter 完成。/ Project Charter completed.
4. Research config 中 target / development / holdout 已冻结。/ Target and periods frozen in research config.
5. 至少成功拉取 `Forecasts_Hour + Day-Ahead + balancing` 核心数据。/ Core forecast, day-ahead and balancing data successfully fetched.
6. Data dictionary 建立，标记 `decision_eligible / diagnostic_only / outcome`。/ Data dictionary with all three eligibility classes.
7. H2 forecast-revision variables 成功构造。/ H2 revision variables constructed.
8. **至少一个 hypothesis 完成一轮真实测试并写出结论，null 也算完成。** / **At least one hypothesis genuinely tested through one complete round with a written conclusion; null is valid.**
9. 至少一个 meaningful chart。/ At least one meaningful chart.
10. Holdout 完全未使用。/ Holdout completely unused.

仅生成本三件套或创建 repo，均未达到 Level A。原 Blueprint 的“明天投递”是当时计划，不是本手册对完成时间的承诺。

This package or an empty repository alone does not achieve Level A. The source Blueprint's next-day application intention is historical context, not a completion-time promise in this handbook.

### Level B — Interview Ready

在 Level A 基础上完成 / In addition to Level A:

- H2 完整第一轮 / Complete first round of H2.
- H1 mechanism research / H1-A 机制研究；H1-B 依赖合格输入 / H1-B remains conditional on eligible inputs.
- H3 preliminary conditioning / H3 初步条件性研究，明确 eligible 或 diagnostic / Explicitly label eligible versus diagnostic work.
- Transparent rule-based signal / 透明规则信号。
- Confidence / 置信度与依据。
- Risk / invalidation / 风险与失效条件。
- Market State Card / 市场状态卡。
- First Market Journal / 第一份市场日志。
- Short research memo / 简短研究备忘录。
- Majority + persistence baseline / 两个强制基准及比较。

达到此级可解释数据、机制、结果、局限及失败条件；holdout 继续锁定。

At this level, explain the data, mechanism, results, limitations and failure conditions. The holdout remains locked.

### Level C — MVP Complete

在 Level B 基础上完成 / In addition to Level B:

- Logistic Regression baseline。
- Locked holdout 按协议解锁 / Unlock the holdout under the protocol.
- Out-of-sample evaluation / 样本外评估。
- Comparison with majority baseline / 与多数类基准比较。
- Comparison with persistence / 与持续性基准比较。
- Probability calibration / 概率校准及评估。
- Regime performance / 各 regime 表现。
- Limitations / 局限。
- Research memo / 完整研究备忘录。
- Polished README / 完善公开说明。

全部满足才标记 **MVP v1 Complete**。发现无 edge 并不妨碍完成 MVP；隐瞒无效结果才会破坏研究。

Only then label the project **MVP v1 Complete**. A finding of no edge does not prevent completion; hiding that finding undermines the research.

<a id="s12"></a>
## 12 · 编号执行路线 / Numbered execution route

编号是工作地址，不是完成百分比。每个步骤的“通过证据”是停止条件；未通过就不将其标 DONE。允许跳到已满足前提的 Level A 包装步骤，不能跳过验收条件。

IDs locate work; they are not completion percentages. Evidence is the stopping condition for each step. Level A packaging can occur once its prerequisites are met, but its acceptance conditions cannot be skipped.

**推荐路线 / Recommended route:**

```text
P0.1  本次完成 / Delivered now
  ↓
P1.1 → P1.2 → P1.3 → P1.4  数据核验 / Source validation
  ↓
P0.2  仓库与环境落实，可在 P1 期间完成 / Repo and environment; may run during P1
  ↓
P2 → P3 → P4.1–P4.3
  ↓
P8    Level A 验收（满足全部 A 条件后）/ Gate A once all A conditions are met
  ↓
P4.4 → P5 → P6 → P7 → P9    Level B
  ↓
P10   Level C
```

P1 元数据核验可在尚未建立运行环境时进行；P0.2 必须在 P2 正式抓取前完成。P1.4 包含 H1 actual 数据来源登记，避免后续突然加入未核验数据。

P1 metadata verification can precede the runtime setup. Complete P0.2 before pipeline ingestion at P2. P1.4 also registers sources for H1 actual fundamentals so later work does not introduce unchecked data.

| Phase / 阶段 | Step / 步骤 | 行动 / Action | 通过证据 / Evidence to finish |
|---|---|---|---|
| P0 · Control & Environment | **P0.1** | 生成并检查三件套 / Create and check the control documents | 三个可导航 MD + ZIP / Three navigable Markdown files and ZIP |
| P0 | P0.2 | 建立 repo、环境、README / Charter 骨架与配置 / Set up repo, environment, document stubs and config | 实际目录、可运行环境、日期约束、版本记录 / Actual structure, usable environment, date controls and version record |
| P1 · Data Source Validation | **P1.1** | 核验 `Forecasts_Hour` / Validate forecast schema | Horizon、时点、类型、历史覆盖及版本证据 / Horizon, timing, type, coverage and vintage evidence |
| P1 | P1.2 | 核验 day-ahead source / Validate day-ahead schema | 小时键、DK1、币种、字段含义 / Hour key, zone, currency and field meaning |
| P1 | P1.3 | 核验 balancing source / Validate outcome schema | 目标字段、历史规则、发布延迟和小时映射 / Target field, historical rules, delay and hour mapping |
| P1 | P1.4 | 核验 cross-border / actual fundamentals / system sources | 来源与资格清单，包括不可用项 / Source/eligibility inventory including unavailable inputs |
| P2 · Data Pipeline | P2.1 | 实现范围受控的 API client / Build date-bounded client | 请求参数、失败处理、development-only 小样本 / Bounded request, error handling and development sample |
| P2 | P2.2 | 保存 raw 与来源 / Preserve raw data and provenance | 原始响应、抓取时间、请求与版本 / Raw responses, retrieval time, request and version |
| P2 | P2.3 | 规范化时点 / Normalize timestamps | UTC、本地时间、DST、availability 映射 / UTC, local time, DST and availability mappings |
| P2 | P2.4 | 合并 dataset / Join datasets | 唯一键、同小时对齐、join 行数 / Unique keys, aligned hours and join counts |
| P2 | P2.5 | 数据质量检查 / Validate data quality | 缺失、重复、单位、范围、资格报告 / Missingness, duplicates, units, bounds and eligibility report |
| P3 · Target Construction | P3.1 | 构造 spread / Build spread | 正确目标字段、相同单位和小时 / Correct fields, units and hours |
| P3 | P3.2 | 计算并冻结 development δ / Freeze development delta | Q25 数值及计算来源写入配置 / Q25 value and provenance in config |
| P3 | P3.3 | 构造三分类标签 / Build labels | 边界、零值、缺失处理验证 / Boundary, zero and missing-value checks |
| P3 | P3.4 | 生成 base-rate 与基准报告 / Build base-rate report | 类分布、majority、persistence 定义与可用性 / Class distribution, baselines and availability |
| P4 · H2 Revision | P4.1 | 预登记 H2 测试规格 / Register H2 test | 方向、样本、分组、失败标准 / Direction, sample, groups and failure criterion |
| P4 | P4.2 | 构造 wind / solar revision / Build revisions | 同小时 5h→1h 配对及 PIT 证据 / Matched horizons and PIT evidence |
| P4 | P4.3 | 完成首次测试和图表 / Complete first test and chart | 数据结果、结论、图表；null 允许 / Result, conclusion and chart; null accepted |
| P4 | P4.4 | 完成 H2 第一轮条件与失效分析 / Complete H2 first-round conditioning | Regime 分层、失败条件、研究记录 / Regimes, failure conditions and research record |
| P5 · H1 Fundamentals | P5.1 | 完成 H1-A 机制研究 / Complete H1-A | Actual RL 图表、diagnostic 标签、结论 / Actual-RL evidence, diagnostic label and conclusion |
| P5 | P5.2 | 判定 H1-B 资格 / Assess H1-B | Eligible proxy 或有理由的 unavailable 状态 / Eligible proxy or evidenced unavailability |
| P6 · H3 Cross-Border | P6.1 | 构造合格条件或 diagnostic 分层 / Build conditioning | 流向定义、可用时间、类别与局限 / Flow signs, availability, classes and limitations |
| P6 | P6.2 | 完成 H3 初步测试 / Complete preliminary H3 | 条件结果、样本数、结论 / Conditional results, sample counts and conclusion |
| P7 · Signal Engine | P7.1 | 构造透明规则信号 / Build transparent rules | 规则、eligible 输入、三个输出 / Rules, eligible inputs and three outputs |
| P7 | P7.2 | 加入 confidence / No Trade / risk / invalidation | 映射和条件明确，可解释单个判断 / Explicit mappings and explainable decisions |
| P7 | P7.3 | 生成状态卡、日志与基准比较 / Produce cards, journal and comparisons | 实际开发期案例、两基准、完整分母 / Real development examples, two baselines and denominators |
| P8 · Level A Packaging | P8.1 | 对照 A 的十条逐项验收 / Audit all ten A criteria | 每项证据；缺一项仍未达到 / Evidence for every criterion |
| P8 | P8.2 | 完成 README / Charter 与事实一致表述 / Finish factual public materials | 与已完成工作一致的文本 / Wording supported by completed work |
| P9 · Level B | P9.1 | 整理 short research memo / Compile short memo | H1/H2/H3、信号、风险、基准与局限 / Hypotheses, signal, risk, baselines and limits |
| P9 | P9.2 | 对照 B 验收并练习解释 / Audit B and explain findings | 完整 B 证据、可独立解释 / Complete B evidence and independent explanation |
| P10 · Level C | P10.1 | Development 内 Logistic Regression 与校准 / Fit model and calibration within development | 时间划分、模型选择和校准记录 / Temporal split, selection and calibration records |
| P10 | P10.2 | 冻结最终规格并执行解锁门槛 / Freeze and pass unlock gate | 配置 / 代码版本、测试计划、解锁记录 / Versions, plan and unlock entry |
| P10 | P10.3 | 运行 locked-holdout evaluation / Evaluate holdout | Q25 主规格、两个基准、校准与 regime 表现 / Primary Q25, both baselines, calibration and regimes |
| P10 | P10.4 | 完成 memo / limitations / README / Finalize documentation | C 条件全满足，才标 MVP v1 Complete / All C criteria met before completion label |

Level A 是证据门槛，不要求先完成 H1/H3、规则引擎或 Logistic Regression；Level B 补齐解释与决策链；Level C 才检验最终样本外表现。

Level A is an evidence gate and does not require prior completion of H1/H3, the rule engine or Logistic Regression. Level B completes the explanatory and decision chain. Level C evaluates the final out-of-sample results.

<a id="s13"></a>
## 13 · 仓库结构 / Repository structure

以下保留冻结版结构，只增加本次要求的 `docs/` 三件套。它是目标目录图，并不表示这些代码、notebooks 和数据已经创建。

The structure preserves the frozen Blueprint and adds the requested `docs/` control layer. It is a target layout, not a claim that the code, notebooks or data already exist.

```text
dk1-power-market-research/
├── README.md
├── config/
│   └── research_config.yaml
├── docs/
│   ├── project_handbook.md
│   ├── project_status.md
│   └── decision_log.md
├── data/
│   ├── raw/
│   ├── processed/
│   └── data_dictionary.md
├── src/
│   ├── fetch_energinet.py
│   ├── build_dataset.py
│   ├── build_features.py
│   ├── build_targets.py
│   └── signal_engine.py
├── notebooks/
│   ├── 01_market_overview.ipynb
│   ├── 02_forecast_revision.ipynb
│   └── 03_signal_research.ipynb
├── research/
│   ├── project_charter.md
│   ├── hypotheses.md
│   └── r01_research_memo.md
├── journal/
│   └── market_journal.md
└── outputs/
    ├── charts/
    └── market_state_cards/
```

| 路径 / Path | 职责 / Responsibility |
|---|---|
| `README.md` | 招聘者两分钟入口：问题、方法、实际结果、局限 / Recruiter-facing question, method, actual results and limits |
| `docs/project_handbook.md` | 稳定地图和验收标准 / Stable map and acceptance criteria |
| `docs/project_status.md` | 唯一动态进度板 / Single live progress board |
| `docs/decision_log.md` | 设计与变更理由、证据 / Decision rationale, changes and evidence |
| `config/research_config.yaml` | 冻结日期、目标、δ、holdout 状态、版本化参数 / Frozen periods, target, delta, holdout state and versioned parameters |
| `data/raw/` → `data/processed/` | 保留原始数据，再构造可重现处理结果 / Preserve source data, then reproducible transformations |
| `data/data_dictionary.md` | 字段定义、单位、时点、资格与数据来源 / Meaning, units, timing, eligibility and provenance |
| `src/` | 可重复运行的抓取、合并、特征、目标和信号逻辑 / Repeatable ingestion, joins, features, targets and signals |
| `notebooks/` | 开发期探索和解释图表，不复制另一套生产定义 / Development exploration and explanation without competing definitions |
| `research/project_charter.md` | 精简研究契约；从冻结定义派生 / Concise charter derived from frozen definitions |
| `research/hypotheses.md` | 事前测试规格与结果登记 / Pre-test specifications and result registry |
| `research/r01_research_memo.md` | R01 的方法、证据、结论、局限与建议 / R01 method, evidence, conclusions, limitations and implications |
| `journal/market_journal.md` | 观点和复盘，包括失败案例 / Views and post-mortems, including failures |
| `outputs/` | 从证据生成的图表与状态卡 / Evidence-backed charts and state cards |

当 config、charter 与 handbook 出现冲突时，先停止受影响的运行并查 decision log；以明确冻结或随后有证据批准的变更为准，不能让三份文件各自漂移。

If the config, charter and handbook disagree, stop the affected run and consult the decision log. Resolve against the frozen decision or a documented subsequent change; do not allow independent definitions to drift.

<a id="s14"></a>
## 14 · 十条冻结原则 / Ten frozen principles

| # | Principle | 中文与执行含义 / Meaning |
|---|---|---|
| 1 | **Point-in-Time Integrity** | 当时不知道的信息不进 decision model / No information unavailable at decision time |
| 2 | **Pre-register Before Testing** | 目标、holdout、基准和核心假设先定后测 / Fix targets, holdout, baselines and core hypotheses before testing |
| 3 | **Market Mechanism Before Model** | 先解释为何可能存在关系 / Explain the mechanism first |
| 4 | **Information Surprise Matters** | 重点看 revision，不只看 level / Study revisions, not only levels |
| 5 | **Probability, Not Certainty** | 观点承认不确定性 / Acknowledge uncertainty |
| 6 | **No Trade Is a Decision** | 没有可信 edge 时可以不参与 / Abstain when the edge is insufficient |
| 7 | **Risk Is Part of Every Thesis** | 每条观点都写 invalidation / Every thesis needs invalidation |
| 8 | **Simple Before Complex** | ML 要证明增量价值 / ML must demonstrate incremental value |
| 9 | **Failed Hypotheses Stay** | 不删 null / failure / Retain nulls and failures |
| 10 | **No Fake P&L** | 没有可执行数据就不声称交易收益 / No profit claims without executable data |

<a id="s15"></a>
## 15 · 每次开工与收工 / Session protocol

**开工 / Start:** 打开 Status，读 Current / Next / Blocker；查看上一轮证据；复述当前一步的完成标准。只在需要理解定义时翻 Handbook。

Open Status, read Current / Next / Blocker, inspect the prior evidence and restate the current step's completion criterion. Consult the handbook when a definition needs clarification.

**工作中 / During work:** 每完成一步，记录 step ID、证据位置、实际结论及它为什么允许进入下一步。遇到事实冲突登记，保留不受影响工作的推进。

For each completed step, record its ID, evidence, actual conclusion and why it enables the next step. Log factual conflicts and continue unaffected work where possible.

**收工前五分钟 / Last five minutes:** 更新 Status 的 **Done / Current / Next / Blocker**、session log 和 milestone 证据；有设计决定时追加 Decision Log；已有 repo 时提交实际变更，记录 commit。不要将“计划提交”写成“已提交”。

Update Done / Current / Next / Blocker, the session log and milestone evidence. Append substantive decisions. When a repository exists, commit actual changes and record the commit; never describe a planned commit as completed.

**变更控制 / Change control:** 普通清晰化与实施参数登记不重新开放范围。数据事实冲突或项目所有者明确要求改变范围时，先记录旧定义、证据、影响和处理，再同步相应文件。新的酷想法放后续，不改 MVP。

Routine clarifications and implementation registrations do not reopen scope. For data conflicts or an explicit owner request to change scope, record the prior definition, evidence, impact and disposition before synchronizing files. Defer new ideas instead of expanding the MVP.

状态词统一为 `DONE / IN PROGRESS / READY / NOT STARTED / BLOCKED / CONDITIONAL`。`CONDITIONAL` 表示依赖尚未满足，不等于已完成；`DONE` 需要可核验的结果。

Use `DONE / IN PROGRESS / READY / NOT STARTED / BLOCKED / CONDITIONAL` consistently. Conditional work awaits a prerequisite; DONE requires verifiable results.

<a id="s16"></a>
## 16 · 公开表述与面试 / Public positioning and interview

名称：**DK1 Short-Term Power Market Research | Independent Project**。

以下保留冻结版的表述边界。只有相应工作确实发生、达到里程碑时才使用；时间性文字如 “this week” 必须与实际日期一致。目前仅文档初始化完成，不应直接当作已达到 Level A 的简历条目。

The wording below preserves the frozen positioning. Use it only when the underlying work and milestone are real. Date-sensitive language such as “this week” must remain factual. Documentation alone is not a Level A CV claim.

**Level A 表述 / Wording after Level A:**

> Building a point-in-time DK1 power-market research pipeline to test how renewable forecast revisions and system conditions relate to short-term balancing pressure, using official Energinet market data.

> Pre-registering target definitions, holdout periods and naive benchmarks to prevent look-ahead bias and distinguish genuine signal from market base rates.

中文含义：研究预报修正和系统条件是否关联平衡压力，并用事前定义、留出期和基准约束结论，而不是宣称盈利交易系统。

**Level B 后可增加 / Additional wording after Level B:**

> Translating hypotheses into directional views, confidence levels and explicit risk/invalidation conditions.

**冻结版 Cover Letter narrative / Frozen narrative, subject to factual timing:**

> I started building a DK1 power-market research repo this week. My first question is whether renewable forecast revisions, residual-load conditions and cross-border factors explain short-term market pressure — and when they stop explaining it. I plan to keep extending the research throughout my master's rather than treat it as a one-off application project.

中文含义：说明正在做什么、首个具体问题是什么，以及长期研究意图。未实际建立 repo 时不能说已经建立；完成日期不在本周时应更新对应时间表述。

**“Intraday 在哪里？” / “Where is the intraday element?”**

> The first version does not claim to reproduce executable intraday P&L because I don't yet have reliable historical transaction-level intraday data. Instead, I study information that arrives inside the short-term decision window—especially renewable forecast revisions—and use balancing pressure relative to the day-ahead price as the first observable outcome. The architecture is intentionally point-in-time, so intraday prices can later replace that proxy without rebuilding the research process.

中文解释：研究的是短期窗口内的新信息，尤其预报修正；当前用 balancing spread 观察结果。它不是可执行日内收益回测，但为未来替换结果层保留了研究架构。

冻结版以 MFT / Vis 的学生交易岗位作为职业背景，强调 new information → interpretation → hypothesis → probability → decision → risk → feedback。这里保留能力对应关系，不重述或认证岗位当前开放状态。

The Blueprint uses MFT / Vis student-trading roles as career context, emphasizing new information → interpretation → hypothesis → probability → decision → risk → feedback. This retains the capability mapping without asserting current job availability.

<a id="s17"></a>
## 17 · 尚待核实的实施细节 / Implementation items to verify

这是执行登记，不是重开目标、日期或假设。原 Blueprint 未提供的数值或字段不能被写成“已经冻结”。各项详细状态见 [Decision Log](decision_log.md#open-items)。

This is an implementation register, not a reopening of the target, dates or hypotheses. Unspecified values or fields must not be described as frozen. See the decision log for tracking.

| ID | 待确定项 / Item | 最迟解决步骤 / Resolve by |
|---|---|---|
| I01 | Balancing/regulating 的具体价格字段与历史语义 / Exact outcome field and historical semantics | P1.3，P3 前 / Before P3 |
| I02 | Forecast timestamp、horizon 版本与历史覆盖 / Forecast timestamps, versions and coverage | P1.1 |
| I03 | Decision cutoff、发布延迟、lag / persistence 可用性 / Decision cutoff, delays and lag eligibility | P2.3，P3.4 / Before baseline evaluation |
| I04 | 日期边界时区、DST、请求端点包含关系 / Boundary timezone, DST and request inclusivity | P1；正式抓取前 / Before ingestion |
| I05 | δ 数值、分位数插值规则、有效样本规则 / Delta value, quantile method and valid sample policy | P3.2 |
| I06 | H1-B / H3 可得性及字段资格 / H1-B and H3 availability and eligibility | P1.4 / P5.2 / P6.1 |
| I07 | Regime、规则、confidence、No Trade 参数 / Regime, rule, confidence and No Trade settings | P4 / P7，测试对应规格前 / Before testing each specification |
| I08 | Logistic Regression、时间验证、校准、指标 convention / Model, temporal validation, calibration and metric conventions | P10.1，holdout 解锁前 / Before unlock |

<a id="s18"></a>
## 18 · 来源对应表与术语 / Source crosswalk and glossary

**权威来源 / Source of truth:** 对话 [Trader 岗位状态监控](chatgpt-conversation://6a999e10-6328-83eb-8525-f79e924ffd7d)，2026-09-03 的完整 `Freeze Candidate v1.1` 回复（31 节）及随后用户的“冻结”；再结合三文件控制体系的后续要求。文档通过完整对话读取整理，没有把预览中的旧版当作最终版。

The authoritative source is the complete 31-section Freeze Candidate v1.1 response, the owner's subsequent explicit freeze, and the following request for the three-document control system in the referenced conversation. The bounded preview's earlier versions do not override that source.

原对话中的外部 API / 市场描述作为已冻结设计的依据保留；本次没有进行 live source validation。P1 将保存官方来源与历史样本证据。迁移到 repo 后保留本来源标识，并在 `research/project_charter.md` 放入冻结摘要。

External API and market descriptions in the source are retained as design context, not newly verified facts. P1 will preserve official-source and historical-sample evidence. Retain this provenance when moving into the repository and place a concise frozen summary in the charter.

| Blueprint 原节 / Source sections | 本手册位置 / Handbook location |
|---|---|
| Long-term context; 1–2 Mission / Scope | 01, 13, 16 |
| 3 Research question / Target | 01–02 |
| 4 Time window; 5 Holdout | 03 |
| 6 PIT; 7 Actual ≠ Feature | 04–05 |
| 8 H1; 9 H2; 10 Vintage honesty; 11 H3 | 05–06 |
| 12 Data universe | 06 |
| 13 Features; 14 Regimes | 07 |
| 15 Research engine | 08 |
| 16 Signal; 17 Confidence; 18 Decision | 09 |
| 19 Risk; 20 State card | 10 |
| 21 Evaluation / Baselines | 08 |
| 22 No Fake P&L; 23 Journal | 10 |
| 24 Modelling roadmap | 09, 12 |
| 25 Repository | 13 |
| 26 Ten principles | 14 |
| 27 Level A / B / C | 11–12 |
| 28 CV; 29 Cover Letter; 30 MFT / Vis; 31 Intraday answer | 16 |
| Subsequent control-system request / 后续三件套要求 | 12, 15, project_status.md, decision_log.md |

| 术语 / Term | 简明理解 / Working meaning |
|---|---|
| Delivery hour | 电力交割所属小时 / Hour in which electricity is delivered |
| Forecast horizon | 预报距交割的时间跨度，不自动等于发布时间 / Lead time, not automatically publication time |
| Vintage | 当时发布的一个预报版本 / A forecast version published at a particular time |
| Revision | 同一交割目标的新旧预报差 / Difference between forecasts for the same delivery target |
| Point-in-time (PIT) | 只使用那个决策时点已经可得的信息 / Information available by the decision time |
| Residual load | Demand 减 wind、solar；需区分 actual 和 known / Demand minus wind and solar, distinguishing actual from known |
| Balancing spread | 同小时 balancing price 减 day-ahead price / Same-hour balancing minus day-ahead price |
| Neutral band | 把小幅 spread 归为 NEUTRAL 的区间 / Band treating small spreads as neutral |
| Regime | 简单定义的市场条件分组 / A simply defined market-state grouping |
| Holdout | 事前留出、开发时不看的最终检验区间 / Predeclared final evaluation data withheld from development |
| Calibration | 预测概率与实际发生频率是否相符 / Agreement between predicted probabilities and observed frequencies |
| Invalidation | 什么证据出现后应撤回观点 / Evidence that requires withdrawing a thesis |

**下一次开工入口 / Next session entry:** [project_status.md](project_status.md#current-step)。
