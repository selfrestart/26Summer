# P8 实施规划 — Evaluation, Observability, and Release Evidence

> **状态**：`Planned`（规划完成，尚未实现）
>
> **前置条件**：P1–P7 稳定产物、服务和策略
>
> **核心输出**：benchmark suite、统一 telemetry、质量 scorecard、发布门

## 1. 阶段目标

P8 回答三个问题：系统输出是否正确、一次运行发生了什么、版本是否可以发布。它统一离线 benchmark、线上 trace/metrics/log/cost 和 CI 回归证据，但不使用单一总分掩盖各阶段缺陷。

## 2. 评测层次

| 能力 | 数据集/fixture | 指标示例 |
|---|---|---|
| P1 解析/阅读 | 标注章节和 Paper QA | section F1、answer correctness、citation coverage |
| P2 方法抽取 | 标注 method/config/evidence | field precision/recall、evidence exactness、unsupported rate |
| P3 代码/实验 | 固定小型方法 | compile/test/pass、sandbox violations、reproducible run rate |
| P4 验证 | 合成/真实 claims-runs | alignment accuracy、verdict accuracy、calibration |
| P5 检索/综述 | query relevance/citation set | recall@k、graph correctness、citation precision |
| P6 平台 | API/MCP/UI journeys | success、latency、SSE recovery、accessibility |
| P7 安全 | attack corpus | block rate、false positive、policy bypass rate |

LLM-as-Judge 只能作为辅助指标，必须固定 judge 配置、记录 prompt/version，并配有人类标注子集和确定性指标。

P8 不从零开始收集数据。P1–P7 每个阶段完成时必须留下小型 seed corpus：正常、
关键失败、边界和回归 fixture，以及指标实现和人工标注说明。P8 负责统一 runner、
manifest、统计和历史基线；缺少 seed corpus 的上游阶段不能仅靠临时生成样本补票。

## 3. Benchmark manifest

每次评测记录：dataset/version/hash、task IDs、model/provider/base URL class、prompt version、code commit、config、seed、environment、start/end、raw outputs、metric implementation version 和费用。

含版权或私有论文的数据不能直接提交全文；使用许可允许的 fixture、hash 和获取说明。

比较只在 manifest 的可比维度满足时进行。dataset/schema/metric implementation、
provider/model class、prompt 或执行环境发生实质变化时，结果标记为新基线或
`not_comparable`，不能用百分比回归掩盖配置漂移。非确定性模型至少报告样本数、
重复运行策略和不确定性；单次运行不用于设置稳定发布阈值。

## 4. 可观测性

### Traces

统一 OpenTelemetry hierarchy：request/job → pipeline → agent run → ReAct step → provider/tool/backend。跨 API、worker、container 传播 trace ID。

### Metrics

- request/job success、latency、queue depth；
- provider calls、tokens、cost、rate limits；
- agent steps、repair、tool errors；
- sandbox build/run/timeout/resource；
- evidence coverage、verification verdict；
- guardrail allow/deny/approval；
- artifact/storage/index operations。

### Logs

结构化 JSON，包含 trace/job/run ID；默认 redact secret/PII，不记录完整论文、prompt 或生成代码。高基数内容不作为 metric labels。

## 5. 成本和预算

按 provider/model/task/job/tenant 统计 token 和估算成本，支持 warning/hard budget。价格表必须版本化；未知价格不得按 0 假装免费，而应标为 unknown。

## 6. 发布 scorecard

每次候选版本生成：

- 工程质量：tests/type/lint/build/security；
- 各阶段 benchmark 指标与置信区间；
- 相对基线回归；
- 性能/成本预算；
- 已知限制和豁免；
- artifact/报告链接。

不同能力独立设置 threshold；不得用平均总分抵消安全或核心正确性失败。

阈值/SLO 不在没有数据时预填。每项 release gate 记录 metric owner、baseline
window、最小样本量、允许回归、置信规则、硬阻断/告警级别和例外期限。性能、成本
和质量可以分别阻断；未知价格、不可比较结果或 telemetry 缺失不能按 0/成功处理。

## 7. 工作包

### P8.0 Evaluation schema/runner

实现 task/manifest/result/metric contracts、缓存和可复现实验目录。

### P8.1 P1/P2 benchmarks

先覆盖解析、Paper QA、方法字段和 evidence grounding。

### P8.2 P3/P4 benchmarks

覆盖代码可运行、sandbox、metric alignment 和 verdict。

### P8.3 P5/P6/P7 benchmarks

覆盖检索/图/引用、API/MCP/UI journeys 和 attack corpus。

### P8.4 Telemetry

接入 OTel、metrics/log correlation、Jaeger/local collector 和 redaction。

### P8.5 Cost/release gates

实现预算、baseline comparison、scorecard 和 CI artifact。

### P8.6 文档和结果治理

记录 benchmark 限制、数据许可、运行命令、历史结果和不可比较版本。

## 8. 测试矩阵

| 风险 | 必测场景 |
|---|---|
| benchmark 泄漏 | train/dev/test 与 prompt 隔离 |
| 不可复现 | seed/config/hash/env 完整 |
| judge 漂移 | 固定版本 + 人工子集 |
| telemetry 泄密 | redaction 和敏感 fixture |
| 高基数指标 | label allowlist |
| 成本错误 | usage/价格版本/unknown handling |
| 回归误报 | 置信区间、最小样本、不可比标记 |
| 总分掩盖风险 | security/core threshold 独立阻断 |
| seed corpus 缺失 | 上游阶段验收时强制保存 fixture/标注/metric version |
| 配置漂移伪回归 | manifest comparability 检查，新基线与回归分开 |
| 单次随机结果 | 重复运行/样本量/不确定性要求 |

## 9. 准入与里程碑提升

P8 转为 `Ready` 前，P1–P7 必须各提供 seed corpus 或明确不可评测原因，P7 的
redaction/security invariants 必须可供 telemetry 和 benchmark runner 复用。

- **P8-A（可安全停止）**：evaluation manifest/runner、comparability、缓存、
  seed corpus registry；
- **P8-B**：分阶段 benchmark 与 OTel trace/metrics/log correlation；
- **P8-C（完整阶段）**：成本预算、历史基线、scorecard、阈值/例外和 CI 发布门。

P8-A/P8-B 的结果可用于诊断，但只有 P8-C 才能宣称存在统一发布证据体系。

## 10. 完成定义

1. P1–P7 每个已实现能力都有版本化 seed corpus 和适当 benchmark/E2E 指标；
2. benchmark manifest 足以重建一次运行；
3. OTel trace 覆盖 request→job→agent→provider/tool/backend；
4. logs/metrics/traces 不泄漏 secrets 和正文；
5. token/cost/budget 计算可验证且价格版本化；
6. CI 只在 manifest 可比时生成相对基线，并输出 scorecard 和发布 artifact；
7. 核心正确性/安全阈值可独立阻断发布；
8. 结果文档明确数据、模型、限制和不可比较项；
9. 全仓回归、构建、安全和端到端门全部通过。

## 11. 路线图闭环

P8 完成后，ReproForge 才具备从论文输入、方法证据、代码实验、结果核验、知识沉淀、平台使用、安全治理到质量证明的完整工程闭环。此时仍不能将一次 benchmark 结果外推为所有学科、模型和论文上的普遍能力。
