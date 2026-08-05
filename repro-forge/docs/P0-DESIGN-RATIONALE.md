# P0 设计论证文档 — 每个技术决策的「为什么」

> **用途**: 面试回答参考文档。当面试官问"你为什么选这个技术/架构"时，本文提供完整的论证链路。
>
> **读者**: 面试官、技术评审、自己的复习备忘
>
> **行文原则**: 每个技术选择遵循 **问题 → 备选方案 → 决策依据 → 代价认知** 四段式论证。
>
> **真实性边界**：本文同时包含当前实现决策和目标架构论证。P0、P1 已完成，
> P2–P8 仍是规划。凡涉及 Methodologist、CodeForger、Experimentor、
> MathChecker、Verifier、长期 Memory、知识图谱、MCP/API/UI、Guardrails、
> Benchmark 或完整 OpenTelemetry 的内容，均应按对应阶段的设计方案理解，
> 不能作为当前代码已实现的陈述。统一状态见 [P0–P8 总体路线图](ROADMAP.md)。

---

## 第一章　项目定位：为什么是「论文复现」而不是通用 Agent 框架

### 1.1 可复现性危机：一个系统性问题

计算机科学研究正面临严重的**可复现性危机**（Reproducibility Crisis）：

| 数据来源 | 关键发现 |
|---------|---------|
| AAAI 2020 调查 | 43% 的 ML 论文无法完全复现 |
| NeurIPS Reproducibility Challenge | 仅 34% 的论文在首次尝试中复现成功 |
| PapersWithCode 统计 | 已发表论文中仅 ~15% 有公开代码 |
| ICML Artifact Evaluation | ~60% 的 artifacts 存在环境依赖问题 |

这些数字意味着：
- **研究者**花大量时间理解他人论文的未公开细节
- **工程师**难以评估是否应该在自己的系统中采用论文方法
- **审稿人**无法验证声称的实验结果

### 1.2 为什么不做一个通用 Agent 框架

市面上的通用 Agent 框架（LangChain、CrewAI、AutoGen）解决的是"如何让 Agent 调用工具"这一横向问题。但论文复现流程面临的是**纵向深度挑战**：

| 通用 Agent 框架的痛点 | 论文复现场景的特殊需求 |
|---------------------|-------------------|
| 工具调用是平面的（search → read → answer） | 工具调用是深度链式的（read → extract algorithm → generate code → execute → verify） |
| 不需要理解学术论文的结构 | 需要解析 LaTeX 源码、提取伪代码、理解神经网络架构描述 |
| 输出是自然语言文本 | 输出是可运行的 PyTorch/TensorFlow 代码 + 实验记录 + 复现报告 |
| 评测标准模糊（"回答得好不好"） | 评测标准精确（"复现的准确率和论文差几个点"） |

**核心论断**：垂直深挖一个领域 > 水平铺开做一个通用框架。论文复现这个细分领域的复杂度和技术深度，足够支撑一个有区分度的 Agent 项目。

### 1.3 与现有工具的差异化

| 工具 | 定位 | 与 ReproForge 的差异 |
|------|------|-------------------|
| PapersWithCode | 论文-代码索引 | 只做索引，不做自动复现 |
| PaperQA / Elicit | 论文问答 | 只做导读，不做代码生成 |
| ReScience C | 人工复现期刊 | 依赖人工，无自动化 |
| SWE-bench (Agent) | 代码仓库 Bug 修复 | 面向软件工程，不面向学术论文 |
| **ReproForge（目标）** | **端到端自动复现** | **P1 已完成导读；P2–P4 规划代码生成、实验执行和结果验证闭环** |

---

## 第二章　技术栈选型

### 2.1 包管理器：uv vs pip vs poetry vs pdm

**问题**：Python 生态有 4+ 个主流包管理器，选哪个？

| 维度 | pip | poetry | pdm | **uv** ✅ |
|------|-----|--------|-----|----------|
| 解析速度 | 慢（单线程） | 慢（Python） | 中（Python） | **极快（Rust）** |
| 安装速度 | 慢 | 慢 | 中 | **10-100x pip** |
| 锁文件 | 无内置 | poetry.lock | pdm.lock | **uv.lock（标准）** |
| PEP 621 | ✅ | ✅ | ✅ | ✅ |
| 虚拟环境管理 | 需手动 `venv` | 内置 | 内置 | **内置** |
| 工具链生态 | pipx 等 | 自成体系 | 自成体系 | **ruff + uv 一体** |

**决策**：选 `uv`，理由有四：

1. **速度**：Rust 实现，解析-安装一体化。实测安装 120 个包从 pip 的 ~120s 降到 ~5s（24x 加速）
2. **生态一致性**：和 `ruff`（项目 linter）同属 Astral 团队，配置风格统一
3. **Python 版本管理**：通过 `.python-version` 文件自动锁定 Python 版本，团队成员无需手动管理
4. **PEP 621 优先**：纯 `pyproject.toml` 驱动，无额外配置文件

