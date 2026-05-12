# Demo 2 — Microsoft Agent Framework DevOps Helper over A2A

A Microsoft Agent Framework agent hosted as an A2A endpoint, mirroring the
canonical MAF sample:
[`agent_framework_to_a2a.py`](https://github.com/microsoft/agent-framework/blob/main/python/samples/04-hosting/a2a/agent_framework_to_a2a.py).

The whole demo lives in a single file: [`mafagent.py`](./mafagent.py) —
agent definition, three simulated DevOps tools (deployment status, restart,
Azure Resource Health), the A2A `AgentCard`, the request handler, and the
Starlette/uvicorn server.

The model is served by the same Foundry project as Demo 1
(`FOUNDRY_PROJECT_ENDPOINT` + `FOUNDRY_DEPLOYMENT_NAME=gpt-5.2`) via
`FoundryChatClient`.

## Prerequisites

- Python 3.11+
- `az login` (or any other `DefaultAzureCredential` source) signed in to the
  tenant that owns the Foundry project, with **Azure AI User** or higher on it.
- Repo-root `.env` filled in (see [`.env.example`](../.env.example)).

## Install (separate venv)

`agent-framework-a2a` is installed **from a git commit on `main`** (commit
`cfd3dfe`, which includes PR
[#5752 — "Migrate agent-framework-a2a to a2a-sdk v1.0"](https://github.com/microsoft/agent-framework/pull/5752)).
The PyPI wheel (`1.0.0b260507`) is older and still pins `a2a-sdk<0.3.24`,
so it cannot use the canonical sample's API. Pinning to a commit SHA keeps
the install reproducible while letting us use the v1.0 server API.

Demo 2 still uses its own venv (separate from Demo 1) because of the heavy
`agent-framework-*` dependency chain. From the repo root:

```powershell
python -m venv .venv-demo2
.\.venv-demo2\Scripts\Activate.ps1
pip install --pre -r demo2-maf\requirements.txt
```

`--pre` is kept because the resolved `agent-framework-a2a` version
(`1.0.0b260507`) is still a pre-release identifier even when installed
from git.

## Run locally

```powershell
.\demo2-maf\run-local.ps1
```

(Activates `.venv-demo2` and runs `python demo2-maf\mafagent.py`.)

The server starts at `http://localhost:9999/` and prints its public URL.

## Local endpoints

| Path | Method | Notes |
|---|---|---|
| `/.well-known/agent-card.json` | GET | A2A agent card |
| `/` | POST | JSON-RPC A2A protocol |

## Smoke test

Once the server is running, in a second terminal use the wrapper that calls
the venv's Python directly (so you don't need to remember to activate):

```powershell
.\demo2-maf\run-smoke.ps1
```

[`smoke_test.py`](./smoke_test.py) mirrors the canonical
[`agent_with_a2a.py`](https://github.com/microsoft/agent-framework/blob/main/python/samples/04-hosting/a2a/agent_with_a2a.py)
client sample: it resolves the AgentCard, wraps it in an `A2AAgent`, and sends
two streaming prompts — one per tool (`Is api-frontend healthy in prod?` →
`check_deployment_status`, `Please restart order-service in staging.` →
`restart_service`). Streaming is the natural model for A2A v1.0 tool-using
turns: the executor pushes the tool result as a task `artifact` and the model's
final answer arrives as SSE chunks.

It points at `DEMO2_PUBLIC_URL` (defaults to `http://localhost:9999/`), so the
same script also works against the ACA endpoint later — just change the env
var. The end-to-end client in [`client-e2e/`](../client-e2e/) (next phase) is
the one that targets APIM specifically with subscription keys.

A bare `curl` against the local card is also useful to confirm the server is
even up:

```powershell
curl http://localhost:9999/.well-known/agent-card.json
```

## Container: build and push to ACR

The same `mafagent.py` runs unchanged inside a container — the only
difference is the value of `DEMO2_PUBLIC_URL` (set to the ACA FQDN, and later
to the APIM URL) so the agent card advertises the right public URL.

> **Required runtime env vars on ACA** (no secrets — Managed Identity covers
> auth):
> | Variable | Notes |
> |---|---|
> | `FOUNDRY_PROJECT_ENDPOINT` | Full Foundry project endpoint (see Demo 1). |
> | `FOUNDRY_DEPLOYMENT_NAME` | `gpt-5.2`. |
> | `DEMO2_PUBLIC_URL` | The public URL the agent card should advertise. **Default is `http://localhost:9999/`** — leave that and the card will point to nothing useful once it sits behind APIM. |
> | `AZURE_CLIENT_ID` | Only if the Container App uses a **user-assigned** managed identity. |
>
> The ACA managed identity must have **Azure AI User** on the Foundry
> resource (or Cognitive Services User as a fallback).
>
> ACA probes are **separate** from the Dockerfile `HEALTHCHECK` — the
> in-image one is only used by `docker run` locally. Define a startup probe
> on the Container App with at least 60–120 s tolerance pointing at
> `/.well-known/agent-card.json`, and reuse the same path for readiness and
> liveness.

Prerequisites:

- `az login` against the subscription that owns ACR.
- `AcrPush` role on the ACR resource for the signed-in identity.
- `ACR_NAME`, `ACR_LOGIN_SERVER`, and `ACR_IMAGE_NAME` set in
  [`../.env`](../.env.example).
  (`ACR_IMAGE_NAME` must be a lowercase Docker repository name).

Then from the repo root:

```powershell
.\demo2-maf\docker-build-push.ps1
```

This script uses **remote build in ACR** (`az acr build`), so local Docker is
not required.

The script tags the image twice: `:<ACR_IMAGE_TAG>` (default `latest`) and
`:sha-<git-short-sha>` for traceability. Both tags are pushed so an ACA
revision can be pinned to a known SHA.

Build only (no push) for a quick sanity check:

```powershell
.\demo2-maf\docker-build-push.ps1 -SkipPush
```

## Next phase: Container Apps + APIM

After `docker-build-push.ps1` succeeds:

1. **Create the ACA** referencing the pushed image. Enable a system-assigned
   managed identity and grant it **Azure AI User** on the Foundry resource.
2. **Set env vars** on the ACA: `FOUNDRY_PROJECT_ENDPOINT`,
   `FOUNDRY_DEPLOYMENT_NAME=gpt-5.2`, and `DEMO2_PUBLIC_URL=<final-public-url>`.
3. **Update `.env`** with `ACA_FQDN` so the APIM phase can wire the backend.

The agent card advertised by `mafagent.py` is whatever `DEMO2_PUBLIC_URL`
says, so when APIM fronts this backend, set `DEMO2_PUBLIC_URL` to the APIM
base path (`https://apim-skyline.azure-api.net/demo2/`) — that way clients
discovering the card always see the gateway URL, not the ACA URL.
