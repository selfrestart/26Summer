FROM python:3.13-slim AS builder

WORKDIR /app

# Build the currently implemented P0/P1/P2 package and core dependencies.
COPY pyproject.toml README.md ./
COPY repro_forge/ ./repro_forge/
RUN pip wheel --no-cache-dir --wheel-dir /wheels .


FROM python:3.13-slim AS runtime

LABEL org.opencontainers.image.title="ReproForge"
LABEL org.opencontainers.image.description="ReproForge P0/P1/P2 paper-reading and methodology package"
LABEL org.opencontainers.image.source="https://github.com/selfrestart/26Summer/tree/main/repro-forge"
LABEL org.opencontainers.image.licenses="Apache-2.0"

WORKDIR /app

COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/*.whl && rm -rf /wheels

RUN useradd --create-home --shell /bin/bash reproforge
USER reproforge

ENTRYPOINT ["repro-forge"]
