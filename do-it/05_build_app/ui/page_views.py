import os
from uuid import UUID
from typing import Any

import streamlit as st

import revive_llm_agent as llm_agent
import revive_postgres as db
from .ui_helpers import (
    _compose_service_brief,
    _db_connect_help,
    _render_issue_flow,
    _render_price_card,
    _render_provider_card,
    _render_range_card,
    _render_safety_alert_banner,
    _render_tool_status_banner,
    _render_triage_card,
    _render_welcome_panel,
)


def render_setup_tab() -> None:

    _render_welcome_panel()
    st.subheader("Vehicle profile")
    st.caption("Set your EV context once so the assistant can answer range, charging, and breakdown support questions accurately.")

    make = st.selectbox("Vehicle make", ["Ather", "Ola", "TVS", "Hero", "Mahindra", "Other"], index=0, key="vehicle_make")
    model = st.text_input("Vehicle model", placeholder="S1 Pro / iQube / Xtreme", key="vehicle_model")
    battery_percent = st.slider("Current battery (%)", 0, 100, 40, key="battery_percent")
    battery_capacity = st.number_input("Battery capacity (kWh)", min_value=1.0, max_value=20.0, value=3.5, step=0.1, key="battery_capacity_kwh")
    battery_health = st.slider("Battery health factor", 50, 100, 95, key="battery_health_factor") / 100.0
    location = st.text_input("Current location (lat,lng)", placeholder="12.9716,77.5946", key="owner_location")
    connector_type = st.selectbox("Connector type", ["Type 2", "CCS", "GB/T", "Other"], index=0, key="connector_type")

    cols = st.columns([3, 1])
    with cols[0]:
        st.write("**Vehicle context saved in session state.**")
    with cols[1]:
        if st.button("Reset vehicle profile", type="secondary"):
            for key in [
                "vehicle_make",
                "vehicle_model",
                "battery_percent",
                "battery_capacity_kwh",
                "battery_health_factor",
                "owner_location",
                "connector_type",
            ]:
                st.session_state.pop(key, None)
            st.experimental_rerun()

    st.markdown("---")
    st.write("Use the Assist tab to report an issue, request charging help, or start a provider booking.")


def render_chat_tab(client) -> None:
    st.subheader("Revvive Assist")
    st.caption("Report what’s wrong, confirm your location, and get help from our EV support workflow.")

    _render_issue_flow()

    try:
        db.ensure_tables()
    except Exception as e:
        st.error(f"PostgreSQL: {e}")
        _db_connect_help(e)
        return

    if not os.environ.get("OPENAI_API_KEY", "").strip():
        st.warning("Set **OPENAI_API_KEY** in `do-it/.env` (and **OPENAI_BASE_URL**, **CHAT_MODEL**).")

    if "vehicle_make" not in st.session_state:
        st.info("Complete the Vehicle profile in the Onboarding tab first.")
        return

    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = []

    user_msg = st.chat_input("Ask Revvive about your EV…")
    if user_msg:
        if not os.environ.get("OPENAI_API_KEY", "").strip():
            st.error("OPENAI_API_KEY is required.")
        else:
            with st.spinner("Planning and calling tools…"):
                vehicle_context = {
                    "vehicle_make": st.session_state.get("vehicle_make"),
                    "vehicle_model": st.session_state.get("vehicle_model"),
                    "battery_percent": st.session_state.get("battery_percent"),
                    "battery_capacity_kwh": st.session_state.get("battery_capacity_kwh"),
                    "battery_health_factor": st.session_state.get("battery_health_factor"),
                    "owner_location": st.session_state.get("owner_location"),
                    "connector_type": st.session_state.get("connector_type"),
                }
                result = llm_agent.run_agent(client, user_msg.strip(), vehicle_context)
            st.session_state["chat_history"].append({"role": "user", "content": user_msg})
            if result.get("ok"):
                st.session_state["chat_history"].append({"role": "assistant", "content": result.get("answer", "")})
            else:
                st.session_state["chat_history"].append({"role": "assistant", "content": f"Error: {result.get('error', 'Unknown')}"})
            st.session_state["last_agent_result"] = result
            st.experimental_rerun()

    for message in st.session_state.get("chat_history", []):
        if message["role"] == "user":
            st.chat_message("user").write(message["content"])
        else:
            st.chat_message("assistant").write(message["content"])

    res = st.session_state.get("last_agent_result")
    if res:
        st.markdown("---")
        if res.get("ok"):
            st.success("Last run completed.")
        else:
            st.error(res.get("error", "Unknown error"))
        st.caption(f"Run id: `{res.get('run_id')}`")

        trace = res.get("trace") or []
        tool_results = _extract_tool_results(trace)
        _render_tool_status_banner(trace)
        _render_safety_alert_banner(tool_results.get("safety_check", {}))
        _render_range_card(tool_results.get("estimate_range", {}))
        _render_triage_card(tool_results.get("triage_issue", {}))
        _render_safety_card(tool_results.get("safety_check", {}))
        if tool_results.get("search_providers"):
            _render_provider_card(tool_results.get("search_providers", {}))
        else:
            _render_provider_card(tool_results.get("get_provider_details", {}))
        _render_price_card(tool_results.get("estimate_fair_price", {}))
        _render_booking_card(tool_results.get("queue_booking", {}), trace)

        with st.expander("Trace (`agent_steps`)", expanded=False):
            for row in trace:
                st.json(
                    {
                        "step": row.get("step_no"),
                        "kind": row.get("kind"),
                        "tool": row.get("tool_name"),
                        "payload": row.get("payload"),
                    },
                    expanded=False,
                )


