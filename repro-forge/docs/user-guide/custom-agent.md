# Custom Agents（P2+ 规划）

P1 暂未提供公开的 Agent 注册/编排 API。可扩展点目前是实现 `BaseProvider`、
注入 `PaperPipeline` 的 parser/reader，或继承 `BaseAgent` 供实验使用；完整
自定义 Agent 配置和多 Agent 编排属于后续阶段。
