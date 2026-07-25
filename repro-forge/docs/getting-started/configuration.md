# P0 Configuration

P0 configuration is contained in `pyproject.toml` and does not require runtime
environment variables.

| Configuration | P0 behavior |
|---|---|
| Python | 3.11-3.13 supported; `.python-version` selects 3.13 locally |
| Dependencies | `uv.lock` is authoritative for development and CI |
| Formatting and lint | Ruff, targeting the minimum supported Python 3.11 |
| Type checking | mypy strict mode |
| Tests | pytest with branch coverage and a 60% minimum |
| Documentation | MkDocs Material, built with strict validation |

`.env.example` reserves provider, storage, execution, and observability settings
for later phases. None of those variables are consumed by the P0 package.
