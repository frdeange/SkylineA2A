"""Local smoke test for the DevOpsHelper A2A server.

Mirrors the canonical Microsoft Agent Framework client sample
(`python/samples/04-hosting/a2a/agent_with_a2a.py`): resolves the AgentCard
from the running server, wraps it in an `A2AAgent`, sends a non-streaming
prompt and a streaming prompt, and prints what comes back.

Run `python mafagent.py` in another terminal first, then:

    python smoke_test.py

Override the target URL by setting DEMO2_PUBLIC_URL in `.env`
(defaults to http://localhost:9999/).
"""

from __future__ import annotations

import asyncio
import os

import httpx
from a2a.client import A2ACardResolver
from agent_framework.a2a import A2AAgent
from dotenv import load_dotenv

load_dotenv()


async def main() -> None:
    base_url = os.environ.get("DEMO2_PUBLIC_URL", "http://localhost:9999/").rstrip("/") + "/"
    print(f"Connecting to A2A agent at: {base_url}")

    async with httpx.AsyncClient(timeout=60.0) as http_client:
        resolver = A2ACardResolver(httpx_client=http_client, base_url=base_url)
        agent_card = await resolver.get_agent_card()
        print(f"Found agent: {agent_card.name} - {agent_card.description}")
        print(f"  Skills: {', '.join(skill.name for skill in agent_card.skills)}")

    async with A2AAgent(
        name=agent_card.name,
        description=agent_card.description,
        agent_card=agent_card,
        url=base_url,
    ) as agent:
        # Streaming is the natural model for A2A v1.0 (the canonical sample
        # uses it for tool-using turns: artifacts arrive as SSE chunks and
        # the client surfaces them as AgentResponseUpdate.contents).
        # We use streaming for both prompts here — one per tool — so this
        # smoke test exercises both Check_Deployment_Status and Restart_Service.

        async def run_streaming(prompt: str, label: str) -> None:
            print(f"\n--- {label} ---")
            print(f"> {prompt}")
            stream = agent.run(prompt, stream=True)
            async for update in stream:
                for content in update.contents:
                    text = getattr(content, "text", None)
                    if text:
                        print(f"  {text}")
            final = await stream.get_final_response()
            print(f"  (final: {len(final.messages)} message(s))")

        await run_streaming(
            "Is api-frontend healthy in prod?",
            "Check_Deployment_Status",
        )
        await run_streaming(
            "Please restart order-service in staging.",
            "Restart_Service",
        )


if __name__ == "__main__":
    asyncio.run(main())
