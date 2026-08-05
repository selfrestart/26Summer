# Agent System（P1 已实现，P2–P6 演进规划）

P1 当前只实现 `PaperReader`，它复用 P0 `BaseAgent` 的 ReAct 生命周期，并
提供 `list_sections`、`read_section`、`search_paper` 三个论文阅读工具。

Methodologist、MathChecker、CodeForger、Experimentor 和 Verifier 以及多 Agent
编排尚未实现。本页记录目标职责边界，不是可运行 API。当前实现请先看
[P1 设计论证](../P1-DESIGN-RATIONALE.md) 和
[P1 技术参考](../P1-TECHNICAL-REFERENCE.md)。

下一步只实现 Methodologist：从 `Paper` 和可选 `PaperNote` 抽取算法、架构、
训练配置和评价协议，并为关键声明绑定章节/页码/quote 证据。P2 不包含代码
生成、实验执行或知识图谱写入。任务拆分和完成定义见
[P2 实施规划](../P2-IMPLEMENTATION-PLAN.md)。

后续职责按阶段固定：P3 交付 CodeForger/Experimentor，P4 交付
MathChecker/Verifier，P5 交付 SurveyScribe，P6 再通过统一 application service
组织跨能力 job 和对外接口。P0 中的 `AgentType` 枚举值只是协议预留，不证明
对应 Agent 类或编排器已经实现。
