"""
Qdrant-backed task store (payload + scroll; no embeddings in this starter).

Each task is a point with a placeholder vector and payload:
title, description, done, created.
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointIdsList, PointStruct, VectorParams

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

DUMMY_VECTOR: list[float] = [0.0]
VECTOR_SIZE = 1


def _new_client() -> QdrantClient:
    path = os.environ.get("QDRANT_PATH", "").strip()
    if path:
        return QdrantClient(path=path)
    url = os.environ.get("QDRANT_URL", "").strip()
    api_key = os.environ.get("QDRANT_API_KEY", "").strip() or None
    if not url:
        raise ValueError(
            "Set QDRANT_URL and QDRANT_API_KEY in do-it/.env (hosted), "
            "or QDRANT_PATH (local folder) for Qdrant."
        )
    port = int(os.environ.get("QDRANT_PORT", "").strip() or "443")
    return QdrantClient(url=url, api_key=api_key, port=port, check_compatibility=False)


def collection_name() -> str:
    return os.environ.get("COLLECTION_NAME", "").strip() or "do_it_tasks"


def ensure_collection(client: QdrantClient | None = None) -> QdrantClient:
    c = client or _new_client()
    name = collection_name()
    existing = {x.name for x in c.get_collections().collections}
    if name not in existing:
        c.create_collection(
            collection_name=name,
            vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
        )
    return c


def _point_to_task(pid: str | int, payload: dict[str, Any] | None) -> dict[str, Any]:
    p = payload or {}
    return {
        "id": str(pid),
        "title": p.get("title", ""),
        "description": p.get("description", ""),
        "done": bool(p.get("done", False)),
        "created": p.get("created", ""),
    }


def list_tasks(client: QdrantClient, page_size: int = 256) -> list[dict[str, Any]]:
    name = collection_name()
    out: list[dict[str, Any]] = []
    offset = None
    while True:
        records, offset = client.scroll(
            collection_name=name,
            limit=page_size,
            offset=offset,
            with_payload=True,
            with_vectors=False,
        )
        for r in records:
            out.append(_point_to_task(r.id, r.payload))
        if offset is None:
            break
    out.sort(key=lambda t: t.get("created") or "", reverse=True)
    return out


def add_task(client: QdrantClient, title: str, description: str = "") -> str:
    title = (title or "").strip()
    if not title:
        raise ValueError("Title is required.")
    pid = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    client.upsert(
        collection_name=collection_name(),
        points=[
            PointStruct(
                id=pid,
                vector=DUMMY_VECTOR,
                payload={
                    "title": title,
                    "description": (description or "").strip(),
                    "done": False,
                    "created": now,
                },
            )
        ],
    )
    return pid


def delete_task(client: QdrantClient, point_id: str) -> None:
    client.delete(
        collection_name=collection_name(),
        points_selector=PointIdsList(points=[point_id]),
    )


def set_done(client: QdrantClient, point_id: str, done: bool) -> None:
    name = collection_name()
    r = client.retrieve(collection_name=name, ids=[point_id], with_payload=True)
    if not r:
        return
    p = dict(r[0].payload or {})
    p["done"] = bool(done)
    client.upsert(
        collection_name=name,
        points=[PointStruct(id=point_id, vector=DUMMY_VECTOR, payload=p)],
    )


def search_tasks(client: QdrantClient, query: str) -> list[dict[str, Any]]:
    q = (query or "").strip()
    all_tasks = list_tasks(client)
    if not q:
        return all_tasks
    qlow = q.lower()
    return [
        t
        for t in all_tasks
        if qlow in (t.get("title") or "").lower() or qlow in (t.get("description") or "").lower()
    ]
