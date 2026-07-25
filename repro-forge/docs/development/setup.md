# Phase 0 — 基础设施搭建

> **状态**: ✅ 已完成
> **交付日期**: 2025-07-24
> **版本**: v0.1.0-alpha

---

## 概述

P0 阶段的目标是建立 Python 项目的工程基础设施和最小核心抽象。在这一阶段不实现论文解析、专项 Agent、真实 LLM Provider、API 或复现流水线，只提供类型系统、抽象运行时以及支撑后续开发的质量门禁。

这相当于一座大厦的地基 —— 所有后续的 Agent 代码、论文管道、复现引擎都建立在它之上。

---

## 交付物清单

### 1. 项目元数据与构建系统

| 文件 | 作用 |
|------|------|
| `pyproject.toml` | 项目唯一配置文件，集中管理：元数据、依赖、ruff/mypy/pytest/coverage 工具链 |
| `uv.lock` | 锁定所有依赖的精确版本，确保开发者环境一致 |
| `.python-version` | `uv` 自动识别，锁定 Python 3.13 |

**设计决策**:
- 使用 **hatchling** 作为构建后端（轻量、现代）
- 使用 **uv** 作为包管理器（比 pip 快 10-100x，由 Ruff 团队维护）
- 依赖分为三层：
  - `dependencies` — 核心运行时（pydantic, httpx, tiktoken 等）
  - `[project.optional-dependencies]` — 按功能模块拆分可选依赖（pdf, memory, api 等）
  - `[dependency-groups] dev` — 纯开发工具（ruff, mypy, pytest 等），用户不需要安装

### 2. 代码质量工具链

| 工具 | 配置位置 | 职责 |
|------|---------|------|
| **ruff** | `pyproject.toml [tool.ruff]` | Lint + 格式化，替代 flake8/isort/pyupgrade/black |
| **mypy** | `pyproject.toml [tool.mypy]` | 严格类型检查 (`strict = true`) |
| **pre-commit** | `.pre-commit-config.yaml` | Git 提交前自动运行 ruff + mypy + 基础安全检查 |

**设计决策**:
- 全部配置集中在 `pyproject.toml`，避免散落的配置文件
- Ruff 以最低支持版本 `py311` 为目标，规则集：pyflakes, pycodestyle, isort, pep8-naming, bugbear 等
- Mypy 开启 `strict` 模式 —— 所有公开函数必须标注类型
- 行宽 100 字符（平衡可读性和宽屏效率）

### 3. 测试框架

| 文件 | 作用 |
|------|------|
| `tests/conftest.py` | 全局测试夹具：`FakeLLMProvider`（模拟 LLM）、`FakeAgent`（测试用虚拟 Agent） |
| `tests/unit/test_types.py` | 15 个单元测试，覆盖所有核心类型（Message, Action, Observation 等） |
| `tests/unit/test_base_agent.py` | 10 个单元测试，覆盖 Agent 生命周期、状态、步数预算、异常清理和 Trace 隔离 |

```
tests/
├── conftest.py          # 共享 fixture + mock
├── unit/                # 单元测试 (≥90% 覆盖目标)
├── integration/         # 集成测试 (≥70% 覆盖目标)
└── e2e/                 # 端到端测试 (≥50% 覆盖目标)
```

**设计决策**:
- 使用 `FakeLLMProvider` 模拟 LLM 调用 —— 测试无需网络、秒级完成
- 使用 `FakeAgent` 测试 BaseAgent 生命周期 —— 每条链路独立验证
- `pytest-asyncio` + `asyncio_mode = "auto"` 支持异步测试

### 4. CI/CD 流水线 (.github/workflows/)

#### `ci.yml` — 持续集成

```
PR → ruff format check → ruff lint → mypy → package build
                                      └→ pytest (3.11 + 3.12 + 3.13)
                                      └→ Docker P0 image build + CLI smoke test
```

#### `release.yml` — 发布产物验证

```
git tag vX.Y.Z → build wheel/sdist → 隔离安装验证 → 上传 Actions artifact
```

#### `docs.yml` — 文档构建

```
main 分支 push → mkdocs strict build
```

**设计决策**:
- PR 和主分支 push 均执行质量、单元测试、包构建和 Docker smoke test
- 使用矩阵测试确保 Python 3.11/3.12/3.13 兼容性
- Dependabot 每周自动更新 pip + GitHub Actions 依赖

