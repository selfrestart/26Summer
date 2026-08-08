# P1 技术参考 — Paper Reading Workflow

> 本文是 P1 的“怎么用、怎么排查、代码在哪里”参考。设计取舍见
> [P1-DESIGN-RATIONALE.md](P1-DESIGN-RATIONALE.md)；P0 基础设施见
> [P0-TECHNICAL-REFERENCE.md](P0-TECHNICAL-REFERENCE.md)。

如果需要按照“从哪一个文件开始读、每一步如何验证、怎样添加 parser/provider”
继续开发，请看 [P1 实现手册](P1-IMPLEMENTATION-GUIDE.md)。

## 1. 能力概览

P1 提供一条本地优先的论文阅读链路：

```text
PDF / arXiv ID → parse → chunk → read → PaperNote
```

| 能力 | Python API | CLI | 依赖 |
|---|---|---|---|
| 解析本地 PDF | `PaperPipeline.parse_pdf` / `PDFParser.parse` | `read-pdf` 间接调用 | `pdf` extra |
| arXiv 搜索/元数据 | `search_arxiv` / `fetch_arxiv` | 暂无独立子命令 | `arxiv` extra |
| arXiv 下载 | `download_arxiv` | 通过 Python API | `arxiv` extra |
| 阅读 `Paper` | `PaperPipeline.read` | `read-json` 间接调用 | Provider |
| PDF 阅读 | `read_pdf` | `read-pdf` | `pdf` + `openai` |
| 真实 LLM | `OpenAIProvider` | 自动构造 Provider | `openai` extra |
| 离线测试 | 注入 `FakeLLMProvider` | 示例脚本 | 无 key |

P1 本身不提供方法抽取、代码生成、实验执行、长期记忆、知识图谱、MCP、HTTP API
或前端服务。仓库后续已交付 P2，并正在实施 P3；对应能力应使用各阶段技术参考，
不能反向视为 P1 能力。

## 2. 目录与职责

```text
repro_forge/
├── core/types.py                # Agent、任务、消息、trace 的 P0 类型
├── core/base.py                 # BaseAgent ReAct 生命周期
├── providers/base.py            # LLMRequest/Response/ToolCall 契约
├── providers/openai_provider.py # OpenAI-compatible async provider
├── agents/paper_reader.py       # P1 PaperReader 与三个阅读工具
├── paper/schemas.py             # Paper、Section、Chunk、Note 模型
├── paper/chunker.py             # token-aware 分块
├── paper/parser/pdf_parser.py   # PyMuPDF 解析和章节检测
├── paper/parser/arxiv_api.py    # arXiv 搜索、归一化、下载
├── paper/pipeline.py            # parser/provider/reader 编排
└── cli.py                       # repro-forge 命令行入口
```

`reproduction/` 现包含 P3 实现；`memory/`、`knowledge/`、`mcp/`、`api/` 等目录
仍是后续阶段占位。P3 入口见 [P3 技术参考](P3-TECHNICAL-REFERENCE.md)。

## 3. 安装与可选 extras

```powershell
uv sync --locked --group dev
uv sync --locked --extra pdf --group dev
uv sync --locked --extra arxiv --group dev
uv sync --locked --extra openai --group dev
```

核心安装不强制包含 PyMuPDF、arXiv SDK 或 OpenAI SDK。`all` extra 面向未来完整演示，不代表 P1 会启用其中的 P2–P8 服务。

## 4. 环境变量

| 变量 | 默认值/优先级 | 用途 |
|---|---|---|
| `OPENAI_API_KEY` | 优先于 DeepSeek key | OpenAI 或兼容服务凭据 |
| `OPENAI_BASE_URL` | 无代码默认值 | OpenAI-compatible 地址 |
| `OPENAI_MODEL` | `gpt-4o` | OpenAI 分支模型 |
| `DEEPSEEK_API_KEY` | 无 OpenAI key 时使用 | 原生 DeepSeek 凭据 |
| `DEEPSEEK_BASE_URL` | `https://api.deepseek.com` | DeepSeek 地址 |
| `DEEPSEEK_MODEL` | `deepseek-chat` | DeepSeek 模型 |

CLI 从当前工作目录的 `.env` 加载这些值，且不覆盖已有环境变量。显式构造 `OpenAIProvider(api_key=..., base_url=..., model=...)` 时，构造参数优先。

