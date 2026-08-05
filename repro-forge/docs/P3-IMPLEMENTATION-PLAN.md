# P3 实施规划 — Auditable Code Generation and Sandboxed Experiments

> **状态**：`Planned`（规划完成，尚未实现）
>
> **前置输入**：P2 `MethodAnalysis`
>
> **核心输出**：`ReproductionBundle`、`ExperimentSpec`、`ExperimentRun`

## 1. 阶段目标

P3 负责把有证据的方法学描述转换为可审计的代码和可重复执行的实验，并在最小隔离环境中运行。P3 只报告运行事实和指标，不判断是否成功复现论文；最终结论属于 P4。

```text
MethodAnalysis
  → CodeForger
  → ReproductionBundle(source/tests/config/manifest)
  → Experimentor(dry-run/build/run)
  → ExperimentRun(logs/metrics/artifacts/environment)
```

## 2. 交付物

| 交付物 | 计划内容 |
|---|---|
| `GeneratedFile` | 相对路径、内容、语言、来源证据、内容哈希 |
| `DependencySpec` | Python/系统依赖、版本来源、锁定状态 |
| `ExperimentSpec` | argv entrypoint、数据/许可/hash、环境锁、网络策略、资源限制、超时、种子、artifact allowlist |
| `ReproductionBundle` | 源码、测试、配置、README、manifest、风险提示 |
| `ExperimentEvent` | stdout/stderr/status/metric/artifact 等事件 |
| `ExperimentRun` | 状态、退出码、环境、日志、指标、artifact manifest |
| `CodeForger` | 生成和修复 bundle |
| `Experimentor` | dry-run、build、sandbox run 和采集 |

所有文件路径必须是 bundle 根目录内的规范化相对路径；禁止绝对路径和 `..` 逃逸。
可执行命令保存为 argv 数组，不接受未经解析的 shell 字符串；环境变量默认空白
allowlist，secret 不得进入 bundle、镜像层、运行环境或日志。

## 3. 非目标

- 不验证数学推导；
- 不判断复现是否达到论文声称结果；
- 不自动下载受限/未知许可证数据；
- 不执行购买、云资源申请或远程 SSH 操作；
- 不提供多租户生产沙箱；
- 不把实验产物写入知识图谱；
- 不在默认测试中运行 GPU 训练。

## 4. CodeForger 规划

### 4.1 生成策略

CodeForger 使用 Plan-Execute 风格：

1. 读取 `MethodAnalysis` 和 evidence；
2. 生成文件计划与依赖计划；
3. 逐文件生成最小实现；
4. 生成配置、README 和 deterministic smoke tests；
5. 静态校验路径、语法、imports 和依赖声明；
6. 最多进行受限修复；
7. 产出不可变 manifest。

### 4.2 bundle 最小结构

```text
bundle/
├── src/
│   ├── model.py
│   └── data.py
├── train.py
├── evaluate.py
├── tests/
│   └── test_smoke.py
├── config.yaml
├── pyproject.toml or requirements.lock
├── README.md
└── reproforge-manifest.json
```

不要求所有论文都使用相同文件名，但必须包含明确 entrypoint、依赖和运行说明。

### 4.3 证据映射

关键实现选择应引用 P2 的 evidence ID。无法从论文确定的配置必须进入 `assumptions`/`unresolved`，不得静默使用所谓“行业默认值”。

## 5. Experimentor 与最小安全沙箱

### 5.1 执行后端

P3 首批只支持：

| 后端 | 用途 | 是否允许真实训练 |
|---|---|---|
| `dryrun` | 校验 manifest、命令、路径和依赖 | 否 |
| `local-subprocess` | 仅执行仓库维护者提交并审查的固定 fixture | 仅小型 smoke |
| `docker` | 构建并运行 CPU 优先隔离实验 | 是，受资源限制 |

Colab、SSH、Vast.ai 等远程后端延后，避免引入外部账号、计费和凭据风险。
`local-subprocess` 绝不执行 LLM 生成或用户上传的任意代码；此类输入只能 dry-run，
或在通过 P3 最低安全门的 Docker backend 中运行。

### 5.2 P3 必须具备的最小安全控制

虽然平台级 Guardrails 在 P7，P3 执行任意生成代码前必须完成：

- 非 root 容器；
- 默认断网，可显式白名单；
- CPU/内存/PID/磁盘/超时限制；
- 只读 root filesystem，单独 writable workspace；
- 禁止 Docker socket 和宿主敏感目录挂载；
- 清理环境变量中的 API key/token；
- 限定 artifact 路径和大小；
- kill/cleanup 在失败与超时路径都执行；
- 镜像和运行命令写入 manifest。

如果这些条件未实现，P3 只能交付 dry-run，不能宣称 Docker execution 完成。

### 5.3 事件、指标和 artifact 协议

- stdout/stderr 是不可信日志，只按大小限制采集，不能通过任意正则自动升级为事实指标；
- metric 只接受版本化 JSON event 或白名单 metrics artifact，包含 name/value/unit/step/split/aggregation/seed；
- event 使用单调序号、run ID 和 timestamp，重复采集必须幂等；
- artifact 记录相对路径、媒体类型、大小、hash 和 producer step；
- 日志、metric、artifact 达到上限时产生明确 truncation/limit event，而不是静默丢失；
- P4 只消费结构化 `ExperimentRun`，不读取 backend 私有目录或重新解析原始 stdout。

