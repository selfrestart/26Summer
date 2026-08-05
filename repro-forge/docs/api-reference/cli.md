# CLI API

发行包名和命令名是 `repro-forge`，Python import 包名是 `repro_forge`。

## Commands

```text
repro-forge --version
repro-forge capabilities
repro-forge read-pdf <path> [--output <note.json>]
repro-forge read-json <paper.json> [--output <note.json>]
```

| 命令 | 前置条件 | 输出 |
|---|---|---|
| `--version` | 核心安装 | 版本字符串 |
| `capabilities` | 核心安装 | P1 能力清单 |
| `read-pdf` | `pdf` + `openai` extra；远程 key 或本地 endpoint | `PaperNote` JSON |
| `read-json` | `openai` extra；有效 `Paper` JSON；远程 key 或本地 endpoint | `PaperNote` JSON |

## Configuration loading

CLI 在当前工作目录读取 `.env`，并使用 `override=False`。环境变量优先于
`.env`。远程 endpoint 缺少 `OPENAI_API_KEY`/`DEEPSEEK_API_KEY` 时会拒绝；
localhost、loopback 和私有网段的兼容 endpoint 可以 keyless 运行。

## Output contract

没有 `--output` 时 JSON 写到 stdout；指定 `--output` 时以 UTF-8 写入文件，
使用 `ensure_ascii=False` 和两格缩进。输出目录必须提前存在。

## CLI 与 Python API 的边界

P1 CLI 没有独立的 arXiv search 子命令，也没有启动 FastAPI 服务。arXiv
搜索、下载和 `read_arxiv` 通过 Python API 使用；HTTP API 属于 P6 规划。
