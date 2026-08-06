# P0 技术参考文档 — 完整的配置、命令与模块说明

> **用途**: 入职/协作场景参考文档。当新同事问"这个项目怎么跑起来？配置在哪？"时，本文提供完整答案。
>
> **读者**: 新加入的开发者、自己的操作备忘、Onboarding 文档
>
> **行文原则**: 每个配置 ← 路径 + 命令 + 输出 → 可复现的操作步骤
>
> **阶段边界**：本文保留 P0 工程基线，并同步记录当前 P1/P2 能力和 P3–P8
> 规划入口。P0、P1、P2 已完成；空包、可选依赖和未来服务模板不表示 P3–P8
> 已实现。统一状态以 [P0–P8 总体路线图](ROADMAP.md) 为准。

---

## 第一章　项目概览

### 1.1 仓库信息

| 项目 | 值 |
|------|-----|
| GitHub 仓库 | `https://github.com/selfrestart/26Summer` |
| 子项目目录 | `repro-forge/` |
| Python 包名 | `repro_forge`（`import repro_forge`） |
| PyPI 分发名 | `repro-forge`（`pip install repro-forge`） |
| 许可证 | Apache License 2.0 |
| Python 版本 | 3.11 / 3.12 / 3.13 |
| 当前版本 | v0.1.0-alpha |

### 1.2 目录树

```
26Summer/                              # GitHub 仓库根目录
├── .github/                           # CI/CD + Issue/PR 模板
│   ├── workflows/
│   │   ├── ci.yml                     # PR 触发：lint + typecheck + test
│   │   ├── release.yml                # Tag 触发：构建 + 验证 artifact
│   │   └── docs.yml                   # Push 触发：文档自动部署
│   ├── ISSUE_TEMPLATE/
│   │   ├── bug_report.md
│   │   ├── feature_request.md
│   │   └── reproduction_task.md
│   ├── PULL_REQUEST_TEMPLATE.md
│   └── dependabot.yml
│
├── README.md                          # Umbrella 仓库说明
├── .gitignore                         # 根级 Git 忽略规则
│
├── repro-forge/                       # 主项目目录
│   ├── pyproject.toml                 # 项目元数据 + 8 个工具的配置
│   ├── Makefile                       # 18 个命令目标
│   ├── uv.lock                        # 锁定依赖精确版本
│   ├── .python-version                # Python 3.13 锁定
│   ├── .env.example                   # 当前能力与未来阶段的环境变量模板
│   ├── .editorconfig                  # 跨 IDE 格式规范
│   ├── .pre-commit-config.yaml        # Git hooks 配置
│   ├── .gitignore                     # 子项目级忽略规则
│   ├── .dockerignore
│   │
│   ├── Dockerfile                     # 多阶段构建（builder + runtime）
│   ├── compose.future.yml             # P5/P8 未来服务模板，不属于当前运行链路
│   │
│   ├── repro_forge/                   # Python 源码包
│   │   ├── __init__.py                # v0.1.0
│   │   ├── cli.py                     # CLI 入口
│   │   ├── core/
│   │   │   ├── types.py               # 29 个类型/枚举（Message, Action, Trace...）
│   │   │   └── base.py                # BaseAgent + ReAct 循环
│   │   ├── providers/
│   │   │   └── base.py                # BaseProvider + LLMRequest/Response
│   │   ├── agents/                    # P1 PaperReader；P2 Methodologist
│   │   ├── paper/                     # P1 解析/阅读；P2 evidence/extractor
│   │   ├── reproduction/              # (P3) 复现引擎
│   │   ├── memory/                    # (P5) 记忆系统
│   │   ├── knowledge/                 # (P5) 知识图谱
│   │   ├── mcp/                       # (P6) MCP 协议
│   │   ├── guardrails/                # (P7) 安全护栏
│   │   ├── evaluation/                # (P8) 评测框架
│   │   ├── observability/             # (P8) 可观测性
│   │   └── api/                       # (P6) API 服务
│   │
│   ├── tests/
│   │   ├── conftest.py                # 全局 fixtures + FakeLLMProvider + FakeAgent
│   │   ├── unit/
│   │   │   ├── test_types.py          # 15 个类型系统测试
│   │   │   └── test_base_agent.py     # 6 个 Agent 生命周期测试
│   │   ├── integration/
│   │   └── e2e/
│   │
│   ├── docs/
│   │   ├── mkdocs.yml                 # Material 主题 + 30 页导航
│   │   ├── index.md                   # 文档首页
│   │   ├── P0-DESIGN-RATIONALE.md     # 面试导向设计论证文档
│   │   ├── P0-TECHNICAL-REFERENCE.md  # 本文档
│   │   ├── ARCHITECTURE.md            # 纯英文架构文档
│   │   ├── getting-started/           # 3 篇
│   │   ├── user-guide/                # 4 篇
│   │   ├── architecture/              # 6 篇
│   │   ├── api-reference/             # 4 篇
│   │   ├── examples/                  # 3 篇
│   │   ├── development/               # 4 篇
│   │   └── evaluation/                # 2 篇
│   │
│   ├── examples/                      # 可运行示例脚本
│   └── notebooks/                     # Jupyter Notebook 演示
│
└── 其他（.coverage, htmlcov/ 等运行时生成物）
```