**代价认知**：
- `uv` 相对较新（2024 GA），生态系统仍在快速迭代
- 部分老旧项目仍用 `requirements.txt`，迁移需要成本
- 某些复杂依赖（如 PyTorch 的 CUDA 版本选择）可能需要额外配置

### 2.2 Lint / Format：ruff vs flake8 + black + isort

**问题**：Python 代码质量工具传统上需要 4 个独立工具配合。

| 维度 | flake8+black+isort | **ruff** ✅ |
|------|-------------------|------------|
| 工具数量 | 3-4 个 | **1 个** |
| 配置文件 | 3 个散落文件 | **1 个 pyproject.toml** |
| Lint 速度 | 慢（Python 实现） | **10-100x（Rust）** |
| 规则数量 | ~200 | **700+** |
| 自动修复 | 部分支持 | **广泛支持** |

**决策**：选 `ruff`，一个工具覆盖 lint（替代 flake8 + isort + pyupgrade）和 format（替代 black）。

**规则集选择**：`E/W`（pycodestyle）、`F`（pyflakes）、`I`（isort）、`N`（pep8-naming）、`B`（bugbear，常见 Bug 模式）、`SIM`（简化建议）、`UP`（自动升级新版 Python 语法）、`C4`（推导式优化）、`RUF`（ruff 专有规则）。

### 2.3 类型检查：mypy strict 的收益与代价

**问题**：Python 是动态类型语言，大型项目的类型安全靠什么？

**决策**：选 `mypy --strict`，而不是 pyright。

| 为什么是 mypy 而非 pyright | 为什么是 strict 模式 |
|--------------------------|-------------------|
| mypy 最成熟的 Python 类型检查器 | `disallow_untyped_defs`：所有公开函数必须有类型标注 |
| pydantic 官方提供 `pydantic.mypy` 插件 | `warn_return_any`：`Any` 返回值会触发警告 |
| 与 pre-commit 生态无缝协作 | `no_implicit_optional`：可空类型必须显式标注 |

| strict 带来的收益 | 需要支付的代价 |
|-----------------|-------------|
| 类型即文档——看函数签名就知道输入输出 | 需要编写更多的类型标注代码 |
| 重构安全网——修改接口后所有调用点自动报错 | 动态模式下的灵活代码需要改造 |
| 拦截运行时 TypeError——编译期发现 | Pydantic 模型与 mypy 的交互偶有摩擦 |

### 2.4 测试框架：pytest + asyncio + FakeLLMProvider

**问题**：Agent 项目依赖 LLM API，如何设计一个既能充分测试又不依赖网络和 API Key 的测试框架？

**决策**：`pytest + pytest-asyncio + FakeLLMProvider` 三层架构。

**FakeLLMProvider 的设计哲学**：

```python
# 核心设计：确定性 + 可控制
provider = FakeLLMProvider(responses=["A", "B", "C"])
response = await provider.generate(request)
assert response.content == "A"       # 完全确定的输出
assert provider.request_count == 1   # 可断言 LLM 被调用次数
```

| 设计原则 | 实现方式 | 为什么重要 |
|---------|---------|----------|
| **确定性** | 按序返回预定义 responses | 同一测试永远返回相同结果 |
| **可观察** | `request_count`、`last_request` | 断言 Agent 调用 LLM 的次数 |
| **快速反馈** | 无网络 I/O | 核心行为可在本地确定性回归，不受模型响应波动影响 |
| **循环返回** | `set_responses()` 动态修改 | 模拟多轮对话的不同回复 |

### 2.5 文档引擎：MkDocs Material vs Sphinx vs Docusaurus

| 维度 | Sphinx | Docusaurus | **MkDocs Material** ✅ |
|------|--------|-----------|----------------------|
| 标记语言 | RST（学习曲线陡） | MDX（React 绑定） | **Markdown（最通用）** |
| Python API 文档 | 原生 autodoc | 需手动维护 | **mkdocstrings 插件** |
| Mermaid 集成 | 需插件 | ✅ | ✅ |
| 搜索 | 内置 | Algolia | **内置 + 搜索建议** |

**决策**：MkDocs Material——Markdown 优先、Material 主题成熟、`mkdocstrings` 自动生成 API 文档、内置 Mermaid 支持。

### 2.6 构建系统：hatchling vs setuptools vs flit

| 维度 | setuptools | flit | poetry-core | **hatchling** ✅ |
|------|-----------|------|------------|-----------------|
| 配置复杂度 | 高 | 低 | 中 | **极低** |
| PEP 621 | 部分 | ✅ | ✅ | ✅ |
| 扩展性 | 高 | 低 | 中 | **插件系统** |

**决策**：`hatchling`——零配置、PyPA 官方推荐、与 `uv` 无缝协作。

### 2.7 面试话术：技术选型的一分钟电梯演讲

> "这个项目的技术选型围绕三个原则：**速度、简洁、可维护**。速度体现在用 Rust 生态的 `uv` 和 `ruff` 替代传统的 `pip` 和 `flake8+black`，实测安装和 lint 都快了 10-100 倍。简洁体现在所有工具的配置都在一个 `pyproject.toml` 里。可维护体现在 `mypy strict`——在 Agent 这种异步、多模块的项目中，类型系统充当了重构安全网和活文档。"

