# P3 技术参考

> **状态**：`Complete`
>
> 版本化契约、CodeForger、静态校验、dry-run、固定本地 fixture runner 和 Docker
> backend 均已实现并验收。Docker 仍按运行时策略要求显式配置经过审查的精确
> image digest；这是一项安全前置条件，不是未完成能力。

## 1. 安装

P3 的 schema、生成、dry-run 和本地 fixture runner 使用基础/开发环境即可：

```powershell
uv sync --locked --group dev
```

Docker backend 还需要可选依赖：

```powershell
uv sync --locked --group dev --extra docker
```

`generate-code` 需要一个已配置的 OpenAI-compatible provider。可以使用
`OPENAI_*`、`DEEPSEEK_*`，或显式本地 endpoint；不要把 API key 写入 bundle。

## 2. 公共模型

| 模型 | schema/version | 作用 |
|---|---|---|
| `GeneratedFile` | bundle 子模型 | 路径、LF 内容、SHA-256、purpose、evidence IDs |
| `DependencySpec` | experiment 子模型 | 名称、版本、来源、锁定状态、import 名 |
| `DatasetReference` | experiment 子模型 | 来源、许可、checksum、split、预期目录 |
| `ResourceLimits` | experiment 子模型 | CPU、内存、PID、磁盘、日志和 artifact 上限 |
| `ExperimentSpec` | `p3.experiment.v1` | argv、依赖、数据、网络、资源、timeout、runtime profile |
| `ReproductionBundle` | `p3.bundle.v1` | 生成文件、实验、证据、trace 和 manifest |
| `ExperimentEvent` | run 子模型 | 单调 sequence、run ID、类型、payload |
| `ObservedMetric` | run 子模型 | name/value/unit/step/split/aggregation/seed |
| `ArtifactRecord` | run 子模型 | 安全相对路径、媒体类型、大小和 SHA-256 |
| `ExperimentRun` | `p3.run.v1` | 状态、错误码、日志、指标、artifact、环境快照 |

主要导入入口：

```python
from repro_forge.reproduction import (
    ExperimentRun,
    ExperimentSpec,
    ReproductionBundle,
    ReproductionPipeline,
    ResourceLimits,
)
```

未知 schema version、危险路径、大小写冲突、content hash 不匹配、manifest 不匹配、
secret-like `environment_lock` 名称和不合法资源范围会在模型校验阶段被拒绝。

## 3. Python API

### 3.1 生成 bundle

```python
from repro_forge.paper.extractor.schemas import MethodAnalysis
from repro_forge.providers import OpenAIProvider
from repro_forge.reproduction import ReproductionPipeline

analysis = MethodAnalysis.model_validate_json(
    open("methodology.json", encoding="utf-8").read()
)
provider = OpenAIProvider(api_key="...")
pipeline = ReproductionPipeline(provider=provider)
bundle = await pipeline.generate(analysis)
```

生成过程发生以下情况时抛出 `GenerationError`：

- plan 或逐文件响应不是预期 JSON；
- 文件引用未知 P2 evidence ID；
- 生成文件或实验声明不能通过 schema；
- 静态校验失败且一次 repair 后仍不合法。

### 3.2 dry-run

```python
pipeline = ReproductionPipeline()
run = await pipeline.execute(bundle, backend="dryrun", experiment_index=0)
```

`dryrun` 会将 bundle materialize 到临时目录、执行静态/manifest 校验、产生结构化
event 并清理目录，但不会启动生成代码。

### 3.3 固定 fixture runner

```python
run = await pipeline.run_registered_fixture(
    "p3-cpu-smoke",
    backend="local-subprocess",
)
```

公共输入只有 fixture ID。传入未知 ID 或调用内部 runner 时提供任意对象会返回
`blocked/security_violation`，不会执行调用者代码。

## 4. CLI

查看当前能力和门状态：

```powershell
uv run repro-forge capabilities
```

从 P2 `MethodAnalysis` 生成 JSON bundle：

```powershell
uv run repro-forge generate-code methodology.json --output bundle.json
```

只校验 bundle，不执行代码：

```powershell
uv run repro-forge run-experiment bundle.json --backend dryrun --output run.json
```

运行维护者固定 fixture：

```powershell
uv run repro-forge run-fixture p3-cpu-smoke `
  --backend local-subprocess `
  --output fixture-run.json
```

输出文件采用临时文件加原子 replace；默认拒绝覆盖，只有显式 `--force` 才覆盖。
成功返回进程码 `0`；`blocked`、`failed`、`timeout` 或 `cancelled` 返回 `3`；参数和
未知命令由 argparse 返回非零。

## 5. 固定 fixture

| ID | 预期用途 |
|---|---|
| `p3-cpu-smoke` | 成功、stdout 和结构化 metric |
| `p3-cpu-smoke-fail` | 非零退出和 `non_zero_exit` |
| `p3-cpu-smoke-timeout` | timeout 与进程树 cleanup |
| `p3-cpu-smoke-large-output` | stdout/stderr 有界采集与 truncation |
| `p3-cpu-smoke-cleanup` | 输出 artifact 和临时目录 cleanup |

fixture registry 是不可变映射；每个 fixture 的代码 SHA-256 在执行前重新验证。
本地 runner 使用隔离临时 cwd、`python -I`、清理后的最小环境和平台对应的进程树
终止逻辑。