### 1.3 核心概念速查表

| 概念 | 对应类型/模块 | 说明 |
|------|------------|------|
| Agent | `core/base.py::BaseAgent` | 遵循 think → act → observe 循环 |
| Task | `core/types.py::TaskSpec` | 任务描述，指定目标和参数 |
| Message | `core/types.py::Message` | OpenAI 兼容的消息格式 |
| Action | `core/types.py::Action` | Agent 决定执行的工具调用 |
| Observation | `core/types.py::Observation` | 工具执行后的观察结果 |
| Trace | `core/types.py::AgentTrace` | 单次 Agent 执行的完整记录 |
| Provider | `providers/base.py::BaseProvider` | LLM 调用的统一抽象 |
| Memory | `memory/` 模块 | P5 规划中的长期记忆；当前仅保留命名空间 |
| Tool | PaperReader 内置只读工具 | P1 已实现；通用注册与 MCP 接口属于后续阶段 |

---

## 第二章　环境搭建

### 2.1 前置依赖

| 依赖 | 版本要求 | 如何安装 |
|------|---------|---------|
| uv | ≥ 0.1.0 | `powershell -c "irm https://astral.sh/uv/install.ps1 \| iex"`（Windows）<br>`curl -LsSf https://astral.sh/uv/install.sh \| sh`（macOS/Linux） |
| Python | 3.11+ | uv 自动通过 `.python-version` 管理 |
| Git | 任意 | `winget install Git.Git` 或 `brew install git` |
| Docker | 24+ | 可选，仅实验执行时需要 |

### 2.2 一键初始化

```bash
cd repro-forge
make setup
```

`make setup` 内部执行：
1. `uv venv` — 创建 `.venv/`，Python 版本取自 `.python-version`
2. `uv sync --group dev` — 安装核心依赖 + 开发工具
3. `uv run pre-commit install` — 安装 Git 提交钩子

### 2.3 手动安装（分步说明）

```bash
# 1. 创建虚拟环境
uv venv
# 创建 .venv/，Python 3.13

# 2. 安装核心 + 开发工具
uv sync --group dev
# 安装: pydantic, httpx, tiktoken + ruff, mypy, pytest ...

# 3. 如需全部可选功能:
uv sync --all-extras --group dev
# 额外安装: PyMuPDF, chromadb, neo4j, fastapi, mlflow ...

# 4. 安装 Git 钩子
uv run pre-commit install

# 5. 配置 API Key
cp .env.example .env
# 编辑 .env，至少填入 OPENAI_API_KEY
```

### 2.4 环境变量配置

完整字段见 `.env.example`，关键字段：

```ini
# 远程 Provider 至少配置一组；共享文档中保持凭据值为空
OPENAI_API_KEY=
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o
DEEPSEEK_API_KEY=
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat

# 仅预留，当前没有 Anthropic Provider 实现
ANTHROPIC_API_KEY=
ANTHROPIC_MODEL=claude-sonnet-4-20250514

# 执行后端
EXECUTION_BACKEND=dryrun               # P3 规划: dryrun | local-subprocess | docker

# 日志
LOG_LEVEL=INFO
```

### 2.5 验证安装

```bash
cd repro-forge
uv run python -c "import repro_forge; print(repro_forge.__version__)"
# 输出: 0.1.0

uv run ruff check repro_forge/ tests/
# 输出: All checks passed!

uv run mypy repro_forge/
# 输出: Success: no issues found in 26 source files

uv run pytest tests/unit/ -q
# 输出: 21 passed
```