---

## 第三章　架构设计：Monorepo + 分层架构

### 3.1 为什么是 Monorepo 而不是多仓库

| 维度 | 多仓库 | **Monorepo** ✅ |
|------|-------|----------------|
| 代码共享 | 需发布包 | **直接 import** |
| 原子提交 | 跨仓库 PR | **单次 commit** |
| CI 复杂度 | 每个仓库独立配置 | **统一工作流** |
| 依赖管理 | 需维护版本矩阵 | **uv.lock 统一锁定** |

**额外考量**：Agent 各模块间有密集内部依赖（types → base → agents → pipeline），拆分仓库会增加接口维护成本。

### 3.2 六层架构设计

这是 P0 确立的**目标分层**。当前落地的是第 1 层，以及 P1 在第 3/4 层的
论文阅读纵向切片；P5 的基础设施和 P6 的 API/UI 尚未实现。

```
┌─────────────────────────────────────┐
│  Web UI (React)                     │  第6层：用户交互
├─────────────────────────────────────┤
│  API Gateway (FastAPI)              │  第5层：服务接口
├─────────────────────────────────────┤
│  Agent Pipeline (6 Agents)          │  第4层：业务流程
├─────────────────────────────────────┤
│  Domain Services (paper/reproduction)│  第3层：领域服务
├─────────────────────────────────────┤
│  Infrastructure (memory/knowledge/mcp)│ 第2层：基础设施
├─────────────────────────────────────┤
│  Core (types/base/providers)        │  第1层：核心抽象
└─────────────────────────────────────┘
```

**依赖方向**：上层依赖下层，下层不感知上层（Dependency Inversion）。

### 3.3 依赖分层策略（optional-dependencies）

按功能模块拆分可选依赖：

```
dependencies（核心，必须装）
├── pydantic, httpx, tiktoken, structlog, pyyaml, rich, tenacity
│
optional-dependencies（按需安装）
├── pdf     → PyMuPDF（PDF 解析，~50MB）
├── memory  → chromadb（向量存储，~200MB）
├── kg      → neo4j（知识图谱，~100MB）
├── api     → fastapi + uvicorn（服务端）
├── docker  → docker SDK（实验执行）
├── mlflow  → mlflow（实验追踪）
├── openai   → openai（LLM 调用）
├── anthropic → anthropic（Claude）
└── all      → 全部安装（开发/演示用）
```

### 3.4 面试话术

> "架构上采用六层分层，核心理念是**依赖倒置**——上层依赖下层抽象，不依赖具体实现。这保证了 Agent 核心（ReAct 循环）可以独立演进，不感知底层是用 ChromaDB 还是 Pinecone 做向量存储。"

---

## 第四章　Agent 系统：为什么 6 个 Agent + 双执行模式

### 4.1 Agent 数量设计：为什么是 6 个

**问题**：为什么是 6 个 Agent 而不是 1 个全能 Agent 或 20 个微 Agent？

**决策逻辑**：按**职责边界**和 **Prompt 复杂度**拆分。

| 如果合并 | 问题 | 拆分后 | 收益 |
|---------|------|-------|------|
| 1 个 Agent 包揽全部 | Prompt 过于复杂（5000+ token），LLM 容易遗漏步骤 | 6 个各司其职 | 每个 system prompt < 500 token |
| 导读 + 方法分析 合并 | 上下文窗口冲突 | PaperReader + Methodologist | 各自有完整上下文 |
| 代码生成 + 实验执行 不分离 | 生成代码后无自动执行 | CodeForger → Experimentor 流水线 | 自动化链式流程 |

**6 个目标 Agent 的职责边界**（当前仅 `PaperReader` 已实现）：

| Agent | 输入 | 输出 | 核心 Prompt |
|-------|------|------|------------|
| **PaperReader** | PDF/arXiv ID | 分层摘要 + 结构化笔记 | "逐节分析论文" |
| **Methodologist** | PaperReader 输出 | 算法伪代码 + 架构描述 | "提取算法、模型架构和训练配置" |
| **MathChecker** | Methodologist 公式 | 推导验证报告 | "逐行检查公式推导正确性" |
| **CodeForger** | Methodologist 算法 | 可运行 PyTorch 代码 | "将算法伪代码翻译为 PyTorch 实现" |
| **Experimentor** | CodeForger 代码 | 实验记录（MLflow） | "在 Docker 中执行训练和评估" |
| **Verifier** | 实验记录 + 论文指标 | 复现报告 | "对比实验指标与论文声称值" |

### 4.2 ReAct + Plan-Execute 双模式

**决策矩阵**：

| 任务类型 | 推荐模式 | 原因 |
|---------|---------|------|
| 论文导读（不确定路径） | ReAct | 边读边决定下一步关注哪个章节 |
| 论文复现（确定路径） | Plan-Execute | 先规划复现清单，再逐步执行 |
| 多论文综述 | Plan-Execute | 先规划检索策略，再批量执行 |

