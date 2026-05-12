"""DevOps Helper A2A server (Microsoft Agent Framework).

Adapted from the canonical Microsoft Agent Framework sample:
https://github.com/microsoft/agent-framework/blob/main/python/samples/04-hosting/a2a/agent_framework_to_a2a.py

Differences vs. the sample:
  * DevOpsHelper agent with three deterministic, simulated DevOps tools
    (check_deployment_status, restart_service, get_resource_health) instead of
    the Europe Travel Agent skills.
  * Model served by a Foundry-hosted gpt-5.2 deployment via FoundryChatClient
    (same FOUNDRY_PROJECT_ENDPOINT used by Demo 1) instead of OpenAIChatClient.
  * Host / port / public URL configurable via .env so the same script runs both
    locally and inside the ACA container behind API Management.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from typing import Any

import uvicorn
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import create_agent_card_routes, create_jsonrpc_routes
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentInterface, AgentSkill
from agent_framework import Agent
from agent_framework.a2a import A2AExecutor
from agent_framework.foundry import FoundryChatClient
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv
from starlette.applications import Starlette

load_dotenv()

# ─────────────────────────────────────────────────────────────────────────────
# Simulated DevOps tools (deterministic, in-memory; no external calls).
# ─────────────────────────────────────────────────────────────────────────────

_BASE_TIME = datetime(2026, 1, 15, 9, 0, tzinfo=UTC)

_DEPLOYMENT_STATUS: dict[tuple[str, str], dict[str, str]] = {
    ("api-frontend", "dev"): {
        "status": "healthy",
        "last_deployed_at": "2026-01-15T08:45:00Z",
        "version": "2026.01.15-dev.4",
        "notes": "Latest feature branch deployed successfully.",
    },
    ("api-frontend", "staging"): {
        "status": "degraded",
        "last_deployed_at": "2026-01-14T17:10:00Z",
        "version": "2026.01.14-rc.2",
        "notes": "Elevated latency on checkout API dependency.",
    },
    ("api-frontend", "prod"): {
        "status": "healthy",
        "last_deployed_at": "2026-01-12T22:05:00Z",
        "version": "2026.01.12.3",
        "notes": "All probes green across primary and secondary regions.",
    },
    ("order-service", "dev"): {
        "status": "healthy",
        "last_deployed_at": "2026-01-15T07:30:00Z",
        "version": "2026.01.15-dev.1",
        "notes": "Smoke tests completed.",
    },
    ("order-service", "staging"): {
        "status": "failed",
        "last_deployed_at": "2026-01-14T16:20:00Z",
        "version": "2026.01.14-rc.5",
        "notes": "Deployment rollback triggered after migration validation failed.",
    },
    ("order-service", "prod"): {
        "status": "degraded",
        "last_deployed_at": "2026-01-10T21:40:00Z",
        "version": "2026.01.10.1",
        "notes": "Queue depth is above baseline but within SLO burn-rate guardrails.",
    },
}

_KNOWN_SERVICES = {service for service, _ in _DEPLOYMENT_STATUS}

_RESOURCE_HEALTH: dict[str, dict[str, str]] = {
    "/subscriptions/demo/resourcegroups/rg-fe/providers/microsoft.web/sites/api-fe": {
        "availability_state": "Available",
        "summary": "App Service is serving traffic normally in West Europe.",
        "reason_type": "PlatformInitiated",
        "reported_time": "2026-01-15T08:55:00Z",
    },
    "/subscriptions/demo/resourcegroups/rg-orders/providers/microsoft.web/sites/order-api": {
        "availability_state": "Degraded",
        "summary": "Intermittent HTTP 503s observed during scale-out warmup.",
        "reason_type": "UserInitiated",
        "reported_time": "2026-01-15T08:50:00Z",
    },
    "/subscriptions/demo/resourcegroups/rg-core/providers/microsoft.compute/virtualmachines/build-agent-01": {
        "availability_state": "Unavailable",
        "summary": "The VM is stopped and not reporting guest heartbeat signals.",
        "reason_type": "UserInitiated",
        "reported_time": "2026-01-15T08:40:00Z",
    },
}


def _normalize(value: str) -> str:
    return value.strip().lower()


def _deterministic_timestamp(*parts: str, offset_minutes: int = 0) -> str:
    joined = "|".join(_normalize(part) for part in parts)
    digest = sha256(joined.encode("utf-8")).hexdigest()
    minutes = int(digest[:8], 16) % (14 * 24 * 60)
    timestamp = _BASE_TIME + timedelta(minutes=minutes + offset_minutes)
    return timestamp.isoformat(timespec="seconds").replace("+00:00", "Z")


def check_deployment_status(service_name: str, environment: str) -> dict[str, Any]:
    """Return simulated deployment health, version, and notes for a service in an environment."""
    service = _normalize(service_name)
    env = _normalize(environment)
    status = _DEPLOYMENT_STATUS.get((service, env))
    if status is None:
        return {
            "service": service_name,
            "environment": environment,
            "status": "unknown",
            "last_deployed_at": None,
            "version": "unknown",
            "notes": "No simulated deployment record exists for this service/environment combination.",
        }
    return {"service": service_name, "environment": environment, **status}


def restart_service(service_name: str, environment: str) -> dict[str, Any]:
    """Simulate restarting a service and return a deterministic operation result."""
    service = _normalize(service_name)
    env = _normalize(environment)
    started_at = _deterministic_timestamp(service_name, environment, "restart")
    estimated_completion = _deterministic_timestamp(
        service_name, environment, "restart", offset_minutes=8
    )
    response: dict[str, Any] = {
        "service": service_name,
        "environment": environment,
        "action": "restart",
        "result": "ok",
        "started_at": started_at,
        "estimated_completion": estimated_completion,
    }
    if env == "prod" and service not in _KNOWN_SERVICES:
        response.update(
            {
                "result": "failed",
                "error_message": "Refusing simulated prod restart for an unknown service.",
            }
        )
    return response


def get_resource_health(resource_id: str) -> dict[str, str]:
    """Return simulated Azure Resource Health availability data for a resource ID."""
    resource_key = _normalize(resource_id)
    health = _RESOURCE_HEALTH.get(
        resource_key,
        {
            "availability_state": "Available",
            "summary": "No simulated incident is associated with this resource.",
            "reason_type": "PlatformInitiated",
            "reported_time": _deterministic_timestamp(resource_id, "health"),
        },
    )
    return {"resource_id": resource_id, **health}


# ─────────────────────────────────────────────────────────────────────────────
# Agent + A2A server (mirrors the canonical sample's __main__ flow).
# ─────────────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """\
You are DevOpsHelper, a concise DevOps assistant exposed over A2A.
Use the available tools whenever the user asks about deployment status, service restarts,
or Azure resource health.
When a requested action affects prod, clearly state that this is a simulated production
action and briefly confirm the user's intent in your response. Keep answers structured,
direct, and focused on operational next steps.
"""


if __name__ == "__main__":
    public_url = os.environ.get("DEMO2_PUBLIC_URL", "http://localhost:9999/").rstrip("/") + "/"
    host = os.environ.get("DEMO2_HOST", "0.0.0.0")
    port = int(os.environ.get("DEMO2_PORT", "9999"))

    agent_name = os.environ.get("DEMO2_AGENT_NAME", "MAFAgent-DevOpsHelper")
    agent_description = os.environ.get(
        "DEMO2_AGENT_DESCRIPTION",
        "DevOps helper exposed as an A2A endpoint by the Microsoft Agent Framework.",
    )
    agent_version = os.environ.get("DEMO2_AGENT_VERSION", "1.0.0")

    public_agent_card = AgentCard(
        name=agent_name,
        description=agent_description,
        version=agent_version,
        default_input_modes=["text"],
        default_output_modes=["text"],
        capabilities=AgentCapabilities(streaming=True),
        supported_interfaces=[AgentInterface(url=public_url, protocol_binding="JSONRPC")],
        skills=[
            AgentSkill(
                id="Check_Deployment_Status",
                name="Check Deployment Status",
                description="Report the status of a service deployment in a given environment.",
                tags=["devops", "deployments", "status"],
                examples=["Is api-frontend healthy in prod?"],
            ),
            AgentSkill(
                id="Restart_Service",
                name="Restart Service",
                description="Simulate restarting a service in a target environment.",
                tags=["devops", "restart", "remediation"],
                examples=["Please restart order-service in staging."],
            ),
            AgentSkill(
                id="Get_Resource_Health",
                name="Get Azure Resource Health",
                description="Report Azure Resource Health for an ARM resource ID.",
                tags=["devops", "azure", "resource-health"],
                examples=[
                    "What's the Azure resource health of "
                    "/subscriptions/demo/resourceGroups/rg-fe/providers/Microsoft.Web/sites/api-fe?"
                ],
            ),
        ],
    )

    agent = Agent(
        client=FoundryChatClient(
            project_endpoint=os.environ["FOUNDRY_PROJECT_ENDPOINT"],
            model=os.environ["FOUNDRY_DEPLOYMENT_NAME"],
            credential=DefaultAzureCredential(),
        ),
        name=agent_name,
        instructions=SYSTEM_PROMPT,
        tools=[check_deployment_status, restart_service, get_resource_health],
    )

    request_handler = DefaultRequestHandler(
        agent_executor=A2AExecutor(agent),
        task_store=InMemoryTaskStore(),
        agent_card=public_agent_card,
    )

    server = Starlette(
        routes=[
            *create_agent_card_routes(public_agent_card),
            *create_jsonrpc_routes(request_handler, rpc_url="/"),
        ]
    )

    print("Starting DevOpsHelper A2A server")
    print(f"  Public URL : {public_url}")
    print(f"  Agent card : {public_url}.well-known/agent-card.json")
    print(f"  JSON-RPC   : {public_url}  (POST)")
    print()

    uvicorn.run(server, host=host, port=port)
