"""Final APIM test: verify both APIM A2A agent-card routes with subscription keys.

This intentionally tests APIM exposure (gateway + product subscription) before
moving to richer end-to-end JSON-RPC tests.
"""

from __future__ import annotations

import json
import os
import time
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path


def load_env(path: Path) -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


@dataclass
class CardTarget:
    label: str
    card_url: str
    runtime_url: str
    a2a_version: str


def summarize_card(payload: dict) -> list[str]:
    agent_name = payload.get("name") or payload.get("id") or "<unknown>"
    description = (payload.get("description") or "").strip()
    card_url = payload.get("url") or payload.get("agentCardUrl") or "<missing>"
    interfaces = payload.get("supportedInterfaces") or []
    interface_url = "<missing>"
    if interfaces and isinstance(interfaces, list) and isinstance(interfaces[0], dict):
        interface_url = interfaces[0].get("url") or "<missing>"

    skills = payload.get("skills") or []
    skill_names = []
    for skill in skills[:5]:
        if isinstance(skill, dict):
            name = (skill.get("name") or skill.get("id") or "").strip()
            if name:
                skill_names.append(name)
    security = payload.get("securitySchemes") or {}
    security_names = ", ".join(security.keys()) if isinstance(security, dict) and security else "none"

    lines = [
        f"    Agent: {agent_name}",
        f"    Card URL: {card_url}",
        f"    Runtime URL: {interface_url}",
        f"    Skills ({len(skills)}): {', '.join(skill_names) if skill_names else 'none'}",
        f"    Security schemes: {security_names}",
    ]
    if description:
        lines.insert(1, f"    Description: {description}")
    return lines


def fetch_json(url: str, subscription_key: str) -> tuple[int, dict]:
    req = urllib.request.Request(
        url=url,
        headers={
            "Accept": "application/json",
            "Ocp-Apim-Subscription-Key": subscription_key,
        },
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=45) as resp:
        body = resp.read().decode("utf-8")
        return resp.status, json.loads(body)


def post_json(url: str, headers: dict[str, str], payload: dict) -> tuple[int, dict]:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url=url,
        headers=headers,
        data=body,
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            text = resp.read().decode("utf-8", errors="replace")
            return resp.status, json.loads(text)
    except urllib.error.HTTPError as exc:
        text = exc.read().decode("utf-8", errors="replace")
        try:
            return exc.code, json.loads(text)
        except Exception:  # noqa: BLE001
            return exc.code, {"raw": text}


def extract_demo1_answer(task_result: dict) -> str:
    artifacts = task_result.get("artifacts") or []
    texts: list[str] = []
    for art in artifacts:
        for part in art.get("parts", []):
            text = (part.get("text") or "").strip()
            if text:
                texts.append(text)
    return "\n".join(texts).strip()


def extract_demo2_answer(send_result: dict) -> str:
    task = send_result.get("task") or {}
    history = task.get("history") or []
    # Prefer the latest ROLE_AGENT message text.
    for msg in reversed(history):
        if msg.get("role") == "ROLE_AGENT":
            texts = [
                (part.get("text") or "").strip()
                for part in (msg.get("parts") or [])
                if (part.get("text") or "").strip()
            ]
            if texts:
                return "\n".join(texts).strip()
    return ""


def runtime_call_demo1(base_url: str, subscription_key: str) -> tuple[bool, str]:
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "A2A-Version": "0.3",
        "Ocp-Apim-Subscription-Key": subscription_key,
    }
    send_payload = {
        "jsonrpc": "2.0",
        "id": "rt-send",
        "method": "message/send",
        "params": {
            "message": {
                "kind": "message",
                "messageId": "rt-msg-1",
                "role": "user",
                "parts": [{"kind": "text", "text": "Explain Azure API Management in one sentence."}],
            }
        },
    }
    status, send_resp = post_json(base_url, headers, send_payload)
    if status != 200 or "result" not in send_resp:
        return False, f"send failed (status={status}): {json.dumps(send_resp)[:300]}"

    task_id = (((send_resp.get("result") or {}).get("id")) or "").strip()
    if not task_id:
        return False, f"send returned no task id: {json.dumps(send_resp)[:300]}"

    get_payload = {"jsonrpc": "2.0", "id": "rt-get", "method": "tasks/get", "params": {"id": task_id}}
    for _ in range(12):
        time.sleep(1.5)
        g_status, get_resp = post_json(base_url, headers, get_payload)
        if g_status != 200 or "result" not in get_resp:
            continue
        result = get_resp.get("result") or {}
        state = (((result.get("status") or {}).get("state")) or "").lower()
        if state == "completed":
            answer = extract_demo1_answer(result)
            if answer:
                return True, answer
            return False, "task completed but no text artifacts returned"
    return False, "task polling timed out before completion"