**阶段状态**：P0/P1 只实现 ReAct。P3 计划先在 CodeForger/Experimentor
内部实现可审计的 Plan-Execute 风格流程；当前 `AgentConfig` 没有
`execution_mode` 字段，不能宣称可动态切换。

### 4.3 Agent 间通信协议

以下协议是目标设计词汇，尚不是可导入或可调用的公共 API：

| 协议 | 语义 | 使用场景 |
|------|------|---------|
| **Handoff** | 完整移交任务和上下文 | PaperReader → Methodologist |
| **Delegate** | 分配子任务，收集结果 | Orchestrator 分配章节 |
| **Broadcast** | 通知所有 Agent | 论文更新/变更通知 |

### 4.4 为什么不用 LangChain / CrewAI / AutoGen

**面试黄金问题，核心回答**：

> "LangChain 是优秀的生产工具，但它解决的是'如何快速地串起 LLM 和工具'这一工程问题。我的项目核心挑战是**领域模型设计**——如何表示论文、算法、实验结果这些概念，以及在它们之间建立正确的工作流。
>
> 具体来说：
> 1. **类型系统**：LangChain 的 `Document`/`Chain` 等抽象不适配论文复现场景。我需要 `Algorithm`、`Architecture`、`ExperimentConfig` 这些论文特化的 Pydantic 模型
> 2. **评测体系**：LangChain 的 eval 框架面向对话质量，我需要的是论文复现准确率
> 3. **学习深度**：自己实现 ReAct 循环让我真正理解了 Agent 每一步——think、act、observe 的状态转换、token 消耗追踪、异常恢复。如果用 LangChain，面试时被问'Agent 内部怎么工作的'就可能回答不深
>
> 这不是说 LangChain 不好，而是对于'展示技术深度'这个目标，自建框架是更优解。"

### 4.5 MCP 协议：P6 计划如何实现

P6 将优先遵循正式 MCP 规范，并让 MCP 复用统一 application service，而不是
在 transport 层复制业务逻辑。是否基于官方 SDK 或实现薄适配层，应在 P6
根据兼容性、维护成本和 contract tests 决定。计划中的收益是：
1. **理解协议细节**：能解释 JSON-RPC 消息格式、stdio/SSE 双传输的原理
2. **定制化**：论文特有的数据结构（LaTeX 公式、BibTeX 引用）需要定制的 MCP Resource 定义
3. **集成一致性**：tool schema 与 application service DTO 共源

### 4.6 面试话术

> "目标架构按职责拆成 6 个专项 Agent，但当前只完成了 PaperReader。P0/P1
> 使用可验证的 ReAct 生命周期；P2 先交付带证据的 Methodologist，P3 再为
> 代码生成和实验引入可审计的 Plan-Execute 风格流程。Handoff、Delegate 和
> Broadcast 仍是后续编排设计，不是当前公共 API。"

---

## 第五章　工程质量：5 层防护体系

### 5.1 质量防线分层

```
第0层：EditorConfig      → 统一缩进、换行符（跨 IDE）
第1层：pre-commit        → 提交前自动检查（ruff + mypy + 基础安全）
第2层：ruff format-check → CI 格式检查
第3层：ruff lint         → CI 代码质量
第4层：mypy strict       → CI 类型检查
第5层：pytest matrix     → Python 3.11/3.12/3.13 矩阵测试
```

**分层逻辑**：越靠近开发者（第 0-1 层）检查越快，越靠近合并（第 4-5 层）越严格。

### 5.2 Conventional Commits 的价值

```
<type>(<scope>): <description>
```

| 收益 | 说明 |
|------|------|
| 自动生成 CHANGELOG | bumpver 按类型分组生成版本日志 |
| 语义化版本号 | `feat` → MINOR bump, `fix` → PATCH bump, `BREAKING CHANGE` → MAJOR bump |
| Git 历史可读性 | 一眼看出每个 commit 是功能、修复还是重构 |

### 5.3 测试金字塔的 Agent 适配

**核心创新：FakeLLMProvider**。传统测试依赖真实 LLM API——慢、不确定、花钱。FakeLLMProvider 返回预定义响应——确定、秒级、零成本。

```python
# FakeLLMProvider 模式
provider = FakeLLMProvider(responses=["deterministic output"])
result = await agent.run(task)  # 任意次数 → 相同结果
assert result.status == "success"
```

| 测试层 | 用 FakeLLM? | 耗时 | 运行时机 |
|--------|-----------|------|---------|
| Unit | ✅ | < 1s | 每次 save |
| Integration | ✅ | < 5s | pre-commit / CI |
| E2E | ❌（真实 API） | 30s-2min | CI 保护分支 |

### 5.4 覆盖率目标设定的依据

| 层级 | 目标 | 依据 |
|------|------|------|
| Unit | ≥ 90% | 核心类型系统和 Agent 循环是项目基石 |
| Integration | ≥ 70% | 管道测试覆盖主要路径，边角情况由单元测试覆盖 |
| E2E | ≥ 50% | 端到端测试昂贵，覆盖核心场景即可 |

### 5.5 面试话术

