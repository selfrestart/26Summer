# Agent System（P2+ 规划）

P1 当前只实现 `PaperReader`，它复用 P0 `BaseAgent` 的 ReAct 生命周期，并
提供 `list_sections`、`read_section`、`search_paper` 三个论文阅读工具。

Methodologist、MathChecker、CodeForger、Experimentor 和 Verifier 以及多 Agent
编排尚未实现。本页记录目标职责边界，不是可运行 API。当前实现请先看
[P1 设计论证](../P1-DESIGN-RATIONALE.md) 和
[P1 技术参考](../P1-TECHNICAL-REFERENCE.md)。
