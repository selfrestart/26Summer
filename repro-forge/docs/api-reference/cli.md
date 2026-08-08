# CLI API

发行包名和命令名是 `repro-forge`，Python import 包名是 `repro_forge`。

## Commands

```text
repro-forge --version
repro-forge capabilities
repro-forge read-pdf <path> [--output <note.json>]
repro-forge read-json <paper.json> [--output <note.json>]
repro-forge analyze-pdf <path> [--paper-note <note.json>] [--read-first]
repro-forge analyze-json <paper.json> [--paper-note <note.json>]
repro-forge generate-code <methodology.json> --output <bundle.json> [--force]
repro-forge run-experiment <bundle.json> [--backend dryrun|docker] [--output <run.json>] [--force]
repro-forge run-fixture <fixture-id> [--backend local-subprocess|docker] [--output <run.json>] [--force]
```

| 命令 | 前置条件 | 输出 |
|---|---|---|
| `--version` | 核心安装 | 版本字符串 |
| `capabilities` | 核心安装 | P1-P3 能力清单和阶段门 |
| `read-pdf` | `pdf` + `openai` extra；远程 key 或本地 endpoint | `PaperNote` JSON |
| `read-json` | `openai` extra；有效 `Paper` JSON；远程 key 或本地 endpoint | `PaperNote` JSON |
| `analyze-pdf` | `pdf` + `openai` extra；可选 P1 note | `MethodAnalysis` JSON |
| `analyze-json` | `openai` extra；有效 `Paper` JSON；可选 P1 note | `MethodAnalysis` JSON |
| `generate-code` | `openai` extra、provider 配置、有效 `MethodAnalysis` | `ReproductionBundle` JSON |
| `run-experiment` | 有效 `ReproductionBundle`；Docker 另需 extra/daemon/精确 digest | `ExperimentRun` JSON |
| `run-fixture` | 仓库注册 fixture ID；Docker 另需相同门 | `ExperimentRun` JSON |

## Configuration loading

CLI 在当前工作目录读取 `.env`，并使用 `override=False`。环境变量优先于
`.env`。远程 endpoint 缺少 `OPENAI_API_KEY`/`DEEPSEEK_API_KEY` 时会拒绝；
localhost、loopback 和私有网段的兼容 endpoint 可以 keyless 运行。

## Output contract

没有 `--output` 时 JSON 写到 stdout；指定 `--output` 时以 UTF-8 写入文件，
使用 `ensure_ascii=False` 和两格缩进。模型/运行输出使用同目录临时文件加原子
replace，父目录按需创建；已有文件默认拒绝覆盖，只有 `--force` 才覆盖。

P3 run 成功返回退出码 `0`；`blocked`、`failed`、`timeout` 或 `cancelled` 返回
`3`。这使 shell/CI 不会把结构化失败 JSON 误判为命令成功。

## CLI 与 Python API 的边界

CLI 没有独立的 arXiv search 子命令，也没有启动 FastAPI 服务。arXiv
搜索、下载和 `read_arxiv` 通过 Python API 使用；HTTP API 属于 P6 规划。

`local-subprocess` 不是 `run-experiment` 可选项：它只接受 `run-fixture` 的维护者
fixture ID，永远不执行 bundle 或用户提供的代码。