---

## 第三章　开发工具链

### 3.1 Makefile 命令参考

| 命令 | 执行的操作 | 适用时机 |
|------|----------|---------|
| `make setup` | venv + deps + pre-commit 安装 | 首次克隆后 |
| `make sync` | 安装核心 + 开发工具 | pull 后有新依赖 |
| `make sync-all` | 安装所有可选依赖 | 需要 chromadb/neo4j 等 |
| `make sync-minimal` | 仅核心依赖 | 生产环境 |
| `make check` | format-check + lint + typecheck + test | **提交前必须运行** |
| `make format` | 自动格式化 + 自动修复 lint | 写代码中 |
| `make format-check` | 仅检查格式 | CI 用 |
| `make lint` | 仅 lint | 快速检查 |
| `make typecheck` | 仅 mypy | 修改类型后 |
| `make test` | 单元 + 集成测试 | 改代码后 |
| `make test-cov` | 测试 + 覆盖率报告 | 提交前 |
| `make test-e2e` | 端到端测试 | 需要服务时 |
| `make test-all` | 所有测试 | 大重构后 |
| `make ci` | 模拟完整 CI 流程 | push 前本地验证 |
| `make docs` | 构建文档站点 | 检查文档 |
| `make docs-serve` | 本地预览文档 | 写文档时 |
| `make pre-commit-all` | 手动全体 pre-commit | 调试 hook 时 |
| `make clean` | 清理构建产物 | 遇缓存问题时 |

### 3.2 ruff 配置详解

配置文件：`pyproject.toml` 的 `[tool.ruff]`、`[tool.ruff.lint]`、`[tool.ruff.format]`。

| 配置项 | 值 | 说明 |
|--------|-----|------|
| `target-version` | `py313` | 目标 Python 版本 |
| `line-length` | `100` | 行宽 |
| `select` | E, W, F, I, N, B, SIM, PYI, UP, C4, RUF | 启用的规则集 |
| `quote-style` | `double` | 双引号 |
| `indent-style` | `space` | 空格缩进 |
| `line-ending` | `lf` | Unix 换行符 |

### 3.3 mypy 配置详解

配置文件：`pyproject.toml` 的 `[tool.mypy]`。

| 配置项 | 值 | 说明 |
|--------|-----|------|
| `strict` | `true` | 启用所有严格选项 |
| `disallow_untyped_defs` | `true` | 禁止无类型标注的函数 |
| `warn_return_any` | `true` | `Any` 返回值触发警告 |
| `no_implicit_optional` | `true` | 可空类型必须显式 Optional |
| `show_error_codes` | `true` | 显示错误码便于搜索 |

### 3.4 pytest 配置详解

文件：`pyproject.toml` 的 `[tool.pytest.ini_options]`。

| 配置项 | 值 | 说明 |
|--------|-----|------|
| `asyncio_mode` | `auto` | 自动识别 async 测试 |
| `testpaths` | `tests` | 测试根目录 |
| `python_files` | `test_*.py` | 测试文件匹配模式 |

**Markers（标记）**：

| 标记 | 说明 | 运行方式 |
|------|------|---------|
| `slow` | 慢速测试 | `pytest -m "not slow"` 跳过 |
| `llm` | 需要真实 LLM API | `pytest -m llm` 单独跑 |
| `unit` | 单元测试 | 按标记筛选 |
| `integration` | 集成测试 | 按标记筛选 |
| `e2e` | 端到端测试 | CI 保护分支跑 |

### 3.5 pre-commit 配置

文件：`.pre-commit-config.yaml`，3 个 repo，7 个 hook：

```
1. ruff-pre-commit
   ├── ruff (lint, --fix)
   └── ruff-format

2. pre-commit-hooks
   ├── check-yaml
   ├── check-toml
   ├── check-json
   ├── check-added-large-files (max 500KB)
   ├── check-merge-conflict
   ├── detect-private-key
   ├── end-of-file-fixer
   ├── trailing-whitespace
   └── mixed-line-ending (--fix=lf)

3. mirrors-mypy
   └── mypy (--strict)
```

### 3.6 uv 命令速查