## 6. 数据和依赖策略

- 数据集只声明来源、许可、校验和和预期目录；
- 自动下载仅允许明确公开、非交互、许可可接受的数据；
- 加密/受限数据必须报告 blocker，不能绕过访问控制；
- 依赖尽量锁定版本并记录 index/source；
- PyTorch CUDA 版本不得由模糊默认值决定；
- 每次 run 记录 Python、OS、包、硬件、seed 和代码哈希。
- dataset reference 记录来源、许可、checksum、split identity 和是否允许再分发；
- 环境锁、基础镜像 digest、argv 和资源/network policy 都进入不可变 manifest。

## 7. 工作包

### P3.0 契约与 manifest

新增 bundle/experiment schema、路径验证、hash 和 JSON round-trip tests。

### P3.1 CodeForger 计划与生成

实现文件计划、证据映射、依赖声明、prompt/tool 协议和 Fake Provider 测试。

### P3.2 静态校验和 repair

实现 AST/compile/import/manifest/test 检查；修复次数受限并保留 diff/trace。

### P3.3 dry-run/local backend

实现无执行预览、临时目录、timeout、event stream 和 cleanup 测试。
`local-subprocess` 只运行仓库维护者提交并评审的固定 CPU fixture，用于验证 runner
协议和清理路径；它不能接收 bundle 中的生成代码或用户上传代码。

### P3.4 Docker backend

实现受限构建/运行、资源限制、断网默认、日志/指标/artifact 收集和容器清理。

### P3.5 Pipeline/CLI

计划 API：

```python
bundle = await reproduction_pipeline.generate(method_analysis)
run = await reproduction_pipeline.execute(bundle, backend="dryrun")
```

计划 CLI：

```powershell
repro-forge generate-code methodology.json --output bundle
repro-forge run-experiment bundle --backend dryrun --output run.json
```

### P3.6 文档和验证

补设计论证、技术参考、bundle 示例、沙箱安全说明、Docker smoke 和 wheel 验证。

## 8. 测试矩阵

| 风险 | 必测场景 |
|---|---|
| 路径逃逸 | 绝对路径、`..`、symlink、Windows drive 路径拒绝 |
| 依赖不确定 | 未锁版本、未知 index、冲突依赖被报告 |
| 代码语法错误 | compile/AST 检查失败并受限 repair |
| 无限运行 | timeout 后进程/容器清理 |
| 资源耗尽 | CPU/memory/PID/disk 限制生效 |
| secret 泄漏 | 环境变量不进入容器/日志/manifest/image layer |
| artifact 逃逸 | 只采集白名单目录和大小范围 |
| shell 注入 | entrypoint 仅 argv，拒绝未评审 shell 字符串 |
| 假 metric | 普通 stdout 不能自动成为 `ObservedMetric` |
| local runner 越界 | 拒绝生成代码，只运行仓库固定 fixture |
| 重复运行 | run ID、临时目录、日志互相隔离 |
| P2 缺失配置 | unresolved/assumption 保留，不伪造值 |
| P1/P2 回归 | 所有历史测试继续通过 |

## 9. 准入与里程碑提升

P3 只有在 P2 `MethodAnalysis` golden fixture 和 consumer contract review 完成后
才能转为 `Ready`。实施分为三个不会混淆状态的里程碑：

- **P3-A（可安全停止）**：bundle schema、路径/argv 校验、证据映射、静态检查、
  dry-run 和结构化 event/metric/artifact；不得执行生成代码；
- **P3-B（可安全停止）**：固定仓库 CPU fixture 的 `local-subprocess` runner、timeout、
  cancellation 和 cleanup；仍不得执行 LLM 生成或用户上传代码；
- **P3-C（完整阶段）**：Docker backend 满足默认断网、资源/挂载/secret/cleanup
  控制，并使用仓库固定 CPU fixture 证明限制实际生效。

如果 P3-C 未通过，P3-A/P3-B 可以作为后续评审产物保留，但 P3 状态最多为
`In Progress`，capabilities/README 不得宣称 sandbox execution 可用。

## 10. 完成定义

1. `ReproductionBundle`/`ExperimentSpec`/`ExperimentRun` 和 event/metric/artifact schema 稳定；
2. CodeForger 输出源码、配置、依赖、测试、README 和 manifest；
3. 每个关键实现选择可回溯到 P2 evidence 或显式 assumption；
4. dry-run/local smoke 完成且所有清理路径有测试；
5. Docker backend 满足最小安全控制并通过受限 CPU fixture；
6. argv、dataset/license/hash、日志、结构化指标、artifact、环境和代码哈希完整；
7. CLI/Python API/离线示例/文档齐全；
8. 不宣称复现结论，P4 仍保持 Planned；
9. 全部质量、构建、wheel 和 Docker smoke gate 通过。

## 11. P4 交接

P4 只接收 `MethodAnalysis`（含 `EquationEvidence`/`ReportedClaimDraft`）、
`ReproductionBundle` 和 `ExperimentRun`，不直接解析 Docker 日志目录或 CodeForger
conversation。P3 必须在 manifest 中提供 P4 需要的结构化 metric、dataset/split、
run status 和 artifact 引用。