### 5. 核心运行时骨架

| 模块 | 文件 | 核心内容 |
|------|------|---------|
| **类型系统** | `core/types.py` | Message, Action, Observation, Thought, AgentTrace, TaskSpec/Result, AgentConfig |
| **Agent 基类** | `core/base.py` | BaseAgent 抽象类，ReAct 循环 (`think → act → observe`)，同步/流式双模式 |
| **Provider 抽象** | `providers/base.py` | BaseProvider 接口，LLMRequest/LLMResponse 统一数据结构 |

```
repro_forge/
├── core/
│   ├── types.py      # 29 个类/枚举，完整类型系统
│   └── base.py       # ReAct 循环 + streaming
├── providers/
│   └── base.py       # 多 LLM Provider 抽象
├── agents/           # (P1-P4 待实现) 六大专项 Agent
├── paper/            # (P1 待实现) 论文解析管道
├── reproduction/     # (P3-P4 待实现) 复现引擎
├── memory/           # (P4 待实现) 记忆系统
├── knowledge/        # (P5 待实现) 知识图谱
├── mcp/              # (P6 待实现) MCP 协议
├── guardrails/       # (P7 待实现) 安全护栏
├── evaluation/       # (P8 待实现) 评测框架
├── observability/    # (P8 待实现) 可观测性
└── api/              # (P6 待实现) API 服务
```

### 6. GitHub 社区与开源治理

| 文件 | 用途 |
|------|------|
| `README.md` | 项目门面：当前 P0 状态、规划功能、安装验证和路线图 |
| `LICENSE` | Apache 2.0（企业友好 + 专利保护） |
| `CONTRIBUTING.md` | 开发流程、Commit 规范（Conventional Commits）、PR 流程 |
| `CODE_OF_CONDUCT.md` | Contributor Covenant 2.1 |
| `GOVERNANCE.md` | 贡献者阶梯：User → Contributor → Reviewer → Maintainer → PMC |
| `SECURITY.md` | 漏洞报告流程、Dependabot 策略 |
| `CHANGELOG.md` | Keep a Changelog 格式 |
| `CITATION.cff` | 学术引用格式（arXiv 论文可直接引用） |
| `ISSUE_TEMPLATE/` | Bug Report / Feature Request / Reproduction Task 三种模板 |
| `PULL_REQUEST_TEMPLATE.md` | PR 提交清单（组件、Checklist、Related Issues） |

### 7. 部署配置

| 文件 | 作用 |
|------|------|
| `Dockerfile` | 多阶段构建当前 P0 Python 包，以非 root 用户运行占位 CLI |
| `compose.future.yml` | P1+ 服务模板；P0 不依赖 Neo4j、ChromaDB 或 Jaeger |
| `.dockerignore` | 排除 `.git`, `__pycache__`, `node_modules` 等 |

### 8. 文档站点

| 文件 | 内容 |
|------|------|
| `docs/mkdocs.yml` | Material 主题，自动生成 API 文档 |
| `docs/index.md` | 首页：Mermaid 架构图、功能卡片、路线图 |
| `docs/` (27 页) | Getting Started / User Guide / Architecture / API Reference / Development 骨架 |

---

## 架构原则

P0 阶段确立的工程原则将贯穿整个项目：

1. **配置集中化** — 所有工具配置在 `pyproject.toml`，一键修改
2. **类型安全** — `mypy --strict`，所有公开接口必须有类型标注
3. **Mock 驱动测试** — `FakeLLMProvider` 确保测试秒级完成，不依赖网络
4. **渐进式依赖** — 按功能模块拆分 optional dependencies，不强制安装所有依赖
5. **自动化验证** — `make setup` 一键安装，`make check` 一键验证；P0 只生成发布产物，不自动公开发布
6. **开源优先** — 从 Day 1 就按开源标准建设（许可证、治理、安全、引用）

---

## 下一阶段

| 阶段 | 内容 | 状态 |
|------|------|------|
| P0 | 基础设施搭建 | ✅ 已完成 |
| **P1** | PaperReader Agent + PDF 解析管道 | 📋 待开始 |
| P2 | Methodologist + 知识图谱写入 | 📋 规划中 |
| P3 | CodeForger + 实验执行 | 📋 规划中 |

P1 及后续阶段保持规划状态，不属于本轮 P0 交付。
