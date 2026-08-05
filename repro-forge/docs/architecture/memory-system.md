# Memory System（P5 规划）

P5 将实现三层状态/记忆和一个版本化事实源：

| 层 | 计划后端 | 职责 |
|---|---|---|
| Working | Agent context | 当前任务临时状态 |
| Artifact repository | 本地文件 + metadata | 保存 P1-P4 JSON、bundle、run、report 的版本与 hash |
| Episodic | ChromaDB | 对 artifact chunks 建立可重建的语义索引 |
| Semantic | Neo4j；测试用 NetworkX | 建立论文、方法、数据集、指标、run 和 evidence 关系 |

Artifact repository 是事实源；Chroma/Neo4j 是可重建索引。向量相似度不能
被当作事实证据，所有结果必须回到版本化 artifact/evidence。

当前 P1 只在单次运行中保留 `AgentTrace`、`reading_trace` 和 `PaperNote`，
没有跨会话记忆。存储 API、迁移、备份、删除和一致性策略见
[P5 实施规划](../P5-IMPLEMENTATION-PLAN.md)。
