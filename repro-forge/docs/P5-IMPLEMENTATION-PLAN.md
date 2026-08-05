# P5 实施规划 — Memory, Knowledge Graph, and Survey Synthesis

> **状态**：`Planned`（规划完成，尚未实现）
>
> **前置输入**：P1–P4 的版本化领域产物
>
> **核心输出**：长期记录、研究知识图谱、`SurveyReport`

## 1. 阶段目标

P5 将一次性运行产物转化为跨会话、跨论文可检索的研究知识。它先建立统一 repository/provenance 层，再分别实现语义检索、图关系和引用约束的综述生成。

## 2. 存储分层

| 层 | 后端计划 | 存储内容 | 查询方式 |
|---|---|---|---|
| Working | 当前 Agent context | 当前任务临时状态 | 直接访问 |
| Artifact repository | 本地文件/SQLite metadata | JSON、报告、bundle、run manifests | ID/hash |
| Episodic | ChromaDB | note/analysis/run/report chunks | 向量检索 |
| Semantic | Neo4j；测试用 NetworkX | 论文、方法、数据集、指标、运行、证据关系 | 图查询 |

ChromaDB 不是事实数据库；向量命中只用于召回，最终结论要回到版本化 artifact/evidence。

## 3. 统一身份和 provenance

所有实体使用稳定 ID：

- paper ID：优先 arXiv/DOI，否则内容 hash；
- artifact ID：schema + canonical JSON hash；
- method ID：paper ID + method local ID；
- run ID：P3 run ID + bundle hash；
- claim/report ID：来源 artifact + local ID。

每次 upsert 记录 schema version、producer version、created_at、source hash 和父 artifact IDs。相同 hash 应幂等，不重复创建节点。

### 数据分类、保留与删除

P5 在没有 P7 多租户平台的情况下仍需具备本地数据治理：

- `public-metadata`、`redistributable-content`、`restricted-local`、`secret/credential`
  分级；secret 永不进入 artifact repository；
- 无再分发许可的论文全文只保存本地引用/hash/获取说明，不进入仓库 fixture、
  survey 导出或远程 telemetry；
- artifact 删除采用 tombstone + 可审计 GC，先从查询面隐藏，再清理可重建索引；
- backup/restore 必须保留分类和删除状态，不能通过恢复旧备份让已删除内容重新可见；
- P7 完成前 repository 是单用户受信存储，不宣称 tenant isolation。

## 4. Knowledge Graph 模型

### 节点

`Paper`、`Method`、`Algorithm`、`ArchitectureComponent`、`Dataset`、`Metric`、`Claim`、`ExperimentRun`、`VerificationReport`、`Evidence`、`Author`、`Venue`。

### 关系

`PROPOSES`、`USES`、`EVALUATED_ON`、`REPORTS`、`OBSERVES`、`VERIFIES`、`SUPPORTED_BY`、`CITES`、`DERIVED_FROM`、`COMPARED_WITH`。

每条关系保留 provenance；禁止创建无法回到 artifact/evidence 的事实边。

## 5. Memory API

计划公共接口：

```python
repository.put(artifact) -> ArtifactRef
repository.get(artifact_id, version=None)
memory.index(artifact_ref)
memory.search(query, filters, top_k)
graph.upsert(artifact_ref)
graph.query(...)
```

需要定义删除/重建、schema migration、embedding model version 和索引一致性策略。测试优先使用临时 repository、in-memory Chroma/adapter 和 NetworkX。

索引写入使用 durable index task/outbox 或等价状态记录：artifact 先提交到事实源，
再异步更新 Chroma/Neo4j。每个 index task 包含 artifact/version/index schema/
embedding version、attempt 和 last error；reconciler 能发现 missing/stale/orphan
索引并幂等修复。查询必须能区分“无结果”和“索引不可用/尚未同步”。

## 6. SurveyScribe

SurveyScribe 接收论文集合或查询计划：