def runtime_call_demo2(base_url: str, subscription_key: str) -> tuple[bool, str]:
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "A2A-Version": "1.0",
        "Ocp-Apim-Subscription-Key": subscription_key,
    }
    send_payload = {
        "jsonrpc": "2.0",
        "id": "rt-send",
        "method": "SendMessage",
        "params": {
            "message": {
                "message_id": "rt-msg-1",
                "role": "ROLE_USER",
                "parts": [{"text": "Is api-frontend healthy in prod?"}],
            }
        },
    }
    status, send_resp = post_json(base_url, headers, send_payload)
    if status != 200 or "result" not in send_resp:
        return False, f"send failed (status={status}): {json.dumps(send_resp)[:300]}"

    answer = extract_demo2_answer(send_resp.get("result") or {})
    if answer:
        return True, answer
    return False, f"no agent answer in response: {json.dumps(send_resp)[:300]}"


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    load_env(repo_root / ".env")

    free_key = os.environ.get("APIM_SUBSCRIPTION_KEY_FREE", "").strip()
    pro_key = os.environ.get("APIM_SUBSCRIPTION_KEY_PRO", "").strip()

    demo1_card = os.environ.get("APIM_DEMO1_AGENT_CARD_URL", "").strip()
    demo2_card = os.environ.get("APIM_DEMO2_AGENT_CARD_URL", "").strip()
    demo1_base = os.environ.get("APIM_DEMO1_BASE_URL", "").strip()
    demo2_base = os.environ.get("APIM_DEMO2_BASE_URL", "").strip()

    if not free_key or not pro_key:
        print("Missing APIM_SUBSCRIPTION_KEY_FREE / APIM_SUBSCRIPTION_KEY_PRO in .env")
        return 2
    if not demo1_card or not demo2_card or not demo1_base or not demo2_base:
        print(
            "Missing APIM_DEMO{1,2}_AGENT_CARD_URL / APIM_DEMO{1,2}_BASE_URL in .env"
        )
        return 2

    targets = [
        CardTarget("demo1", demo1_card, demo1_base, "0.3"),
        CardTarget("demo2", demo2_card, demo2_base, "1.0"),
    ]
    keys = [("FREE", free_key), ("PRO", pro_key)]

    failures = 0
    for target in targets:
        print(f"\n=== {target.label} card ===")
        print(target.card_url)
        baseline_payload: dict | None = None
        for key_label, key in keys:
            try:
                status, payload = fetch_json(target.card_url, key)
                agent_id = payload.get("name") or payload.get("id") or "<unknown>"
                print(f"  [{key_label}] {status} OK -> agent: {agent_id}")
                if baseline_payload is None:
                    baseline_payload = payload
                    for line in summarize_card(payload):
                        print(line)
                else:
                    if payload != baseline_payload:
                        print("    WARNING: FREE/PRO card payload differs.")
            except urllib.error.HTTPError as exc:
                body = exc.read().decode("utf-8", errors="replace")
                print(f"  [{key_label}] HTTP {exc.code} ERROR")
                print(f"    {body[:300]}")
                failures += 1
            except Exception as exc:  # noqa: BLE001
                print(f"  [{key_label}] ERROR: {exc}")
                failures += 1

        print(f"\n=== {target.label} runtime call ===")
        print(target.runtime_url)
        for key_label, key in keys:
            if target.label == "demo1":
                ok, detail = runtime_call_demo1(target.runtime_url, key)
            else:
                ok, detail = runtime_call_demo2(target.runtime_url, key)
            preview = " ".join(detail.split())[:260]
            if ok:
                print(f"  [{key_label}] runtime OK")
                print(f"    Answer: {preview}")
            else:
                print(f"  [{key_label}] runtime FAILED")
                print(f"    Detail: {preview}")
                failures += 1

    if failures:
        print(f"\nFinal result: FAIL ({failures} failing checks)")
        return 1

    print(
        "\nFinal result: PASS (agent-card + runtime probes succeeded for both keys)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
