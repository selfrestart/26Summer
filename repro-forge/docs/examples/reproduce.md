# Reproduce a Paper（P3 离线流程可运行，P4 规划）

P2 方法学抽取已实现，可运行示例见
[Methodology Analysis](../user-guide/methodology-analysis.md)。P3 可以从
`MethodAnalysis` 生成 `ReproductionBundle`，并通过 dry-run 验证而不执行代码：

```powershell
uv run repro-forge generate-code methodology.json --output bundle.json
uv run repro-forge run-experiment bundle.json --backend dryrun --output run.json
```

还可以用固定仓库 fixture 验证 runner 协议：

```powershell
uv run repro-forge run-fixture p3-cpu-smoke --output fixture-run.json
```

Docker backend 已完成 P3-C 真实安全验收；每个运行环境仍要求 daemon、已审查
精确镜像 digest 和同一 security smoke。P4 才会根据论文 claim 和
`ExperimentRun` 输出 `VerificationReport`，因此本页当前示例不宣称论文已复现。

详见 [P3 技术参考](../P3-TECHNICAL-REFERENCE.md) 和
[总体路线图](../ROADMAP.md)。
