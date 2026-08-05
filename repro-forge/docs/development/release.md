# 发布产物流程

P0 建立了标准 Python wheel/source distribution 验证，当前 artifact 包含 P0/P1
能力。工作流不会自动发布到 PyPI、GHCR 或创建 GitHub Release。

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

## 当前 P0/P1 发布检查清单

- [ ] `make check` 通过
- [ ] `uv build` 成功生成 wheel 和 source distribution
- [ ] wheel 可以在隔离环境中安装并运行 CLI
- [ ] `make docs` 严格构建成功
- [ ] `make docker-run` 成功运行当前 CLI
- [ ] 版本号在 `pyproject.toml`、`repro_forge/__init__.py` 和 `CITATION.cff` 中一致
- [ ] CHANGELOG 已更新

P8 将在现有工程检查之上增加 benchmark、成本、性能、安全和 scorecard 发布门；
在 P8 前不能用单一总分替代各阶段的阻断条件。
