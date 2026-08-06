# P2 技术参考 — 方法学抽取模块完整说明

> **状态**: ✅ 已完成
>
> 本文档描述 P2 的模块、API、CLI、配置和测试方法。所有示例基于当前代码。

---

## 第一章　模块概览

### 1.1 新增文件

```
repro_forge/
├── paper/
│   └── extractor/
│       ├── __init__.py    # 公共导出（MethodAnalysis, MethodologyPipeline, ...）
│       ├── schemas.py     # 方法学数据模型（EvidenceRef, MethodAnalysis, ...）
│       ├── evidence.py    # PaperEvidenceView 只读证据层
│       └── pipeline.py    # MethodologyPipeline 组合层
├── agents/
│   ├── __init__.py        # 新增 Methodologist 导出
│   └── methodologist.py   # Methodologist Agent
├── cli.py                 # 新增 analyze-pdf / analyze-json 命令

tests/
├── unit/
│   ├── test_methodology_schemas.py   # schema round-trip + golden fixture
│   ├── test_evidence.py              # 哈希/引用验证
│   ├── test_methodologist.py         # Agent 生命周期
│   ├── test_methodology_pipeline.py  # Pipeline 组合
│   ├── test_public_api.py            # 公共导出
│   └── test_cli.py                   # CLI 命令
├── integration/
│   └── test_methodology_flow.py      # 端到端流程

examples/
└── analyze_methodology.py            # 离线示例（Fake Provider）
```

---

## 第二章　数据模型（schemas.py）

### 2.1 EvidenceStatus（五态）

| 值 | 含义 |
|----|------|
| `verified` | 原文可定位到匹配证据 |
| `inferred` | 模型推断，论文未直接陈述 |
| `conflicting` | 论文不同位置冲突 |
| `not_reported` | 论文未报告 |
| `unverified` | 提供了引用但本地无法匹配 |

### 2.2 EvidenceRef（证据引用）

```python
EvidenceRef(
    evidence_id="",        # 本次分析内稳定 ID
    paper_id="1706.03762",
    source_hash="abc123",  # 论文内容哈希（16 位 hex）
    section_id="sec_01_...",  # 确定性章节 ID
    section_title="Model Architecture",
    page_start=5,          # 1-based；未知为 None（P2 边界由 0 转换）
    page_end=None,
    quote="multi-head self-attention",
    quote_hash="...",      # 归一化 quote 哈希
    chunk_index=None,
    status=EvidenceStatus.VERIFIED,
    confidence=1.0,
)
```

### 2.3 EquationEvidence（公式证据）

```python
EquationEvidence(
    equation_id="eq_1",
    label="(1)",                    # 论文公式编号；无则 None
    raw_text="Attention(Q,K,V)=...", # 必须来自论文实际文本
    normalized_text="",
    parse_status="captured",        # captured / partial / not_available
    symbol_hints={},                # 仅供 P4 建立符号表候选
    evidence=EvidenceRef(...),
)
```

### 2.4 ReportedClaimDraft（声明草稿）

```python
ReportedClaimDraft(
    claim_id="c_1",
    dataset="WMT 2014 En-De",
    split="",                       # 缺失保留为空
    metric_name="BLEU",
    reported_value="28.4",          # 原始字符串，不做数值归一化
    raw_text="",
    unit="",                        # 缺失不猜测
    scale="",
    direction="",
    status="verified",
    evidence=EvidenceRef(...),
)
```

### 2.5 MethodAnalysis（顶层输出）

```python
MethodAnalysis(
    paper_id="1706.03762",
    title="Attention Is All You Need",
    problem_statement="...",
    algorithms=[AlgorithmSpec(...)],
    architecture=[ArchitectureComponent(...)],
    training_recipe=TrainingRecipe(...),
    evaluation_protocol=EvaluationProtocol(
        reported_claims=[ReportedClaimDraft(...)],
    ),
    equations=[EquationEvidence(...)],
    assumptions=[...],
    reproducibility_gaps=[ReproducibilityGap(...)],
    evidence_coverage=0.86,
    total_tokens_used=0,
    extraction_trace=["0:list_sections:ok", "1:finalize:ok"],
)
```

`evidence_coverage` 由代码确定性计算（有 quote 的 evidence 占比），模型不能自行填百分比。
`evaluation_protocol.reported_claims` 是 claim 的唯一序列化位置；旧版顶层输入会
自动迁移，`analysis.reported_claims` 是只读兼容视图。`extraction_trace` 仅保留
`step:tool:outcome`，不会暴露模型思维或论文正文。

---

## 第三章　证据层（evidence.py）

### 3.1 PaperEvidenceView

```python
from repro_forge.paper.extractor import PaperEvidenceView

view = PaperEvidenceView(paper, chunk_size=4000)

view.source_hash          # str: 确定性内容哈希
view.section_ids          # dict[str, str]: unique title/alias → section_id
view.section_titles()     # 重复标题会变成 "Method", "Method [2]"
view.read_section(title, chunk_index=0)  # str
view.search(query)        # list[dict]: [{section_title, section_id, snippet}]
view.list_sections()      # str（agent 友好格式）
view.verify_quote_location(quote, section_title)  # bool
view.verify_evidence(evidence_ref)  # "verified" | "unverified"
```

### 3.2 归一化规则

```python
normalize_quote("multi-\nhead\n  attention")  # → "multi-head attention"
```