> "工程质量体现在从本地格式检查到 CI 的 Ruff、mypy strict 和多 Python
> 版本测试。FakeLLMProvider 把模型输出变成确定性 fixture，使 Agent 生命周期、
> 工具调用和失败路径可离线回归；真实 Provider 再由独立 smoke test 覆盖。"

---

## 第六章　P5 规划：Memory、Artifact 与知识图谱

本章是 P5 设计论证。当前 `memory/` 和 `knowledge/` 只是空命名空间，尚无
ChromaDB/Neo4j adapter、schema、迁移或跨存储一致性实现。

### 6.1 为什么需要三阶记忆

| 维度 | 纯上下文窗口 | 三阶记忆 |
|------|-----------|---------|
| 容量 | 128K-200K tokens | **由持久化配额控制，可扩展但并非无上限** |
| 持久性 | 会话结束即丢失 | **跨会话持久** |
| 检索效率 | 全量处理（慢、贵） | **按需检索（快、省 token）** |
| 结构化查询 | 不支持 | **计划由 Neo4j/Cypher 与 NetworkX adapter 提供** |

**三阶对应三种记忆类型**：

| 记忆层 | 类比人类记忆 | 存储后端 | 检索方式 |
|--------|-----------|---------|---------|
| **Working** | 当前注意力 | Agent 上下文窗口 | 全量可用 |
| **Episodic** | 经历/事件 | ChromaDB 向量库 | 语义相似度 |
| **Semantic** | 知识/概念 | Neo4j 知识图谱 | 图查询 |

### 6.2 向量库选型对比

| 维度 | ChromaDB | Milvus | Pinecone | Qdrant |
|------|---------|--------|---------|--------|
| 部署复杂度 | **低（pip install）** | 高（需 K8s） | 无（SaaS） | 中 |
| 免费使用 | ✅ | ✅ | ❌（免费层有限） | ✅ |
| 单元测试 | **in_memory=True** | 需 Docker | ❌ | 需 Docker |

**决策**：ChromaDB——本地开发体验极好、`in_memory=True` 支持零依赖测试、内置 embedding function。

### 6.3 知识图谱选型：Neo4j + NetworkX 双后端

| 模式 | 后端 | 适用场景 |
|------|------|---------|
| 轻量模式 | NetworkX 内存图 | 开发/测试，不依赖外部服务 |
| 生产模式 | Neo4j | 完整图数据库功能 + 浏览器可视化 |

### 6.4 混合检索策略

```
查询 "ImageNet classification with attention"
        │
        ├─► Dense Embedding → 语义相关的 Top-K
        ├─► BM25 关键词    → 精确匹配的 Top-K
        ├─► 知识图谱推理   → 结构化关系查询
        └─► Cross-encoder Reranker → 融合排序 → Top-N
```

### 6.5 论文知识图谱 Schema

```
(Paper) → PROPOSES → (Method)
(Paper) → CITES → (Paper)
(Paper) → EVALUATED_ON → (Benchmark) → CONTAINS → (Metric {name, value})
```

### 6.6 面试话术

> "P5 计划把版本化 artifact 作为事实源，再用 ChromaDB 和
> Neo4j/NetworkX 构建可重建索引。Working context 处理当前任务，Episodic
> index 支持语义召回，Semantic graph 表达论文、方法、数据集、指标和证据关系。
> 当前只完成了设计和依赖预留，尚未实现存储 adapter。"

---

## 第七章　开源策略

### 7.1 许可证选型：Apache 2.0 vs MIT vs GPL

| 维度 | MIT | Apache 2.0 | GPL v3 |
|------|-----|-----------|--------|
| 传染性 | 无 | 无 | **有** |
| 专利权保护 | 无 | **明确授权** | 有 |
| 企业使用友好度 | ★★★ | ★★★ | ★☆☆ |
| 与 PyTorch/TF 一致 | ❌（MIT 不涵盖专利） | ✅ | ❌ |

**决策**：Apache 2.0——专利保护明确、企业法务最熟悉、与 PyTorch/TensorFlow/K8s 生态一致。

### 7.2 贡献者阶梯设计

```
User ──(1 PR)──► Contributor ──(3 PRs + 1月)──► Reviewer
                                                      │
                                                 (2月活跃)
                                                      ▼
PMC ◄──(6月 + 投票)── Maintainer ◄──(2月 + 投票)───┘
```

### 7.3 社区文件的价值

| 文件 | 如果没有它 | 有了它 |
|------|---------|--------|
| CODE_OF_CONDUCT.md | 社区缺乏行为准则 | 明确的社区规范，保护贡献者 |
| CONTRIBUTING.md | 新人不知道如何参与 | 降低参与门槛 |
| GOVERNANCE.md | 决策过程不透明 | 公开的治理规则 |
| SECURITY.md | 漏洞无法安全上报 | 负责任的披露流程 |
| CITATION.cff | 无法被学术引用 | 论文可直接引用 |

### 7.4 面试话术

> "项目从 Day 1 按开源标准建设。许可证选 Apache 2.0——企业友好且有专利保护。贡献者阶梯从 User 到 PMC 五个层级。社区文件参考了 CNCF 和 Apache 基金会的模板。"

