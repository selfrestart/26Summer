# Methodology Analysis (P2)

P2 的 `MethodologyPipeline` 从论文抽取**证据化方法学结构**——算法、架构、
训练配置、评价协议，并把每个结论绑定到原文证据。

## 快速开始

```python
from repro_forge.paper.extractor import MethodologyPipeline

pipeline = MethodologyPipeline(provider=my_provider)
analysis = await pipeline.analyze_pdf("papers/attention.pdf")
print(analysis.model_dump_json(indent=2))
```

从 arXiv 直接分析：

```python
analysis = await pipeline.analyze_arxiv("1706.03762", output_dir="data/papers")
```

## 三种输入模式

| 入口 | 输入 | 说明 |
|------|------|------|
| `analyze(paper, paper_note=None)` | 已解析 `Paper` | 最灵活；可用 P1 `PaperNote` 作为线索 |
| `analyze_pdf(path, read_first=False)` | PDF 文件 | `read_first=True` 先跑 P1 阅读 |
| `analyze_arxiv(id, output_dir, read_first=False)` | arXiv ID | 自动下载 + 解析 |

## CLI

```powershell
# JSON Paper 文件 → MethodAnalysis JSON
uv run repro-forge analyze-json paper.json --output analysis.json

# PDF → MethodAnalysis JSON
uv run repro-forge analyze-pdf paper.pdf --output analysis.json

# 使用 P1 阅读笔记作为上下文
uv run repro-forge analyze-pdf paper.pdf --paper-note note.json
```

## 输出内容

```python
analysis.problem_statement          # 论文解决的问题
analysis.algorithms                 # 算法列表（含步骤与证据）
analysis.architecture               # 架构组件（参数 + 证据）
analysis.training_recipe            # 训练配置（每个值带状态和证据）
analysis.evaluation_protocol        # 评价协议
analysis.evaluation_protocol.reported_claims  # 唯一序列化的 claim 列表
analysis.reported_claims             # 兼容读取属性，指向同一列表
analysis.equations                  # 公式证据（captured/partial/not_available）
analysis.reproducibility_gaps       # 复现障碍清单
analysis.evidence_coverage          # 有证据声明的覆盖率
analysis.verified_claim_count       # 本地证据验证通过的 claim 数
analysis.extraction_trace           # step:tool:outcome，不含模型思维/论文正文
```

## 证据状态语义

| 状态 | 含义 | 示例 |
|------|------|------|
| `verified` | 原文可定位到匹配引用 | "We use Adam with lr=1e-4" |
| `inferred` | 模型推断 | 从上下文推断 batch 大小 |
| `conflicting` | 论文不同位置冲突 | 两章节写不同 epochs |
| `not_reported` | 论文未报告 | 未提 random seed |
| `unverified` | 引用无法本地匹配 | 章节名错误或版本漂移 |

**不要**把 `inferred`/`unverified` 当成 `verified` 使用——它们会误导下游
代码生成和结果核验。

## 离线示例

```bash
uv run python examples/analyze_methodology.py
```

使用内置样本论文和 Fake Provider，无需 API Key。

## 真实使用要求

- `openai` extra（或 `anthropic`/本地端点）
- `OPENAI_API_KEY` 或 `DEEPSEEK_API_KEY`
- PDF 输入需要 `pdf` extra；arXiv 输入需要 `arxiv` extra

详见 [P2 技术参考](../P2-TECHNICAL-REFERENCE.md)。