```bash
# 虚拟环境
uv venv                          # 创建 .venv
uv venv --python 3.12            # 指定 Python 版本

# 依赖管理
uv sync                          # 装核心依赖
uv sync --group dev              # + 开发工具
uv sync --all-extras             # + 所有可选依赖
uv lock                          # 重新生成锁文件

# 运行命令
uv run python script.py          # 在 venv 中运行
uv run ruff check .              # 在 venv 中运行 ruff
uv run pytest                    # 在 venv 中运行 pytest

# 与 pip 互操作
uv pip install package           # pip install 等效
uv pip list                      # 列出已装包
uv pip freeze > requirements.txt # 导出
```

---

## 第四章　项目配置

### 4.1 pyproject.toml 完整字段说明

`pyproject.toml` 是项目唯一核心配置文件，包含 8 个工具体系的配置。

**`[build-system]`**
```toml
requires = ["hatchling"]
build-backend = "hatchling.build"
```
构建系统声明。hatchling 是 PyPA 推荐的现代构建后端，零配置。

**`[project]`**
- `name`：PyPI 上的包名 `repro-forge`
- `version`：当前版本，由 `bumpver` 自动管理
- `dependencies`：核心运行时依赖，安装 `pip install repro-forge` 时自动安装
- `optional-dependencies`：按功能分组的可选依赖（pdf / openai / memory / kg / api ...）
- `urls`：GitHub 仓库、文档站点、Issue 追踪链接

**`[project.scripts]`**
```toml
repro-forge = "repro_forge.cli:main"
```
定义命令行入口：`uv run repro-forge` 等同于 `python -m repro_forge.cli`

**`[tool.ruff]`** — lint + format 规则配置（见 3.2）

**`[tool.mypy]`** — 类型检查配置（见 3.3）

**`[tool.pytest.ini_options]`** — 测试配置（见 3.4）

**`[tool.coverage.run]` / `[tool.coverage.report]`**
- `source = ["repro_forge"]`：只统计 repro_forge 包的覆盖率
- `fail_under = 80`：覆盖率低于 80% 时 CI 失败

**`[tool.bumpver]`**
```toml
current_version = "0.1.0"
version_pattern = "MAJOR.MINOR.PATCH"
```
语义化版本管理。`bumpver update --minor` 自动更新所有文件中的版本号。

**`[tool.uv]`** — uv 专有配置（当前为空，保留扩展空间）

**`[dependency-groups]`**
```toml
[dependency-groups]
dev = ["pytest>=8.2.0", "ruff>=0.5.0", ...]
```
开发依赖组，通过 `uv sync --group dev` 安装。

### 4.2 .env 字段说明（按阶段分组）

| 阶段 | 分类 | 变量 | 当前含义 |
|------|------|------|----------|
| P1 已实现 | OpenAI-compatible | `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `OPENAI_MODEL` | OpenAI 或兼容端点 |
| P1 已实现 | DeepSeek | `DEEPSEEK_API_KEY`, `DEEPSEEK_BASE_URL`, `DEEPSEEK_MODEL` | CLI 自动识别的 DeepSeek 配置 |
| 预留 | Anthropic | `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL` | 依赖已声明，当前没有对应 Provider 实现 |
| P5 规划 | Memory/KG | `CHROMA_*`, `NEO4J_*` | 向量索引、知识图谱和显式镜像引用 |
| P3 规划 | Execution | `EXECUTION_BACKEND`, `MLFLOW_TRACKING_URI` | dry-run/local fixture/Docker 执行和实验记录 |
| 延后 | Remote execution | `SSH_*`, `COLAB_*`, `VASTAI_*` | P3 首批不实现，变量存在不表示 adapter 可用 |
| P6 规划 | API | `SERVER_*`, `ENABLE_CORS`, `ALLOWED_ORIGINS` | FastAPI 服务配置 |
| P8 规划 | Observability/Evaluation | `OTEL_*`, `LOG_LEVEL`, `EVALUATION_*` | 遥测、成本和评测配置 |

`.env.example` 中出现某个变量，只表示为对应阶段预留了统一命名，不表示消费该
变量的模块已经实现。P1 的真实模型调用可以只配置 `DEEPSEEK_API_KEY`，不要求
同时提供 OpenAI key。

### 4.3 .pre-commit-config.yaml

3 个 repo 源，修改 hook 版本时更新 `rev` 字段：
- `astral-sh/ruff-pre-commit` — rev: v0.5.0
- `pre-commit/pre-commit-hooks` — rev: v4.6.0
- `pre-commit/mirrors-mypy` — rev: v1.10.0

### 4.4 .editorconfig

```ini
[*]
charset = utf-8
end_of_line = lf
indent_style = space
indent_size = 4
max_line_length = 100

