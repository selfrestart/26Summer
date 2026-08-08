# 测试策略

本文档描述 ReproForge 的测试策略、工具和最佳实践。当前测试覆盖 P0 核心运行时、
P1 论文阅读、P2 证据化方法抽取，以及 P3 bundle/CodeForger/runner 安全边界。
P3-C 真实 Docker smoke 已通过；P4-P8 仍为未来阶段。

---

## 测试哲学

ReproForge 采用 **测试金字塔** 模型：

```
         ╱  E2E  ╲         少而精，验证完整用户场景
        ╱─────────╲
       ╱ Integration ╲     验证模块间协作，使用 Mock
      ╱───────────────╲
     ╱      Unit       ╲   大量，快速，每个函数都要测
    ╱───────────────────╲
```

### 核心原则

1. **单元测试不调用真实 LLM** — 用 `FakeLLMProvider` 替代
2. **每个 PR 必须带测试** — 新增代码对应新增测试
3. **测试即文档** — 测试用例应该展示 API 的正确用法
4. **快速反馈** — 全部单元测试应在 5 秒内完成

---

## 测试工具

| 工具 | 用途 |
|------|------|
| `pytest` | 测试框架 |
| `pytest-asyncio` | 异步测试支持 |
| `pytest-cov` | 覆盖率报告 |
| `testcontainers` | Docker 容器集成测试（Neo4j, ChromaDB） |
| `coverage` | 覆盖率指标 |

---

## 运行测试

```bash
# 全量测试（Windows/Linux 通用）
uv run pytest -q

# 带覆盖率报告
uv run pytest -q

# 端到端测试（需要服务运行）
# 质量检查
uv run ruff check repro_forge tests
uv run ruff format --check repro_forge tests
uv run mypy repro_forge

# 跳过 LLM 标记的测试
uv run pytest -m "not llm"

# 只跑 LLM 测试
uv run pytest -m llm

# P3 离线契约与安全回归（不需要 Docker）
uv run pytest -q --no-cov tests/unit/test_p3_*.py

# P3 真实 Docker smoke（需要 daemon + 审查过的精确 digest）
uv run pytest -q --no-cov -m docker tests/integration/test_p3_docker_smoke.py
```

---

## Mock 架构

### FakeLLMProvider

项目中最核心的 Mock 组件。它模拟 LLM 调用，返回预定义的文本：

```python
from tests.conftest import FakeLLMProvider

# 返回 "A", "B", "C", 循环
provider = FakeLLMProvider(responses=["A", "B", "C"])

# 可以通过 set_responses 动态修改
provider.set_responses(["new response"])

# 断言 LLM 被调用的次数和内容
assert provider.request_count == 3
assert "expected text" in provider.last_request.messages[0]["content"]
```

### FakeAgent

用于测试 `BaseAgent` 子类的标准生命周期：

```python
from tests.conftest import FakeAgent

agent = FakeAgent(max_steps=3)
result = await agent.run(task)

# 验证状态
assert agent.state == AgentState.DONE
assert len(agent.trace.steps) == 3
```

---

## 测试覆盖目标

| 阶段 | 单元 | 集成 | E2E |
|------|------|------|-----|
| P0（核心与基础设施） | 已覆盖 | - | - |
| P1（PaperReader + paper pipeline） | 已覆盖 | 集成测试已覆盖主要链路 | 外部 smoke test 按需运行 |
| P2（Methodologist + evidence pipeline） | 已覆盖 | 离线端到端和 JSON round-trip | DeepSeek smoke 按需运行 |
| P3（CodeForger + experiment backends） | 已覆盖离线契约和安全回归 | Docker mock + 条件化真实 smoke | 已完成；真实隔离/资源/cleanup gate 通过 |
| P4-P8 | >= 90% | >= 70% | >= 50% |

---

## P1 测试映射

| 测试文件 | 关注点 |
|---|---|
| `test_pdf_parser.py` | 文件、元数据、标题检测、页码和可选依赖 |
| `test_arxiv_api.py` | ID 归一化、搜索、下载和安全文件名 |
| `test_chunker.py` | 合并、长段落、token 预算和空输入 |
| `test_paper_reader.py` | 工具参数错误、native calls、预算耗尽、trace 和 JSON |
| `test_pipeline.py` | 注入、解析/阅读组合和 arXiv 委托 |
| `test_openai_provider.py` | 配置优先级、响应适配和流式停止序列 |
| `test_cli.py` | 版本、能力、dotenv、keyless endpoint 和输出文件 |
| `test_read_pipeline.py` | PaperChunker + PaperReader 集成链路 |

当前精确用例数和覆盖率以 `uv run pytest -q` 输出为准，避免文档在每次增加测试后
失真。真实 DeepSeek 和 arXiv smoke test 需要网络、凭据或外部服务，不属于默认
测试套件。

## P2 测试映射

