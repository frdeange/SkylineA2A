# 🚀 SkylineA2A — Agent-to-Agent demo with APIM monetization

This project demonstrates **two A2A agent flavors** behind **one Azure API Management gateway** to answer a core business question:

> *How do we operationalize and monetize agent-to-agent communication at scale?*

---

## ✅ What we built

- 🧠 **Demo 1 (Foundry Agent Service)**  
  Prompt agent (`gpt-5.2`) exposed as A2A, grounded with **Microsoft Learn MCP**.
- ⚙️ **Demo 2 (Microsoft Agent Framework)**  
  Python MAF agent (`gpt-5.2`) exposed as A2A from an app runtime (local/ACA).
- 💰 **Monetization control plane (APIM)**  
  Product-based access (`Free`, `Pro`), subscription-key enforcement, quota/rate policies, and usage telemetry.

---

## 🏗️ Architecture (high level)

```text
                          ┌──────────────────────────────────────────┐
                          │ Azure API Management (A2A Gateway)       │
 A2A Client ──sub key───▶ │ Products: Free / Pro                     │
                          │ Policies: auth, rate-limit, metering     │
                          │ Routes: /demo1/* and /demo2/*            │
                          └──────────────┬────────────────────────────┘
                                         │
                    ┌────────────────────┴───────────────────┐
                    ▼                                        ▼
       ┌───────────────────────────────┐        ┌──────────────────────────────┐
       │ Demo 1 — Foundry Agent Service│        │ Demo 2 — MAF A2A Server      │
       │ Docs Expert + Learn MCP       │        │ DevOps Helper + tool functions│
       │ A2A JSON-RPC                  │        │ A2A JSON-RPC                  │
       └───────────────────────────────┘        └──────────────────────────────┘
```

---

## 🧪 Demos at a glance

| Dimension | Demo 1 — Foundry | Demo 2 — MAF |
|---|---|---|
| Persona | Microsoft Docs Expert | DevOps Helper |
| Runtime | Foundry Agent Service | Starlette app (local / ACA) |
| Model | `gpt-5.2` | `gpt-5.2` |
| A2A exposure | Foundry A2A endpoint | `agent-framework-a2a` server |
| Tooling | Microsoft Learn MCP | Simulated DevOps tools |

---

## 📂 Repository layout

```text
SkylineA2A/
├── README.md
├── .env.example
├── demo1-foundry/       # Foundry scripts + requirements
├── demo2-maf/           # MAF agent server + smoke tests + Docker
├── apim/                # APIM policy XML + notes
└── client-e2e/          # Final validation through APIM
```

---

## ⚡ Quickstart

1. **Create local config**
   ```powershell
   Copy-Item .env.example .env
   ```
2. **Run Demo 1 locally**
   ```powershell
   python -m venv .venv-demo1
   .\.venv-demo1\Scripts\Activate.ps1
   pip install --pre -r demo1-foundry\requirements.txt
   ```
3. **Run Demo 2 locally**
   ```powershell
   python -m venv .venv-demo2
   .\.venv-demo2\Scripts\Activate.ps1
   pip install --pre -r demo2-maf\requirements.txt
   ```
4. **Publish Demo 2 to ACR/ACA**  
   Use `demo2-maf\docker-build-push.ps1`.
5. **Apply APIM configuration**  
   See `apim\README.md`.
6. **Execute final APIM validation**
   ```powershell
   python .\client-e2e\final_test_apim_cards.py
   ```

---

## 💳 API Management monetization strategy

| Capability | Status in this solution |
|---|---|
| Product-tier access (Free / Pro) | ✅ Implemented |
| Subscription-key authentication | ✅ Implemented |
| Per-subscription throttling / quota | ✅ Implemented |
| Per-call telemetry (metering signals) | ✅ Implemented |
| Native token-level billing for A2A | ⚠️ Not native for A2A routes |

**Practical approach:** APIM products + subscriptions provide a clear first monetization layer, while advanced billing (for example, token-linked monetization) can be layered on top with custom telemetry pipelines.

---

## 🔐 Secrets and subscription keys

- `client-e2e\final_test_apim_cards.py` **does not hardcode subscription keys**.
- Keys are read from environment variables:
  - `APIM_SUBSCRIPTION_KEY_FREE`
  - `APIM_SUBSCRIPTION_KEY_PRO`
- Keep real keys only in local `.env` (gitignored).  
  `.env.example` stays sanitized for repository sharing.

---

## 📚 References

- Foundry A2A endpoint  
  https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/enable-agent-to-agent-endpoint
- Microsoft Agent Framework A2A package  
  https://github.com/microsoft/agent-framework/tree/main/python/packages/a2a
- APIM A2A API  
  https://learn.microsoft.com/en-us/azure/api-management/agent-to-agent-api
- Microsoft Learn MCP  
  https://learn.microsoft.com/en-us/training/support/mcp
