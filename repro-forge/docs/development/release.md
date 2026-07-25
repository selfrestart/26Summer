# 发布产物流程

P0 只验证 ReproForge 可以构建为标准 Python wheel 和 source distribution，
不会自动发布到 PyPI、GHCR 或创建 GitHub Release。

## Tag 触发流程

推送符合 `v*` 的 tag 后，根目录 `.github/workflows/release.yml` 将：

1. 从当前源码构建 wheel 和 source distribution。
2. 在隔离虚拟环境中安装 wheel 并运行 `repro-forge`。
3. 将 `dist/` 上传为 GitHub Actions artifact。

这些 artifact 仅供检查和手动下载，不构成公开发布。

## 本地验证

```bash
cd repro-forge
uv build
uv run --isolated --no-project --with dist/*.whl repro-forge
```

## P0 发布检查清单

- [ ] `make check` 通过
- [ ] `uv build` 成功生成 wheel 和 source distribution
- [ ] wheel 可以在隔离环境中安装并运行 CLI
- [ ] `make docs` 严格构建成功
- [ ] `make docker-run` 成功运行 P0 CLI
- [ ] 版本号在 `pyproject.toml`、`repro_forge/__init__.py` 和 `CITATION.cff` 中一致
- [ ] CHANGELOG 已更新

公开发布策略将在项目具备首个可用工作流后单独设计。