[*.{yaml,yml}]     → indent_size = 2
[*.{json,markdown}] → indent_size = 2
[Makefile]          → indent_style = tab
[*.{bat,cmd,ps1}]   → end_of_line = crlf
```

### 4.5 .python-version

```
3.13
```
`uv` 自动读取，创建 `.venv` 时匹配此 Python 版本。

### 4.6 .gitignore / .dockerignore

**根 `.gitignore`**：Python 通用忽略（`__pycache__/`、`*.pyc`、`.venv/`、`dist/`、`.coverage` ...）

**子 `.gitignore`**（`repro-forge/` 内）：扩展规则（`.tox`、`site`、`docs/_build`、密钥文件 `.pem` `credentials.json`、MLflow/WandB/checkpoint、Notebook checkpoint、Neo4j 数据）

**`.dockerignore`**：排除 `.git`、`__pycache__`、`.venv`、IDE 配置、测试产物、文档 site

---

## 第五章　代码架构

### 5.1 模块依赖图

```
cli.py
  └── repro_forge (入口)

core/
  ├── types.py       ← 所有模块的基础类型
  └── base.py        ← 所有 Agent 的基类
       └── providers/base.py  ← LLM 抽象

agents/              ← 依赖 core + providers
  ├── paper_reader.py
  ├── methodologist.py
  └── ...

paper/               ← 依赖 core + agents
reproduction/        ← 依赖 core + agents + paper
memory/              ← 依赖 core
knowledge/           ← 依赖 core
mcp/                 ← 依赖 core + tools
tools/               ← 依赖 core + mcp
guardrails/          ← 依赖 core
evaluation/          ← 依赖 core + agents
observability/       ← 依赖 core
api/                 ← 依赖 core + agents + all
```

### 5.2 core/types.py — 类型系统一览（29 个类/枚举）

| 分类 | 类型 | 用途 |
|------|------|------|
| **标识符** | `AgentId`, `TaskId`, `ToolId`, `MemoryId`, `RunId` | 类型别名 = `str` |
| **枚举** | `MessageRole`, `AgentState`, `AgentType`, `TaskStatus` | 消息/Action 的各种状态 |
| **消息** | `Message`, `FunctionCall`, `FunctionResult` | OpenAI 兼容消息格式 |
| **ReAct 原语** | `Thought`, `Action`, `Observation` | think-act-observe 循环核心 |
| **追踪** | `TraceStep`, `AgentTrace` | 执行过程记录 |
| **任务** | `TaskSpec`, `TaskResult` | 任务输入输出 |
| **配置** | `AgentConfig`, `PipelineConfig` | Agent 和管道的配置 |
| **工具** | `new_id()` | 生成唯一短 ID |

### 5.3 core/base.py — ReAct 循环状态机

```python
class BaseAgent(ABC):
    async def run(task: TaskSpec) -> TaskResult:
        # 1. setup() → IDLE
        # 2. while step < max_steps:
        #      think(task) → THINKING
        #      act(thought) → ACTING
        #      observe(action) → OBSERVING
        #      if should_stop(obs): break → DONE
        # 3. finalize(task) → TaskResult

    async def stream(task: TaskSpec) -> AsyncIterator[TraceStep]:
        # 同上，但每一步 yield TraceStep
```

**抽象方法（子类必须实现）**：
- `think()` — 推理
- `act()` — 决策
- `observe()` — 观察
- `should_stop()` — 终止判断
- `finalize()` — 结果

**生命周期方法（可选覆写）**：
- `setup()` — 初始化资源
- `teardown()` — 释放资源

### 5.4 providers/base.py — Provider 抽象接口

```python
class BaseProvider(ABC):
    async def generate(request: LLMRequest) -> LLMResponse
    async def generate_stream(request: LLMRequest) -> AsyncIterator[str]
    async def count_tokens(text: str) -> int
