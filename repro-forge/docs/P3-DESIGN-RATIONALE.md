# P3 设计论证 — 可审计代码生成与受限实验执行

> **阶段状态**：`Complete`
>
> P3-A（bundle/校验/dry-run）、P3-B（固定 fixture runner）和 P3-C（受限
> Docker）均已实现并验收。P3-C 于 2026-08-08 使用经过审查的精确 Python CPU
> 镜像 digest 通过真实 Docker security smoke。

## 1. P3 解决什么问题

P2 输出带原文证据的 `MethodAnalysis`。P3 将它转换为两个可持久化、可审计的
artifact：

1. `ReproductionBundle`：源码、测试、配置、依赖、实验声明、证据映射和 manifest；
2. `ExperimentRun`：执行状态、错误码、受限日志、结构化指标、artifact 摘要和环境快照。

P3 只记录“生成了什么、执行了什么、观察到什么”。它不判断指标是否达到论文
claim，也不输出“复现成功”结论；claim 对齐和最终判断属于 P4。

## 2. 威胁边界与安全不变量

P3 的主要不可信输入是 LLM 生成内容、序列化 bundle、实验 stdout/stderr 和容器
输出文件。最重要的安全不变量是：

- 用户或 LLM 提供的任意代码绝不能进入宿主 `local-subprocess`；
- bundle 文件只能位于规范化相对路径内，不能路径穿越或发生大小写碰撞；
- bundle 的代码、实验声明、证据映射和生成 trace 必须由 manifest hash 覆盖；
- 结构化生成失败、静态校验失败或 repair 后仍不合法时必须 fail closed；
- Docker 只能使用维护者配置的精确 digest 镜像，不能由 bundle 选择镜像或自动拉取标签；
- 生成代码的 Docker 执行默认断网、非 root、只读根文件系统，并受 CPU、内存、
  PID、临时磁盘、日志、artifact 和超时限制；
- stdout/stderr 永远只是日志，不能被模糊正则自动提升为可信指标；
- 只有版本化 JSONL 指标和 allowlist 内 artifact 可以进入 `ExperimentRun`。

## 3. 为什么使用版本化 Pydantic 契约

P3 artifact 会被 CLI、P4、P5 和未来服务层长期消费，因此不能把 Docker SDK
对象、临时目录或 Agent conversation 当作公共接口。当前契约固定为：

- `p3.bundle.v1`
- `p3.experiment.v1`
- `p3.run.v1`

关键模型拒绝未知字段和未知 schema version；文件内容统一为 LF 后计算 SHA-256。
这让旧消费者遇到新格式时显式失败，避免把未理解字段静默丢弃后继续执行。

`reproforge-manifest.json` 由模型自动生成。它覆盖所有非易变生成事实，包括文件
内容/证据、实验规范、P2 输入 hash、假设、未解决项、风险提示和生成 trace。
`created_at` 等易变展示字段不参与同一性判断。

## 4. 为什么 CodeForger 必须 fail closed

CodeForger 使用“计划 → 逐文件生成 → 静态校验 → 最多一次定向 repair → 再校验”
流程。所有引用的 evidence ID 必须实际存在于 P2 `MethodAnalysis` 的任意嵌套模型中。
缺失的论文信息必须进入 `assumptions` 或 `unresolved`，不能静默补成常见默认值。

选择 fail closed 的原因是：P3 的输出会进入执行边界。把无效 JSON、未知证据、
语法错误或 repair 后仍不合法的 bundle 当作“部分成功”，会把生成错误升级成可执行
输入。当前实现统一抛出 `GenerationError`，由调用者决定重试或终止。

## 5. 为什么有三个不同的执行边界

| 后端 | 输入边界 | 用途 | 是否执行生成代码 |
|---|---|---|---|
| `dryrun` | 合法 `ReproductionBundle` | materialize、静态校验、清理 | 否 |
| `local-subprocess` | 仓库内不可变 fixture ID | runner、超时、日志、指标和清理回归 | 否 |
| `docker` | 合法 bundle 或仓库 fixture | 受限隔离执行 | 是 |

`local-subprocess` 没有接受 `FixtureSpec` 或代码字符串的公共入口。它只按精确 ID
解析维护者拥有的只读 registry，并在执行前再次校验 fixture hash。这样宿主 runner
可用于快速验证进程树终止和协议采集，而不会退化成通用本地代码执行器。

`dryrun` 不是弱化版训练后端。它明确保证不执行代码，适合审查 bundle、CI 和没有
Docker 的环境。

## 6. Docker 策略

bundle 只能声明受信任的 `runtime_profile`，当前唯一 profile 为 `python-cpu`。
profile 由运维环境变量 `REPROFORGE_P3_PYTHON_CPU_IMAGE` 解析，值必须符合
`repository@sha256:<64 lowercase hex>`。后端只查询本地镜像，不自动 pull。

容器启动参数固定包含：

- `user=65532:65532`、`network_mode=none`、`read_only=true`；
- `cap_drop=[ALL]`、`no-new-privileges`、`init=true`；
- bundle 只读挂载到 `/bundle`，工作目录固定为 `/bundle`；
- `/tmp` 和 `/output` 使用带大小限制的 `tmpfs`；
- CPU、内存和 PID 限制来自经过 schema 校验的 `ResourceLimits`；
- 仅传入最小运行环境，不继承宿主 API key/token；
- timeout、取消、异常和正常完成路径都尝试强制删除容器和临时目录。

由于 Docker archive API 不会暴露已挂载 tmpfs 的内容，实验 argv 通过 Docker exec
运行，使容器在输出采集期间保持存活；随后由固定、受限的可信 collector 从
`/output` 生成 tar 流。collector 和宿主解析器都拒绝路径穿越、symlink、hardlink、
非普通文件和超限/超量文件，最后再强制删除容器。

## 7. 指标、日志与 artifact

日志采用 stdout/stderr 分流并保留有界 tail；达到上限时设置 `log_truncated` 并产生
`truncation` event。日志内容不参与指标判断。

指标只从 `/output/reproforge-metrics.jsonl` 读取，每行必须是合法
`ObservedMetric` JSON。artifact 必须位于 `/output`、路径安全且匹配
`ExperimentSpec.artifact_allowlist`；进入 `ExperimentRun` 的仅是路径、媒体类型、
大小、SHA-256 和 producer step，不是任意宿主路径。

## 8. 状态门与剩余风险

P3-A/P3-B 仍是可独立保留的安全停止点。P3-C 已在真实 Docker daemon 上使用
经过审查并预拉取的精确 digest 镜像完成验证：成功/失败/timeout/artifact 路径、
容器 cleanup、非 root、network none、cap drop、no-new-privileges、只读
bundle/rootfs、CPU/内存/PID cgroup 和输出 tmpfs 限制均实际生效。

剩余风险属于运行部署条件：每个环境仍必须显式配置并审查自己的精确镜像 digest，
且 daemon/内核升级后应重跑 security smoke。P3 完成不等于允许 mutable tag、联网、
远程账号、GPU 自动选择或多租户生产暴露。

## 9. P4/P5 交接

P4 只消费 `MethodAnalysis`、`ReproductionBundle` 和 `ExperimentRun`，不重新解析
私有 Docker 目录或 CodeForger conversation。P5 可按 bundle/run ID 和 hash 存储
artifact 元数据，但不得修改历史 P3 artifact；后续判断应产生新的派生报告。

具体 API、CLI、错误码和验证命令见
[P3 技术参考](P3-TECHNICAL-REFERENCE.md)。
