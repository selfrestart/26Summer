# Evaluation Results（当前工程基线）

当前尚未实现 P8 benchmark 平台，也没有可宣称的论文问答、方法抽取或复现
质量排行榜。现有结果只是 P0-P2 软件工程基线：

| 检查 | 当前记录 |
|---|---|
| pytest | 175 passed（2026-08-06） |
| 总体覆盖率 | 86.34% |
| Ruff | lint/format 通过 |
| mypy | 37 个源文件通过 |
| MkDocs/build/wheel smoke | 通过 |
| DeepSeek P2 smoke | `deepseek-chat` 通过；未记录响应正文或密钥 |

这些结果不能外推为模型准确率或论文复现成功率。P8 将建立版本化 benchmark
manifest、OpenTelemetry、成本统计和发布 scorecard；见
[P8 实施规划](../P8-IMPLEMENTATION-PLAN.md)。
