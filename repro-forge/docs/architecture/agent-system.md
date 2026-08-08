# Agent System（P1-P3 已完成，P4-P6 规划）

P1 实现 `PaperReader`，它复用 P0 `BaseAgent` 的 ReAct 生命周期，并
提供 `list_sections`、`read_section`、`search_paper` 三个论文阅读工具。

P2 已实现 `Methodologist`。P3 已实现 fail-closed `CodeForger` 和负责
dry-run/local fixture/Docker 路由的 `Experimentor`；Docker 已通过真实安全 smoke。
MathChecker、Verifier 以及多 Agent 编排尚未实现。本页同时记录当前能力和目标职责边界。P1 实现见
[P1 设计论证](../P1-DESIGN-RATIONALE.md) 和
[P1 技术参考](../P1-TECHNICAL-REFERENCE.md)。

P2 已实现 Methodologist：从 `Paper` 和可选 `PaperNote` 抽取算法、架构、
训练配置和评价协议，并为关键声明绑定章节/页码/quote 证据。P2 本身不包含代码
生成、实验执行或知识图谱写入；P3 通过公开 `MethodAnalysis` 消费这些事实。任务拆分和完成定义见
[P2 实施规划](../P2-IMPLEMENTATION-PLAN.md)。

后续职责按阶段固定：P3 已交付 CodeForger/Experimentor，P4 交付
MathChecker/Verifier，P5 交付 SurveyScribe，P6 再通过统一 application service
组织跨能力 job 和对外接口。P0 中的 `AgentType` 枚举值只是协议预留，不证明
对应 Agent 类或编排器已经实现。
