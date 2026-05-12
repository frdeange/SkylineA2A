from __future__ import annotations

import inspect
import json
import os
from collections.abc import Mapping
from typing import Any
from urllib.parse import quote

from dotenv import load_dotenv

load_dotenv()

AI_SCOPE = "https://ai.azure.com/.default"


def section(title: str) -> None:
    print(f"\n=== {title} ===")


def value_from(obj: Any, name: str, default: str = "") -> Any:
    if hasattr(obj, name):
        return getattr(obj, name)
    if isinstance(obj, Mapping):
        return obj.get(name, default)
    return default


def is_not_found_error(exc: BaseException) -> bool:
    return getattr(exc, "status_code", None) == 404


def load_config() -> dict[str, str]:
    return {
        "project_endpoint": os.environ["FOUNDRY_PROJECT_ENDPOINT"].rstrip("/"),
        "agent_name": os.environ.get("DEMO1_AGENT_NAME", "ms-docs-expert"),
        "agent_description": os.environ.get(
            "DEMO1_AGENT_DESCRIPTION",
            "Microsoft documentation expert grounded in Microsoft Learn via MCP.",
        ),
        "agent_version": os.environ.get("DEMO1_AGENT_VERSION", "1.0.0"),
    }


def a2a_base_url(project_endpoint: str, agent_name: str) -> str:
    return f"{project_endpoint}/agents/{quote(agent_name, safe='')}/endpoint/protocols/a2a"


def card_payload(config: dict[str, str]) -> dict[str, Any]:
    return {
        "agent_card": {
            "description": config["agent_description"],
            "version": config["agent_version"],
            "skills": [
                {
                    "id": "microsoft-docs-search",
                    "name": "Microsoft Docs Search",
                    "description": "Finds and cites official Microsoft Learn documentation using the Learn MCP server.",
                    "tags": ["microsoft-learn", "documentation", "mcp"],
                    "examples": [
                        "Find the Learn page for Azure Container Apps scaling.",
                        "Cite the Microsoft Learn article for Foundry Agent Service A2A endpoints.",
                    ],
                },
                {
                    "id": "azure-product-explainer",
                    "name": "Azure Product Explainer",
                    "description": "Explains Azure service differences and implementation guidance grounded in Learn docs.",
                    "tags": ["azure", "architecture", "product-comparison"],
                    "examples": [
                        "Compare Azure Container Apps and Azure Container Instances with citations.",
                    ],
                },
            ],
        },
        "agent_endpoint": {"protocols": ["responses", "a2a"]},
    }


def patch_with_rest(project_endpoint: str, agent_name: str, credential: Any, payload: dict[str, Any]) -> dict[str, Any]:
    try:
        import httpx
    except ImportError as exc:
        raise RuntimeError("REST fallback requires httpx. Install with: python -m pip install httpx") from exc

    token = credential.get_token(AI_SCOPE).token
    url = f"{project_endpoint}/agents/{quote(agent_name, safe='')}?api-version=v1"
    response = httpx.patch(
        url,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json=payload,
        timeout=60.0,
    )
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        body = exc.response.text[:2000]
        raise RuntimeError(f"REST PATCH failed with HTTP {exc.response.status_code}: {body}") from exc
    return response.json()


def main() -> int:
    config = load_config()
    payload = card_payload(config)
    base_url = a2a_base_url(config["project_endpoint"], config["agent_name"])
    card_url = f"{base_url}/agentCard/v0.3"

    try:
        from azure.ai.projects import AIProjectClient
        from azure.ai.projects.models import AgentEndpoint, AgentEndpointProtocol
        from azure.core.exceptions import HttpResponseError, ResourceNotFoundError
        from azure.identity import DefaultAzureCredential
    except ImportError as exc:
        raise RuntimeError(
            "Missing dependencies. Install with: python -m pip install --pre -r requirements.txt"
        ) from exc

    try:
        from azure.ai.projects.models import AgentCard, AgentCardSkill
    except ImportError:
        AgentCard = None
        AgentCardSkill = None

    section("Configuration")
    print(f"Foundry project endpoint: {config['project_endpoint']}")
    print(f"Agent name:              {config['agent_name']}")
    print(f"Agent-card version:      {config['agent_version']}")

    try:
        with (
            DefaultAzureCredential() as credential,
            AIProjectClient(
                endpoint=config["project_endpoint"],
                credential=credential,
                allow_preview=True,
            ) as project_client,
        ):
            section("Reading agent")
            try:
                agent = project_client.agents.get(config["agent_name"])
            except ResourceNotFoundError:
                print("Agent not found. Run python create_agent.py first.")
                return 1
            except HttpResponseError as exc:
                if is_not_found_error(exc):
                    print("Agent not found. Run python create_agent.py first.")
                    return 1
                raise
            print(f"Agent ID:   {value_from(agent, 'id', '(unknown)')}")
            print(f"Agent name: {value_from(agent, 'name', config['agent_name'])}")

            section("Enabling A2A")
            patch_method = project_client.beta.agents.patch_agent_details
            patch_signature = inspect.signature(patch_method)
            if "agent_card" in patch_signature.parameters and AgentCard and AgentCardSkill:
                print("Using azure-ai-projects SDK beta.agents.patch_agent_details with AgentCard support.")
                agent_card = AgentCard(
                    version=config["agent_version"],
                    description=config["agent_description"],
                    skills=[AgentCardSkill(**skill) for skill in payload["agent_card"]["skills"]],
                )
                endpoint_config = AgentEndpoint(
                    protocols=[AgentEndpointProtocol.RESPONSES, AgentEndpointProtocol.A2A]
                )
                patched = patch_method(
                    agent_name=config["agent_name"],
                    agent_endpoint=endpoint_config,
                    agent_card=agent_card,
                )
                print(f"Patched agent ID: {value_from(patched, 'id', '(unknown)')}")
            else:
                print("Installed SDK cannot set AgentCard; falling back to REST PATCH.")
                patched_json = patch_with_rest(
                    config["project_endpoint"], config["agent_name"], credential, payload
                )
                print(json.dumps(patched_json, indent=2, sort_keys=True))

            section("Resulting A2A URLs")
            print(f"A2A base URL:     {base_url}")
            print(f"Agent-card URL:   {card_url}")

            section("Suggested .env lines")
            print(f'DEMO1_A2A_BASE_URL="{base_url}"')
            print(f'DEMO1_AGENT_CARD_URL="{card_url}"')
            print("\nNext step: python test_a2a_client.py")
            return 0
    except HttpResponseError as exc:
        section("Foundry error")
        print(f"Status:  {getattr(exc, 'status_code', '(unknown)')}")
        print(f"Message: {getattr(exc, 'message', str(exc))}")
        print("\nCheck Azure AI User (or higher) on the Foundry project and that A2A preview is enabled.")
        return 1
    except Exception as exc:
        section("Unexpected error")
        print(f"{type(exc).__name__}: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