## 6. Docker 配置

Docker 执行默认关闭。先由维护者审查镜像内容，再配置精确 digest：

```powershell
$env:REPROFORGE_P3_PYTHON_CPU_IMAGE = 'repository@sha256:<64-lowercase-hex>'
```

以下值会被拒绝：裸 tag、缺少 digest、大写/非十六进制 digest、bundle 自带镜像名、
未知 `runtime_profile`。后端不会自动 pull；镜像必须已存在于 daemon。

运行真实 smoke：

```powershell
uv run pytest -q --no-cov -m docker tests/integration/test_p3_docker_smoke.py
```

真实 smoke 的前置条件：

1. Docker daemon 可连接；
2. 安装 `docker` extra；
3. `REPROFORGE_P3_PYTHON_CPU_IMAGE` 是已审查精确 digest；
4. 对应镜像已预拉取并支持非 root Python 执行。

未满足任一条件时必须把 Docker 验证报告为 unavailable/blocked，不能用 mock 测试或
包镜像 build 代替。

## 7. Docker 运行限制

当前 `python-cpu` profile 强制：

- `network_mode=none`；只支持 `ExperimentSpec.network_policy="offline"`；
- 非 root `65532:65532`；
- `/bundle` 只读挂载并作为工作目录；
- rootfs 只读；`/tmp`、`/output` 为受限 tmpfs；
- `cap_drop=ALL`、`no-new-privileges`、PID/CPU/内存限制；
- argv 直接传给容器，不经 shell；
- 依赖必须有明确版本且 `locked=true`；存在 `unresolved` 时拒绝执行；
- 正常、异常、timeout 和 cancellation 路径都执行容器与临时目录 cleanup。

P3 不支持联网 allowlist、远程 SSH、Colab、Vast.ai、GPU 自动选择、任意宿主挂载或
Docker socket 挂载。

## 8. 指标和 artifact 协议

实验将 JSONL 指标写入：

```text
/output/reproforge-metrics.jsonl
```

每行示例：

```json
{"name":"accuracy","value":0.91,"unit":"ratio","step":100,"split":"test","aggregation":"mean","seed":42}
```

普通 stdout 文本不会变成 `ObservedMetric`。无效 UTF-8 或无效 metric JSON 会得到
`metric_parse_error`。除指标文件外，输出文件只有匹配 `artifact_allowlist` 才会
被记录。`/output` 是 tmpfs，因此后端在容器存活期间用固定可信 collector 生成
有界 tar 流；路径穿越、link、非普通文件、文件数和超限输出会被拒绝。

## 9. 状态与错误码

`RunStatus`：`pending`、`running`、`success`、`failed`、`timeout`、`cancelled`、
`blocked`。

常见 `FailureCode`：

| 错误码 | 含义 |
|---|---|
| `path_validation` | bundle、manifest、entrypoint 或 experiment index 无效 |
| `security_violation` | 后端、fixture、依赖或未解决项违反执行策略 |
| `docker_unavailable` | SDK/daemon 或 Docker 调用不可用 |
| `image_pull_failed` | profile 未配置、digest 镜像不存在；不会自动 pull |
| `network_denied` | Docker 请求了非 offline 网络 |
| `timeout` / `cancelled` | 超时或调用取消，随后执行 cleanup |
| `non_zero_exit` | 被执行 fixture/容器返回非零 |
| `resource_exhausted` | 容器退出表现为资源限制触发 |
| `metric_parse_error` | 结构化指标无效 |
| `artifact_rejected` | 输出归档、路径或大小违反策略 |

## 10. 验证命令

离线 P3 回归：

```powershell
uv run pytest -q --no-cov tests/unit/test_p3_*.py
```

完整非 Docker 门：

```powershell
uv run ruff format --check repro_forge tests
uv run ruff check repro_forge tests
uv run mypy repro_forge
uv run pytest -q
uv run mkdocs build --clean --strict -f docs/mkdocs.yml
uv build
git diff --check
```

CI 的 `p3-security` job 始终运行离线契约与沙箱回归；`p3-docker-smoke` 只有在仓库
变量配置了精确 digest 时运行。P0 包镜像 build 不是 P3 Docker sandbox smoke。

## 11. P3-C 验收记录

2026-08-08 的真实验证环境：

- Docker Desktop `4.82.0`，Linux Engine `29.6.1`，`linux/amd64`；
- reviewed image：`python@sha256:9d7f287598e1a5a978c015ee176d8216435aaf335ed69ac3c38dd1bbb10e8d64`；
- `tests/integration/test_p3_docker_smoke.py`：`5 passed`。

真实 smoke 覆盖：成功 metric、非零退出、timeout、artifact、所有终态容器 cleanup；
安全探针还确认 UID/GID `65532`、仅 loopback interface、`NoNewPrivs=1`、有效
capabilities 为零、只读 bundle/rootfs、`/output` 为限额 tmpfs，以及 CPU、内存、
PID cgroup 限制实际生效。宿主 `OPENAI_API_KEY` 未进入容器。

P3 因此标记为 `Complete`。在其他 daemon、内核或镜像 digest 上部署时仍必须重跑
同一 smoke；阶段完成不构成对任意镜像或未来运行环境的永久信任。
