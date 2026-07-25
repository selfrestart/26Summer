# 开发工作流

本文档描述 ReproForge 的日常开发流程，包括环境搭建、代码提交规范和验证步骤。

---

## 环境搭建

### 前置条件

- **[uv](https://docs.astral.sh/uv/)** — Python 包管理器
  ```bash
  # macOS / Linux
  curl -LsSf https://astral.sh/uv/install.sh | sh
  
  # Windows (PowerShell)
  powershell -ExecutionPolicy Bypass -c "irm https://astral.sh/uv/install.ps1 | iex"
  ```

### 一键初始化

```bash
git clone https://github.com/selfrestart/26Summer.git
cd repro-forge
make setup
```

`make setup` 内部执行：
1. `uv venv` — 根据 `.python-version` 创建虚拟环境（锁定 Python 3.13）
2. `uv sync --group dev` — 安装核心依赖 + 开发工具（ruff, mypy, pytest 等）
3. `uv run pre-commit install` — 安装 Git 提交钩子

### 手动初始化（高级用户）

```bash
uv venv
uv sync --group dev
# 如需完整功能：
uv sync --all-extras --group dev
```

---

## 日常开发周期

### 写代码前

```bash
# 确保在最新的 develop 分支
git checkout develop
git pull origin develop

# 创建功能分支
git checkout -b feat/<module>/<description>
# 例如: git checkout -b feat/agents/paper-reader
```

### 写代码中

```bash
# 运行一次 lint 检查当前代码（不修复）
make lint

# 自动修复 lint 问题
uv run ruff check --fix repro_forge/ tests/

# 自动格式化
make format

# 类型检查
make typecheck
```

### 提交前

```bash
# 一键运行所有检查
make check
```

`make check` 等价于依次执行：
1. `format-check` — 检查代码格式是否符合规范
2. `lint` — 运行 ruff linter
3. `typecheck` — 运行 mypy 类型检查
4. `test` — 运行所有单元测试 + 集成测试

### 提交

```bash
git add <files>
git commit -m "feat(agents): implement PaperReader agent"
# pre-commit hooks 会自动运行 ruff + mypy

git push origin feat/agents/paper-reader
```

---

## Makefile 命令手册

| 命令 | 用途 | 何时使用 |
|------|------|---------|
| `make setup` | 全新环境初始化 | 第一次克隆项目后 |
| `make sync` | 安装核心依赖 + 开发工具 | pull 后有新依赖 |
| `make sync-all` | 安装所有可选依赖 | 需要 chromadb/neo4j/mlflow 等 |
| `make check` | 一站式检查 | 提交前必须运行 |
| `make format` | 自动格式化 | 写代码过程中 |
| `make lint` | 仅 lint | 快速检查语法问题 |
| `make typecheck` | 仅类型检查 | 修改了类型定义后 |
| `make test` | 运行单元 + 集成测试 | 写/改代码后 |
| `make test-cov` | 测试 + 覆盖率报告 | 提交前确认覆盖率 |
| `make test-e2e` | 端到端测试 | 需要服务时 |
| `make ci` | 模拟完整 CI 流程 | 推送前本地验证 |
| `make clean` | 清理构建产物 | 遇到奇怪的缓存问题时 |

---

## 代码规范

### 分支命名

```
feat/<module>/<desc>      新功能     feat/agents/add-paper-reader
fix/<module>/<desc>       修复       fix/pdf-parser/memory-leak
docs/<desc>               文档       docs/api-reference-update
refactor/<module>/<desc>  重构       refactor/memory/retrieval-api
```

### Commit Message 格式

遵循 [Conventional Commits](https://www.conventionalcommits.org/)：

```
<type>(<scope>): <简短描述>

<可选详细说明>
<可选：Closes #issue_id>
```

类型：`feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`, `perf`

**示例**：

```
feat(agents): implement Verifier agent with metric comparison

- Add comparator module for paper vs reproduced metrics
- Implement statistical significance tests using scipy
- Generate reproduction fidelity report

Closes #42
```

### Python 风格

- 行宽：100 字符
- 缩进：4 空格
- 引号：双引号
- 换行符：LF (`\n`)
- 导入：单行、按字母排序（ruff 自动处理）
- Docstring：Google 风格（见下文）
- 类型标注：所有公开函数必须标注

### Docstring 模板

```python
def calculate_fidelity(
    claimed: dict[str, float],
    reproduced: dict[str, float],
) -> float:
    """Calculate the reproduction fidelity score.

    Compares claimed metric values from the paper against reproduced
    results. Returns a score between 0 and 100 where higher values
    indicate better reproduction fidelity.

    Args:
        claimed: Paper-claimed metrics as {metric_name: value}.
        reproduced: Reproduced metrics as {metric_name: value}.

    Returns:
        Fidelity score between 0.0 and 100.0.

    Raises:
        ValueError: If claimed and reproduced have different metric sets.

    Example:
        >>> calculate_fidelity({"acc": 94.5}, {"acc": 93.1})
        98.5
    """
```

---

## 测试策略

### 测试层级

| 层级 | 位置 | 目标覆盖率 | 特点 |
|------|------|-----------|------|
| **Unit** | `tests/unit/` | ≥ 90% | 无 LLM 调用、无网络、无 I/O |
| **Integration** | `tests/integration/` | ≥ 70% | 使用 FakeLLMProvider 模拟 LLM |
| **E2E** | `tests/e2e/` | ≥ 50% | 真实 PDF 输入，可能调用 LLM API |

### Mock 策略

```python
# ✅ 正确：使用 FakeLLMProvider
def test_my_agent(fake_provider):
    agent = MyAgent(provider=fake_provider)
    result = await agent.run(task)
    assert result.status == "success"

# ❌ 错误：单元测试调用真实 API
def test_my_agent():
    agent = MyAgent(provider=OpenAIProvider())  # 慢、花钱、不稳定
```

### 标记

```python
@pytest.mark.slow      # 慢速测试，CI 默认不跑
@pytest.mark.llm       # 需要真实 LLM API，CI 不跑
@pytest.mark.unit      # 单元测试标记
@pytest.mark.e2e       # 端到端测试
```

---

## 发布流程

```
develop 积累 PR
        │
        ▼
  release/vX.Y.Z 分支
        │
        ├── 版本号 bump（pyproject.toml + __init__.py）
        ├── CHANGELOG 更新
        │
        ▼
  PR → main (保护分支)
        │
        ├── CI 全量回归
        │
        ▼
  git tag vX.Y.Z
        │
        ├── PyPI 自动发布 (release.yml)
        ├── Docker 镜像推送 GHCR
        └── GitHub Release 自动生成
```

---

## FAQ

### Q: Windows 上 Makefile 不可用？

A: 使用 Git Bash 或 WSL 运行 `make` 命令。或者直接用 `uv run` 前缀手动执行：

```powershell
uv run ruff check repro_forge/ tests/
uv run mypy repro_forge/
uv run pytest tests/unit/
```

### Q: pre-commit 安装失败？

A: 确保网络可达 GitHub：
```bash
uv run pre-commit install
uv run pre-commit run --all-files  # 手动全体检查
```

### Q: uv sync 很慢？

A: 首次同步需要下载所有依赖，后续有缓存后只需数秒。如果不需要所有可选功能，只运行 `make sync`（仅装核心 + 开发工具）。
