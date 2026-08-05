# Tools API（P1 范围）

PaperReader 当前内置三个进程内只读工具：`list_sections`、`read_section` 和
`search_paper`。它们由 `repro_forge.agents.paper_reader` 管理，不是 MCP 工具
注册表。参数、错误和 chunk 行为见 [P1 Technical Reference](../P1-TECHNICAL-REFERENCE.md)。
