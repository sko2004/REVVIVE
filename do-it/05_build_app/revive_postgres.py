"""
Extended PostgreSQL schema and booking approval helpers for Revvive.
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from dotenv import load_dotenv
import postgres_db as db
from psycopg.types.json import Json

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def ensure_tables() -> None:
    db.ensure_tables()
    with db.connection() as conn:
        conn.execute(
            """
            ALTER TABLE pending_actions
            ADD COLUMN IF NOT EXISTS action_type TEXT DEFAULT 'delete',
            ADD COLUMN IF NOT EXISTS action_detail JSONB NOT NULL DEFAULT '{}'
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS pricing_history (
                id SERIAL PRIMARY KEY,
                subsystem TEXT NOT NULL,
                symptom_category TEXT,
                vehicle_category TEXT,
                region TEXT,
                cost_min NUMERIC,
                cost_max NUMERIC,
                sample_size INT,
                last_updated TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS bookings (
                id TEXT PRIMARY KEY,
                run_id UUID REFERENCES agent_runs(id),
                owner_id TEXT,
                provider_id TEXT,
                provider_name TEXT,
                issue_summary TEXT,
                triage_json JSONB,
                estimated_cost_min NUMERIC,
                estimated_cost_max NUMERIC,
                urgency TEXT,
                status TEXT DEFAULT 'confirmed',
                booked_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
        conn.commit()


def enqueue_booking_approval(
    run_id: UUID | None,
    provider_id: str,
    provider_name: str,
    issue_summary: str,
    triage_json: dict[str, Any],
    estimated_cost_min: float,
    estimated_cost_max: float,
    urgency: str,
    owner_notes: str | None = None,
) -> UUID:
    pid = uuid4()
    with db.connection() as conn:
        action_detail = {
            "provider_id": provider_id,
            "provider_name": provider_name,
            "issue_summary": issue_summary,
            "triage": triage_json,
            "estimated_cost_min": estimated_cost_min,
            "estimated_cost_max": estimated_cost_max,
            "urgency": urgency,
            "owner_notes": owner_notes,
        }
        conn.execute(
            """
            INSERT INTO pending_actions (id, run_id, task_id, task_title, action_type, action_detail, status)
            VALUES (%s, %s, %s, %s, 'booking', %s, 'pending')
            """,
            (
                str(pid),
                str(run_id) if run_id else None,
                provider_id,
                provider_name[:500],
                Json(action_detail),
            ),
        )
        conn.commit()
    return pid


def list_pending_bookings() -> list[dict[str, Any]]:
    with db.connection() as conn:
        cur = conn.execute(
            """
            SELECT id, run_id, task_id AS provider_id, task_title AS provider_name, action_detail, status, created_at
            FROM pending_actions
            WHERE status = 'pending' AND action_type = 'booking'
            ORDER BY created_at ASC
            """
        )
        return list(cur.fetchall())


def resolve_pending_booking(pending_id: UUID, status: str, note: str | None = None) -> dict[str, Any] | None:
    if status not in ("approved", "rejected"):
        raise ValueError("status must be approved or rejected")
    with db.connection() as conn:
        cur = conn.execute(
            """
            UPDATE pending_actions
            SET status = %s, resolved_at = now(), resolution_note = %s
            WHERE id = %s AND status = 'pending'
            RETURNING id, run_id, task_id AS provider_id, task_title AS provider_name, action_detail
            """,
            (status, note, str(pending_id)),
        )
        row = cur.fetchone()
        conn.commit()
    return dict(row) if row else None


def insert_booking_record(
    booking_id: str,
    run_id: UUID | None,
    owner_id: str | None,
    provider_id: str,
    provider_name: str,
    issue_summary: str,
    triage_json: dict[str, Any],
    estimated_cost_min: float,
    estimated_cost_max: float,
    urgency: str,
    status: str = "confirmed",
) -> None:
    with db.connection() as conn:
        conn.execute(
            """
            INSERT INTO bookings (id, run_id, owner_id, provider_id, provider_name, issue_summary,
                                  triage_json, estimated_cost_min, estimated_cost_max, urgency, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                booking_id,
                str(run_id) if run_id else None,
                owner_id,
                provider_id,
                provider_name,
                issue_summary,
                Json(triage_json),
                estimated_cost_min,
                estimated_cost_max,
                urgency,
                status,
            ),
        )
        conn.commit()


def query_pricing_history(
    subsystem: str,
    symptom_category: str | None,
    vehicle_category: str | None,
    region: str | None,
) -> dict[str, Any] | None:
    with db.connection() as conn:
        cur = conn.execute(
            """
            SELECT cost_min, cost_max, sample_size
            FROM pricing_history
            WHERE subsystem = %s
              AND (symptom_category = %s OR %s IS NULL)
              AND (vehicle_category = %s OR %s IS NULL)
              AND (region = %s OR %s IS NULL)
            ORDER BY sample_size DESC NULLS LAST
            LIMIT 1
            """,
            (subsystem, symptom_category, symptom_category, vehicle_category, vehicle_category, region, region),
        )
        row = cur.fetchone()
    return dict(row) if row else None


def list_recent_runs(limit: int = 20) -> list[dict[str, Any]]:
    return db.list_recent_runs(limit)


def fetch_trace(run_id: UUID) -> list[dict[str, Any]]:
    return db.fetch_trace(run_id)


def list_bookings(limit: int = 50) -> list[dict[str, Any]]:
    with db.connection() as conn:
        cur = conn.execute(
            """
            SELECT id, run_id, owner_id, provider_id, provider_name, issue_summary, triage_json,
                   estimated_cost_min, estimated_cost_max, urgency, status, booked_at
            FROM bookings
            ORDER BY booked_at DESC
            LIMIT %s
            """,
            (limit,),
        )
        return list(cur.fetchall())


def clear_connection_string_cache() -> None:
    db.clear_connection_string_cache()

reset_database_url_cache = clear_connection_string_cache
