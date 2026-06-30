"""
LLM + tool loop for Do-It (OpenAI-compatible API), with trace rows in PostgreSQL.

Requires: ``OPENAI_API_KEY``; optional ``OPENAI_BASE_URL``, ``CHAT_MODEL``.
Call ``postgres_db.ensure_tables()`` before first use (handled in ``run_agent``).
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

import postgres_db as db
from agent_tools import TOOL_DEFINITIONS, ToolContext, execute_tool


def _openai_client() -> OpenAI:
    api_key = os.environ.get("OPENAI_API_KEY", "").strip() or None
    base_url = os.environ.get("OPENAI_BASE_URL", "").strip() or None
    kw: dict[str, Any] = {"api_key": api_key}
    if base_url:
        kw["base_url"] = base_url
    return OpenAI(**kw)


def chat_model() -> str:
    return os.environ.get("CHAT_MODEL", "").strip()


def max_tool_rounds() -> int:
    return int(os.environ.get("AGENT_MAX_TOOL_LOOPS", "").strip() or "10")


def run_agent(qdrant: QdrantClient, user_message: str) -> dict[str, Any]:
    """One user turn: ensure DB tables, log run, run tool loop, return answer + trace."""
    db.ensure_tables()
    run_id = uuid4()
    db.insert_run(run_id, user_message)
    ctx = ToolContext(qdrant=qdrant, run_id=run_id)
    client = _openai_client()
    model = chat_model()

    messages: list[dict[str, Any]] = [
        {
            "role": "system",
            "content": (
                "You are Do-It, a helpful task assistant. You manage a task list stored in Qdrant. "
                "Use tools to read or change data; do not invent task ids — take them from list_tasks "
                "or search_tasks. "
                "To remove a task you MUST call queue_task_delete (human approval required); never claim "
                "a task was deleted until the user approves it in the UI."
            ),
        },
        {"role": "user", "content": user_message},
    ]

    step_no = 0
    final_text: str | None = None

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
            assistant_payload: dict[str, Any] = {
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
            db.log_step(
                run_id,
                step_no,
                "assistant",
                payload=assistant_payload,
            )

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
                raw_args = tc.function.arguments or "{}"
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