---

## 第八章　关键取舍：10 组二元决策

| # | 决策点 | 当前选择/规划 | 状态与理由 |
|---|--------|---------------|------------|
| 1 | 自建框架 vs 封装 LangChain | 小型自建 Core | P0 已完成，保持领域契约透明 |
| 2 | 同步 vs 异步 | async 接口 | P0/P1 已完成，适合 Provider I/O |
| 3 | DryRun vs 必须 GPU | dry-run 优先 | P3 规划，先验证 manifest 再消耗算力 |
| 4 | Provider 热切换 vs litellm | 薄 Provider 抽象 | P0/P1 已完成 OpenAI-compatible 路径 |
| 5 | 流式 vs 非流式 | Provider 双模式 | P1 已完成 Provider stream；SSE 属于 P6 |
| 6 | JSON Schema vs tool calling | OpenAI-compatible tool calling | P1 PaperReader 已使用 |
| 7 | Docker 隔离 vs宿主执行 | 受限 Docker | P3 规划，必须满足资源/网络/挂载限制 |
| 8 | 嵌入模型：本地 vs API | adapter 后决定 | P5 规划，索引必须记录 embedding 版本 |
| 9 | Pydantic v2 vs dataclasses | 边界模型优先 Pydantic | P0/P1 已采用，内部对象按需选择 |
| 10 | 动态规划 vs静态配置 | versioned schema/config | P2–P8 逐阶段冻结，避免隐藏默认值 |

### 8.1 面试话术：「自建 vs 框架」

> "P0/P1 自建了小型 Agent/Provider 边界，是为了让状态机、工具协议和失败语义
> 可测试，而不是排斥所有框架。P6 实现 MCP 时会优先规范兼容和维护成本；如果
> 官方 SDK 能减少协议漂移，就应复用 SDK，只把领域 DTO 和 application service
> 保持在自己的边界内。"

---

## 第九章　性能与安全

### 9.1 依赖体积控制

| 安装模式 | 包数量 | 安装体积 | 适用场景 |
|---------|-------|---------|---------|
| `pip install repro-forge` | ~15 | ~50MB | 只使用类型系统 |
| `pip install repro-forge[pdf,openai]` | ~30 | ~200MB | 论文导读 |
| `pip install repro-forge[all]` | ~120 | ~1.5GB | 完整开发 |

### 9.2 P7 规划：安全护栏三层设计

当前只有 Pydantic 边界校验和包镜像的非 root 用户等局部基础。输入注入检测、
工具策略、输出检查、身份权限和审计属于 P7，尚未实现。

```
Input → [Input Guard: Pydantic 校验 + 注入检测]
         →
    Agent 处理
         →
    [Tool Policy: 操作白名单 + 参数校验]
         →
    Tool 执行
         →
    [Output Guard: 抄袭检测 + 内容过滤]
         →
    Output
```

### 9.3 Docker 安全策略

- **多阶段构建**：builder（编译工具链）→ runtime（仅运行时依赖），减小攻击面
- **非 root 用户**：`USER reproforge`，最小权限原则
- **当前用途**：镜像入口是 `repro-forge` CLI，不是 API，也不是执行生成代码的沙箱
- **P3 最低门**：默认断网、资源/PID/磁盘/超时限制、只读 rootfs、受限挂载、secret 清理和可靠 cleanup

### 9.4 Token 感知的上下文管理

P1 用 `tiktoken` 做 chunk 估算，并在不可用时采用保守 fallback；当前没有通用的
滑动窗口或自动摘要压缩器。P2 及以后需要按 evidence 优先级分配上下文，并在
截断时保留可追踪的来源引用。

### 9.5 面试话术

> "当前安全基线包括 Pydantic 输入校验、受控的 P1 只读工具，以及非 root
> 包镜像。P3 在执行生成代码前必须加入最小沙箱控制；P7 再提供身份、策略、
> Guardrails 和审计。当前不能宣称已经有完整的注入检测或输出合规系统。"

---

## 第十章　P8 规划：如何量化 Agent 质量

当前验证结果是工程测试、静态检查、构建和 smoke test，不是模型质量 benchmark。
本章描述 P8 的评测设计。

### 10.1 多维度评测框架

| 评测维度 | 评测对象 | 指标 |
|---------|---------|------|
| 论文理解 | PaperReader | 问答准确率（vs 人类研究生） |
| 算法提取 | Methodologist | 伪代码完整性（vs 论文附录） |
| 代码正确性 | CodeForger | 可运行率 + 测试通过率 |
| 复现忠实度 | 全管道 | 指标偏差百分比 |
| 综述质量 | SurveyScribe | 覆盖度 + 引用准确率 |

### 10.2 评测方法对比

| 方法 | 原理 | 局限 | 对策 |
|------|------|------|------|
| **人工评测** | 领域专家打分 | 成本高、不可规模化 | 用于 golden set 标定 |
| **LLM-as-Judge** | 用更强 LLM 评判输出质量 | 可能存在偏差 | 多 Judge 交叉验证 + 人工抽查 |
| **自动指标** | BLEU/ROUGE/CodeBLEU | 与人类判断相关性弱 | 仅用于快速回归检测 |

