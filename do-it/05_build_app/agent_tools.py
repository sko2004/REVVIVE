"""
OpenAI-style tool definitions and execution for the Do-It task agent.

Deletes requested by the agent go through ``enqueue_delete_approval`` (HITL), not Qdrant delete.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from qdrant_client import QdrantClient

from postgres_db import enqueue_delete_approval
from qdrant_tasks import add_task, list_tasks, search_tasks, set_done


@dataclass
class ToolContext:
    qdrant: QdrantClient
    run_id: UUID | None


TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "list_tasks",
            "description": "List all tasks with id, title, description, done flag, and created time.",
            "parameters": {
                "type": "object",
                "properties": {
                    "include_done": {
                        "type": "boolean",
                        "description": "If false, only return tasks that are not done yet.",
                    }
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_tasks",
            "description": "Find tasks whose title or description contains a keyword (case-insensitive).",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Substring to search for, e.g. 'milk' or 'invoice'.",
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_task",
            "description": "Create a new open task.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "description": {
                        "type": "string",
                        "description": "Optional longer text.",
                    },
                },
                "required": ["title"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_task_status",
            "description": "Mark a task done (complete) or not done (reopen) using its task id from list_tasks.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "UUID of the task point."},
                    "done": {"type": "boolean", "description": "True to complete, false to reopen."},
                },
                "required": ["task_id", "done"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "queue_task_delete",
            "description": (
                "Request deletion of a task. This does NOT delete immediately: it queues a "
                "human approval (HITL). Tell the user to open the Approvals section or Tasks tab "
                "to approve or reject."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "task_id": {"type": "string"},
                    "task_title": {
                        "type": "string",
                        "description": "Short human-readable title for approvers.",
                    },
                },
                "required": ["task_id", "task_title"],
            },
        },
    },
]


def _parse_args(raw: str | dict[str, Any]) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    if not raw or not str(raw).strip():
        return {}
    return json.loads(raw)


def execute_tool(ctx: ToolContext, name: str, arguments: str | dict[str, Any]) -> dict[str, Any]:
    args = _parse_args(arguments)
    q = ctx.qdrant

    if name == "list_tasks":
        inc = args.get("include_done", True)
        tasks = list_tasks(q)
        if not inc:
            tasks = [t for t in tasks if not t.get("done")]
        return {"ok": True, "tasks": tasks, "count": len(tasks)}

    if name == "search_tasks":
        query = (args.get("query") or "").strip()
        if not query:
            return {"ok": False, "error": "query is required"}
        hits = search_tasks(q, query)
        return {"ok": True, "tasks": hits, "count": len(hits)}

    if name == "add_task":
        title = (args.get("title") or "").strip()
        desc = (args.get("description") or "").strip()
        tid = add_task(q, title, desc)
        return {"ok": True, "task_id": tid, "title": title}

    if name == "update_task_status":
        tid = (args.get("task_id") or "").strip()
        if not tid:
            return {"ok": False, "error": "task_id is required"}
        done = bool(args.get("done"))
        set_done(q, tid, done)
        return {"ok": True, "task_id": tid, "done": done}

    if name == "queue_task_delete":
        tid = (args.get("task_id") or "").strip()
        title = (args.get("task_title") or "").strip() or "(untitled)"
        if not tid:
            return {"ok": False, "error": "task_id is required"}
        pid = enqueue_delete_approval(ctx.run_id, tid, title)
        return {
            "ok": True,
            "pending_action_id": str(pid),
            "message": "Delete queued for human approval. It is not applied yet.",
            "task_id": tid,
        }

    return {"ok": False, "error": f"unknown tool: {name}"}
