"""
Revive agent orchestration using Vayu Model as a Service.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from dotenv import load_dotenv
from openai import OpenAI
from qdrant_client import QdrantClient

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

import revive_postgres as db
from revive_tools import ToolContext, TOOL_DEFINITIONS


def _openai_client() -> OpenAI | None:
    api_key = os.environ.get("OPENAI_API_KEY", "").strip() or None
    base_url = os.environ.get("OPENAI_BASE_URL", "").strip() or None
    if api_key is None:
        return None
    kw: dict[str, Any] = {"api_key": api_key}
    if base_url:
        kw["base_url"] = base_url
    return OpenAI(**kw)


def chat_model() -> str:
    return os.environ.get("CHAT_MODEL", "").strip() or "gpt-4o-mini"


def max_tool_rounds() -> int:
    return int(os.environ.get("AGENT_MAX_TOOL_LOOPS", "").strip() or "10")


def _intent_for_tool(tool_name: str) -> str | None:
    mapping = {
        "estimate_range": "RANGE",
        "find_chargers_on_route": "RANGE",
        "triage_issue": "BREAKDOWN",
        "safety_check": "SAFETY",
        "search_providers": "PROVIDER_SEARCH",
        "get_provider_details": "PROVIDER_DETAIL",
        "estimate_fair_price": "PRICING",
        "queue_booking": "BOOKING",
    }
    return mapping.get(tool_name)


def run_agent(qdrant: QdrantClient, user_message: str, vehicle_context: dict[str, Any] | None = None) -> dict[str, Any]:
    db.ensure_tables()
    run_id = uuid4()
    db.insert_run(run_id, user_message)
    ctx = ToolContext(qdrant=qdrant, run_id=run_id, vehicle_context=vehicle_context)
    client = _openai_client()
    model = chat_model()

    context_lines = []
    if vehicle_context:
        for key, value in vehicle_context.items():
            context_lines.append(f"{key}: {value}")
    messages: list[dict[str, Any]] = [
        {
            "role": "system",
            "content": (
                "You are Revvive, an electric vehicle assistant for Indian EV owners. "
                "Handle range confidence and repair booking workflows. "
                "If the user asks about range or whether they can reach a destination, use estimate_range. "
                "If estimate_range returns Tight or Not Advisable, call find_chargers_on_route to recommend reachable charging stops. "
                "Use the tools to compute route energy, classify faults, search suitable providers, estimate pricing, "
                "and queue bookings for human approval. "
                "Do not invent provider IDs or booking IDs. "
                "If a booking is required, call queue_booking and do not state that the booking is confirmed until it is approved. "
                "If the user describes an unsafe condition or safety_check returns is_safe=false, escalate urgency, warn the user clearly, "
                "and ensure any provider search call uses urgency=urgent so emergency-capable providers are returned."
            ),
        }
    ]
    if context_lines:
        messages.append({"role": "system", "content": "Vehicle context:\n" + "\n".join(context_lines)})
    messages.append({"role": "user", "content": user_message})

    step_no = 0
    final_text: str | None = None

    if client is None:
        err = "OPENAI_API_KEY is not configured."
        db.finish_run(run_id, assistant_final=None, status="error", error_message=err)
        return {"ok": False, "run_id": str(run_id), "answer": "", "error": err, "trace": []}

    if not os.environ.get("OPENAI_BASE_URL", "").strip():
        err = "OPENAI_BASE_URL is not configured."
        db.finish_run(run_id, assistant_final=None, status="error", error_message=err)
        return {"ok": False, "run_id": str(run_id), "answer": "", "error": err, "trace": []}

    try:
        for _ in range(max_tool_rounds()):
            step_no += 1
            completion = client.chat.completions.create(
                model=model,
                messages=messages,
                tools=TOOL_DEFINITIONS,
                tool_choice="auto",
                temperature=0.2,
            )
            msg = completion.choices[0].message
            assistant_payload = {
                "content": msg.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    }
                    for tc in (msg.tool_calls or [])
                ],
            }
            db.log_step(run_id, step_no, "assistant", payload=assistant_payload)

            if not msg.tool_calls:
                final_text = msg.content or ""
                break

            messages.append(
                {
                    "role": "assistant",
                    "content": msg.content,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                        }
                        for tc in msg.tool_calls
                    ],
                }
            )

            for tc in msg.tool_calls:
                step_no += 1
                name = tc.function.name
                if step_no == 2:
                    intent_type = _intent_for_tool(name)
                    if intent_type:
                        db.update_run_intent(run_id, intent_type)
                raw_args = tc.function.arguments or "{}"
                from revive_tools import execute_tool

                result = execute_tool(ctx, name, raw_args)
                db.log_step(
                    run_id,
                    step_no,
                    "tool_result",
                    tool_name=name,
                    tool_call_id=tc.id,
                    payload={"arguments": raw_args, "result": result},
                )
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": json.dumps(result, default=str),
                    }
                )
        else:
            raise RuntimeError("Agent stopped: max tool loop iterations reached")

        db.finish_run(run_id, assistant_final=final_text, status="completed")
        trace = db.fetch_trace(run_id)
        return {"ok": True, "run_id": str(run_id), "answer": final_text or "", "trace": trace}

    except Exception as e:
        err = str(e)
        db.finish_run(run_id, assistant_final=None, status="error", error_message=err)
        trace = db.fetch_trace(run_id)
        return {"ok": False, "run_id": str(run_id), "answer": "", "error": err, "trace": trace}
