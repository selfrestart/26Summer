# ReproForge P0 分级面试题库

本文档基于 ReproForge 当前 P0 代码生成，适用于校招、中高级和高级/专家候选人。
每套题设计为约 60 分钟的实际问答，不把尚未实现的 PaperReader、真实 LLM Provider、
API、知识图谱或复现流水线当作现成功能。

## 通用使用说明

- 面试官可根据候选人回答深度跳过部分追问，但应控制每题总时间。
- 每题满分 3 分：`3` 表示完整且能讨论边界，`2` 表示核心正确，`1` 表示只掌握表面概念，`0` 表示错误或无法回答。
- 参考答案是评分要点，不要求候选人逐字复述。
- 如候选人提前给出追问中的内容，可直接计入该题评分。

---

# 第一套：校招/初级候选人

**总时长：60 分钟；8 题；满分 24 分；建议通过线 15 分，优秀线 19 分。**

## 1. ID 生成与碰撞风险（5 分钟）

参考代码：[`core/types.py`](https://github.com/selfrestart/26Summer/blob/main/repro-forge/repro_forge/core/types.py) 中的 `new_id()`。

### 题目

解释 `uuid.uuid4().hex[:12]` 的作用。它生成的 ID 是否绝对不会重复？`prefix` 有什么价值？

### 参考答案

- `uuid4()` 生成随机 UUID，`.hex` 得到不含连字符的十六进制表示。
- 截取 12 个十六进制字符相当于保留约 48 bit，缩短了日志和调试中的 ID。
- 截断会提高碰撞概率，因此不能声称绝对唯一。
- `task_`、`agent_`、`run_` 等前缀能够快速识别对象类型，但不能替代数据库唯一约束。
- 数据量大或需要长期持久化时，应增加长度，并在存储层设置唯一约束和碰撞重试。

### 追问

1. 为什么对象数量增加后，碰撞风险会比直觉增长得快？
2. 自增 ID 与随机 UUID 在分布式系统中各有什么优缺点？

### 评分标准

- **3 分：**说明 48 bit、碰撞可能、前缀用途以及存储层唯一约束。
- **2 分：**理解 UUID、截断和前缀，但缺少碰撞处理。
- **1 分：**只回答“生成随机 ID”。
- **0 分：**认为截断 UUID 仍然绝对唯一。

## 2. `StrEnum` 与状态建模（7 分钟）

参考代码：`MessageRole`、`AgentState`、`AgentType`、`TaskStatus`。

### 题目

为什么这些状态继承 `StrEnum`，而不是直接使用普通字符串或普通 `Enum`？

### 参考答案

- 枚举限制合法值，避免代码中散落的魔法字符串和拼写错误。
- `StrEnum` 同时具有字符串值，便于 JSON、日志、Pydantic 和未来 HTTP API 序列化。
- 静态类型检查器可以发现非法状态。
- 普通 `Enum` 往往需要显式使用 `.value` 才能得到字符串。
- 新增或删除枚举值属于协议演进问题，仍需考虑旧客户端兼容性。

### 追问

1. `StrEnum` 与 `Literal["idle", "done"]` 有什么区别？
2. 旧客户端遇到新增枚举值时可能发生什么？

### 评分标准

- **3 分：**覆盖类型安全、序列化和兼容性。
- **2 分：**能说明枚举约束和字符串行为。
- **1 分：**只知道枚举能保存常量。
- **0 分：**认为它与任意字符串没有区别。

## 3. Pydantic 字段校验（7 分钟）

参考代码：`Message._coerce_content()`。

### 题目

解释 `@field_validator("content", mode="before")` 的执行时机和目的。把 `None` 转换为空字符串有什么利弊？

### 参考答案

- `mode="before"` 表示在 Pydantic 按声明类型校验之前处理原始输入。
- 它兼容外部数据中的 `None`，避免模型构造直接失败。
- 优点是适配 Provider 数据时更宽容；缺点是可能掩盖上游数据错误，让“缺失内容”和“空内容”无法区分。
- 如果 `None` 属于协议错误，应抛出验证异常；如果它是可接受的外部格式，则应补充测试并记录转换规则。

### 追问

1. 如何测试字符串、结构化列表、`None` 和非法整数输入？
2. 为什么这里出现了 `type: ignore`，它可能暗示什么？

### 评分标准

- **3 分：**解释校验时机，并能讨论宽容解析与错误隐藏的权衡。
- **2 分：**理解 `None -> ""` 和 before validator。
- **1 分：**只会复述代码。
- **0 分：**无法说明校验器何时运行。

## 4. Pydantic 与 dataclass 的选择（8 分钟）

参考代码：`core/types.py` 与 `providers/base.py`。

### 题目

为什么任务、消息模型使用 Pydantic，而 `LLMRequest` 和 `LLMResponse` 使用 dataclass？这种混合方案有什么问题？

### 参考答案

- Pydantic 适合外部输入边界：运行时校验、字段约束、JSON 序列化和 API schema。
- dataclass 适合可信内部数据传输，开销和概念更轻。
- 当前混用可以表达不同信任边界，但会导致校验、复制和序列化方式不统一。
- 如果 Provider 对象未来直接暴露为公开 API，统一为 Pydantic 或增加转换层会更清晰。

### 追问

1. dataclass 会自动验证 `temperature` 的范围吗？
2. 什么情况下你会坚持保留 dataclass？

### 评分标准

- **3 分：**能从信任边界、验证、性能和接口一致性分析。
- **2 分：**知道 Pydantic 有验证，dataclass 更轻量。
- **1 分：**只知道二者都能保存字段。
- **0 分：**认为两者行为完全相同。

## 5. 抽象基类与模板方法（8 分钟）

参考代码：[`core/base.py`](https://github.com/selfrestart/26Summer/blob/main/repro-forge/repro_forge/core/base.py) 中的 `BaseAgent`。

### 题目

`BaseAgent` 为什么继承 `ABC`？`run()` 与 `think()`、`act()`、`observe()` 分别承担什么职责？

### 参考答案

- `BaseAgent` 使用模板方法模式：基类固定执行流程，子类实现具体步骤。
- `run()` 负责生命周期、状态、Trace、异常和资源清理。
- `think()`、`act()`、`observe()`、`should_stop()`、`finalize()` 是业务扩展点。
- `@abstractmethod` 防止未完成实现的 Agent 被实例化。
- 优点是复用和一致性；缺点是继承耦合，复杂后可考虑策略组合。

### 追问

1. 如果子类没有实现 `finalize()` 会发生什么？
2. 什么情况下组合优于继承？

### 评分标准

- **3 分：**指出模板方法模式，并能讨论继承与组合。
- **2 分：**理解抽象方法和流程复用。
- **1 分：**只回答“子类必须实现”。
- **0 分：**无法解释抽象类用途。

## 6. 异步 Agent 生命周期（8 分钟）

### 题目

按顺序描述 `BaseAgent.run()` 的完整执行流程，并解释 `await` 是否等于创建新线程。

### 参考答案

1. 为本次运行创建独立 Trace。
2. 执行 `setup()`。
3. 计算任务与 Agent 的步数上限。
4. 每轮依次进入 thinking、acting、observing 状态。
5. 保存 `TraceStep` 并判断是否终止。
6. 正常结束后调用 `finalize()`。
7. 异常被转换为失败的 `TaskResult`。
8. `finally` 记录结束状态、结束时间并执行 `teardown()`。

`await` 表示协作式让出事件循环，不等于自动创建线程。是否使用线程取决于被等待操作的实现。

### 追问

1. `observe()` 抛异常后哪些步骤仍然执行？
2. 为什么清理逻辑必须放在 `finally`？

### 评分标准

- **3 分：**完整描述正常、异常和清理流程，并正确解释异步。
- **2 分：**能描述 think/act/observe 循环。
- **1 分：**知道需要 `await`，但误解调度机制。
- **0 分：**认为每个 `await` 都创建线程。

## 7. 双重步数预算（9 分钟）

### 题目

为什么执行上限使用 `min(self.config.max_steps, task.max_steps)`？还应该为哪些资源设置预算？

### 参考答案

- Agent 配置给出自身安全上限，Task 给出单次调用限制。
- 取最小值保证任意一方的限制都不会被突破。
- 这可以限制循环、Token 消耗、工具调用量和延迟。
- Pydantic 应进一步约束步数为正数或明确 0 的语义。
- 生产系统还应限制 wall-clock deadline、Token、成本、重试、并发和工具执行时间。

### 追问

1. `max_steps=0` 应表示立即结束还是非法输入？
2. 如果任务 deadline 先到，Trace 应记录什么？

### 评分标准

- **3 分：**解释双重约束，并扩展到时间、Token 和成本预算。
- **2 分：**理解取最小值是为了不突破限制。
- **1 分：**只说“防止死循环”。
- **0 分：**认为应该使用最大值。

## 8. 单元测试方法（8 分钟）

参考代码：[`tests/unit`](https://github.com/selfrestart/26Summer/tree/main/repro-forge/tests/unit)。

### 题目

指出当前测试使用的至少三种方法，并解释为什么不直接调用真实 LLM。

### 参考答案

- `pytest.fixture` 提供共享、可复用的测试对象。
- `pytest.mark.asyncio` 驱动异步测试。
- `FakeAgent` 和 `FakeLLMProvider` 提供确定性行为。
- Monkey patch 用于构造异常路径。
- 断言覆盖结果、状态、Trace、资源清理和重复运行隔离。
- 不调用真实 LLM可避免网络不稳定、费用、限流、隐私问题和非确定性结果。

### 追问

1. Fake 与 Mock 有什么区别？
2. 高覆盖率为什么不等于测试质量高？

### 评分标准

- **3 分：**识别至少三种方法，并能讨论确定性和测试边界。
- **2 分：**能指出 fixture、异步测试和 Fake。
- **1 分：**只回答“使用 pytest”。
- **0 分：**认为单元测试应直接请求真实模型。

---

# 第二套：中高级候选人

**总时长：60 分钟；8 题；满分 24 分；建议通过线 16 分，优秀线 20 分。**

## 1. Trace 隔离与重复运行（7 分钟）

### 题目

为什么每次 `run()` 和 `stream()` 都必须创建新的 `AgentTrace`？历史 Trace 应由谁保存？

### 参考答案

- 复用旧 Trace 会造成跨任务步骤、时间、成本和状态污染，步号也可能重复。
- 一次运行应对应一个 `run_id` 和独立观测单元。
- Agent Runtime 负责产生 Trace；持久化应由独立 repository、event sink 或 observability adapter 负责。
- 如果需要恢复，不能只在下一次运行时简单重建，而应加载持久化事件或 checkpoint。

### 追问

1. Trace 应该是可变列表还是追加式事件流？
2. 如何防止 Trace 中记录 API key？

### 评分标准

- **3 分：**覆盖隔离、持久化、恢复和敏感数据。
- **2 分：**指出重复运行会污染数据。
- **1 分：**只说“为了生成新 run ID”。
- **0 分：**认为所有任务共用 Trace 更方便。

## 2. `run()` 与 `stream()` 的错误语义（8 分钟）

### 题目

为什么 `run()` 将异常转换为失败结果，而 `stream()` 将异常抛给消费者？你会保持这种设计吗？

### 参考答案

- 普通调用可以通过单一 `TaskResult` 表达成功或失败。
- async generator 已经进入迭代协议，部分数据可能已经发送，异常传播更自然。
- 差异必须写入接口契约，否则调用者容易漏处理。
- 可选方案是定义结构化 `StreamEvent`，包含 step、error、completed，但系统级异常仍应传播。
- 需要区分业务失败、Provider 错误、取消、超时和编程错误。

### 追问

1. 已发送三个 step 后发生错误，客户端如何知道结果不完整？
2. 错误事件和抛异常可以同时存在吗？

### 评分标准

- **3 分：**讨论部分结果、错误分类和结构化流事件。
- **2 分：**理解两类调用协议的差异。
- **1 分：**只描述当前代码行为。
- **0 分：**认为流式函数不会抛异常。

## 3. 资源清理的剩余风险（8 分钟）

### 题目

`teardown()` 已放在 `finally` 中，为什么仍不能认为资源清理绝对可靠？

### 参考答案

- `teardown()` 自身可能抛异常并覆盖原始异常或返回结果。
- setup 可能只完成一部分，清理必须识别哪些资源已经初始化。
- 多个资源中第一个清理失败不应阻止其余资源关闭。
- 可以使用 `AsyncExitStack`、独立异常捕获、超时和 `ExceptionGroup`。
- 清理失败应记录到 Trace/日志，并明确是否改变任务最终状态。

### 追问

1. 如何同时保留业务异常和清理异常？
2. 清理操作是否应该允许重试？

### 评分标准

- **3 分：**识别异常覆盖、部分初始化和多资源清理问题。
- **2 分：**知道 teardown 本身也会失败。
- **1 分：**只建议再加一层 try/except。
- **0 分：**认为 finally 可以解决所有问题。

## 4. 并发复用风险（7 分钟）

### 题目

同一个 `BaseAgent` 实例能否安全地同时执行两个任务？请指出具体竞态。

### 参考答案

当前不能，因为 `_state` 和 `_trace` 是实例级共享可变状态：

- 两次运行会互相覆盖 Trace。
- 状态机会交叉。
- 一个任务的步骤可能写入另一个任务的 Trace。
- teardown 可能关闭另一个任务使用的资源。

短期可以用锁拒绝并发；更好的设计是将运行状态放入独立 `AgentRunContext`，Agent 定义和共享 Provider 尽量保持无状态。

### 追问

1. `asyncio.Lock` 为什么只是串行化而不是并发方案？
2. Provider 连接池是否可以共享？

### 评分标准

- **3 分：**指出具体竞态，并比较锁与 RunContext。
- **2 分：**知道当前实例不能并发复用。
- **1 分：**笼统回答“可能线程不安全”。
- **0 分：**认为 async 天然无竞态。

## 5. Provider 流接口类型设计（8 分钟）

参考代码：[`providers/base.py`](https://github.com/selfrestart/26Summer/blob/main/repro-forge/repro_forge/providers/base.py)。

### 题目

`generate_stream()` 返回 `Any` 有什么问题？请设计一个更清晰的接口。

### 参考答案

- `Any` 让调用者无法确定返回的是协程、异步迭代器还是响应对象，mypy 也无法检查实现一致性。
- 仅有文本时可以返回 `AsyncIterator[str]`。
- 真实系统更适合 `AsyncIterator[LLMStreamEvent]`，事件可包含文本增量、tool call、usage、结束原因和错误。
- 流结束时的 usage 需要通过终止事件或独立最终结果表达。

### 追问

1. async generator 的返回类型为什么不是 `Coroutine`？
2. 如何表达一个被分片传输的 tool call？

### 评分标准

- **3 分：**提出结构化流事件并处理 usage/tool call。
- **2 分：**知道应该使用 `AsyncIterator`。
- **1 分：**只说 `Any` 不够严格。
- **0 分：**认为 `Any` 最灵活所以没有问题。

## 6. 测试策略评审（8 分钟）

### 题目

当前 25 个测试和较高覆盖率还缺少哪些关键场景？请区分单元、契约和集成测试。

### 参考答案

- 单元：setup/finalize/teardown 失败、正常 stream、消费者提前关闭、0 步预算、取消和同实例并发。
- 契约：所有 Provider 实现满足相同请求、响应和 streaming 行为。
- 集成：wheel 安装、CLI、Docker 非 root 运行、MkDocs strict、不同 Python 版本。
- 未来真实 Provider 测试应使用录制响应或受控 sandbox，不应让普通 CI 依赖外部计费 API。
- 覆盖率只说明哪些行被执行，不能证明断言质量和错误语义正确。

### 追问

1. 如何证明一个回归测试在修复前确实会失败？
2. Fake 测试为什么可能只验证 Fake 自身？

### 评分标准

- **3 分：**按层次给出具体场景，并说明覆盖率局限。
- **2 分：**列出多个有效边界测试。
- **1 分：**只建议“提高覆盖率”。
- **0 分：**认为现有覆盖率足以证明生产可用。

## 7. CI/CD 与子目录布局（7 分钟）

参考代码：[根 CI workflow](https://github.com/selfrestart/26Summer/blob/main/.github/workflows/ci.yml)。

### 题目

评价当前 CI 的正确性、效率和供应链安全。为什么 GitHub workflow 必须位于仓库根 `.github/workflows/`？

### 参考答案

- GitHub 只从仓库根识别 workflow 和模板，子项目内 `.github` 不生效。
- 当前矩阵覆盖 3.11–3.13，质量、测试、构建和 Docker smoke test 分层合理。
- `working-directory` 必须指向 `repro-forge`。
- 可改进：Action 固定 commit SHA、上传测试报告、Docker BuildKit cache、artifact checksum/SBOM。
- `paths` 过滤可能遗漏根级配置对项目的影响，应谨慎维护。

### 追问

1. 为什么不在三个 Python 版本上都重复构建 Docker？
2. Dependabot 的 pip directory 为什么应是 `/repro-forge`？

### 评分标准

- **3 分：**覆盖路径、效率、缓存和供应链风险。
- **2 分：**理解根 workflow 和矩阵测试。
- **1 分：**只知道 CI 会运行测试。
- **0 分：**认为子目录 `.github` 也会被 GitHub 自动发现。

## 8. P0 文档真实性与版本策略（7 分钟）

### 题目

为什么 README 必须区分当前 P0 能力与未来 API？如何避免文档与代码长期漂移？

### 参考答案

- 不可运行的 Quick Start 会直接破坏用户信任和安装体验。
- 产品愿景可以保留，但必须显式标记 Planned，并提供当前可运行的安装、测试和 CLI 命令。
- 文档代码示例应进入 doctest、snippet test 或 smoke test。
- CI 应 strict build 文档并检查链接。
- Release 文档必须与真实 workflow 对齐，不能声称未配置的 PyPI/GHCR 发布。

### 追问

1. 未来 API 示例是否应该完全删除？
2. 如何自动检查 README 中的导入示例？

### 评分标准

- **3 分：**兼顾愿景、真实性和自动化防漂移。
- **2 分：**知道当前与规划必须明确区分。
- **1 分：**只建议手工更新 README。
- **0 分：**认为文档可以先写，代码以后自然会追上。

---

# 第三套：高级/专家候选人

**总时长：60 分钟；7 题；满分 21 分；建议通过线 15 分，优秀线 18 分。**

## 1. 可重入 Agent Runtime（8 分钟）

### 题目

在保留共享 Provider 连接池的前提下，如何把当前 `BaseAgent` 重构为可并发、可重入的运行时？

### 参考答案

将定义与运行状态分离：

```text
AgentDefinition
  immutable config / prompt / tools / shared provider

AgentRunContext
  task / state / trace / budgets / cancellation / per-run memory
```

- `run(context)` 不修改 Agent 实例字段。
- 每个任务拥有独立状态机和 Trace。
- Provider 明确并发安全契约，通过连接池、限流器和熔断器共享。
- Tool 和 Memory 也必须区分共享只读对象与运行级可变对象。

### 追问

1. 并发限制放在 Agent、Provider 还是调度器？
2. RunContext 如何序列化并支持恢复？

### 评分标准

- **3 分：**给出 definition/context 分离，并讨论共享资源和限流。
- **2 分：**能把 state/trace 移出实例。
- **1 分：**只建议增加全局锁。
- **0 分：**看不到共享可变状态问题。

## 2. 取消、超时与预算传播（9 分钟）

### 题目

`TaskSpec` 已有 `deadline_seconds`。请设计任务、子任务、Provider 和 Tool 之间的完整 deadline/cancellation 语义。

### 参考答案

- 运行开始时将相对时长转换为基于 monotonic clock 的绝对 deadline。
- 每个阶段使用剩余预算，子任务只能继承或缩短 deadline。
- 使用 `asyncio.timeout()` 或结构化取消作用域。
- 区分用户取消、超时、系统关闭、业务失败和编程错误。
- teardown 使用独立且有限的清理宽限期。
- Provider/Tool 必须接收取消信号，不能让客户端断开后继续计费。
- Trace 记录取消来源、最后完成步骤和资源消耗。

### 追问

1. `CancelledError` 应该转换为普通 `TaskResult.FAILED` 吗？
2. 不响应取消的第三方 SDK 如何隔离？

### 评分标准

- **3 分：**覆盖 monotonic deadline、传播、错误分类和清理宽限期。
- **2 分：**知道使用 timeout 和 cancellation。
- **1 分：**只建议增加一个超时参数。
- **0 分：**没有预算传播概念。

## 3. Trace 事件化与崩溃恢复（9 分钟）

### 题目

如何把当前内存 `AgentTrace` 演进为支持审计、恢复和幂等工具调用的持久化事件模型？

### 参考答案

定义追加式事件，例如：

```text
RunStarted
ThoughtProduced
ActionRequested
ActionCompleted
ObservationRecorded
RunCompleted / RunFailed / RunCancelled
```

- 事件包含 run ID、step ID、严格 sequence、schema version 和幂等键。
- 不可逆工具调用前先持久化 intent，完成后持久化结果。
- 恢复时重放事件构造状态，并查询是否已有 ActionCompleted。
- 对敏感 Thought/Prompt 进行分级、脱敏和保留期控制。
- 不能轻率承诺 exactly-once；通常实现 at-least-once 加幂等。

### 追问

1. 写入 `ActionRequested` 后进程立即崩溃怎么办？
2. Thought 是否应该完整持久化？

### 评分标准

- **3 分：**讨论事件顺序、崩溃窗口、幂等和敏感数据。
- **2 分：**提出追加事件与重放恢复。
- **1 分：**只建议定期保存 JSON。
- **0 分：**忽略副作用重复执行问题。

## 4. Streaming 背压与断连处理（8 分钟）

### 题目

如果 Agent 生成速度高于客户端消费速度，如何设计背压？客户端断开后如何避免上游 LLM 继续计费？

### 参考答案

- Python async generator 在 `yield` 处具有基础协作式背压。
- 跨网络和多生产者场景还需要有界队列、慢消费者超时、心跳和断连检测。
- 客户端断开应取消 RunContext，并向 Provider 流传播取消。
- Trace 持久化与用户输出应分通道；审计事件不能因为客户端慢而随意丢弃。
- 必须定义哪些增量可以合并或丢弃，哪些完成/错误事件必须送达或持久化。

### 追问

1. SSE 与 WebSocket 的背压和重连能力有何差异？
2. Tool call 参数分片到一半时断开怎么办？

### 评分标准

- **3 分：**覆盖有界缓冲、断连取消、事件等级和协议差异。
- **2 分：**知道 async generator 有自然背压并需传播取消。
- **1 分：**只建议增加队列。
- **0 分：**忽略慢消费者和继续计费问题。

## 5. Provider 能力协商与接口演进（9 分钟）

### 题目

不同模型对 streaming、tools、JSON schema、多模态和上下文长度支持不同，如何避免大量 Provider 条件分支？

### 参考答案

- Provider/Model 暴露结构化 `ProviderCapabilities`。
- 任务声明 required capabilities，调度前完成预检。
- Adapter 负责规范消息与厂商格式的双向转换，并报告转换损失。
- 缺失能力应显式失败或采用配置化降级，不能静默改变语义。
- 能力分为 Provider 级、模型级和部署级；部分能力需要运行时探测和缓存。
- 公共 wire model 与内部 Provider 模型应分离，避免核心模型成为所有厂商字段的并集。

### 追问

1. 自动降级 tools 到纯文本有什么风险？
2. Capability cache 失效策略如何设计？

### 评分标准

- **3 分：**提出能力模型、预检、适配器和显式降级。
- **2 分：**知道需要 Provider adapter 和能力描述。
- **1 分：**仍主要依赖 `if provider == ...`。
- **0 分：**认为所有 OpenAI-compatible 服务能力完全一致。

## 6. 多租户安全与可观测性（9 分钟）

### 题目

未来 Trace 可能包含论文、Prompt、工具参数和 Provider 原始响应。请同时设计安全边界和可观测性方案。

### 参考答案

- 租户级鉴权、存储分区和访问审计。
- API key 永不进入 Trace；敏感字段在产生端脱敏，而不是只依赖日志后端。
- 定义数据分类、保留期、用户删除和调试授权流程。
- Metrics 记录成功率、延迟、Token、成本、重试、超时、工具错误和队列深度。
- Trace 层级为 task -> agent step -> provider/tool span，run ID 关联 OpenTelemetry trace ID。
- 避免将 user ID、run ID 等高基数字段作为 Metrics label。
- Prompt injection 不能绕过工具 ACL 或访问其他租户资源。

### 追问

1. 调试需要查看原始 Prompt 时如何授权？
2. 哪些字段适合日志，哪些只适合加密审计存储？

### 评分标准

- **3 分：**同时覆盖隔离、脱敏、保留、三类观测信号和高基数风险。
- **2 分：**能提出合理安全和观测措施。
- **1 分：**只回答加密、HTTPS 或接入 OpenTelemetry。
- **0 分：**允许把完整 Prompt 和 API key 写入普通日志。

## 7. 从 P0 演进到生产系统（8 分钟）

### 题目

路线图包含 Agent、Memory、知识图谱、MCP、API、Guardrails 和 Observability。如何避免过早构建复杂平台？

### 参考答案

- 按可验证的纵向用户闭环演进，而不是一次横向铺开所有基础设施。
- 保持 P0 核心契约小而稳定，每个新基础设施必须由当前功能需求驱动。
- Provider、Tool、Memory 先定义端口接口，默认提供进程内实现。
- 达到明确的吞吐量、可靠性或团队边界后，再引入数据库、队列或独立服务。
- 用 ADR 记录不可逆决策，每个阶段具备独立验收、监控和回滚边界。
- 公开模型采用 schema version 和兼容迁移，避免内部重构直接破坏客户端。

### 追问

1. 什么时候值得引入消息队列？
2. Neo4j 相比关系数据库的引入条件是什么？

### 评分标准

- **3 分：**强调纵向切片、延迟复杂化和明确演进信号。
- **2 分：**能提出分阶段实现和接口隔离。
- **1 分：**直接建议拆微服务但说不出规模依据。
- **0 分：**认为路线图中的所有组件都必须同时建设。

---

# 面试官总评表

除题目得分外，建议额外记录以下观察项：

| 维度 | 观察重点 |
|---|---|
| 代码理解 | 能否引用实际代码和执行路径，而不是只背概念 |
| 边界意识 | 能否发现异常、并发、取消、资源清理和数据污染问题 |
| 工程权衡 | 能否说明方案的收益、成本和适用条件 |
| 测试意识 | 能否区分单元、契约、集成和端到端验证 |
| 沟通能力 | 回答是否结构化，能否在追问后修正不准确结论 |

## 明显减分信号

- 把 `async` 等同于多线程，或认为异步代码天然没有竞态。
- 认为高覆盖率等于没有缺陷。
- 认为把清理代码放入 `finally` 就解决了所有资源问题。
- 把规划中的 P1+ 功能当成当前已经实现的能力。
- 系统设计中完全不讨论取消、幂等、兼容性、隐私和可观测性。
- 遇到扩展需求立即拆分微服务，却无法说明吞吐量、可靠性或组织边界依据。

## 建议记录格式

```text
候选人：
面试级别：校招 / 中高级 / 高级专家
题目得分：
代码理解：强 / 中 / 弱
工程权衡：强 / 中 / 弱
沟通能力：强 / 中 / 弱
关键亮点：
主要风险：
最终建议：通过 / 加面 / 不通过
```
