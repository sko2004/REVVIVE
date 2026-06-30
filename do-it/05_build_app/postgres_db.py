"""
PostgreSQL: agent runs, tool-trace steps, HITL pending queue.

Hosted Postgres only: set ``DATABASE_URL`` to a ``postgresql://`` URL (validated; placeholder
hosts rejected). Tables are created on first successful connect via ``ensure_tables()``.

The connection string is **cached only after** ``ensure_tables()`` succeeds, so retries are not
stuck on a failed URL.
"""

from __future__ import annotations

import os
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Generator
from urllib.parse import urlparse
from uuid import UUID

from dotenv import load_dotenv
import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Json

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

_DDL_STATEMENTS: tuple[str, ...] = (
    """
    CREATE TABLE IF NOT EXISTS agent_runs (
        id UUID PRIMARY KEY,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        user_message TEXT NOT NULL,
        assistant_final TEXT,
        status TEXT NOT NULL DEFAULT 'running',
        error_message TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS agent_steps (
        id BIGSERIAL PRIMARY KEY,
        run_id UUID NOT NULL REFERENCES agent_runs (id) ON DELETE CASCADE,
        step_no INT NOT NULL,
        kind TEXT NOT NULL,
        tool_name TEXT,
        tool_call_id TEXT,
        payload JSONB NOT NULL DEFAULT '{}',
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        UNIQUE (run_id, step_no)
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_agent_steps_run ON agent_steps (run_id, step_no)",
    """
    CREATE TABLE IF NOT EXISTS pending_actions (
        id UUID PRIMARY KEY,
        run_id UUID REFERENCES agent_runs (id) ON DELETE SET NULL,
        task_id TEXT NOT NULL,
        task_title TEXT,
        status TEXT NOT NULL DEFAULT 'pending',
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        resolved_at TIMESTAMPTZ,
        resolution_note TEXT
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_pending_open ON pending_actions (status) WHERE status = 'pending'",
)

_REQUIRED_TABLE_COUNT = 3

_url_cache: str | None = None

_PLACEHOLDER_HOSTS = frozenset(
    {
        "db.host",
        "example.com",
        "hostname",
        "your-host",
        "your_host",
        "postgres.host",
    }
)


def _validate_hosted_url(url: str) -> None:
    try:
        parsed = urlparse(url)
    except ValueError as e:
        raise ValueError(f"Invalid DATABASE_URL: {e}") from e
    if parsed.scheme not in ("postgresql", "postgres"):
        raise ValueError(
            f"DATABASE_URL must use postgresql:// or postgres:// (got scheme {parsed.scheme!r})."
        )
    host = (parsed.hostname or "").strip().lower()
    if not host:
        raise ValueError("DATABASE_URL is missing a hostname (the part after @).")
    if host in _PLACEHOLDER_HOSTS or host.startswith("your-"):
        raise ValueError(
            f"DATABASE_URL uses placeholder hostname {host!r}. "
            "Use the real hostname from your provider."
        )


def resolve_connection_string() -> str:
    """
    Read ``DATABASE_URL`` from the environment (no process-wide cache here).
    Used while connecting / retrying; the URL cache is set only after ``ensure_tables()`` succeeds.
    """
    u = os.environ.get("DATABASE_URL", "").strip()
    if not u:
        raise ValueError(
            "DATABASE_URL is required. Set it in do-it/.env (copy from .env.example)."
        )
    _validate_hosted_url(u)
    return u


def clear_connection_string_cache() -> None:
    """After changing env vars, call this then re-run ``ensure_tables()``."""
    global _url_cache
    _url_cache = None


def database_url() -> str:
    """
    Return the working connection string.

    If the in-process cache is empty (e.g. Streamlit ``@st.cache_resource`` still holds
    ``bootstrap_postgres`` as done after a module reload, or ``clear_connection_string_cache()``
    was used), run ``ensure_tables()`` once so callers do not depend on tab order.
    """
    global _url_cache
    if _url_cache is None:
        ensure_tables()
    assert _url_cache is not None  # ensure_tables sets this or raises
    return _url_cache


def _connect_timeout() -> int:
    return int(os.environ.get("POSTGRES_CONNECT_TIMEOUT", "").strip() or "15")


def _tables_ready(conn: psycopg.Connection) -> bool:
    row = conn.execute(
        """
        SELECT COUNT(*) AS n
        FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_name IN ('agent_runs', 'agent_steps', 'pending_actions')
        """
    ).fetchone()
    if not row:
        return False
    n = row["n"] if isinstance(row, dict) else row[0]
    return int(n) >= _REQUIRED_TABLE_COUNT


def _apply_ddl(conn: psycopg.Connection) -> None:
    if not _tables_ready(conn):
        for stmt in _DDL_STATEMENTS:
            conn.execute(stmt.strip())
    conn.execute("ALTER TABLE agent_runs ADD COLUMN IF NOT EXISTS intent_type TEXT")


def ensure_tables() -> None:
    """
    Connect (with retries), create tables if missing.
    Caches the working connection string only after success.
    """
    global _url_cache
    timeout = _connect_timeout()
    retries = int(os.environ.get("POSTGRES_CONNECT_RETRIES", "").strip() or "4")
    last: Exception | None = None
    for attempt in range(retries):
        url = resolve_connection_string()
        try:
            with psycopg.connect(url, row_factory=dict_row, connect_timeout=timeout) as conn:
                _apply_ddl(conn)
                conn.commit()
            _url_cache = url
            return
        except Exception as e:
            last = e
            if attempt + 1 < retries:
                time.sleep(0.35 * (attempt + 1))
    assert last is not None
    raise last


# Backward-compatible name used in older snippets
init_schema = ensure_tables


@contextmanager
def connection() -> Generator[psycopg.Connection, None, None]:
    with psycopg.connect(
        database_url(),
        row_factory=dict_row,
        connect_timeout=_connect_timeout(),
    ) as conn:
        yield conn


def insert_run(run_id: UUID, user_message: str, intent_type: str | None = None) -> None:
    with connection() as conn:
        conn.execute(
            "INSERT INTO agent_runs (id, user_message, intent_type, status) VALUES (%s, %s, %s, %s)",
            (str(run_id), user_message, intent_type, "running"),
        )
        conn.commit()


def update_run_intent(run_id: UUID, intent_type: str) -> None:
    with connection() as conn:
        conn.execute(
            "UPDATE agent_runs SET intent_type = %s WHERE id = %s",
            (intent_type, str(run_id)),
        )
        conn.commit()


def finish_run(
    run_id: UUID,
    *,
    assistant_final: str | None,
    status: str,
    error_message: str | None = None,
) -> None:
    with connection() as conn:
        conn.execute(
            """
            UPDATE agent_runs
            SET assistant_final = %s, status = %s, error_message = %s
            WHERE id = %s
            """,
            (assistant_final, status, error_message, str(run_id)),
        )
        conn.commit()


def log_step(
    run_id: UUID,
    step_no: int,
    kind: str,
    *,
    tool_name: str | None = None,
    tool_call_id: str | None = None,
    payload: dict[str, Any] | None = None,
) -> None:
    with connection() as conn:
        conn.execute(
            """
            INSERT INTO agent_steps (run_id, step_no, kind, tool_name, tool_call_id, payload)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (run_id, step_no) DO UPDATE SET
                kind = EXCLUDED.kind,
                tool_name = EXCLUDED.tool_name,
                tool_call_id = EXCLUDED.tool_call_id,
                payload = EXCLUDED.payload
            """,
            (
                str(run_id),
                step_no,
                kind,
                tool_name,
                tool_call_id,
                Json(payload or {}),
            ),
        )
        conn.commit()


def fetch_trace(run_id: UUID) -> list[dict[str, Any]]:
    with connection() as conn:
        cur = conn.execute(
            """
            SELECT step_no, kind, tool_name, tool_call_id, payload, created_at
            FROM agent_steps
            WHERE run_id = %s
            ORDER BY step_no ASC
            """,
            (str(run_id),),
        )
        return list(cur.fetchall())


def list_recent_runs(limit: int = 20) -> list[dict[str, Any]]:
    with connection() as conn:
        cur = conn.execute(
            """
            SELECT id, created_at, user_message, assistant_final, intent_type, status, error_message
            FROM agent_runs
            ORDER BY created_at DESC
            LIMIT %s
            """,
            (limit,),
        )
        return list(cur.fetchall())


def enqueue_delete_approval(run_id: UUID | None, task_id: str, task_title: str) -> UUID:
    from uuid import uuid4

    pid = uuid4()
    with connection() as conn:
        conn.execute(
            """
            INSERT INTO pending_actions (id, run_id, task_id, task_title, status)
            VALUES (%s, %s, %s, %s, 'pending')
            """,
            (str(pid), str(run_id) if run_id else None, task_id, task_title[:500]),
        )
        conn.commit()
    return pid


def list_pending_actions() -> list[dict[str, Any]]:
    with connection() as conn:
        cur = conn.execute(
            """
            SELECT id, run_id, task_id, task_title, status, created_at
            FROM pending_actions
            WHERE status = 'pending'
            ORDER BY created_at ASC
            """
        )
        return list(cur.fetchall())


def resolve_pending(
    pending_id: UUID,
    status: str,
    note: str | None = None,
) -> dict[str, Any] | None:
    if status not in ("approved", "rejected"):
        raise ValueError("status must be approved or rejected")
    with connection() as conn:
        cur = conn.execute(
            """
            UPDATE pending_actions
            SET status = %s, resolved_at = now(), resolution_note = %s
            WHERE id = %s AND status = 'pending'
            RETURNING id, task_id, task_title
            """,
            (status, note, str(pending_id)),
        )
        row = cur.fetchone()
        conn.commit()
    return dict(row) if row else None


# Alias for older imports
queue_delete_approval = enqueue_delete_approval
reset_database_url_cache = clear_connection_string_cache
