# P1 开发环境与配置

> **状态**：✅ P0 基础设施与 P1 论文阅读链路已完成
>
> 本页提供开发者入口；完整的 API、环境变量、CLI 和故障排查见
> [P1 Technical Reference](../P1-TECHNICAL-REFERENCE.md)。P0 的工程决策见
> [P0 Technical Reference](../P0-TECHNICAL-REFERENCE.md)。

## P1 交付范围

P1 在 P0 的 `BaseAgent`、Provider 契约、uv/ruff/mypy/pytest 工具链之上，
实现了：

- `PDFParser`：本地 PDF 文本、元数据、章节和页码抽取；
- `ArxivClient`：搜索、元数据查询、现代/旧式 ID 归一化和 PDF 下载；
- `Paper` / `Section` / `PaperChunk` / `PaperNote` 领域模型；
- `PaperChunker`：token-aware、章节优先的上下文切分；
- `PaperReader`：ReAct 阅读循环、章节读取、全文搜索和最终 JSON 总结；
- `OpenAIProvider`：OpenAI、DeepSeek 和其他兼容 endpoint；
- `PaperPipeline` 与 `repro-forge` CLI。

Methodologist、代码生成、Docker 实验、Verifier、Memory、Knowledge Graph、
MCP、FastAPI、前端、Guardrails 和 Evaluation 仍是 P2+ 规划。

## 先决条件

- Python 3.11、3.12 或 3.13；仓库的 `.python-version` 当前选择 3.13；
- [uv](https://docs.astral.sh/uv/)；
- 远程阅读需要 OpenAI 或 DeepSeek key；离线示例和测试不需要 key。

## 安装

```powershell
uv sync --locked --group dev
uv run repro-forge --version
uv run repro-forge capabilities
```

按需安装集成：

```powershell
uv sync --locked --extra pdf --group dev
uv sync --locked --extra arxiv --group dev
uv sync --locked --extra openai --group dev
```

这些 extra 是独立的：只运行 `read-json` 或单元测试时不需要安装 PDF、arXiv
或 OpenAI SDK。

## 环境变量

复制 `.env.example` 为 `.env`，或直接在 PowerShell 中设置：

```powershell
$env:DEEPSEEK_API_KEY = "..."
$env:DEEPSEEK_MODEL = "deepseek-chat"
uv run repro-forge read-pdf paper.pdf --output note.json
```

变量优先级为显式 Provider 参数，其次 `OPENAI_*`，再其次 `DEEPSEEK_*`。CLI
从当前目录 `.env` 加载配置且不覆盖已有环境变量。无 key 只允许 localhost、
loopback 或私有网段的兼容 endpoint：

```powershell
$env:OPENAI_BASE_URL = "http://localhost:11434/v1"
$env:OPENAI_MODEL = "llama3"
uv run repro-forge read-pdf paper.pdf
```

不要把真实 key 写入 `.env.example`、代码或提交记录。

## 离线开发路径

无需 PDF 和 API key 即可运行确定性示例：

```powershell
uv run python examples/read_paper.py
uv run pytest -q
```

测试通过 `FakeLLMProvider` 注入响应，不访问外部模型。需要真实 PDF 时安装
`pdf` extra；需要 arXiv 时再安装 `arxiv` extra。

## Python API 最小用法

```python
from repro_forge.paper import PaperPipeline
from repro_forge.providers import OpenAIProvider

pipeline = PaperPipeline(provider=OpenAIProvider())
note = await pipeline.read_pdf("paper.pdf")
print(note.summary())
```

如果已经有结构化 `Paper`，使用 `await pipeline.read(paper)`；arXiv 完整链路
使用 `await pipeline.read_arxiv("1706.03762", "data/papers")`。

## Windows 说明

项目的主要验证命令使用 `uv run`，不依赖 GNU `make`。如果本机安装了 make，
也可以使用仓库 Makefile；Windows 下推荐显式执行 `uv run pytest`、`uv run ruff`
和 `uv run mypy`，以确保使用项目解释器。

## 下一步阅读

- [P1 Design Rationale](../P1-DESIGN-RATIONALE.md)：为什么这样设计；
- [P1 Technical Reference](../P1-TECHNICAL-REFERENCE.md)：模块、参数、命令和故障排查；
- [Architecture Overview](../architecture/overview.md)：当前 P1 与 P2+ 的边界；
- [Testing](testing.md)：测试层次和验证基线。