```powershell
# DeepSeek
$env:DEEPSEEK_API_KEY = "..."
uv run repro-forge read-pdf paper.pdf --output note.json

# 无 key 的本地兼容 endpoint
$env:OPENAI_BASE_URL = "http://localhost:11434/v1"
$env:OPENAI_MODEL = "llama3"
uv run repro-forge read-pdf paper.pdf --output note.json
```

远程服务没有 key 时 CLI 会拒绝运行；只有 localhost、loopback 或私有网段 endpoint 才允许 keyless 模式。

## 5. Paper schemas

### `PaperMetadata`

保存标题、作者、`arxiv_id`、DOI、年份、venue、URL 和摘要。PDF 元数据不完整时字段可以为空。

### `Section`

```python
Section(
    title="Method",
    content="...",
    section_type=SectionType.METHOD,
    page_start=3,
    page_end=6,
    token_count=2100,
)
```

`SectionType` 包括 abstract、introduction、related_work、method、experiments、results、discussion、conclusion、appendix、references 和 unknown。

### `Paper`

包含 `metadata`、`sections`、`raw_text`、`total_pages`、`total_tokens` 和绝对路径 `source`。提供 `abstract_section`、`method_sections`、`section_titles` 便捷属性。

### `PaperChunk`

是 Agent 的上下文单元，包含 `text`、来源章节、章节类型、全局 `chunk_index` 和 token 数。`PaperChunk.chunk_index` 是全局编号；`read_section` 的 `chunk_index` 是指定章节内的零基编号。

### `PaperNote`

最终结构化输出包括 `tldr`、`contributions`、`methodology_summary`、`key_findings`、`section_notes`、`strengths`、`weaknesses`、`questions`、`reading_trace` 和 `total_tokens_used`。

## 6. `PDFParser`

```python
from repro_forge.paper import PDFParser

paper = PDFParser().parse("paper.pdf")
```

处理流程：

1. 惰性导入 PyMuPDF；
2. 打开并逐页提取文本；
3. 从 PDF info 字典提取标题和作者；
4. 按页扫描行，用保守的标题正则识别章节；
5. 为每个章节记录页码范围和 token 估计；
6. 汇总 `raw_text`、页数和总 token 数。

`parse()` 对不存在路径抛出 `FileNotFoundError`，缺少 `pdf` extra 抛出带安装提示的 `ImportError`。扫描型图片 PDF 没有 OCR 能力，可能得到空文本。

## 7. `ArxivClient`

```python
from repro_forge.paper import ArxivClient

client = ArxivClient()
results = client.search("attention mechanism", max_results=5)
metadata = client.fetch_by_id("arXiv:1706.03762")
pdf_path = client.download_pdf("hep-th/9901001", "data/papers")
```

