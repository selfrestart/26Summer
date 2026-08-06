# P2 设计论证 — 为什么证据必须回到原文

> **状态**: ✅ 已完成
>
> **核心问题**: 方法学抽取（Methodology Extraction）如何做到可信？
> 答案：**每个结论都必须能追溯到论文章节和原文引用**，而不是"模型觉得对"。

---

## 第一章　为什么要做"证据化"方法抽取

### 1.1 问题的本质：LLM 抽取的幻觉风险

直接让 LLM "总结一下这篇论文的方法"会得到流畅但可能错误的结果：

| 幻觉类型 | 例子 | 后果 |
|---------|------|------|
| 编造超参数 | 论文没写 lr，模型说 "lr=1e-4" | P3 生成错误代码 |
| 补写公式 | PDF 文本层没公式，模型"重建"一个 | P4 数学核验基于假输入 |
| 错误归因 | 把 Related Work 的结论当成论文贡献 | 误导综述和对比 |
| 单位缺失 | "accuracy=94.5" 没说是 % 还是小数 | P4 无法比较 |
| 跨节冲突 | 两个章节写了不同的 batch size | 无法判断哪个对 |

**P2 的核心设计决策**：与其让模型"自由发挥"，不如给每个结论绑定：
- 它来自论文的哪个章节（`section_id`）
- 原文里确切的引用（`quote` + `quote_hash`）
- 它是论文明确说的、还是模型推断的（`EvidenceStatus`）

### 1.2 EvidenceStatus 五态设计

```
verified      原文中可定位到匹配证据        → 最可信
inferred      模型推断，论文没有直接陈述     → 可用于提示，不能当事实
conflicting   论文不同位置存在冲突          → 保留两处证据，标注矛盾
not_reported  论文未报告                   → 显式标记，绝不填默认值
unverified    提供了引用但本地无法匹配       → 可能引用错章节或版本漂移
```

**关键规则**：P2 输出必须保留状态，**禁止**把 `inferred` 或 `unverified` 自动提升为 `verified`。

---

## 第二章　Schema 设计决策

### 2.1 为什么 `EvidenceRef` 需要 hash 而不是只存章节名

| 方案 | 问题 |
|------|------|
| 只存 `section_title` | 标题重复、PDF 版本变化、章节改名 |
| 存 `section_title` + `quote` | 无法判断 quote 是否真的匹配 |
| **`source_hash` + `section_id` + `quote_hash`** | 内容哈希变化 → 旧引用失效，防版本漂移 |

`PaperEvidenceView` 对 canonical `Paper` 内容计算确定性 `source_hash`：
- 同一 Paper 两次解析 → 相同 hash
- 正文内容变化 → hash 变化 → 旧 `EvidenceRef` 失效（而不是静默复用）

### 2.2 为什么 `Quote` 要归一化而不是模糊匹配

PDF 文本层常有：
- 换行拆词：`multi-\nhead` → `multi-head`
- 多余空白、大小写差异

`normalize_quote()` 做**受控归一化**（去连字符断行、合并空白），然后做**精确子串匹配**。
**禁止**使用模糊匹配（如编辑距离）把完全不同的句子判为 verified——那会引入新的误判。

### 2.3 为什么 `EquationEvidence` 禁止模型补写公式

PDF 文本层经常丢失公式（公式渲染为图像）。如果让模型"重建"公式：
1. 重建的公式可能错误，但看起来正确
2. P4 MathChecker 会把错误的公式当成论文声明来验证

**决策**：`parse_status = captured / partial / not_available`。
捕获不到就显式标记 `not_available` 并输出 reproducibility gap，**绝不补写**。

### 2.4 为什么 `ReportedClaimDraft` 保留 raw 值

P4 Verifier 需要比较"论文声称值 vs 复现值"。如果 P2 就做归一化（比如把 "94.5%" 转成 0.945）：

| 问题 | 说明 |
|------|------|
| 单位猜测 | 模型可能猜错单位 |
| 丢失原文 | 归一化后无法回溯到原始表达 |
| P4 无法验证 | 比较逻辑失去了原始输入 |

**决策**：P2 只抽取 `reported_value`（原始字符串）+ `raw_text` + `unit`/`scale` 字段，
不判断正确性、不做数值归一化。可比性判断属于 P4。

---

## 第三章　Methodologist Agent 设计

### 3.1 为什么继续用 ReAct 而不是 Plan-Execute

P2 规划曾考虑引入 Plan-Execute，但最终**继续使用 ReAct**：

1. **复用已验证的运行时**：P0 的 BaseAgent + ReAct 生命周期、trace、repair 都经过测试
2. **方法章节命名不统一**：论文用 Method/Approach/Architecture/Model 等各种标题，需要边读边决定
3. **风险聚焦**：P2 的新增风险是"证据正确性"，不应同时修改核心执行模型
4. **评估时机**：等 P3 有确定的代码生成步骤后，再评估 Plan-Execute 是否值得

### 3.2 工具集合：只读优先