```

**LLMRequest 字段**：`messages`, `model`, `temperature`, `max_tokens`, `tools`, `tool_choice`, `stop_sequences`

**LLMResponse 字段**：`content`, `model`, `finish_reason`, `usage`, `raw`

### 5.5-5.14 模块概览（P1/P2 已实现，P3-P8 待实现）

| 模块 | P0 状态 | P1-P8 规划 |
|------|---------|-----------|
| `agents/` | P1：`PaperReader`；P2：`Methodologist` | P3-P4：其余专项 Agent |
| `paper/` | P1：PDF/arXiv 解析、分块、`PaperPipeline`；P2：`MethodologyPipeline` 与 evidence view | P3：代码与实验 |
| `reproduction/` | 空包 | P3-P4：复现引擎 |
| `memory/` | 空包 | P5：版本化 artifact、Episodic/Semantic memory |
| `knowledge/` | 空包 | P5：知识图谱 |
| `mcp/` | 空包 | P6：MCP Server/Client |
| `tools/` | 空包 | P2 只读 evidence 工具位于 `paper/extractor`；通用注册与 MCP 保留到后续阶段 |
| `guardrails/` | 空包 | P7：安全护栏 |
| `evaluation/` | 空包 | P8：评测框架 |
| `observability/` | 空包 | P8：OTel + 成本追踪 |
| `api/` | 空包 | P6：FastAPI 服务 |

---

## 第六章　CI/CD 流水线

### 6.1 ci.yml — PR 触发流程

```
PR 提交到 main/develop
    │
    ├── quality job:
    │   └── pre-commit/action@v3.0.1
    │       ├── ruff format check
    │       ├── ruff lint
    │       └── mypy strict
    │
    └── test job (需要 quality 通过):
        ├── Python 3.11 + 3.12 矩阵
        ├── 安装 deps → 单元测试 → 集成测试
        └── 上报 codecov（仅 3.12）
```

### 6.2 release.yml — 发布流程

```
git tag vX.Y.Z 推送
    │
    ├── python -m build（wheel + sdist）
    ├── 隔离安装验证
    ├── 上传 Actions artifact
    └── （P0 不发布 PyPI/GHCR/GitHub Release）
```

### 6.3 docs.yml — 文档部署

```
main 分支 push（仅 docs/ 或 repro_forge/ 变化时）
    │
    ├── mkdocs build --strict
    └── GitHub Pages 部署
```

### 6.4 dependabot.yml — 依赖更新策略

```yaml
pip: 每周一检查，最多 10 个 PR，按组聚合
  ├── testing: pytest*, coverage*
  ├── linters: ruff, mypy, pre-commit
  ├── llm: openai, anthropic, litellm, tiktoken
  └── docs: mkdocs*, mkdocstrings*

github-actions: 每周一检查
```

### 6.5 本地模拟 CI

```bash
cd repro-forge
make ci
# 等价于:
#   ruff format --check → ruff check → mypy → pytest unit → pytest integration
```

---

## 第七章　测试体系

### 7.1 测试目录结构

```
tests/
├── conftest.py              # 全局 fixtures + mock
├── unit/
│   ├── test_types.py        # 类型系统测试（15 个）
│   └── test_base_agent.py   # Agent 生命周期测试（6 个）
├── integration/             # （P1+）
└── e2e/                     # （P3+）
```

### 7.2 conftest.py 的 fixtures 清单

| Fixture | 返回类型 | 用途 |
|---------|---------|------|
| `fake_provider` | `FakeLLMProvider` | 模拟 LLM 调用 |
| `fake_agent` | `FakeAgent` | 测试 Agent 生命周期 |
| `sample_task` | `TaskSpec` | 通用测试任务 |
| `sample_pdf_path` | `str` | 最小 PDF 文件路径 |
| `simple_config` | `AgentConfig` | 最小配置 |

### 7.3 FakeLLMProvider 接口

```python
class FakeLLMProvider(BaseProvider):
    def __init__(self, responses: list[str] | None = None)
    async def generate(request: LLMRequest) -> LLMResponse
    async def generate_stream(request: LLMRequest) -> AsyncIterator[str]
    def set_responses(responses: list[str]) -> None
    @property last_request: LLMRequest | None
    @property request_count: int
```

### 7.4 FakeAgent 用法

```python
agent = FakeAgent(max_steps=3)
result = await agent.run(task)
assert result.status == "success"
assert len(agent.actions) == 3
assert agent.state == AgentState.DONE
```

### 7.5 编写新测试的模板

```python
"""Tests for <module_name>."""

import pytest
from repro_forge.core.types import TaskSpec


class Test<ClassName>:
    """Test suite for <ClassName>."""

    @pytest.mark.asyncio
    async def test_<scenario>(
        self,
        fake_provider: FakeLLMProvider,  # 注入 fixture
        sample_task: TaskSpec,
    ) -> None:
        # Arrange
        provider = fake_provider
        provider.set_responses(["expected output"])

        # Act
        result = await my_function(provider, sample_task)

        # Assert
        assert result.status == "success"
