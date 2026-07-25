# 发布流程

本文档描述 ReproForge 的版本发布流程。

---

## 版本号规范

遵循 [Semantic Versioning 2.0.0](https://semver.org/)：

```
MAJOR.MINOR.PATCH

MAJOR — 不兼容的 API 变更
MINOR — 向后兼容的新功能
PATCH — 向后兼容的 Bug 修复
```

### 预发布标识

```
0.1.0-alpha.1    # Alpha 版本
0.5.0-beta.1     # Beta 版本
1.0.0-rc.1       # Release Candidate
1.0.0            # 正式版
```

---

## 自动化发布

当 `git tag vX.Y.Z` 被推送时，`.github/workflows/release.yml` 自动执行：

```
git tag v0.2.0
git push origin v0.2.0

  ┌─────────────────────────────────────────────┐
  │ CI: Release Workflow                         │
  │                                              │
  │  1. 检出 tag 对应代码                        │
  │  2. python -m build (构建 wheel + sdist)     │
  │  3. PyPI 发布                                │
  │  4. Docker 镜像构建 + 推送 GHCR              │
  │  5. GitHub Release 自动生成                  │
  └─────────────────────────────────────────────┘
```

---

## 手动发布步骤

### 1. 准备 Release 分支

```bash
git checkout develop
git pull origin develop

# 创建 release 分支
git checkout -b release/v0.2.0
```

### 2. 更新版本号

```bash
# 使用 bumpver 自动更新
uv run bumpver update --minor --dry   # 预览
uv run bumpver update --minor         # 执行
```

`bumpver` 会自动更新：
- `pyproject.toml` — `version = "0.2.0"`
- `repro_forge/__init__.py` — `__version__ = "0.2.0"`
- `CITATION.cff` — `version: 0.2.0`
- 自动 commit + tag

### 3. 更新 CHANGELOG

```bash
# 将 [Unreleased] 改为 [0.2.0] - YYYY-MM-DD
# 添加新增/修复/变更条目
```

### 4. 创建 PR 并合并

```bash
git push origin release/v0.2.0

# 在 GitHub 上创建 PR: release/v0.2.0 → main
# 等待 CI 全量通过
# Maintainer 审查并合并
```

### 5. 创建 Tag 并发布

```bash
git checkout main
git pull origin main

git tag -a v0.2.0 -m "Release v0.2.0"
git push origin v0.2.0
# CI 自动执行发布流程
```

---

## 发布检查清单

- [ ] 所有单元测试通过 (`make test`)
- [ ] 所有集成测试通过 (`make test --integration`)
- [ ] E2E 测试通过 (CI 自动运行)
- [ ] 类型检查通过 (`make typecheck`)
- [ ] Lint 检查通过 (`make lint`)
- [ ] 版本号已更新（pyproject.toml / __init__.py / CITATION.cff）
- [ ] CHANGELOG 已更新
- [ ] 文档无死链 (`make docs`)
- [ ] Release notes 已撰写