def _extract_tool_results(trace: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    results: dict[str, dict[str, Any]] = {}
    for row in trace:
        if row.get("kind") != "tool_result":
            continue
        tool_name = row.get("tool_name")
        payload = row.get("payload") or {}
        result = payload.get("result")
        if tool_name and isinstance(result, dict):
            results[tool_name] = result
    return results


def _render_booking_card(booking: dict[str, Any], trace: list[dict[str, Any]]) -> None:
    if not booking:
        return
    urgent = str(booking.get('urgency', '')).strip().lower() == 'urgent'
    header = "#### Booking approval"
    if urgent:
        header += " ⚠️ URGENT"
    st.markdown(header)
    if urgent:
        st.markdown("<div style='border:2px solid #e02424;padding:10px;border-radius:8px;background:#fff0f0;'>" \
                    "<strong>Urgent booking requested:</strong> please approve immediately and contact the service provider directly if needed." \
                    "</div>", unsafe_allow_html=True)
    st.markdown(f"- Provider: {booking.get('provider_name')}")
    st.markdown(f"- Issue: {booking.get('issue_summary')}")
    st.markdown(f"- Urgency: {booking.get('urgency')}")
    st.markdown(f"- Cost estimate: ₹{booking.get('estimated_cost_min')} – ₹{booking.get('estimated_cost_max')}")
    pending_id = booking.get('pending_action_id')
    if pending_id:
        if st.button("Approve booking", key=f"chat_approve_{pending_id}"):
            out = db.resolve_pending_booking(UUID(str(pending_id)), "approved", note="chat")
            if out:
                booking_id = str(UUID(str(pending_id)))
                db.insert_booking_record(
                    booking_id=booking_id,
                    run_id=UUID(str(out["run_id"])) if out.get("run_id") else None,
                    owner_id=None,
                    provider_id=out.get("provider_id", ""),
                    provider_name=out.get("provider_name", ""),
                    issue_summary=booking.get('issue_summary', ""),
                    triage_json=booking.get('triage_json', {}),
                    estimated_cost_min=float(booking.get('estimated_cost_min', 0.0)),
                    estimated_cost_max=float(booking.get('estimated_cost_max', 0.0)),
                    urgency=booking.get('urgency', "routine"),
                )
                st.success("Booking approved and recorded.")
                st.markdown("**Service brief:**")
                st.write(_compose_service_brief(booking, trace))
            else:
                st.warning("Booking could not be approved or was already resolved.")
        if st.button("Reject booking", key=f"chat_reject_{pending_id}"):
            db.resolve_pending_booking(UUID(str(pending_id)), "rejected", note="chat")
            st.info("Booking rejected.")


def _db_connect_help(exc: Exception) -> None:
    msg = str(exc).lower()
    if any(
        x in msg
        for x in (
            "name or service not known",
            "resolve host",
            "could not translate host",
            "nodename nor servname",
            "temporary failure in name resolution",
        )
    ):
        st.warning(
            "**Hostname in `DATABASE_URL` is wrong or unreachable.** "
            "Use the exact host and port from your hosted Postgres provider. "
            "Inside Docker, `localhost` refers to the container — use the URL your provider gives for external access."
        )
    elif "password authentication failed" in msg or "authentication failed" in msg:
        st.warning("Check **username** and **password** in `DATABASE_URL` (URL-encode special characters).")
    elif "ssl" in msg or "tls" in msg or "certificate" in msg:
        st.warning("Try appending **`?sslmode=require`** to `DATABASE_URL` if your provider requires TLS.")
    elif "call postgres_db.ensure_tables" in msg or "postgresql is not ready" in msg:
        st.warning("Database layer was used before startup completed; use **Reload Postgres cache** or restart the app.")
    st.markdown(
        "Tables are created by ``revive_postgres.ensure_tables()`` on first load. "
        "Optional manual DDL: ``psql \"$DATABASE_URL\" -f 04_starter_kit/db/schema.sql``."
    )


def render_approvals_tab(client) -> None:
    st.subheader("Pending booking approvals")
    st.caption("Approve or reject provider bookings that Revvive has queued for human review.")

    try:
        db.ensure_tables()
    except Exception as e:
        st.error(f"PostgreSQL: {e}")
        _db_connect_help(e)
        return

    pending = db.list_pending_bookings()
    if not pending:
        st.info("No pending booking approvals.")
        return

    for row in pending:
        pid = row["id"]
        detail = row.get("action_detail") or {}
        st.write(f"**{row.get('provider_name', '?')}** — `{row.get('provider_id', '')[:12]}…`")
        st.caption(f"Issue: {detail.get('issue_summary', 'N/A')} | Urgency: {detail.get('urgency', 'routine')}")
        st.write(detail)
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Approve booking", key=f"apb_{pid}"):
                out = db.resolve_pending_booking(UUID(str(pid)), "approved", note="streamlit")
                if out:
                    booking_id = str(UUID(str(pid)))
                    db.insert_booking_record(
                        booking_id=booking_id,
                        run_id=UUID(str(out["run_id"])) if out.get("run_id") else None,
                        owner_id=None,
                        provider_id=out.get("provider_id", ""),
                        provider_name=out.get("provider_name", ""),
                        issue_summary=detail.get("issue_summary", ""),
                        triage_json=detail.get("triage", {}),
                        estimated_cost_min=float(detail.get("estimated_cost_min", 0.0)),
                        estimated_cost_max=float(detail.get("estimated_cost_max", 0.0)),
                        urgency=detail.get("urgency", "routine"),
                    )
                    st.success("Booking approved and recorded.")
                else:
                    st.warning("Already resolved.")
                st.experimental_rerun()
        with c2:
            if st.button("Reject booking", key=f"rjb_{pid}"):
                db.resolve_pending_booking(UUID(str(pid)), "rejected", note="streamlit")
                st.info("Rejected.")
                st.experimental_rerun()


def render_history_tab() -> None:
    st.subheader("Agent history")
    st.caption("Review past Revvive runs and booking outcomes.")

    try:
        db.ensure_tables()
    except Exception as e:
        st.error(f"PostgreSQL: {e}")
        _db_connect_help(e)
        return

    runs = db.list_recent_runs(limit=20)
    if not runs:
        st.info("No agent history yet.")
        return

    for run in runs:
        title = f"{run['created_at']} — {run.get('intent_type') or 'UNKNOWN'} — {run['status']}"
        with st.expander(title, expanded=False):
            st.markdown(f"**User message:** {run['user_message']}")
            st.markdown(f"**Intent:** {run.get('intent_type') or 'N/A'}")
            st.markdown(f"**Assistant summary:** {run.get('assistant_final', '')}")
            st.markdown(f"**Outcome:** {run['status']}")
            if run.get("error_message"):
                st.error(run["error_message"])
            trace = db.fetch_trace(run["id"])
            st.write(f"Tool calls: {len(trace)}")
            for row in trace:
                st.json({
                    "step": row.get("step_no"),
                    "tool": row.get("tool_name"),
                    "kind": row.get("kind"),
                    "payload": row.get("payload"),
                    "timestamp": row.get("created_at"),
                })

    st.markdown("---")
    st.subheader("Booking audit")
    bookings = db.list_bookings(limit=50)
    if not bookings:
        st.info("No booking history yet.")
        return

    for booking in bookings:
        with st.expander(f"{booking['booked_at']} — {booking['provider_name']} — {booking['status']}", expanded=False):
            st.markdown(f"**Provider:** {booking['provider_name']}")
            st.markdown(f"**Issue:** {booking['issue_summary']}")
            st.markdown(f"**Urgency:** {booking['urgency']}")
            st.markdown(f"**Cost estimate:** ₹{booking['estimated_cost_min']} – ₹{booking['estimated_cost_max']}")
            st.markdown(f"**Status:** {booking['status']}")
            st.markdown(f"**Run ID:** {booking.get('run_id')}")
            st.json(booking.get('triage_json') or {})
