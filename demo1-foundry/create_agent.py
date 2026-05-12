from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Any

from dotenv import load_dotenv

load_dotenv()

SYSTEM_PROMPT = """
You are Microsoft Docs Expert, a documentation specialist for Microsoft technologies.

Use the Microsoft Learn MCP server as your primary source for Microsoft-product-specific answers. Prefer
Microsoft Learn MCP results over training data whenever the user asks about Azure, Microsoft Foundry,
Microsoft 365, .NET, Microsoft developer tooling, or any other Microsoft product or service.

Always cite the Microsoft Learn page URL(s) you used. If the MCP server does not return a relevant Learn
page, say that you could not find an authoritative Learn source and clearly separate any general reasoning
from documented facts. Keep answers practical and concise unless the user asks for deep detail.
""".strip()


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
        "project_endpoint": os.environ["FOUNDRY_PROJECT_ENDPOINT"],
        "deployment_name": os.environ.get("FOUNDRY_DEPLOYMENT_NAME", "gpt-5.2"),
        "agent_name": os.environ.get("DEMO1_AGENT_NAME", "ms-docs-expert"),
        "agent_description": os.environ.get(
            "DEMO1_AGENT_DESCRIPTION",
            "Microsoft documentation expert grounded in Microsoft Learn via MCP.",
        ),
        "agent_version": os.environ.get("DEMO1_AGENT_VERSION", "1.0.0"),
        "mcp_learn_endpoint": os.environ.get("MCP_LEARN_ENDPOINT", "https://learn.microsoft.com/api/mcp"),
    }


def main() -> int:
    config = load_config()

    try:
        from azure.ai.projects import AIProjectClient
        from azure.ai.projects.models import MCPTool, PromptAgentDefinition
        from azure.core.exceptions import HttpResponseError, ResourceNotFoundError
        from azure.identity import DefaultAzureCredential
    except ImportError as exc:
        raise RuntimeError(
            "Missing dependencies. Install with: python -m pip install --pre -r requirements.txt"
        ) from exc

    section("Configuration")
    print(f"Foundry project endpoint: {config['project_endpoint']}")
    print(f"Model deployment:        {config['deployment_name']}")
    print(f"Agent name:              {config['agent_name']}")
    print(f"Agent version label:     {config['agent_version']}")
    print(f"Microsoft Learn MCP:     {config['mcp_learn_endpoint']}")

    section("Connecting to Foundry")
    try:
        with (
            DefaultAzureCredential() as credential,
            AIProjectClient(
                endpoint=config["project_endpoint"],
                credential=credential,
                allow_preview=True,
            ) as project_client,
        ):
            section("Checking for existing agent")
            try:
                existing_agent = project_client.agents.get(config["agent_name"])
                print("Existing agent found; creating a new prompt-agent version with the latest definition.")
                print(f"Existing agent ID: {value_from(existing_agent, 'id', '(unknown)')}")
            except ResourceNotFoundError:
                print("No existing agent found; creating the first version.")
            except HttpResponseError as exc:
                if is_not_found_error(exc):
                    print("No existing agent found; creating the first version.")
                else:
                    raise

            section("Creating/updating prompt agent")
            mcp_tool = MCPTool(
                server_label="microsoft-learn",
                server_url=config["mcp_learn_endpoint"],
                server_description="Public Microsoft Learn MCP server for official Microsoft documentation.",
                require_approval="never",
            )
            definition = PromptAgentDefinition(
                model=config["deployment_name"],
                instructions=SYSTEM_PROMPT,
                tools=[mcp_tool],
            )
            agent_version = project_client.agents.create_version(
                agent_name=config["agent_name"],
                definition=definition,
                description=config["agent_description"],
                metadata={
                    "demo": "demo1-foundry",
                    "version": config["agent_version"],
                    "mcp_server": "microsoft-learn",
                },
            )

            section("Result")
            print("Prompt agent is ready.")
            print(f"Agent ID:       {value_from(agent_version, 'id', '(unknown)')}")
            print(f"Agent name:     {value_from(agent_version, 'name', config['agent_name'])}")
            print(f"Agent version:  {value_from(agent_version, 'version', '(unknown)')}")
            print("\nNext step: python enable_a2a.py")
            return 0
    except HttpResponseError as exc:
        section("Foundry error")
        print(f"Status:  {getattr(exc, 'status_code', '(unknown)')}")
        print(f"Message: {getattr(exc, 'message', str(exc))}")
        print(
            "\nCheck that your account has Azure AI User (or higher) on the Foundry project, "
            "the model deployment name exists, and the project endpoint is correct."
        )
        return 1
    except Exception as exc:
        section("Unexpected error")
        print(f"{type(exc).__name__}: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
