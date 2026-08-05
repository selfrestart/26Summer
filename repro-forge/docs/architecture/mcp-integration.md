# MCP Integration（P6 规划）

P6 将在统一 application service 之上提供 MCP tools/resources。PaperReader 当前
的 `list_sections`、`read_section`、`search_paper` 是进程内方法，不是 MCP。

规划 tools 覆盖 parse/read/analyze/generate/run/verify/search/survey；大文件、
日志和报告通过 resource/artifact 引用返回。首个 transport 使用 stdio，并
支持 capability negotiation、timeout、cancellation 和 structured error。

MCP 不直接访问 Docker、Neo4j 或内部文件路径，也不是任意命令执行接口。
完整协议边界和与 FastAPI/前端的共享方式见
[P6 实施规划](../P6-IMPLEMENTATION-PLAN.md)。
