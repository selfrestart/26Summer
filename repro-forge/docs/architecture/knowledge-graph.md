# Knowledge Graph（P5 规划）

P5 计划把 P1-P4 的稳定产物映射为带 provenance 的研究图谱。

主要节点：`Paper`、`Method`、`Algorithm`、`ArchitectureComponent`、`Dataset`、
`Metric`、`Claim`、`ExperimentRun`、`VerificationReport`、`Evidence`。

主要关系：`PROPOSES`、`USES`、`EVALUATED_ON`、`REPORTS`、`OBSERVES`、
`VERIFIES`、`SUPPORTED_BY`、`CITES` 和 `DERIVED_FROM`。

每个节点和关系必须能回到 artifact ID、schema version 和 evidence。P2 不写
知识图谱，只输出 `MethodAnalysis`；P5 才负责幂等 upsert、NetworkX/Neo4j
adapter、migration 和跨论文查询。详见
[P5 实施规划](../P5-IMPLEMENTATION-PLAN.md)。
