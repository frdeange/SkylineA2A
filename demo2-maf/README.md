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

Demo 2 uses `agent-framework-a2a` (beta), which pins `a2a-sdk<0.3.24`. Demo 1
needs `a2a-sdk 1.0.x` for the Foundry A2A protocol. **They cannot coexist** —
use a dedicated venv for each demo.

From the repo root:

```powershell
python -m venv .venv-demo2
.\.venv-demo2\Scripts\Activate.ps1
pip install --pre -r demo2-maf\requirements.txt
```

`--pre` is required: `agent-framework-a2a==1.0.0b260507` is a pre-release.

## Run locally

```powershell
.\demo2-maf\run-local.ps1
```

(Activates `.venv-demo2` and runs `python demo2-maf\mafagent.py`.)

The server starts at `http://localhost:9999/` and prints its public URL.

## Local endpoints

| Path | Method | Notes |
|---|---|---|
| `/.well-known/agent.json` | GET | A2A agent card |
| `/` | POST | JSON-RPC A2A protocol |

## Smoke test

Once the server is running, in a second terminal (same `.venv-demo2` activated)
run the smoke test:

```powershell
.\.venv-demo2\Scripts\Activate.ps1
python demo2-maf\smoke_test.py
```

[`smoke_test.py`](./smoke_test.py) mirrors the canonical
[`agent_with_a2a.py`](https://github.com/microsoft/agent-framework/blob/main/python/samples/04-hosting/a2a/agent_with_a2a.py)
client sample: it resolves the AgentCard, wraps it in an `A2AAgent`, sends a
non-streaming prompt (`Is api-frontend healthy in prod?` — exercises
`check_deployment_status`) and a streaming prompt (`Please restart
order-service in staging.` — exercises `restart_service`) and prints both
responses.

It points at `DEMO2_PUBLIC_URL` (defaults to `http://localhost:9999/`), so the
same script also works against the ACA endpoint later — just change the env
var. The end-to-end client in [`client-e2e/`](../client-e2e/) (next phase) is
the one that targets APIM specifically with subscription keys.

A bare `curl` against the local card is also useful to confirm the server is
even up:

```powershell
curl http://localhost:9999/.well-known/agent.json
```

## Next phase: ACA behind APIM

Docker, ACR, ACA, and APIM are intentionally out of scope for this local
phase. The same `mafagent.py` runs in the container — the only difference
is the value of `DEMO2_PUBLIC_URL` (set to the ACA FQDN) so the agent card
advertises the right public URL.
