# MCP API（P6 规划）

当前没有可导入的 MCP Server/Client API。P1 使用进程内 PaperReader 工具，
相关 Provider 和 Pipeline 契约见 [Core API](core.md)。`repro_forge.mcp` 目前是
空命名空间，安装 MCP 相关依赖或启动 `compose.future.yml` 不会创建 MCP Server。

P6 计划让 CLI、FastAPI 和 MCP 共享同一个 application service。首批 MCP 面包括：

- tools：论文解析/阅读、P2 方法分析、P3 bundle/experiment、P4 验证、P5 检索/综述；
- resources：paper、analysis、run、report 和 graph view 的稳定 URI；
- stdio transport、capability negotiation、timeout/cancellation 和 structured error；
- tool schema 与 application DTO 共源，并由 contract tests 防止协议漂移。

P7 才会补齐远程部署所需的身份、授权、tool policy 和审计。因此 P6 完成前，
本页不能提供可运行的 MCP 命令；P7 完成前，也不能把 MCP 暴露为公网任意命令
入口。详细完成定义见 [P6 实施规划](../P6-IMPLEMENTATION-PLAN.md)。
