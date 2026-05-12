# Demo 1 — Microsoft Docs Expert (Foundry A2A)

This demo creates a Microsoft Foundry Agent Service **Prompt Agent** grounded in the public Microsoft Learn MCP server and exposes it as a Foundry **A2A v0.3** endpoint.

## Prerequisites

- Python 3.11+
- Azure CLI or another `DefaultAzureCredential` source signed in to the tenant that owns the Foundry project
- A Foundry project endpoint in `.env` as `FOUNDRY_PROJECT_ENDPOINT`
- A deployed model in the project, configured as `FOUNDRY_DEPLOYMENT_NAME` (defaults to `gpt-5.2`)
- RBAC: the signed-in identity needs **Azure AI User** or higher on the Foundry project for data-plane access. If create/update operations are denied, use **Azure AI Project Manager** or **Azure AI Owner** on the Foundry resource/project. The calling identity used by `test_a2a_client.py` also needs **Azure AI User** or higher.
- The project managed identity should have **Azure AI User** on the Foundry resource/project. For any model or connected resource hosted outside this Foundry project, grant the project managed identity the relevant access required by that external resource.

## Install dependencies (separate venv)

Demo 1 talks to Foundry's A2A v0.3 endpoint with the **`a2a-sdk 1.0.x`** client
(protobuf bindings). Demo 2 pulls in `agent-framework-a2a` (beta) which pins
`a2a-sdk<0.3.24`. **They cannot coexist in a single venv** — use one venv per
demo.

From the repo root:

```powershell
python -m venv .venv-demo1
.\.venv-demo1\Scripts\Activate.ps1
python -m pip install --pre -r demo1-foundry\requirements.txt
```

## Configure `.env`

Copy `.env.example` to `.env` and fill at least:

```powershell
FOUNDRY_PROJECT_ENDPOINT="https://<account>.services.ai.azure.com/api/projects/<project>"
FOUNDRY_DEPLOYMENT_NAME="gpt-5.2"
DEMO1_AGENT_NAME="ms-docs-expert"
DEMO1_AGENT_DESCRIPTION="Microsoft documentation expert grounded in Microsoft Learn via MCP."
DEMO1_AGENT_VERSION="1.0.0"
MCP_LEARN_ENDPOINT="https://learn.microsoft.com/api/mcp"
```

Do not commit `.env`.

## Run the demo

From the repo root, the whole flow is wrapped in a single PowerShell script
that activates `.venv-demo1` and runs the three steps in order:

```powershell
.\demo1-foundry\run-local.ps1
```

It runs:

1. `create_agent.py` — creates (or reuses) the agent in Foundry.
2. `enable_a2a.py` — flips the A2A toggle and prints the public URLs.
3. `test_a2a_client.py` — sends a Microsoft Learn question through A2A.

If any step exits with a non-zero code the script stops. To run the steps
manually instead:

```powershell
cd demo1-foundry
python create_agent.py
python enable_a2a.py
python test_a2a_client.py
```

`enable_a2a.py` prints copy-pasteable values for `.env`:

```powershell
DEMO1_A2A_BASE_URL="https://<account>.services.ai.azure.com/api/projects/<project>/agents/<agent>/endpoint/protocols/a2a"
DEMO1_AGENT_CARD_URL="https://<account>.services.ai.azure.com/api/projects/<project>/agents/<agent>/endpoint/protocols/a2a/agentCard/v0.3"
```

## Foundry A2A quirk

Foundry Agent Service currently supports A2A **v0.3** only. Its authenticated agent card is not at the standard `/.well-known/agent-card.json` path; it is at:

```text
<DEMO1_A2A_BASE_URL>/agentCard/v0.3
```

That is why `test_a2a_client.py` passes `agent_card_path="agentCard/v0.3"` to `A2ACardResolver`.

## Cleanup

```powershell
python delete_agent.py
```

The cleanup script is idempotent: if the agent is already gone, it exits successfully.