```

### 7.6 覆盖率报告解读

```bash
$ make test-cov
# 生成 htmlcov/index.html
# 终端输出:
#   repro_forge/core/types.py  96%
#   repro_forge/core/base.py   76%  (流式部分 P0 未覆盖)
#   repro_forge/providers/base.py  97%
#   TOTAL                      89%
```

---

## 第八章　部署

### 8.1 当前 Dockerfile

当前 `Dockerfile` 是 Python 3.13 两阶段**包镜像**：builder 构建 wheel，runtime
安装 wheel、切换到非 root 用户，并以 `repro-forge` CLI 为入口。它没有启动
FastAPI、Neo4j、ChromaDB 或 Jaeger，也不代表 P3 实验沙箱已经实现。

```bash
make docker-build
docker run --rm repro-forge:p0 --version
docker run --rm repro-forge:p0 capabilities
```

镜像 tag 中的 `p0` 是现有 Makefile 的历史命名；镜像实际打包当前工作树中的
P0/P1 Python 包。P3 实验镜像和 P6 API 镜像必须在对应阶段单独设计。

### 8.2 `compose.future.yml` 服务模板

| 服务 | 所属阶段 | 端口 | 用途 |
|------|----------|------|------|
| `neo4j` | P5 | 7474 / 7687 | 知识图谱索引 |
| `chroma` | P5 | 8001 | 向量索引 |
| `jaeger` | P8 | 16686 / 4317 / 4318 | OpenTelemetry trace 后端 |

该文件不包含 API 服务，且不在 P0/P1 默认启动路径中。服务镜像存在不代表应用
adapter、schema、迁移、健康检查集成或备份恢复已经完成。

### 8.3 显式启动未来服务模板

先在本地 `.env` 设置非默认的 `NEO4J_PASSWORD`，并显式设置 `NEO4J_IMAGE`、
`CHROMA_IMAGE` 和 `JAEGER_IMAGE`。`compose.future.yml` 不提供 fallback 密码或
`latest` 镜像，且所有端口仅绑定 `127.0.0.1`；这仍不等价于 P7 生产安全。
P5/P8 准入评审必须记录兼容版本和 digest；P7 生产门还要求 digest 固定、SBOM
和镜像策略检查。

```bash
cd repro-forge
docker compose -f compose.future.yml up -d
docker compose -f compose.future.yml ps
docker compose -f compose.future.yml down
```

除非明确要丢弃 P5 索引数据，不要执行带 `-v` 的关闭命令。当前 P1 阅读流程
不需要启动这些服务。

### 8.4 未来持久化边界

| 数据 | 阶段 | 计划中的事实源/索引角色 |
|------|------|------------------------|
| 版本化 artifact | P5 | 事实源；保存 P1–P4 JSON、报告、bundle 和 run manifest |
| ChromaDB | P5 | 可重建的语义索引，不作为事实源 |
| Neo4j/NetworkX | P5 | 可重建的关系索引，边必须保留 provenance |
| 实验输出 | P3 | 由 `ExperimentRun`/artifact manifest 追踪 |
| Trace/metrics/cost | P8 | 遥测与发布证据，不替代领域 artifact |

---

## 第九章　文档体系

### 9.1 四层文档结构

```
Layer 1: README (入口)
  └─ 项目简介 / 快速开始 / 徽章 / 目录导航

Layer 2: MkDocs 站点 (完整文档)
  └─ 30 页 + P0 三份核心文档

Layer 3: Docstring (代码内文档)
  └─ Google 风格，mkdocstrings 自动生成 API 文档

Layer 4: Examples / Notebooks (交互式)
  └─ 5 个典型场景的 Python 脚本
```

### 9.2 MkDocs 站点配置

文件：`docs/mkdocs.yml`

| 配置项 | 值 |
|--------|-----|
| 主题 | Material |
| 配色 | 默认 + Dark mode 自动切换 |
| 特性 | instant loading, tabs, sections, search, code copy, mermaid |
| 插件 | search, mkdocstrings（Python docstring → API 文档） |
| 扩展 | admonition, highlight, superfences, tabbed, emoji, toc |

### 9.3 本地构建与预览

```bash
cd repro-forge
make docs           # 构建到 site/ 目录
make docs-serve     # 启动本地服务器 http://localhost:8000
```

### 9.4 GitHub Pages 自动部署

`main` 分支 push → `docs.yml` workflow → `mkdocs build` → GitHub Pages。访问：`https://selfrestart.github.io/26Summer`

