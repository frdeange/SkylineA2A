# syntax=docker/dockerfile:1.7

# ═════════════════════════════════════════════════════════════════════════════
#  Demo 2 — Microsoft Agent Framework A2A server (DevOps Helper)
#  Multi-stage build:
#    1. builder — installs deps (including the git-pinned agent-framework-a2a).
#    2. runtime — slim image with only the virtualenv + the agent script.
#  The image is pushed to ACR and run on Azure Container Apps, fronted by APIM.
# ═════════════════════════════════════════════════════════════════════════════


# ─── Stage 1: builder ────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# git is required at install time because requirements.txt pins
# agent-framework-a2a to a specific commit on github.com/microsoft/agent-framework.
# build-essential covers the (rare) case where a wheel is missing and pip falls
# back to a source build.
RUN apt-get update \
 && apt-get install -y --no-install-recommends git build-essential \
 && rm -rf /var/lib/apt/lists/*

# Create an isolated virtualenv that we copy into the runtime stage.
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# Copy requirements.txt only (keeps this layer cacheable across code changes).
COPY requirements.txt ./

# `--pre` is required because agent-framework-a2a is pinned via a git URL whose
# `pyproject.toml` declares a pre-release version string. The protobuf<7 pin
# inside requirements.txt blocks `--pre` from pulling in protobuf RCs.
RUN pip install --upgrade pip \
 && pip install --pre -r requirements.txt


# ─── Stage 2: runtime ────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    DEMO2_HOST="0.0.0.0" \
    DEMO2_PORT="9999"

# curl is used by the HEALTHCHECK; no other apt packages needed at runtime.
RUN apt-get update \
 && apt-get install -y --no-install-recommends curl \
 && rm -rf /var/lib/apt/lists/* \
 && groupadd --system app \
 && useradd --system --gid app --home /app --shell /sbin/nologin app

# Copy the built virtualenv from the builder stage.
COPY --from=builder /opt/venv /opt/venv

WORKDIR /app
COPY --chown=app:app mafagent.py ./

USER app
EXPOSE 9999

# A local healthcheck for `docker run` sanity checks. **ACA ignores this** —
# you must configure startup/liveness/readiness probes on the Container App
# itself (point them at /.well-known/agent-card.json with a generous
# start-period to absorb the cold-start cost of importing the agent-framework
# package chain + initializing FoundryChatClient + Managed Identity).
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl --fail --silent http://127.0.0.1:${DEMO2_PORT}/.well-known/agent-card.json || exit 1

CMD ["python", "mafagent.py"]
