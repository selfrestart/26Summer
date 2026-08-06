# Tools API（P1 范围）

PaperReader 当前内置三个进程内只读工具：`list_sections`、`read_section` 和
`search_paper`。它们由 `repro_forge.agents.paper_reader` 管理，不是 MCP 工具
注册表。参数、错误和 chunk 行为见 [P1 Technical Reference](../P1-TECHNICAL-REFERENCE.md)。

后续阶段按风险和领域边界扩展工具，而不是提前建立一个无约束的全局注册表：

| 阶段 | 工具边界 | 状态 |
|------|----------|------|
| P1 | 论文章节列举、读取和全文搜索 | 已实现，进程内只读 |
| P2 | `PaperEvidenceView` 只读 evidence view，支持方法学证据定位 | 已实现 |
| P3 | 生成文件、静态检查、dry-run 和受限 sandbox backend | 规划，必须满足最低安全门 |
| P4 | 公式、claim、metric 和 run artifact 查询 | 规划，默认只读 |
| P5 | artifact、向量索引、知识图谱和 survey 检索 | 规划，写入必须保留 provenance |
| P6 | 将稳定能力映射为 MCP tools/resources | 规划，共享 application service |
| P7 | 身份、权限、审批、策略和审计包装 | 规划，不能由 P6 绕过 |

P8 评测这些工具的成功率、延迟、错误和安全回归，但不再新增另一套工具协议。
