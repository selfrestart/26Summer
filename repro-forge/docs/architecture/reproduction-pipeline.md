# Reproduction Pipeline（P2–P4 规划）

目标流程是 `Paper → Methodologist → CodeForger → Experimentor → Verifier →
Report`。P1 在此之前只完成可靠的 `PDF/arXiv → PaperReader → PaperNote` 阅读
事实层；方法抽取、代码生成、Docker 执行和指标对比尚未实现。

请使用 [P1 Paper Reading](../user-guide/paper-reading.md) 验证当前能力，
不要把 `compose.future.yml` 当作已交付的执行环境。

P2 将新增有证据归因的 `MethodAnalysis`，作为 P3 CodeForger 的稳定输入；
详细边界见 [P2 实施规划](../P2-IMPLEMENTATION-PLAN.md)。

P3 负责生成 `ReproductionBundle` 并在最小安全沙箱中产出 `ExperimentRun`；
P4 再对公式、论文 claims 和实验 metrics 做独立核验。分别参见
[P3 实施规划](../P3-IMPLEMENTATION-PLAN.md) 和
[P4 实施规划](../P4-IMPLEMENTATION-PLAN.md)。