| 测试文件 | 关注点 |
|---|---|
| `test_methodology_schemas.py` | schema round-trip、claim 迁移、coverage 和失败 fixtures |
| `test_evidence.py` | source/quote hash、bounded chunks、重复标题和来源校验 |
| `test_methodologist.py` | ReAct/native tools、repair、模型继承、证据降级和 trace |
| `test_methodology_pipeline.py` | Paper/PDF 组合、PaperNote 和依赖注入 |
| `test_methodology_flow.py` | 离线端到端分析与 JSON round-trip |

## P3 测试映射

| 测试文件 | 关注点 |
|---|---|
| `test_p3_schemas.py` | schema version、路径、hash、manifest、round-trip、大小写碰撞 |
| `test_p3_validation.py` | AST/compile/import/entrypoint/config/test/manifest 静态校验 |
| `test_p3_code_forger.py` | evidence 递归收集、结构化失败、repair 和 post-repair fail closed |
| `test_p3_backends.py` | dry-run、本地 fixture 隔离、timeout/cancel、日志、metric、artifact、Docker 参数 |
| `test_p3_pipeline.py` | backend 路由、experiment index、CLI 原子输出和非零返回码 |
| `test_p3_docker_smoke.py` | 真实离线 Docker fixture；显式 `docker` marker，默认不应伪造通过 |

P3 安全回归必须同时包含恶意输入和合法 control。重点证明：调用者代码不能进入
宿主 fixture runner；篡改 evidence/manifest 被拒绝；非法 CodeForger 输出不会返回
bundle；bundle 路径、artifact tar 和 Docker runtime profile 均 fail closed。

`p3-security` CI job 始终运行离线 P3 测试。`p3-docker-smoke` 只有仓库变量
`REPROFORGE_P3_PYTHON_CPU_IMAGE` 配置为审查过的精确 digest 时才运行。P0 package
Docker build 不能替代 P3 sandbox smoke。

## 失败排查顺序

```text
pytest 收集失败
  → 检查 uv sync --locked --group dev 和当前解释器
测试 import 失败
  → 检查 optional extra，而不是直接修改测试
PaperReader 测试失败
  → 先使用 FakeLLMProvider 检查 request/response 和 trace
PDF 测试失败
  → 区分 fitz 缺失、文件无效、抽取文本为空三种情况
真实 Provider 失败
  → 最后再检查 key、base URL、model、网络和额度
Docker smoke 被 skip/blocked
  → 检查 daemon、docker extra、精确 digest 环境变量和本地镜像；不要改成 mutable tag
```

不要在单元测试中临时接入真实 API；这会让测试变慢、产生费用并引入非确定性。

## 测试与实现的对应关系

每个阶段变更至少应回答一个对应测试问题：

| 变更 | 应补充/更新的测试 |
|---|---|
| 新增 schema 字段 | `test_schemas.py` + JSON round-trip |
| 修改章节识别 | `test_pdf_parser.py` 的正例和误识别反例 |
| 修改 chunk 算法 | `test_chunker.py` 的预算、索引、长段落用例 |
| 修改 tool 参数 | `test_paper_reader.py` 的成功和错误 observation |
| 修改 provider 优先级 | `test_openai_provider.py` 的环境隔离 fixture |
| 修改 CLI 配置 | `test_cli.py` 的 dotenv、keyless、公网拒绝用例 |
| 修改 pipeline 注入 | `test_pipeline.py` 的 fake dependency 断言 |
| 修改 P3 schema/manifest | `test_p3_schemas.py` 的 tamper、round-trip 和版本反例 |
| 修改 CodeForger | `test_p3_code_forger.py` 的非法响应、未知 evidence 和合法 control |
| 修改 local runner | `test_p3_backends.py` 的 caller-code 拒绝、cwd 隔离、timeout/cancel/cleanup |
| 修改 Docker 参数/采集 | Docker mock 安全参数回归 + 条件化真实 `docker` smoke |
| 修改 P3 CLI | `test_p3_pipeline.py` 的原子输出、覆盖保护和失败返回码 |

## 示例：给 P1 PaperReader 写测试

```python
"""A minimal deterministic PaperReader test."""

import pytest
from repro_forge.agents.paper_reader import PaperReader
from repro_forge.core.types import AgentConfig, AgentType
from repro_forge.paper import Paper, Section, SectionType
from tests.conftest import FakeLLMProvider


@pytest.fixture
def reader(fake_provider: FakeLLMProvider) -> PaperReader:
    config = AgentConfig(agent_type=AgentType.PAPER_READER, max_steps=3)
    return PaperReader(config=config, provider=fake_provider)


class TestPaperReader:
    @pytest.mark.asyncio
    async def test_reads_a_paper_without_network(self, reader: PaperReader) -> None:
        reader.provider.set_responses([
            "Let me list the sections.",
            'DONE\n{"tldr": "A deterministic paper note.", "contributions": [], '
            '"methodology_summary": "", "key_findings": [], "strengths": [], '
            '"weaknesses": [], "questions": []}',
        ])
        paper = Paper(sections=[Section(title="Abstract", content="A short abstract.",
                                        section_type=SectionType.ABSTRACT)])

        note = await reader.read(paper)

        assert note.tldr == "A deterministic paper note."
        assert note.total_tokens_used >= 0
```
