# SkylineA2A — Agent-to-Agent demo with monetization via Azure API Management

> **Customer question** (relayed by Olav from Sebastiaan):
> *"For tomorrow's sync, we'd like to focus the conversation on the long-term vision for
> agent-to-agent communication knowing that usage in the end would need to be billed.
> What are our options here?"*
>
> This repo is the working answer — **two flavours of A2A-compliant agents** sitting behind a
> single **Azure API Management** gateway that handles authentication, rate-limiting and
> per-subscription metering.

---

## Architecture

```
                          ┌──────────────────────────────────────────┐
                          │   Azure API Management (GenAI Gateway)   │
   A2A Client ──── sub ──▶│                                          │
                key       │   Products: Free / Pro                   │
                          │   Policies: rate-limit-by-key,           │
                          │             emit-metric, MI outbound     │
                          │                                          │
                          │   /demo1/* ─▶ Foundry A2A endpoint        │
                          │   /demo2/* ─▶ MAF A2A server (ACA)        │
                          └─────┬──────────────────────┬──────────────┘
                                │                      │
                                ▼                      ▼
                  ┌──────────────────────────┐  ┌────────────────────────────┐
                  │ Foundry Agent Service    │  │ Microsoft Agent Framework  │
                  │ "Microsoft Docs Expert"  │  │ "DevOps Helper Agent"      │
                  │ ─ Prompt Agent           │  │ ─ ChatAgent + 3 function   │
                  │ ─ MCP: Learn MCP Server  │  │   tools (simulated ops)    │
                  │ ─ Model: gpt-5.2         │  │ ─ Model: gpt-5.2           │
                  │ ─ A2A v0.3, JSON-RPC     │  │ ─ A2A v1.0, JSON-RPC + SSE │
                  └──────────────────────────┘  └────────────────────────────┘
```

## Demos at a glance

| | **Demo 1 — Foundry** | **Demo 2 — MAF** |
|---|---|---|
| Persona | Microsoft Docs Expert | DevOps Helper |
| Platform | Foundry Agent Service (Prompt Agent) | Microsoft Agent Framework |
| Hosting | Foundry-managed | ACA (image from ACR) |
| Tooling | MCP → `learn.microsoft.com/api/mcp` | 3 simulated function tools |
| SDK | `azure-ai-projects>=2.0.0` (preview v2.x) | `agent-framework` + `agent-framework-a2a` (beta) |
| A2A status | Public Preview | Beta (sub-package only) |

## Repo layout

```
SkylineA2A/
├── README.md              ← this file
├── .env.example           ← committed; fill ".env" with real values
├── pyproject.toml         ← tooling config (ruff); no shared dependencies
├── demo1-foundry/         ← Demo 1 scripts + requirements (Foundry A2A v0.3)
│   ├── create_agent.py
│   ├── enable_a2a.py
│   ├── test_a2a_client.py
│   ├── delete_agent.py
│   ├── run-local.ps1      ← runs the 3 steps end-to-end in .venv-demo1
│   └── requirements.txt
├── demo2-maf/             ← Demo 2 server (a single file) + requirements
│   ├── mafagent.py        ← agent + tools + A2A card + Starlette server
│   ├── smoke_test.py      ← local A2AAgent smoke test
│   ├── run-local.ps1
│   └── requirements.txt
├── apim/                  ← APIM import scripts, policies, products
├── client-e2e/            ← End-to-end A2A client used for both demos
└── docs/                  ← monetization narrative + customer talking points
```

> **Two virtual environments.** Demo 1 needs `a2a-sdk 1.0.x` (Foundry's A2A v0.3
> protocol uses gRPC/protobuf bindings); Demo 2 transitively pins `a2a-sdk<0.3.24`
> via `agent-framework-a2a` beta. They cannot coexist in one venv, so the repo
> has no shared root `requirements.txt` — each demo owns its own.

## Quickstart (high-level)

1. **Bootstrap your local env**
   ```powershell
   Copy-Item .env.example .env       # then fill in real values
   ```
2. **Demo 1 — Foundry A2A agent**
   ```powershell
   python -m venv .venv-demo1
   .\.venv-demo1\Scripts\Activate.ps1
   pip install --pre -r demo1-foundry\requirements.txt
   ```
   Walkthrough: [`demo1-foundry/README.md`](demo1-foundry/README.md).
3. **Demo 2 — MAF A2A server (local first)**
   ```powershell
   python -m venv .venv-demo2
   .\.venv-demo2\Scripts\Activate.ps1
   pip install --pre -r demo2-maf\requirements.txt
   ```
   Walkthrough: [`demo2-maf/README.md`](demo2-maf/README.md).
4. **Demo 2 — push to ACR → ACA** — `demo2-maf/docker-build-push.ps1`, then create the ACA.
5. **APIM monetization layer** — see [`apim/README.md`](apim/README.md).
6. **End-to-end demo through APIM** — see [`client-e2e/`](client-e2e/).

## Monetization story (TL;DR)

| Capability | Native APIM A2A support |
|---|---|
| Subscription-key gating | ✅ |
| Per-subscription rate limit / quota | ✅ (`rate-limit-by-key`) |
| Per-call metering to App Insights | ✅ (`emit-metric`) |
| Built-in GenAI OTel attrs (`genai.agent.id`) | ✅ |
| **Per-token billing** | ❌ (`llm-token-limit`/`llm-emit-token-metric` don't apply to A2A) |
| Marketplace metered billing | ❌ (custom Event-Hub + metering function needed) |

Full breakdown lives in [`docs/monetization.md`](docs/monetization.md) once that phase lands.

## Key references

- Foundry A2A endpoint:
  https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/enable-agent-to-agent-endpoint
- Microsoft Agent Framework A2A package:
  https://github.com/microsoft/agent-framework/tree/main/python/packages/a2a
- APIM A2A API (GA):
  https://learn.microsoft.com/en-us/azure/api-management/agent-to-agent-api
- Microsoft Learn MCP Server:
  https://learn.microsoft.com/en-us/training/support/mcp

---

> **Status**: WIP. Each sub-folder README is filled in as that phase of the implementation lands.