`normalize_arxiv_id()` 统一 `1706.03762`、`arXiv:1706.03762`、`https://arxiv.org/abs/1706.03762`、PDF URL 和旧式 `hep-th/9901001`。下载文件名会把 `/` 和 `\` 替换为 `_`，避免把 ID 解释为目录。

arXiv SDK 仅在实例化时导入。查询为空返回空列表；下载不到论文时抛出 `ValueError`。

## 8. `PaperChunker`

```python
chunks = PaperChunker(max_tokens=4000, min_tokens=500).chunk(paper)
```

行为规则：

- 空白章节被跳过；
- 小章节在预算内合并；
- 大章节优先按段落切分；
- 单个超长段落按约 `max_tokens * 4` 字符切分，并尽量在空格处断开；
- token metadata 为 0 或过低时使用保守估计；
- 每个输出 chunk 的 `token_count` 为正数。

它不承诺模型 tokenizer 精确计数，`max_tokens` 应视为安全预算而不是服务端硬性证明。

## 9. `PaperReader`

### 生命周期

```text
setup → think → act → observe → (repeat) → finalize → teardown
```

`read(paper)` 会创建 `PaperChunker(max_tokens=4000)`，验证 Provider 和可读内容，然后委托给 P0 `BaseAgent.run()`。

### 工具

| 工具 | 参数 | 返回 |
|---|---|---|
| `list_sections` | 无 | 去重后的章节标题 |
| `read_section` | `section_title`, `chunk_index=0` | 一个有界章节块，长章节附续读提示 |
| `search_paper` | `query` | 最多五个带 `[Section Title]` 的片段 |
| `finalize` | 内部 raw JSON | `PaperNote` |

原生 tool call 会逐个执行并把同一 `tool_call_id` 写回对话。文本模型若只说“read the method”，P1 仍会尝试保守识别；无法识别时回退到 `list_sections`。

### 失败与预算

工具参数类型、空标题、空 query、未知章节和越界 chunk 都生成 `Observation.is_error`，并继续让模型修正。达到 `max_steps` 后，未执行的 parallel calls 会被标记为 skipped，并发起一次无工具的最终总结请求。`AgentTrace` 记录步骤，`PaperNote.total_tokens_used` 汇总 Provider usage。

## 10. `OpenAIProvider`

`OpenAIProvider` 使用异步 OpenAI SDK，但只暴露项目自己的 `LLMRequest` / `LLMResponse`。请求字段包括 messages、model、temperature、max_tokens、tools、tool_choice 和 stop sequences；响应统一提取文本、工具调用和 token usage。

支持 OpenAI、DeepSeek、Qwen、vLLM、Ollama 等实现相同 chat completions 协议的服务。`generate_stream()` 逐块 yield 文本，不伪造 usage；需要完整 token 统计时使用非流式 `generate()` 或由上层 provider 补充。

## 11. `PaperPipeline`

```python
pipeline = PaperPipeline(provider=provider)
paper = pipeline.parse_pdf("paper.pdf")
note = await pipeline.read_pdf("paper.pdf")
metadata = pipeline.fetch_arxiv("1706.03762")
note = await pipeline.read_arxiv("1706.03762", "data/papers")
```

| 方法 | 作用 |
|---|---|
| `parse_pdf` | 调用注入的 parser |
| `search_arxiv` | 延迟创建 client 后搜索 |
| `fetch_arxiv` | 归一化 ID 后取元数据 |
| `download_arxiv` | 归一化 ID 后下载 PDF |
| `read` | 读取已解析 `Paper` |
| `read_pdf` | 解析后读取 |
| `read_arxiv` | 下载、解析、读取 |

Parser、Arxiv client、reader 和 Provider 均可注入，便于替换和测试。

## 12. CLI 参考

```powershell
uv run repro-forge --version
uv run repro-forge capabilities
uv run repro-forge read-pdf paper.pdf
uv run repro-forge read-pdf paper.pdf --output note.json
uv run repro-forge read-json paper.json --output note.json
```

`read-json` 要求输入是 `Paper.model_dump_json()` 兼容结构，而不是任意 PDF 转出的 JSON。没有子命令时默认打印 capabilities。

## 13. 测试与验证

```powershell
uv run pytest -q
uv run ruff check repro_forge tests
uv run ruff format --check repro_forge tests
uv run mypy repro_forge
uv run mkdocs build --clean -f docs/mkdocs.yml
uv build
```

P1 测试重点位于 `test_pdf_parser.py`、`test_arxiv_api.py`、`test_chunker.py`、`test_paper_reader.py`、`test_pipeline.py`、`test_openai_provider.py`、`test_cli.py` 和 `test_read_pipeline.py`。Fake provider 不访问网络，真实 DeepSeek/arXiv smoke test 需要显式外部凭据和网络。

已验证基线是 107 passed、86.06% coverage、Ruff/mypy/MkDocs/build 通过。覆盖率数字会随代码和测试变化，运行命令得到的当前结果优先。

## 14. 常见故障

### `PDFParser requires the optional 'pdf' extra`

```powershell
uv sync --locked --extra pdf --group dev
```

### Provider 报缺少 key

远程服务设置 `OPENAI_API_KEY` 或 `DEEPSEEK_API_KEY`；本地服务设置 `OPENAI_BASE_URL` 和 `OPENAI_MODEL`。不要把真实 key 写入仓库。

### `Section not found` 或 chunk 越界

先调用 `list_sections`，使用返回标题；长章节从 `chunk_index=0` 开始递增，直到工具返回的续读提示结束。

### PDF 没有章节

检查是否为扫描件或标题不符合常见英文模式。P1 没有 OCR 和版式模型，必要时先做 OCR 或手工构造 `Paper`。

### 想运行完整复现

当前不能。P3 CodeForger/Experimentor、P4 Verifier、P5 存储和 P6 服务层尚未交付；P2 Methodologist 已通过 `MethodologyPipeline` 提供；不要把 `compose.future.yml` 或空包目录当作可运行实现。
