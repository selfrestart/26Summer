# P4 实施规划 — Mathematical and Reproduction Verification

> **状态**：`Planned`（规划完成，尚未实现）
>
> **前置输入**：`Paper`、`MethodAnalysis`、`ReproductionBundle`、`ExperimentRun`
>
> **核心输出**：`MathCheckReport`、`VerificationReport`、可发布复现报告

## 1. 阶段目标

P4 把“代码能运行”提升为“结果是否支持论文声明”。它包含两个相互独立但可组合的角色：MathChecker 检查数学表达和推导，Verifier 对齐论文 claims 与实验 observations。

```text
Paper + MethodAnalysis ──→ MathChecker ──→ MathCheckReport
Paper claims + ExperimentRun ──→ Verifier ──→ VerificationReport
                                      ↓
                               Reproduction Report
```

### 1.1 实现顺序与运行时顺序

P4 在开发顺序上位于 P3 之后，因此 P3 首次实现不能依赖 P4。P4 完成后的正常
运行时允许先执行 `Paper + MethodAnalysis -> MathChecker`，将
`MathCheckReport` 作为 CodeForger 的**可选 preflight**；Verifier 仍在
`ExperimentRun` 之后运行。MathChecker 的严重问题是否阻断 P3 必须由显式 policy
决定，不能让 LLM 自行授权或修改 P2/P3 artifact。

## 2. 数据契约

P4 不重新从论文自由文本发明公式或声称值。P2 的 `EquationEvidence` 和
`ReportedClaimDraft` 是输入草案，P4 负责规范化、可比性判断和验证结论：

- P2 `EquationEvidence` -> P4 `EquationRef`，保留 raw、source hash、producer 和 parse status；
- P2 `ReportedClaimDraft` -> P4 `ReportedClaim`，保留 raw value/evidence，再增加单位、scale 和 identity 规范化；
- P3 structured metric event/artifact -> P4 `ObservedMetric`，不把任意 stdout 文本当作指标；
- 输入缺失、版本不兼容或来源 hash 不符时返回 `inconclusive/failed`，不得隐式重抽取。

### `EquationRef`

公式 raw/normalized 文本、编号、parse status、符号表、章节/页码、P2 evidence、
source hash 和 producer version。`not_available/partial` 必须计入 math coverage，
不能被隐藏在总体 verdict 中。

### `MathIssue`

issue type、severity、description、affected equation、evidence、是否阻断实现。问题类型包括未定义符号、维度不一致、推导跳步、目标函数/实现不一致和数值稳定性风险。

### `ReportedClaim`

论文中的 dataset、split、metric、raw/normalized value、unit/scale、direction、
aggregation、evaluation setting、uncertainty、evidence 和 normalization notes。

### `ObservedMetric`

P3 run 中的 metric name/value、step、split、aggregation、seed/run ID 和 artifact 来源。

### `MetricComparison`

标准化 metric、claimed/observed 值、绝对/相对差异、tolerance、comparability 和 verdict。

### `VerificationReport`

总体 verdict、可比/不可比 claims、metric comparisons、math issues、run failures、fidelity score（确定性计算）、限制和 provenance。

## 3. Verdict 语义

```text
verified       可比且在预先定义容差内
partial        部分 claims 验证或部分 run 有效
not_reproduced 可比但明确超出容差
inconclusive   缺数据、配置或统计证据
not_comparable metric/split/protocol 无法对齐
failed         执行或验证流程失败
```

默认不得把 `inconclusive`/`not_comparable` 转换为失败或成功。容差必须在比较前由 policy/配置给出，不能根据结果动态放宽。

## 4. MathChecker 规划

- 从 P2 equations/evidence 建立符号表；
- 检查同一符号跨章节含义冲突；
- 执行形状/维度一致性规则；
- 对简单代数使用 SymPy 等确定性工具；
- 区分工具验证、LLM 解释和人工待确认；
- 不声称完成形式化证明；
- 输出问题严重度和对 P3 实现的影响。

## 5. Verifier 规划

### 5.1 Claim 对齐

匹配键至少包括：dataset、split、metric、evaluation procedure、checkpoint/ensemble setting。仅 metric 名相同不足以判定可比。

### 5.2 统计策略

- 单次 run：只报告点估计差异，不宣称统计显著性；
- 多 seed：报告均值、标准差、置信区间；
- 论文只给区间/图：标记近似来源；
- 方向性指标显式记录 higher/lower is better；
- 多重比较策略在 benchmark 配置中声明。

### 5.3 Fidelity score

如果提供总分，必须由已比较 claims 的确定性权重计算，同时公开分项和不可比比例。总分不能掩盖关键 claim 失败。

## 6. 报告结构

