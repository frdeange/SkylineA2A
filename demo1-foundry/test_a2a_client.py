from __future__ import annotations

import asyncio
import json
import os
from urllib.parse import quote

from dotenv import load_dotenv

load_dotenv()

AI_SCOPE = "https://ai.azure.com/.default"
AGENT_CARD_PATH = "agentCard/v0.3"
DEFAULT_PROMPT = (
    "What is the difference between Azure Container Apps and Azure Container Instances? "
    "Cite the Learn doc you used."
)


def section(title: str) -> None:
    print(f"\n=== {title} ===")


def compute_a2a_base_url(project_endpoint: str, agent_name: str) -> str:
    return f"{project_endpoint.rstrip('/')}/agents/{quote(agent_name, safe='')}/endpoint/protocols/a2a"


def load_config() -> dict[str, str]:
    base_url = os.environ.get("DEMO1_A2A_BASE_URL", "")
    if not base_url:
        base_url = compute_a2a_base_url(
            os.environ["FOUNDRY_PROJECT_ENDPOINT"],
            os.environ.get("DEMO1_AGENT_NAME", "ms-docs-expert"),
        )
    return {
        "a2a_base_url": base_url.rstrip("/"),
        "prompt": os.environ.get("DEMO1_TEST_PROMPT", DEFAULT_PROMPT),
    }


def import_a2a_dependencies() -> dict[str, object]:
    try:
        import httpx
        from a2a.client import A2ACardResolver, ClientConfig, create_client
        from a2a.helpers import get_stream_response_text, new_text_message
        from a2a.types.a2a_pb2 import Role, SendMessageRequest
        from azure.identity import DefaultAzureCredential
        from google.protobuf.json_format import MessageToDict
    except ImportError as exc:
        raise RuntimeError(
            "Missing or incompatible dependencies. Demo 1 requires a2a-sdk>=1.0.2, azure-identity, "
            "httpx, and protobuf. Install with: python -m pip install a2a-sdk==1.0.2 azure-identity httpx"
        ) from exc

    return {
        "httpx": httpx,
        "A2ACardResolver": A2ACardResolver,
        "ClientConfig": ClientConfig,
        "create_client": create_client,
        "get_stream_response_text": get_stream_response_text,
        "new_text_message": new_text_message,
        "Role": Role,
        "SendMessageRequest": SendMessageRequest,
        "DefaultAzureCredential": DefaultAzureCredential,
        "MessageToDict": MessageToDict,
    }


async def run_client() -> int:
    config = load_config()
    deps = import_a2a_dependencies()

    httpx = deps["httpx"]
    A2ACardResolver = deps["A2ACardResolver"]
    ClientConfig = deps["ClientConfig"]
    create_client = deps["create_client"]
    get_stream_response_text = deps["get_stream_response_text"]
    new_text_message = deps["new_text_message"]
    Role = deps["Role"]
    SendMessageRequest = deps["SendMessageRequest"]
    DefaultAzureCredential = deps["DefaultAzureCredential"]
    MessageToDict = deps["MessageToDict"]

    section("Configuration")
    print(f"A2A base URL:     {config['a2a_base_url']}")
    print(f"Agent-card path:  {AGENT_CARD_PATH}")
    print(f"Prompt:           {config['prompt']}")

    section("Authenticating")
    with DefaultAzureCredential() as credential:
        token = credential.get_token(AI_SCOPE).token
    print(f"Acquired Microsoft Entra token for scope: {AI_SCOPE}")

    headers = {"Authorization": f"Bearer {token}"}
    timeout = httpx.Timeout(120.0)
    async with httpx.AsyncClient(headers=headers, timeout=timeout) as httpx_client:
        section("Fetching agent card")
        resolver = A2ACardResolver(
            httpx_client=httpx_client,
            base_url=config["a2a_base_url"],
            agent_card_path=AGENT_CARD_PATH,
        )
        agent_card = await resolver.get_agent_card()
        print(json.dumps(MessageToDict(agent_card, preserving_proto_field_name=True), indent=2, sort_keys=True))

        section("Sending A2A message")
        client_config = ClientConfig(streaming=False, httpx_client=httpx_client)
        client = await create_client(agent=agent_card, client_config=client_config)
        try:
            message = new_text_message(config["prompt"], role=Role.ROLE_USER)
            request = SendMessageRequest(message=message)
            extracted_text: list[str] = []
            response_number = 0
            async for response in client.send_message(request):
                response_number += 1
                print(f"\n--- Stream response {response_number} ---")
                print(json.dumps(MessageToDict(response, preserving_proto_field_name=True), indent=2, sort_keys=True))
                text = get_stream_response_text(response).strip()
                if text:
                    extracted_text.append(text)
        finally:
            await client.close()

    section("Extracted response text")
    if extracted_text:
        print("\n".join(extracted_text))
    else:
        print("No text extracted. Inspect the raw stream response above.")
    return 0


def main() -> int:
    try:
        return asyncio.run(run_client())
    except Exception as exc:
        section("A2A client error")
        print(f"{type(exc).__name__}: {exc}")
        print(
            "\nCheck that enable_a2a.py completed, DEMO1_A2A_BASE_URL is correct, and the caller has "
            "Azure AI User (or higher) on the Foundry project. Foundry uses agentCard/v0.3, not "
            "/.well-known/agent-card.json."
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