### 9.5 Docstring 写作规范

采用 **Google Style**：

```python
def calculate_fidelity(
    claimed: dict[str, float],
    reproduced: dict[str, float],
) -> float:
    """Calculate the reproduction fidelity score.

    Args:
        claimed: Paper-claimed metrics as {metric_name: value}.
        reproduced: Reproduced metrics as {metric_name: value}.

    Returns:
        Fidelity score between 0.0 and 100.0.

    Raises:
        ValueError: If metric sets differ.
    """
```

---

## 第十章　维护与贡献

### 10.1 版本号规范

遵循 [SemVer 2.0.0](https://semver.org/)：

```
MAJOR.MINOR.PATCH

0.1.0-alpha.1   # Alpha
0.5.0-beta.1    # Beta
1.0.0-rc.1      # Release Candidate
1.0.0           # 正式版

MAJOR — 不兼容 API 变更
MINOR — 向后兼容新功能
PATCH — 向后兼容 Bug 修复
```

### 10.2 发布检查清单

- [ ] `make check` 全绿
- [ ] 版本号已更新（pyproject.toml / `__init__.py` / CITATION.cff）
- [ ] CHANGELOG 已更新
- [ ] 文档无死链（`make docs`）
- [ ] 新功能有测试
- [ ] PR 已审批

### 10.3 向后兼容承诺

- P0 阶段（v0.x）：无向后兼容承诺，API 可能 Breaking
- P1-P8 阶段：Core 类型系统（`core/types.py`）尽量稳定，内部 Agent API 可变更
- v1.0.0 起：公开 API 遵循 SemVer 向后兼容

### 10.4 废弃 API 处理流程

1. 标记 `@deprecated`（Python 3.13+ 标准库装饰器）
2. 文档标注替代方案
3. 至少保留一个 MINOR 版本后移除

---

## 附录 A：依赖版本矩阵

| 包 | 最低版本 | 当前版本（uv.lock） |
|----|---------|-------------------|
| pydantic | ≥ 2.7.0 | 2.13.4 |
| httpx | ≥ 0.27.0 | 0.28.1 |
| tiktoken | ≥ 0.7.0 | 0.13.0 |
| structlog | ≥ 24.4.0 | 26.1.0 |
| pyyaml | ≥ 6.0.0 | 6.0.3 |
| rich | ≥ 13.7.0 | 15.0.0 |
| tenacity | ≥ 8.5.0 | 9.1.4 |
| jinja2 | ≥ 3.1.0 | 3.1.6 |
| python-dotenv | ≥ 1.0.0 | 1.2.2 |
| ruff (dev) | ≥ 0.5.0 | 0.16.0 |
| mypy (dev) | ≥ 1.10.0 | 2.3.0 |
| pytest (dev) | ≥ 8.2.0 | 9.1.1 |

## 附录 B：GitHub 链接索引

| 用途 | URL |
|------|-----|
| 仓库 | `https://github.com/selfrestart/26Summer` |
| Issues | `https://github.com/selfrestart/26Summer/issues` |
| Discussions | `https://github.com/selfrestart/26Summer/discussions` |
| CI Actions | `https://github.com/selfrestart/26Summer/actions` |
| 项目看板 | `https://github.com/selfrestart/26Summer/projects` |

## 附录 C：故障排查 FAQ

### Q: `uv run` 报 `ModuleNotFoundError: No module named 'pydantic'`

```bash
cd repro-forge
uv sync --group dev  # 重新安装核心依赖
```

### Q: pre-commit 安装失败（GitHub 不可达）

```bash
# 跳过 pre-commit，直接手动运行检查
uv run ruff check repro_forge/ tests/
uv run mypy repro_forge/
uv run pytest tests/unit/
```

### Q: Windows 上 `make` 命令不存在

```bash
# 方案 1: 使用 Git Bash
# 方案 2: 手动执行等价命令
uv run ruff check repro_forge/ tests/
uv run mypy repro_forge/
uv run pytest tests/unit/
```

### Q: Docker build 失败

```bash
# 确保在 repro-forge/ 目录下
cd repro-forge
docker build -t repro-forge:local .
```