计划输出 Markdown + JSON：

1. Executive summary；
2. Scope and artifacts；
3. Environment and data provenance；
4. Mathematical checks；
5. Claim-by-claim comparisons；
6. Reproduction gaps and failures；
7. Limitations；
8. Exact commands、hashes 和证据链接。

P4 不生成虚构的“成功证书”；报告必须能表达失败和不可判定。

## 7. 工作包

### P4.0 Claim/metric schema 和标准化规则

建立 metric alias、单位、方向、dataset/split identity 和 tolerance policy。

### P4.1 MathChecker

实现公式/符号工具、确定性校验、Agent 解释和 `MathCheckReport`。

### P4.2 Verifier

实现 claim extraction consumption、metric alignment、difference/statistics/verdict。

### P4.3 报告生成

模板化 Markdown/JSON 报告、artifact 引用和 provenance。

### P4.4 Pipeline/CLI

计划命令：

```powershell
repro-forge verify methodology.json run.json --output report.json
repro-forge render-report report.json --output report.md
```

### P4.5 验证

使用合成 metrics 覆盖 exact match、tolerance、wrong split、missing seed、failed run 和 non-comparable。

## 8. 测试矩阵

| 风险 | 必测场景 | 期望 |
|---|---|---|
| metric 同名异义 | 相同 metric、不同 dataset/split/procedure | `not_comparable`，不计算误导差异 |
| direction 错误 | higher/lower-is-better 相反 | 标准化后 verdict 正确 |
| 单次 run 过度结论 | 只有一个 seed | 只报告点估计，不输出显著性 |
| 多 seed 聚合错误 | 缺 seed、异常值、不同 run 数 | 显式样本数、均值/方差/CI 规则 |
| 容差后验调整 | 结果生成后修改 tolerance | policy/version 可追踪并拒绝隐式变化 |
| 单位/比例错配 | 0.94 vs 94%、ms vs s | 单位转换可审计或标记不可比 |
| 数学工具与 LLM 冲突 | SymPy/规则结果不同于解释 | 分栏保留，确定性结果不被覆盖 |
| artifact 缺失 | 日志、checkpoint 或 metric 来源不存在 | `inconclusive`/`failed`，不伪造证据 |
| 公式源丢失 | P2 `not_available/partial` | 降低 math coverage，不让 LLM 重建后冒充原文 |
| 来源版本错配 | paper/source/bundle/run hash 不一致 | 拒绝比较并报告 provenance 错误 |
| 报告重建 | 仅使用版本化输入重新渲染 | JSON/Markdown 内容确定且引用完整 |
| P0–P3 回归 | 历史测试和公共 API | 全部继续通过 |

## 9. 风险

| 风险 | 缓解 |
|---|---|
| 指标同名异义 | dataset/split/procedure 组合身份 |
| 单次 run 过度结论 | 明确禁止统计显著性声明 |
| 容差后验调整 | 比较前冻结 policy |
| 数学 LLM 幻觉 | 确定性工具结果与 LLM 解释分栏 |
| 论文报告不完整 | `inconclusive/not_comparable` 一等状态 |
| 总分误导 | 强制分项、coverage 和关键 claim 展示 |

## 10. 准入与里程碑提升

P4 转为 `Ready` 前需要 P2 equation/claim golden fixtures 和 P3 structured
metric/run fixtures。里程碑分为：

- **P4-A（可安全停止）**：identity、unit/scale、metric、equation 和 tolerance
  规范化器，加上确定性合成测试；
- **P4-B**：MathChecker 和 `MathCheckReport`，明确 coverage/unknown；
- **P4-C（完整阶段）**：Verifier、可重建 JSON/Markdown 报告、CLI/API 和外部抽查。

P4-A/P4-B 可以供内部评审，但只有 P4-C 通过全部阶段门后才能把 P4 标为
`Complete`。报告渲染失败不得覆盖已经生成的结构化 verification artifact。

## 11. 完成定义

1. claim/metric/equation/report schema 稳定，并通过 P2/P3 consumer fixtures；
2. MathChecker 输出可追踪 issue/coverage 且不伪称形式化证明或补造原文公式；
3. Verifier 按 dataset/split/metric/protocol 对齐；
4. verdict 和 tolerance 为确定性规则；
5. 多 seed/单 run/不可比/失败路径均有测试；
6. JSON/Markdown 报告可从 artifacts 重建；
7. Python API、CLI、文档和示例齐全；
8. P0–P3 回归、质量和构建全部通过。

## 12. P5 交接

P5 持久化版本化 `VerificationReport` 和 claim/evidence/run 关系，但不能重算或更改 P4 verdict。图数据库中的结论必须引用报告 ID、schema version 和 artifact hash。