### 10.3 LLM-as-Judge 的设计

```python
class LLMJudge:
    def evaluate(
        self,
        output: str,
        rubric: dict[str, float],
        reference: str | None = None,
    ) -> dict[str, float]:
        """
        rubric = {
            "accuracy": 0.3,      # 权重 30%
            "completeness": 0.25,  # 权重 25%
            "correctness": 0.45,   # 权重 45%
        }
        """
```

### 10.4 复现忠实度量化公式

```
Fidelity = (1 - Σ|claimed_i - reproduced_i| / claimed_i / N) × 100

其中:
  claimed_i    = 论文声称的第 i 个指标值
  reproduced_i = 复现得到的第 i 个指标值
  N            = 指标总数
```

### 10.5 面试话术

> "P8 会为各阶段分别建立确定性指标、人工 golden set 和必要的
> LLM-as-Judge 辅助评测。Judge 不能作为唯一真值，安全或核心正确性失败也不能
> 被平均总分抵消。当前 107 个测试只证明工程回归基线，不证明论文复现质量。"

---

## 第十一章　P8 规划：可观测性

P0/P1 已有进程内 `AgentTrace` 和 token usage；完整 OTel span/metrics/log
correlation、成本预算和发布 scorecard 尚未实现。

### 11.1 为什么 OTel 而不是 LangSmith

| 维度 | LangSmith | **OpenTelemetry** ✅ |
|------|----------|-------------------|
| 厂商锁定 | 是（LangChain 生态） | **否（开放标准）** |
| 学习价值 | 会用一个工具 | **会用一个标准（CNCF）** |
| 社区生态 | LangChain 生态内 | **Jaeger/Zipkin/Prometheus** |
| 可迁移性 | 离开 LangChain 即失效 | **任何语言、任何框架** |

### 11.2 Agent Trace 结构设计

```
AgentTrace（一次 Agent 执行）
  ├── run_id: "run_abc123"
  ├── agent_type: "paper_reader"
  ├── start_time → end_time
  └── steps:
       ├── TraceStep #0:
       │    ├── thought: "I should read Section 3..."
       │    ├── action: Action(tool="read_section", input={"section": "3"})
       │    └── observation: "Section 3 describes the attention..."
       ├── TraceStep #1: ...
       └── TraceStep #N: final_state → "done"
```

每个 TraceStep 对应一个完整 ReAct 轮次，携带 token 消耗和延迟指标。

### 11.3 成本追踪

```python
CostTracker.track(
    model="gpt-4o",
    prompt_tokens=1240,
    completion_tokens=350,
    latency_ms=2340,
)
# 按 Agent / 任务 / 会话聚合成本
```

### 11.4 面试话术

> "当前 `AgentTrace` 能记录 ReAct 步骤和 token usage。P8 计划把
> request/job/pipeline/agent/provider/tool/backend 统一映射到 OpenTelemetry，
> 并版本化价格表与发布 scorecard；这些平台能力目前尚未落地。"

---

## 第十二章　Multi-Provider LLM：为什么自建抽象层

### 12.1 为什么不用 litellm

| 维度 | litellm | **自建抽象层** ✅ |
|------|---------|-----------------|
| 包体积 | ~200MB+ | ~5KB |
| 学习深度 | 会用 API | **理解 Provider 抽象全链路** |
| 定制化 | 受限于 litellm 接口 | **完全自主** |

### 12.2 抽象层设计

```python
@dataclass
class LLMRequest:
    messages: list[dict[str, Any]]
    model: str = "gpt-4o"
    temperature: float = 0.0
    max_tokens: int = 4096
    tools: list[dict[str, Any]] | None = None

@dataclass
class LLMResponse:
    content: str
    model: str
    finish_reason: str = "stop"
    usage: dict[str, int]

class BaseProvider(ABC):
    async def generate(request: LLMRequest) -> LLMResponse
    async def generate_stream(request: LLMRequest) -> AsyncIterator[str]
```

### 12.3 降级策略

```python
async def generate_with_fallback(request, providers):
    for provider in providers:
        try:
            return await provider.generate(request)
        except (RateLimitError, TimeoutError):
            continue  # 自动 fallback 到下一个 provider
    raise AllProvidersFailed()
```

### 12.4 面试话术

> "项目用小型 `BaseProvider` 契约隔离模型调用，P1 已实现并验证
> OpenAI-compatible/DeepSeek 的生成、流式 stop 传播和 keyless 本地端点。
> Anthropic adapter 和跨 Provider 自动降级仍是规划，不能从可选依赖反推为
> 当前能力。"

---

## 第十三章　P3 规划：实验执行引擎

### 13.1 五层执行后端

```
首批：DryRun → 受限 local fixture → 受限 Docker（CPU 优先）

后续候选：Colab / SSH / VastAI；这些远程后端不属于 P3 首批交付。
```

