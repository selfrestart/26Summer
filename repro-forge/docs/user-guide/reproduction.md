# Paper Reproduction（P3 已完成）

P2 已将 `Paper` 转换为带原文证据的 `MethodAnalysis`。P3 现在可以继续生成
`ReproductionBundle`、执行无代码运行的 dry-run，并运行维护者提供的固定 CPU
fixture。Docker backend 保持 fail closed，并已通过真实 digest-pinned security smoke。

## 1. 生成可审计 bundle

先使用 P2 CLI 生成方法学 JSON，再运行：

```powershell
uv run repro-forge generate-code methodology.json --output bundle.json
```

该命令需要已配置的 LLM provider。输出包含：

- 版本化文件、内容 hash 和 P2 evidence IDs；
- argv 形式的实验 entrypoint；
- 依赖、数据集、资源、网络和 artifact 声明；
- assumptions、unresolved、risk warnings 和 generation trace；
- 自动生成的 `reproforge-manifest.json` 与整体 manifest hash。

如果模型返回无效 JSON、引用未知 evidence、生成非法路径/代码，或一次受限 repair 后
仍无法通过静态校验，命令失败且不会写出一个可执行的“部分成功” bundle。

## 2. 安全预览，不执行代码

```powershell
uv run repro-forge run-experiment bundle.json `
  --backend dryrun `
  --output dryrun.json
```

`dryrun` 只 materialize、校验和清理。成功输出 `ExperimentRun(status="success")`；
它不安装依赖、不下载数据、不启动 Python entrypoint，也不代表模型结果正确。

## 3. 验证 runner 协议

```powershell
uv run repro-forge run-fixture p3-cpu-smoke `
  --backend local-subprocess `
  --output fixture-run.json
```

本地 runner 只接受仓库维护者注册的 fixture ID。它不能运行 bundle 代码、用户脚本
或调用者构造的 `FixtureSpec`。可用 fixture 及预期行为见
[P3 技术参考](../P3-TECHNICAL-REFERENCE.md)。

成功命令返回退出码 `0`；`blocked`、`failed`、`timeout` 或 `cancelled` 返回 `3`。
已有输出默认不会被覆盖；需要覆盖时显式传入 `--force`。

## 4. Docker（显式配置能力）

Docker 执行要求安装 optional extra、运行中的 daemon、已预拉取镜像，以及维护者审查
过的精确 digest：

```powershell
uv sync --locked --group dev --extra docker
$env:REPROFORGE_P3_PYTHON_CPU_IMAGE = 'repository@sha256:<reviewed-digest>'
uv run repro-forge run-experiment bundle.json --backend docker --output docker-run.json
```

后端不接受 mutable tag，不允许 bundle 指定镜像，也不会自动 pull。当前只支持
`offline` 网络策略、锁定依赖和无 `unresolved` 项的实验。缺少配置或违反策略时返回
结构化 `blocked` run，而不是降级到宿主执行。

!!! note "P3-C 已完成，运行环境仍需独立审查"

    P3-C 已在真实 daemon 和审查过的 digest 镜像上通过 security smoke。新的
    daemon、内核或镜像 digest 仍必须重跑同一验证；不要把 P0 包镜像 build 当作
    P3 sandbox 验证，也不要自动信任 mutable tag。

## 5. 如何读取 `ExperimentRun`

重点字段：

| 字段 | 含义 |
|---|---|
| `status` / `failure_code` | 运行事实和机器可读失败原因 |
| `events` | 有序状态、日志、metric、artifact、truncation/error 事件 |
| `stdout_tail` / `stderr_tail` | 有界日志 tail，不是可信指标 |
| `metrics` | 从版本化 JSONL 解析的 `ObservedMetric` |
| `artifacts` | allowlist 内输出的路径、大小、媒体类型和 SHA-256 |
| `environment` | Python/OS/package、bundle hash 和镜像 digest 快照 |

P3 不把 `ExperimentRun` 与论文 claim 自动比较。公式检查、dataset/split 对齐、误差
容忍度和“是否复现”结论属于 P4。

## 6. 相关文档

- [P2 方法学分析指南](methodology-analysis.md)
- [P3 设计论证](../P3-DESIGN-RATIONALE.md)
- [P3 技术参考](../P3-TECHNICAL-REFERENCE.md)
- [复现流水线架构](../architecture/reproduction-pipeline.md)