1. 连字符断行：`-\n` → `-`
2. 其余换行 → 空格
3. 连续空白 → 单空格

**不使用模糊匹配**；归一化后做精确子串匹配。

---

## 第四章　Methodologist Agent

### 4.1 使用

```python
from repro_forge.agents import Methodologist
from repro_forge.core.types import AgentConfig, AgentType
from repro_forge.paper.extractor import PaperEvidenceView
from repro_forge.providers.openai_provider import OpenAIProvider

# 从 OPENAI_* / DEEPSEEK_* 环境变量解析 endpoint、key 和 model。
provider = OpenAIProvider()
methodologist = Methodologist(
    config=AgentConfig(agent_type=AgentType.METHODOLOGIST, max_steps=15),
    provider=provider,
)
view = PaperEvidenceView(paper)
analysis = await methodologist.analyze(view, paper_note=note)  # note 可选
```

`provider` 是必需依赖。未在 `AgentConfig` 显式填写 `model` 时继承 provider
模型；显式模型不会被覆盖。

### 4.2 工具集合

| 工具 | 参数 | 行为 |
|------|------|------|
| `list_sections` | 无 | 返回所有章节标题 |
| `read_section` | `section_title`, `chunk_index=0` | 返回受 token 预算约束的章节块；越界返回提示 |
| `search_paper` | `query` | 返回最多 5 条带章节的摘要 |
| `get_paper_note` | 无 | 返回 P1 摘要线索或 unavailable |

### 4.3 修复策略

1. JSON 解析失败 → 一次 repair 请求
2. 结构校验失败（缺 problem_statement / 算法缺名 / claim 缺 dataset）→ 一次 repair
3. 两次失败 → `RuntimeError("Methodologist failed: ...")`
4. repair 前后的步骤都保留在脱敏 `extraction_trace` 中

---

## 第五章　MethodologyPipeline

### 5.1 构造与注入

```python
from repro_forge.paper.extractor import MethodologyPipeline
from repro_forge.paper.pipeline import PaperPipeline

pipeline = MethodologyPipeline(
    paper_pipeline=PaperPipeline(provider=provider),
    methodologist=methodologist,          # 或只传 provider 自动创建
)
```

### 5.2 方法

| 方法 | 参数 | 返回 |
|------|------|------|
| `analyze(paper, paper_note=None)` | 已解析 Paper | `MethodAnalysis` |
| `analyze_pdf(path, read_first=False)` | PDF 路径 | `MethodAnalysis` |
| `analyze_arxiv(arxiv_id, output_dir, read_first=False)` | arXiv ID | `MethodAnalysis` |

`read_first=True` 时先运行 P1 PaperReader 生成 PaperNote 作为上下文。
用户已提供 note 时不重复运行。

---

## 第六章　CLI

### 6.1 命令

```powershell
# 方法学抽取（JSON Paper 文件）
uv run repro-forge analyze-json paper.json --output analysis.json

# 方法学抽取（PDF）
uv run repro-forge analyze-pdf paper.pdf --output analysis.json

# 可选参数
--paper-note note.json   # P1 PaperNote 作为上下文
--read-first             # 先运行 P1 PaperReader
```

### 6.2 Provider 配置

复用 P1 的环境变量规则（优先级从高到低）：

1. `OPENAI_API_KEY` + `OPENAI_BASE_URL` + `OPENAI_MODEL`
2. `DEEPSEEK_API_KEY` + `DEEPSEEK_BASE_URL` + `DEEPSEEK_MODEL`
3. 本地端点（localhost/私有 IP）免 key

### 6.3 输出

UTF-8 JSON，完整保留 `EvidenceRef`、`None` 页码、raw/status 字段。
**不丢弃** provenance，**不填充**缺失单位/split/公式。

---

## 第七章　测试

### 7.1 P2 测试映射

| 文件 | 覆盖 |
|------|------|
| test_methodology_schemas.py | schema round-trip、golden fixture、旧 claim 迁移 |
| test_evidence.py | 哈希、引用、bounded chunk、重复标题和归一化 |
| test_methodologist.py | 成功/repair/失败、并行 native tools、模型继承、trace |
| test_methodology_pipeline.py | 组合、note、read_first、缺 provider |
| test_public_api.py | 公共导出路径 |
| test_cli.py | help、capabilities、analyze-json |
| test_methodology_flow.py (integration) | 端到端 + JSON round-trip |

### 7.2 运行

```bash
uv run pytest tests/ -q          # 当前基线：175 passed
uv run ruff check repro_forge tests
uv run mypy repro_forge
```

---

## 第八章　示例

```bash
uv run python examples/analyze_methodology.py
```

输出 Transformer 论文的：问题陈述、算法步骤、架构组件、训练配置、
报告声明（含 evidence quote）和可复现性缺口。

---

## 附录：常见问题

### Q: evidence_coverage 是什么？

有非空 quote 的 `EvidenceRef` 占所有 `EvidenceRef` 的比例。由代码计算，模型不填。

### Q: 为什么 page_start 是 None 而不是 0？

P1 用 `0` 表示未知页码。P2 边界把 `0` 转换为 `None`，避免 JSON round-trip 恢复 sentinel。

### Q: 模型输出乱 JSON 会怎样？

触发一次 repair 请求；仍失败则返回 FAILED（`RuntimeError`），不生成伪成功分析。
