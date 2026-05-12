from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Any

from dotenv import load_dotenv

load_dotenv()


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


def main() -> int:
    project_endpoint = os.environ["FOUNDRY_PROJECT_ENDPOINT"]
    agent_name = os.environ.get("DEMO1_AGENT_NAME", "ms-docs-expert")

    try:
        from azure.ai.projects import AIProjectClient
        from azure.core.exceptions import HttpResponseError, ResourceNotFoundError
        from azure.identity import DefaultAzureCredential
    except ImportError as exc:
        raise RuntimeError(
            "Missing dependencies. Install with: python -m pip install --pre -r requirements.txt"
        ) from exc

    section("Configuration")
    print(f"Foundry project endpoint: {project_endpoint}")
    print(f"Agent name:              {agent_name}")

    try:
        with (
            DefaultAzureCredential() as credential,
            AIProjectClient(endpoint=project_endpoint, credential=credential, allow_preview=True) as project_client,
        ):
            section("Looking up agent")
            try:
                agent = project_client.agents.get(agent_name)
            except ResourceNotFoundError:
                print(f"Agent '{agent_name}' does not exist. Nothing to delete.")
                return 0
            except HttpResponseError as exc:
                if is_not_found_error(exc):
                    print(f"Agent '{agent_name}' does not exist. Nothing to delete.")
                    return 0
                raise

            print(f"Deleting agent ID: {value_from(agent, 'id', '(unknown)')}")
            project_client.agents.delete(agent_name)
            section("Result")
            print(f"Deleted agent '{agent_name}'.")
            return 0
    except HttpResponseError as exc:
        section("Foundry error")
        print(f"Status:  {getattr(exc, 'status_code', '(unknown)')}")
        print(f"Message: {getattr(exc, 'message', str(exc))}")
        return 1
    except Exception as exc:
        section("Unexpected error")
        print(f"{type(exc).__name__}: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
