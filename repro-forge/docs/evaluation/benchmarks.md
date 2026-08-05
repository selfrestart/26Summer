# Evaluation Benchmarks（P8 规划）

P8 将为每个已实现阶段建立独立 benchmark，而不是只给系统一个总分：

| 能力 | 计划指标 |
|---|---|
| 论文解析/阅读 | section F1、Paper QA、citation coverage |
| 方法抽取 | field precision/recall、evidence exactness、unsupported rate |
| 代码/实验 | compile/test/pass、sandbox violation、reproducible run rate |
| 结果核验 | claim alignment、verdict accuracy、calibration |
| 检索/综述 | recall@k、graph correctness、citation precision |
| 平台/安全 | API/MCP/UI journey、attack block/false-positive rate |

每次运行记录 dataset/model/prompt/code/config/seed/environment/hash/cost。
LLM-as-Judge 只能作为辅助指标，必须配有人类标注子集和确定性指标。完整计划见
[P8 实施规划](../P8-IMPLEMENTATION-PLAN.md)。
