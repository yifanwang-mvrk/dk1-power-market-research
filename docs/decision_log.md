# Decision Log / 设计决策记录

**Project:** DK1 Short-Term Power Market Research
**Initialized:** 2026-09-03
**Design baseline:** Frozen MVP Blueprint v1.1
[Handbook / 项目地图](project_handbook.md) · [Status / 当前进度](project_status.md)

本文件回答“为什么这样决定”。D001–D018 记录完整最终 Blueprint 中已冻结的设计；D019 记录随后确定的项目控制体系；E001–E003 是本次将冻结设计落地时补充的执行说明，**不冒充原 Blueprint 的逐字决定**。I01–I08 是仍待核实的实施细节。

D001–D018 capture frozen Blueprint decisions. D019 records the subsequently agreed control system. E001–E003 are operational clarifications added for execution, **not claims of verbatim decisions in the Blueprint**. I01–I08 remain open implementation items.

冻结来源：对话 [Trader 岗位状态监控](chatgpt-conversation://6a999e10-6328-83eb-8525-f79e924ffd7d)，完整 31 节 `MVP Project Blueprint — Freeze Candidate v1.1`，回复标识 `d88638cb-9d9b-4932-8663-0690f547caa4`，随后项目所有者明确回复“冻结”。日期均为 **2026-09-03**。本次整理没有重新验证 live API。

Source: the complete 31-section final Blueprint response and the owner's subsequent explicit freeze, followed by the control-document request. All initial entries are dated **2026-09-03**. Live API facts were not independently revalidated during this documentation task.

## 使用规则 / How to maintain this log

1. 新决定追加，旧决定不删除；变更用新 ID 指向被替代项。/ Append decisions and preserve superseded entries with links.
2. 区分 `FROZEN`、`IMPLEMENTATION NOTE`、`OPEN`、`SUPERSEDED`。历史假设不等于已验证数据事实。/ Distinguish design status from empirical verification.
3. 记录决定、理由、替代选项、影响、证据及受影响文件。参数应在相应测试前登记。/ Record decision, rationale, alternative, impact, evidence and affected files before testing the specification.
4. 新想法不自动重开 scope；数据冲突或所有者明确要求改变范围时，记录处理过程。/ New ideas do not reopen scope; log factual conflicts or explicit owner-requested changes.

## 决策索引 / Decision index

| ID | 决策 / Decision | 状态 / Status |
|---|---|---|
| D001 | Balancing spread primary target | FROZEN |
| D002 | Three classes and development-only Q25 | FROZEN |
| D003 | DK1 scope and honest naming | FROZEN |
| D004 | 2022–2024 hourly research window | FROZEN |
| D005 | Locked 2024 H2 holdout | FROZEN |
| D006 | Point-in-time eligibility classes | FROZEN |
| D007 | H1 actual / known residual-load separation | FROZEN |
| D008 | H2 5h→1h forecast revision at MVP core | FROZEN |
| D009 | Forecast vintage honesty | FROZEN |
| D010 | H3 cross-border conditioning | FROZEN |
| D011 | Energinet-first data, focused features, simple regimes | FROZEN |
| D012 | Mandatory majority and persistence baselines | FROZEN |
| D013 | Research protocol, metrics and model order | FROZEN |
| D014 | Confidence, three decisions and No Trade | FROZEN |
| D015 | Risk, state cards and retained post-mortems | FROZEN |
| D016 | No Fake P&L | FROZEN |
| D017 | Evidence-based Level A / B / C | FROZEN |
| D018 | Repo structure, ten principles and public wording | FROZEN |
| D019 | Three documents and session closing protocol | AGREED CONTROL SYSTEM |
| E001–E003 | 执行说明 / Execution clarifications | IMPLEMENTATION NOTE |
| I01–I08 | 字段、参数和可用性 / Fields, parameters and availability | OPEN |

## D001 · Use balancing spread as the primary target

**决定 / Decision:** 对同一 DK1 hourly delivery period，`Spread_t = P_Balancing,t - P_DayAhead,t`。Day-ahead 是参考，balancing/regulating 是结果；具体 outcome 字段待 I01 核实。

**理由 / Rationale:** 5h / 1h 预报更新发生在日前价格确定之后；用其预测已确定的 DA price 会造成时序倒置。/ Revisions arriving after day-ahead clearing cannot predict an already-cleared price without temporal inconsistency.

**未采用 / Alternative:** `P_DA,t - P_DA,t-1` 作为主目标；可保留为 descriptive analysis。/ Adjacent-hour DA movement remains descriptive only.

**影响 / Impact:** H1/H2/H3 围绕短期 balancing pressure；目标、代码、README 统一这一含义。/ Align hypotheses and reporting around balancing pressure. **Source:** Blueprint §3.

## D002 · Three classes with a pre-registered neutral band

**决定 / Decision:** UP if `Spread > delta`; DOWN if `Spread < -delta`; NEUTRAL if `abs(Spread) <= delta`。

`delta = Q25(abs(Spread) | abs(Spread) > 0)`，仅 development。计算后立即冻结进 config；目前数值 **TBD**。

**理由 / Rationale:** 避免把微小波动当方向信号，防止观察结果后临时调整标签。/ Separate small spreads from meaningful direction and prevent result-driven label tuning.

**未采用 / Alternative:** 任意小变化均算方向，或用 holdout 调 δ。/ No neutral band or holdout-tuned thresholds.

**影响 / Impact:** Q25 是 primary；Level C 的 Q20 / Q30 仅作为次要敏感性分析，不替换主规格。/ Secondary sensitivities cannot replace Q25. **Source:** §3.3–3.4.

## D003 · One zone and a scope-matched project name

**决定 / Decision:** MVP 仅 DK1 — Western Denmark；repo `dk1-power-market-research`，公开名称 **DK1 Short-Term Power Market Research**。

**理由 / Rationale:** 先研究清楚一个 bidding zone，避免名字大于证据。/ Master one zone and keep the name proportionate to the evidence.

**未采用 / Alternative:** 现在就用 Nordic 项目范围或同时扩 DK2 / Germany / Norway / Sweden。/ Immediate Nordic coverage.

**影响 / Impact:** R01 方法成熟后再扩区域；Nordic umbrella 属于未来。/ Geographic expansion follows mature R01 methods. **Source:** Long-term context; §2.

## D004 · Fix the historical hourly window

**决定 / Decision:** Development **2022-01-01 → 2024-06-30**；holdout **2024-07-01 → 2024-12-31**；单小时交割段。

**理由 / Rationale:** 按冻结版设计，保持小时研究并避免把 2025+ 的新 balancing design / 15-minute structure 混进首版。/ Keep the intended hourly study separate from the later designs identified in the Blueprint.

**未采用 / Alternative:** 默认抓最新数据或把不同市场设计直接拼接。/ Default latest-data pulls or unexamined mixing of market designs.

**影响 / Impact:** P1 仍需验证窗口内的历史字段和语义；日期边界时区见 I04。/ Historical consistency still requires verification. **Source:** §4.

## D005 · Lock holdout from day one

**决定 / Decision:** 2024 H2 在 Level C 前不做 EDA、相关性、标签分布、性能评估或任何调参；Level A / B 默认不抓取。

**理由 / Rationale:** 事前留出才能作为未参与开发的检验数据。/ A holdout must be withheld before development, not merely evaluated last.

**未采用 / Alternative:** 看过数据后把最后一段称为 out-of-sample。/ Calling the last inspected segment unseen data.

**影响 / Impact:** 日期先写 config；解锁前固定规格和评估计划并记版本；解锁后不得用其结果重选 primary。/ Record a freeze and unlock trail. **Source:** §5, §27 Level C.

## D006 · Enforce three point-in-time classes

**决定 / Decision:** 所有字段分类为 `decision_eligible`、`diagnostic_only` 或 `outcome`；未核实的候选先隔离。只有决策时合理可得的信息可进入 simulated decision。

**理由 / Rationale:** 今天可以下载的历史字段未必当时可见。/ Historical availability today does not establish availability then.

**未采用 / Alternative:** 所有历史字段默认当特征，或认为 lag 自动合格。/ Treating historical or lagged fields as automatically eligible.

**影响 / Impact:** Data dictionary 记录定义、时间含义、发布证据、版本和资格；cutoff 待 I03。/ Eligibility must be evidenced. **Source:** §6.

## D007 · Separate H1-A from H1-B

**决定 / Decision:** `RL_actual = Demand_actual - Wind_actual - Solar_actual` 用于 H1-A diagnostic mechanism research；H1-B 仅使用当时可得的 forecast / scheduled / lag-based `RL_known`。

**理由 / Rationale:** Actual 可以解释发生了什么，但不能伪装成当时知道什么。/ Realized values explain events, not prior knowledge.

**未采用 / Alternative:** 缺 consumption forecast 时以 actual demand 补入信号。/ Filling a forecast gap with actual demand.

**影响 / Impact:** H1-A 可完成；H1-B 依赖可靠 PIT 数据，不能因赶 CV 造数据。/ H1-B remains conditional. **Source:** §7–8.

## D008 · Make H2 forecast revision central to the MVP

**决定 / Decision:** 同一交割小时分别构造 wind 和 solar 的 `Forecast_1h - Forecast_5h`；正向 wind revision 的预期机制是更宽松系统与更高 DOWN pressure 概率。

**理由 / Rationale:** 研究重点是信息更新如何改变预期，并检查关系何时失效。/ Study new information and the conditions under which its relationship breaks down.

**未采用 / Alternative:** 仅研究实际风电与电价相关性，或把相邻交割小时之差当 revision。/ Only level correlations or revisions across different hours.

**影响 / Impact:** H2 是核心，不自动降级；先通过 P1.1 验证历史 horizon 与时点，再构造和测试。/ Validate the data basis before implementation. **Source:** §9.

## D009 · Do not fabricate forecast vintage history

**决定 / Decision:** 首版描述为 **forecast horizon revision research**，不宣称完整 tick-by-tick vintage reconstruction。Current / Intraday 只有历史语义和时点验证后才加入。

**理由 / Rationale:** 多个 horizon 不证明每次更新都被历史保存。/ Multiple horizons do not establish retention of every update.

**未采用 / Alternative:** 人工合成 vintage、把最后版本当历史当时版本。/ Synthetic vintages or treating final versions as historically available.

**影响 / Impact:** P1.1 核实 publication rows、`TimestampUTC`、Current / Intraday 定义和留存；数据冲突须登记。/ Record evidence and conflicts. **Source:** §10.

## D010 · Use cross-border conditions with the same PIT rule

**决定 / Decision:** H3 检查 cross-border / system conditions 是否改变 H2 的关系。已公布 exchanges、countertrade、capacity 是候选；事前未知的 realized flow 仅 diagnostic。

**理由 / Rationale:** 跨境条件可能抵消本地 renewable revision，但只有当时已知的条件才可支持决策。/ Conditioning must reflect available information for decision use.

**未采用 / Alternative:** 把 final physical flow 当可用特征并声称提高预测。/ Hindsight physical-flow predictors.

**影响 / Impact:** H3 报告明确区分 eligible 与 diagnostic conditioning。/ Separate predictive and diagnostic evidence. **Source:** §11.

## D011 · Keep data, features and regimes focused

**决定 / Decision:** 优先 Energinet；六层为 DA reference、balancing outcome、renewable forecasts、actual fundamentals、cross-border、system。特征集中在 revision、known fundamentals、eligible lags、time context 和 cross-border context。

**理由 / Rationale:** 每个特征都要能解释交易者为何关心；先用 Tight / Normal / Loose 或 renewable-level regime 检查条件性。/ Every feature needs an economic rationale; simple regimes reveal conditionality.

**未采用 / Alternative:** 为数量加入特征、复杂 clustering 或立即引入多平台数据。/ Feature accumulation and premature complexity.

**影响 / Impact:** 字段与分组规则在 development 中登记；weather、ENTSO-E、intraday order/trade data 属未来。/ Register definitions before use. **Source:** §12–14.

## D012 · Require majority and persistence in the scorecard

**决定 / Decision:** Majority = 训练期最多类；persistence = `y_hat_t = y_(t-1)`。任何方向性表现必须相对两个基准解释。

**理由 / Rationale:** 类别不平衡和自相关可能产生看似很高的准确率。/ Base rates and persistence can explain apparently strong accuracy.

**未采用 / Alternative:** 单独报 “58% accuracy” 或以 holdout 标签选 majority。/ Standalone accuracy or holdout-derived benchmarks.

**影响 / Impact:** 只有稳定超过基准才讨论 incremental information；没超过就如实写无已证明 edge。PIT 的实施冲突见 E001 / I03。/ Report no demonstrated edge when benchmarks are not beaten. **Source:** §21.

## D013 · Register tests, retain nulls and earn model complexity

**决定 / Decision:** Observation → Hypothesis → Mechanism → Eligible information → Test → Result → Implication → Failure condition。结论可为 Supported、Conditionally supported、Rejected / Null。

**理由 / Rationale:** 可解释的研究包括失效条件，不能只保留成功案例。/ Explainable research retains failures and limitations.

**未采用 / Alternative:** 先做复杂模型再寻找故事，或删失败假设。/ Modelling first and selecting favorable narratives.

**影响 / Impact:** 先机制 → 描述 / 条件统计 → 规则 → Logistic Regression → 后续复杂模型。报告 class distribution、directional / balanced accuracy、macro F1、confusion matrix、class hit rate、regime 表现；概率阶段加 calibration / Brier / buckets。/ Complexity must beat simpler baselines out of sample. **Source:** §15, §21, §24.

## D014 · Separate signal, confidence and decision

**决定 / Decision:** 透明规则输出 UP / DOWN / NEUTRAL；早期置信度 Low / Medium / High；决策 Bullish / Bearish / No Trade。统计阶段再加入三类概率与校准。

**理由 / Rationale:** Signal ≠ Trade，低 edge、冲突、缺信息或未知 regime 都可以支持 No Trade。/ A directional view need not become a position.

**未采用 / Alternative:** 强迫每个小时给交易方向，或用伪精确概率包装主观信心。/ Forced trades or false probability precision.

**影响 / Impact:** `NEUTRAL` 标签与 `No Trade` 动作分开存储和评估；阈值、映射待 I07。/ Keep outcome labels and actions distinct. **Source:** §16–18.

## D015 · Make risk and post-mortem mandatory

**决定 / Decision:** 每条观点包含 driver、counterargument、key risk、invalidation、no-trade condition；Market State Card 与 Journal 记录事前判断、事后结果和教训。

**理由 / Rationale:** 没有失效条件的观点不完整，失败案例是研究证据。/ A thesis needs falsification and an honest feedback loop.

**未采用 / Alternative:** 只存命中观点，或事后改写原始判断。/ Keeping only winners or rewriting prior views.

**影响 / Impact:** Outcome / Post-Mortem 在结果出现后补充，保留原始 snapshot。/ Preserve the prior decision record. **Source:** §19–20, §23.

## D016 · No Fake P&L

**决定 / Decision:** **Balancing pressure is used as a short-term market-outcome proxy, not as executable intraday P&L.**

**理由 / Rationale:** 当前没有完整可靠的可执行历史 intraday transactions / order-book data。/ The necessary executable historical market data are absent from the MVP design.

**未采用 / Alternative:** 把 spread classifier 结果转换成声称真实可交易的收益率。/ Presenting classifier results as realized trading returns.

**影响 / Impact:** 不声称盈利策略；未来获得交易、成本和流动性数据后再扩 outcome layer。/ Extend execution analysis only with suitable data. **Source:** §22, §31.

## D017 · Use evidence-based Level A / B / C gates

**决定 / Decision:** A = repo、README、Charter、config、三类核心数据、字典、H2 variables、至少一次完成的真实测试与结论、一张 meaningful chart、未用 holdout。B 增加完整 H2、H1 机制、H3 条件、规则 / confidence / risk、卡片 / 日志 / memo、两基准。C 增加 Logistic Regression、受控解锁、OOS / 基准 / 校准 / regime、局限和最终文档。

**理由 / Rationale:** “已开始分析”不足以支持 CV；交付必须有结果证据，null 也有效。/ Starting analysis is not a completed achievement; a null conclusion is valid evidence.

**未采用 / Alternative:** 建 repo 即 CV-safe，或没有 holdout 评估就标 MVP complete。/ Treating scaffolding as a completed project.

**影响 / Impact:** 三件套交付后 A/B/C 仍均未达到。完整清单以 [Handbook 11](project_handbook.md#s11) 为准。/ Use evidence, not task counts, for completion. **Source:** §27.

## D018 · Preserve a lean repo, principles and factual positioning

**决定 / Decision:** 保留 Blueprint 的 config / data / src / notebooks / research / journal / outputs 结构；研究遵守十条原则；公开名称与证据一致，明确 intraday proxy 的边界。

**理由 / Rationale:** 可追溯、可解释的研究优先；招聘材料应描述真实完成工作。/ Traceability and factual claims matter more than breadth or presentation complexity.

**未采用 / Alternative:** 过度工程化、夸大 Nordic 范围、profitable strategy 或未完成的技能。/ Overengineering and unsupported scope or profit claims.

**影响 / Impact:** README 面向外部快速理解，Handbook 面向内部理解；CV 随 A/B 证据升级，CL 的 “this week” 必须符合实际。十条原则完整保存在 [Handbook 14](project_handbook.md#s14)。/ Keep public language aligned with evidence. **Source:** §25–26, §28–31.

## D019 · Maintain three control documents and a numbered handover

**决定 / Decision:** `docs/project_handbook.md` 是稳定地图；`docs/project_status.md` 是动态进度；`docs/decision_log.md` 记录理由。工作按 P0–P10 编号，每次收工更新 Done / Current / Next / Blocker，已有 repo 时提交变更。

**理由 / Rationale:** 防止项目逻辑和实时进度混在一起，让停工后可以直接续上。/ Separate the project map from current progress so work can resume reliably.

**未采用 / Alternative:** 只写巨大手册、依赖聊天回忆或按投入时间算完成。/ A handbook without a live state record.

**影响 / Impact:** 本次 P0.1 完成，当前待执行 P1.1；P0.2 的 repo/environment 未完成，P2 前落实。不为新想法反复改变冻结 MVP。/ Preserve one explicit next step. **Source:** Post-freeze control-system discussion and current user request.

## 本次执行说明 / Operational clarifications

### E001 · Preserve both persistence and point-in-time integrity

冻结版同时要求 `y_hat_t = y_(t-1)` 和决策时已知。若上一小时标签尚未发布，不能把它视为可实施策略。保留冻结公式并标为 ex-post reference；另外登记、报告真实可用的 lagged benchmark。**目前尚未判定延迟或替代 lag，见 I03。**

The frozen persistence formula and PIT rule must both remain visible. If the preceding label is unavailable, retain the formula as an ex-post reference and separately register an availability-correct benchmark. No publication delay or replacement lag has been established yet. This implements D006 / D012 without silently changing either.

### E002 · Make evaluation denominators explicit

执行时把三分类准确率与 active-view hit rate 分开；每类 hit rate 按 predicted-class precision 报告，并同时报告 recall；No Trade、coverage、缺失与排除样本都给数量。所有方法用可比样本。

Distinguish three-class accuracy from active-view hit rate. Report class hit rate as precision alongside recall, and disclose coverage, No Trade and exclusions. These metric conventions clarify reporting and do not constitute completed results.

δ 按完整 development 估计的主规格保留。若内部验证沿用这个 δ，注明该标签阈值使用过完整 development；不能把它当作全流程严格未见的测试。最终 holdout 仍使用固定 development δ。

Retain the frozen development-wide delta. Internal validation using that delta must disclose its full-development label construction. The final holdout remains separate and uses the frozen development delta.

### E003 · Document execution truth and unlock evidence

本三件套交付仅证明 P0.1 完成；仓库、配置、数据和测试不得提前标 DONE。解锁 holdout 前在日志记录冻结规格、版本和测试计划；校准器只在 development 拟合，holdout 的敏感性结果不能替换主规格。

The package establishes P0.1 only. Require real artifacts for later completion and a versioned specification and test plan before holdout access. Fit calibration within development and preserve primary-versus-secondary reporting. These are operational checks supporting D005 / D017 / D019.

<a id="open-items"></a>
## Open implementation items / 待核实实施项

所有条目初始状态为 **OPEN**。没有已确认的外部 blocker；尚未验证也不等于已证实可用。解决后记录证据、数值或字段、新决策 ID 和受影响文件。

All items begin **OPEN**. There is no confirmed external blocker, and lack of verification is not proof of availability. On resolution, record evidence, the chosen value or field, a decision ID and affected files.

| ID | 问题 / Question | 解决步骤 / Gate | 需要的证据 / Evidence required |
|---|---|---|---|
| I01 | 哪个历史 DK1 balancing/regulating 字段构成单一目标价格？/ Which exact historical price field? | P1.3，P3 前 | 字段定义、规则适用日期、单位、hour mapping；不能结果导向挑选 / Definition, dates, units and mapping |
| I02 | Forecast horizon、`TimestampUTC`、Current / Intraday、版本留存和历史覆盖如何解释？ | P1.1 | 官方 metadata + development 样本 + pairing / availability 说明 |
| I03 | 决策 cutoff、预报可得时刻、outcome 发布延迟与 `y_t-1` 可用性？ | P2.3 / P3.4；信号前 | 有证据的时间线、as-of 规则、基准处理；未定数值不补猜 / Evidenced timeline and benchmark handling |
| I04 | 日期按 UTC 还是当地交割日？DST 和 API endpoints 是否包含边界？ | P1；P2 抓取前 | 明确日期语义、UTC 映射、范围测试，不改变冻结日历日期 / Boundary contract and checks |
| I05 | δ 的实际值、quantile interpolation、有效样本与 missing policy？ | P3.2 | Development-only 非零绝对 spread、样本数、算法、配置值和版本 |
| I06 | H1-B load proxy、H3 exchange / capacity / flow 哪些可用？ | P1.4 / P5.2 / P6.1 | 逐字段资格；缺失时明确 conditional / diagnostic / unavailable |
| I07 | Regime bins、strong revision、rule thresholds、confidence / No Trade 如何定义？ | P4 / P7；对应测试前 | Development-only 预登记规格、理由和版本 |
| I08 | Logistic Regression、时间训练/验证、校准和 Brier / undefined metric conventions？ | P10.1；解锁前 | 固定时间切分、模型与校准参数、评估与敏感性计划 |

## 后续决策模板 / Template for the next entry

```text
Decision ID / 决策编号: D020 (or next unused ID)
Date / 日期:
Status / 状态: FROZEN / IMPLEMENTATION NOTE / OPEN / SUPERSEDED
Related step / 对应步骤:
Related open item / 对应 I 编号:
Context / 问题是什么:
Decision / 决定:
Rationale / 为什么:
Alternative considered / 考虑过的替代方案:
Evidence / 官方来源、样本、配置或结果版本:
Impact / 影响的定义、分析、文件与里程碑:
Holdout implications / 是否影响留出期及其处理:
Supersedes / 替代哪个旧决定，或 None:
Owner direction if scope changes / 若改范围，对应所有者指示:
```

<a id="holdout-unlock"></a>
## Level C 解锁记录模板 / Holdout unlock template

**当前状态：未解锁；以下为空模板。/ Current state: locked; the following is a blank template.**

```text
Decision ID:
Unlock date/time:
Related step: P10.2
Level B evidence:
Development data/version:
Frozen code/config version:
Target field, Q25 delta and label rules:
Feature eligibility and decision cutoff:
Model selection and development-only calibration:
Majority and persistence definitions / availability:
Primary metrics, sample filters and regime definitions:
Predeclared secondary sensitivities, if any:
Evidence of no prior holdout use:
Planned holdout request boundaries:
Results destination:
Protocol for changes after inspection:
```

完成模板并满足 [Handbook 的解锁门槛](project_handbook.md#s03) 后，才更新 Status 的 holdout 状态。填写一个日期本身不代表门槛通过。

Update the status board only after the unlock record and handbook gate are satisfied. Entering a date alone does not pass the gate.
