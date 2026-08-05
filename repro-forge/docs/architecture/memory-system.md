# Memory System（P5+ 规划）

Working、Episodic（ChromaDB）和 Semantic（Neo4j）三阶记忆属于目标架构，
当前 P1 尚未实现持久化记忆或跨论文检索。P1 的状态仅保存在当前
`PaperReader` 运行的 `AgentTrace`、`reading_trace` 和 `PaperNote` 中。

不要把本页的存储配置当作当前可用服务。P1 的领域模型和边界见
[P1 技术参考](../P1-TECHNICAL-REFERENCE.md)。