**为什么先做 DryRun**：
1. 无需 GPU 即可验证整个管道的逻辑正确性
2. 代码生成、配置生成、报告生成全部可以 Done
3. 用户 review 通过后再投入 GPU 资源

### 13.2 CPU-only 是架构亮点

```python
class BaseExecutionBackend(ABC):
    @abstractmethod
    async def execute(self, code, config, dataset) -> ExecutionResult: ...

class DryRunBackend(BaseExecutionBackend):
    # 生成文件 + 模拟指标

class DockerBackend(BaseExecutionBackend):
    # 构建镜像 + 运行容器 + 收集指标

class ColabBackend(BaseExecutionBackend):
    # 推送代码到 Colab + 触发执行 + 拉取结果
```

以上类是设计草图，不是当前代码。P3 只有在 manifest、超时、资源限制、默认
断网、受限挂载、secret 清理和 cleanup 均有测试后，才能宣称 Docker execution
完成；否则最多只完成 dry-run。

### 13.3 面试话术

> "P3 计划先交付可审计 bundle、dry-run 和受限 Docker CPU 执行。远程 GPU
> 后端会在本地契约、凭据和计费风险处理成熟后再评估。当前没有 Experimentor
> 后端实现，因此不会把设计草图描述成已运行能力。"

---

## 第十四章　全文总结：三个版本的项目介绍

### 14.1 技术面试版（30 秒）

> "我开发了 ReproForge 的前两个阶段：P0 建立类型、ReAct、Provider、测试、
> CI 和包构建基线；P1 把本地 PDF/arXiv 转成可追踪的 `PaperNote`，支持
> OpenAI-compatible/DeepSeek Provider、token-aware chunking、pipeline 和 CLI。
> 当前基线是 107 个测试、Ruff、mypy、MkDocs 和 wheel smoke 全部通过；P2–P8
> 已冻结接口和验收计划，但尚未实现。"

### 14.2 HR 面试版（30 秒）

> "我在做一个开源项目 ReproForge，目标是逐阶段帮助研究者从阅读论文走向
> 可验证复现。目前已完成工程基础和论文阅读链路，并建立 CI、代码质量、环境
> 锁定、文档和开源治理；方法抽取、实验和验证按清晰的阶段门继续推进。"

### 14.3 非技术领导版（60 秒）

> "我在做一个能让研究者更高效复现论文的工具。背景是——读论文时经常遇到作者声称效果很好但代码不公开，或者环境对不上。大量研究时间浪费在'能不能跑通'上。
>
> 方案是把流程拆成可验收阶段：目前能把 PDF/arXiv 论文变成结构化阅读笔记；
> 后续再依次加入证据化方法抽取、代码与隔离实验、结果验证和知识沉淀。这样每
> 一步都能独立测试，而不是先声称一个尚不可验证的一条龙系统。
>
> 商业价值：如果作为 SaaS 服务提供给高校和企业，解决学术可复现性这一系统性问题，市场空间可观。这个方向目前没有成熟的商业产品，是蓝海。"

---

## 附录 A：Agent 框架横向对比

| 维度 | LangChain | CrewAI | AutoGen | Semantic Kernel | **ReproForge** |
|------|----------|--------|---------|----------------|---------------|
| 定位 | 通用 LLM 应用 | 多 Agent 协作 | 对话式 Agent | 企业级编排 | **论文复现专项** |
| Agent 模型 | Chain/Agent | Crew/Task | ConversableAgent | Plugin/Function | **6 专项 Agent** |
| MCP 支持 | ✅ | ❌ | ❌ | ❌ | **P6 规划** |
| 记忆系统 | 基础 | 无 | 无 | 基础 | **P5 规划** |
| 评测体系 | LangSmith 付费 | 无 | 无 | 无 | **P8 规划** |
| 学习深度 | 浅 | 浅 | 中 | 浅 | **深** |
| 面试可讲性 | 一般 | 一般 | 较好 | 一般 | **最佳** |

## 附录 B：论文复现生态对比

| 工具 | 做代码索引 | 做自动生成 | 做实验执行 | 做结果验证 |
|------|---------|---------|---------|---------|
| PapersWithCode | ✅ | ❌ | ❌ | ❌ |
| PaperQA | ❌ | ❌ | ❌ | ❌ |
| SWE-bench | ❌ | ❌ | ✅ | ❌ |
| **ReproForge** | ❌ | **✅** | **✅** | **✅** |

## 附录 C：推荐阅读

| 分类 | 论文/资源 |
|------|---------|
| Agent 架构 | ReAct (Yao et al., 2022), Plan-and-Solve (Wang et al., 2023), SWE-agent (Yang et al., 2024) |
| 多 Agent | AutoGen (Wu et al., 2023), ChatDev (Qian et al., 2023), CAMEL (Li et al., 2023) |
| MCP 协议 | Anthropic Model Context Protocol Specification |
| 可复现性 | Reproducibility in ML (Pineau et al., 2021), ML Reproducibility Challenge |
| 工程实践 | Python Packaging Guide (PyPA), Conventional Commits, OpenTelemetry Docs |
