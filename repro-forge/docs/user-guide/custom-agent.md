# Custom Agents（P6 规划，P7 治理）

P1 暂未提供公开的 Agent 注册/编排 API。可扩展点目前是实现 `BaseProvider`、
注入 `PaperPipeline` 的 parser/reader，或继承 `BaseAgent` 供实验使用；完整
自定义 Agent 配置和多 Agent 编排属于后续阶段。

P2-P5 会先通过内部 Python API 验证各专项 Agent；P6 才计划通过统一
application service 和 MCP/API 暴露稳定扩展面。P7 将补充权限和工具策略，
因此在此之前不应允许不受信任的远程自定义 Agent 执行工具。