| 工具 | 参数 | 为什么只读 |
|------|------|----------|
| `list_sections` | 无 | 了解结构 |
| `read_section` | `section_title`, `chunk_index` | 读取有边界原文 |
| `search_paper` | `query` | 定位超参/指标/公式 |
| `get_paper_note` | 无 | P1 摘要作为线索 |

P2 **不引入通用 MCP/tool registry**——共享逻辑抽成 `PaperEvidenceView`，
供 PaperReader 和 Methodologist 复用，避免 P1/P2 行为漂移。

### 3.3 修复策略：一次 repair，失败即 FAILED

```
模型输出 JSON
  → Pydantic 校验
  → 本地验证所有 EvidenceRef（source_hash/section/quote）
  → 计算 evidence coverage
  → 若有错误 → 一次 repair 请求
  → 再次失败 → FAILED（不生成伪成功分析）
```

与 P1 不同：P2 **不允许**把非 JSON 输出降级为 `tldr` 后算成功。
因为 P3 需要稳定的结构化输入，伪成功会污染下游。

---

## 第四章　Pipeline 与公共 API

### 4.1 为什么新建 MethodologyPipeline 而不是扩大 PaperPipeline

P1 的 `PaperPipeline` 职责是"解析 + 阅读笔记"。如果直接把方法抽取加进去：

- 单一类承担两个 Agent 的编排，职责膨胀
- P1 行为可能被 P2 需求破坏（回归风险）

**决策**：新建 `MethodologyPipeline` 作为组合根（composition root），
注入 P1 `PaperPipeline` 和 `Methodologist`，不改 P1 的公共 API。

### 4.2 `read_first` 语义

| 值 | 行为 | 适用场景 |
|----|------|---------|
| `False`（默认） | 直接从 Paper 做方法抽取 | 省一次 LLM 阶段，快 |
| `True` | 先跑 P1 PaperReader，Methodologist 接收 PaperNote | 需要摘要/贡献线索 |

用户已提供 `PaperNote` 时**不重复**运行 PaperReader。

### 4.3 为什么从子包导出而不是顶层

P2 的 schema 和行为在 P3 消费后可能微调。从 `repro_forge.agents` 和
`repro_forge.paper.extractor` 导出（而非顶层 `repro_forge`），
避免过早承诺过宽的顶层 API。

---

## 第五章　测试策略

### 5.1 测试矩阵（确定性优先）

| 风险 | 测试验证 |
|------|---------|
| 模型编造 quote | quote 不存在时不能标记 verified |
| 版本漂移 | 相同 Paper 重复生成相同 hash；内容变化旧引用失效 |
| 未知页码 | P1 的 `0` 在 P2 view 边界转换为 `None` |
| 公式丢失 | `parse_status="not_available"` + gap，不让模型补写 |
| claim 单位缺失 | 保留 raw value，标记缺失 |
| 错误章节归因 | quote 在其他章节时返回 mismatch |
| 未报告超参数 | `not_reported`，不填默认值 |
| 多方法论文 | `algorithms[]` 支持多方法 + 组件级 evidence |
| 并行工具调用 | call id 全部闭合 |
| 重复运行 | trace/conversation/evidence 状态独立 |

### 5.2 工程指标 vs 模型指标

- **阻断性工程指标**：测试、类型、lint、构建、schema、证据验证全部通过
- **记录但不作为成功声明**：evidence coverage、verified 比例、token 用量

P2 完成 ≠ 通用算法抽取达到 benchmark 水平。完整评测框架属于 P8。

---

## 第六章　与 P1 的边界

| 维度 | P1（已完成） | P2（本次完成） |
|------|-------------|--------------|
| 输出 | `PaperNote`（阅读笔记） | `MethodAnalysis`（方法学结构） |
| 证据 | 无强制要求 | **每个关键结论绑定 EvidenceRef** |
| 失败处理 | 非 JSON 降级为 tldr | 一次 repair，失败 FAILED |
| 消费方 | 人类阅读 | P3 CodeForger、P5 知识图谱 |

**P2 不破坏 P1**：107 个 P1 历史测试继续回归通过；截至 2026-08-06，
全项目为 175 个测试。

---

## 面试话术：P2 总结

> "P2 解决了 LLM 抽取方法学的信任问题。核心设计是**证据可追溯**——每个算法步骤、训练参数、指标声明都绑定 `EvidenceRef`（章节 ID + 原文引用 + 内容哈希），并区分 verified / inferred / conflicting / not_reported / unverified 五种状态。
>
> 两个关键防幻觉机制：公式用 `EquationEvidence` 显式标记捕获状态，捕获不到就标 not_available 而不是让模型补写；论文声称值用 `ReportedClaimDraft` 保留原始字符串和单位，不提前归一化。
>
> 技术上实现了只读证据层 `PaperEvidenceView`（确定性哈希 + 引用验证）、ReAct 驱动的 `Methodologist`（一次 repair 失败即 FAILED）、组合层 `MethodologyPipeline`（注入 P1 pipeline 不破坏其 API），以及 analyze-pdf/analyze-json CLI。截至 2026-08-06，全项目 175 个测试通过，覆盖率 86.34%。"