1. 检索相关 artifact；
2. 通过图关系组织方法族、数据集和演进；
3. 生成带 citation ID 的大纲；
4. 逐段生成并验证每个 claim 的引用；
5. 输出 `SurveyReport`、bibliography 和 unresolved claims。

任何无法绑定 evidence/artifact 的陈述必须删除或标记为 synthesis/inference。P5 不使用 LLM-as-Judge 自行宣布综述正确；完整质量评测属于 P8。

## 7. 工作包

### P5.0 Artifact repository 和 schema versioning

实现 canonical JSON、hash、metadata、幂等 put/get/list 和 migration 测试。

### P5.1 Episodic memory

实现 chunk/index/search、metadata filters、embedding version 和 rebuild。

### P5.2 Knowledge Graph

先 NetworkX adapter + contract tests，再 Neo4j adapter + container integration。

### P5.3 跨存储一致性

定义 repository 为事实源；Chroma/Neo4j 是可重建索引。实现 index task/outbox、
reconciler、staleness 状态和 full rebuild。失败时不得出现只有索引没有 artifact
的状态，也不能把索引故障伪装成空搜索结果。

### P5.4 SurveyScribe

实现 outline、citation binding、claim validation、Markdown/BibTeX 输出。

### P5.5 CLI/导入导出

计划命令：

```powershell
repro-forge index-artifact report.json
repro-forge search "attention training recipe"
repro-forge write-survey --query "efficient transformers" --output survey.md
```

### P5.6 文档与验证

补存储运维、备份恢复、migration、Neo4j/Chroma compose smoke 和引用完整性测试。

## 8. 测试矩阵

| 风险 | 必测场景 |
|---|---|
| 重复 ingest | 相同 hash 幂等 |
| partial failure | repository 成功、索引失败后可重建 |
| schema migration | 旧 fixture 可读取/迁移 |
| embedding drift | model version 变化触发 rebuild |
| 图边无来源 | 无 provenance 的关系拒绝 |
| 删除一致性 | artifact tombstone/索引清理 |
| 备份恢复删除回流 | tombstone/分类在 restore 后仍生效 |
| 无再分发许可内容 | 导出只含 hash/引用，不含正文 |
| 索引未同步 | 查询返回 degraded/stale 状态而非“无结果” |
| orphan/stale index | reconciler 幂等清理/重建 |
| survey 错引 | claim-citation-evidence 自动校验 |
| 数据库不可用 | 清晰错误，不伪装空结果 |

## 9. 非目标

- 不提供公共 HTTP/MCP/UI；属于 P6；
- 不建立多租户权限；属于 P7；
- 不完成 benchmark 平台；属于 P8；
- 不把向量相似度当作事实真值；
- 不自动抓取未授权全文或绕过访问控制。

## 10. 准入与里程碑提升

P5 转为 `Ready` 前必须收齐 P1–P4 各至少一个版本化 artifact fixture，并完成
canonical JSON/hash 与许可分类评审。里程碑分为：

- **P5-A（可安全停止）**：artifact repository、schema migration、分类、
  tombstone、backup/restore；此时还没有“智能记忆”；
- **P5-B**：Chroma/NetworkX/Neo4j adapter、index task/reconciler 和 rebuild；
- **P5-C（完整阶段）**：SurveyScribe、引用校验、导入导出和运维文档。

P5-A 可以作为事实源被后续内部开发复用，但索引或 SurveyScribe 未完成时 P5
仍为 `In Progress`，不得把向量搜索描述为已交付记忆系统。

## 11. 完成定义

1. artifact repository 是可版本化、幂等、可迁移且有分类/删除语义的事实源；
2. Chroma/Neo4j 索引可完全重建，并能报告 stale/degraded 状态；
3. NetworkX/Neo4j 通过同一 contract tests；
4. 图节点/边均有 provenance；
5. SurveyReport 的事实声明均有引用或明确 inference；
6. 备份、恢复、删除和故障路径有文档与测试；
7. P0–P4 回归、质量、构建和容器 smoke 通过。
