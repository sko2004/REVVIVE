from typing import Any

import streamlit as st


def inject_ui_styles() -> None:
    st.markdown(
        """
        <style>
        .revv-card {
            border-radius: 22px;
            padding: 20px;
            background: linear-gradient(180deg, #111827 0%, #1f2937 100%);
            color: #f8fafc;
            box-shadow: 0 18px 40px rgba(15, 23, 42, 0.28);
            margin-bottom: 18px;
        }
        .revv-card h2, .revv-card h3, .revv-card h4 {
            margin: 0 0 10px 0;
        }
        .revv-card-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 16px;
            margin-bottom: 16px;
        }
        .revv-badge {
            display: inline-block;
            background: #10b981;
            color: white;
            padding: 6px 14px;
            border-radius: 999px;
            font-weight: 700;
            font-size: 0.9rem;
        }
        .revv-badge.warning { background: #f59e0b; }
        .revv-badge.danger { background: #ef4444; }
        .revv-hero {
            border-radius: 28px;
            padding: 28px;
            background: linear-gradient(135deg, #0f172a 0%, #111827 55%, #1f2937 100%);
            box-shadow: 0 24px 50px rgba(15, 23, 42, 0.3);
            margin-bottom: 24px;
            color: #f8fafc;
        }
        .revv-hero h1 {
            margin-bottom: 0.4rem;
            font-size: 3rem;
            letter-spacing: -0.03em;
        }
        .revv-hero p {
            color: #cbd5e1;
            margin-bottom: 1.2rem;
            font-size: 1.05rem;
        }
        .revv-hero .button-row {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
        }
        .revv-button-secondary .stButton>button {
            background: #1f2937 !important;
            color: #f8fafc !important;
            border: 1px solid #334155 !important;
        }
        .revv-status-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 16px;
        }
        .revv-section-title {
            margin-top: 0;
            margin-bottom: 0.25rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


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


def _render_welcome_panel() -> None:
    st.markdown(
        "<div class='revv-hero'>"
        "<div class='revv-card-header'>"
        "<div><h1>revvive</h1><p>Emergency support for your EV, when you need it most.</p></div>"
        "<span class='revv-badge'>24/7 Support</span>"
        "</div>"
        "</div>",
        unsafe_allow_html=True,
    )
    c1, c2 = st.columns([3, 1])
    with c1:
        st.markdown(
            "**Fast roadside support, EV expert dispatch, and confidence when your battery or charging stops working.**"
        )
    with c2:
        if st.button("Get Emergency Help", key="onboarding_help"):
            st.session_state["focus_chat"] = True
            st.success("Ready to assist — use the Assist tab to report the issue.")


def _render_issue_flow() -> None:
    st.markdown("#### What’s wrong?")
    st.selectbox(
        "Select the issue you’re experiencing",
        [
            "Vehicle won't start",
            "Battery not charging",
            "Charging issue / stuck",
            "Tire issue / flat",
            "Warning light on",
            "Other",
        ],
        index=0,
        key="issue_category",
    )
    st.text_area(
        "Tell us more",
        placeholder="Provide any details that help Revvive identify the fault quickly...",
        key="issue_details",
        height=110,
    )
    st.markdown("#### Confirm your location")
    location = st.session_state.get("owner_location", "Not set yet")
    st.info(f"Your location: {location}")
    if st.button("Confirm location and continue", key="confirm_issue_location"):
        st.success("Issue and location confirmed. Ask Revvive for support below.")


def _render_tool_status_banner(trace: list[dict[str, Any]]) -> None:
    tool_names = [row.get("tool_name") for row in trace if row.get("kind") == "tool_result" and row.get("tool_name")]
    if not tool_names:
        return
    unique_tools = list(dict.fromkeys(tool_names))
    st.info(f"Tools used in the last run: {', '.join(unique_tools)}")


def _render_safety_alert_banner(safety: dict[str, Any]) -> None:
    if not safety or safety.get("is_safe", True):
        return
    st.markdown(
        "<div style='border:2px solid #d32f2f;padding:14px;border-radius:10px;background:#ffebee;'>"
        "<strong>Safety Alert:</strong> This run detected an unsafe condition. "
        "Do not ride or charge the vehicle until a qualified service provider inspects it."
        "</div>",
        unsafe_allow_html=True,
    )


def _compose_service_brief(booking: dict[str, Any], trace: list[dict[str, Any]]) -> str:
    provider = booking.get("provider_name", "the recommended provider")
    issue = booking.get("issue_summary", "EV repair")
    triage = booking.get("triage_json") or {}
    tools = [row.get("tool_name") for row in trace if row.get("kind") == "tool_result"]
    tool_list = ", ".join(dict.fromkeys([t for t in tools if t]))
    safety_note = ""
    for row in trace:
        if row.get("kind") == "tool_result" and row.get("tool_name") == "safety_check":
            result = (row.get("payload") or {}).get("result")
            if isinstance(result, dict):
                safety_note = result.get("hazard_description") or result.get("safety_advisory") or ""
                break
    lines = [
        f"Service brief for {provider}:",
        f"Owner reported: {issue}.",
        f"Diagnosis: {triage.get('subsystem', 'Unknown')} / {triage.get('symptom_category', 'General')} / severity {triage.get('severity', 'Medium')}",
        f"Estimated cost: ₹{booking.get('estimated_cost_min', 0.0)} – ₹{booking.get('estimated_cost_max', 0.0)}.",
        f"Urgency: {booking.get('urgency', 'routine')}.",
    ]
    if safety_note:
        lines.append(f"Safety warning: {safety_note}.")
    if tool_list:
        lines.append(f"Relevant analysis steps: {tool_list}.")
    lines.append("Please inspect the vehicle, verify the reported symptom, and provide a detailed repair estimate.")
    return "\n".join(lines)


def _render_triage_card(triage: dict[str, Any]) -> None:
    if not triage:
        return
    st.markdown("#### Triage summary")
    st.markdown(f"- **Subsystem:** {triage.get('subsystem')}")
    st.markdown(f"- **Symptom:** {triage.get('symptom_category')}")
    st.markdown(f"- **Severity:** {triage.get('severity')}")
    st.markdown(f"- **Explanation:** {triage.get('explanation')}")


def _render_safety_card(safety: dict[str, Any]) -> None:
    if not safety:
        return
    if not safety.get("is_safe", True):
        st.markdown(
            "<div style='border:2px solid #e02424;padding:12px;border-radius:8px;background:#ffe5e5;'>"
            f"<strong>Safety Alert:</strong> {safety.get('hazard_description', '')}<br>"
            f"<strong>Advisory:</strong> {safety.get('safety_advisory', '')}<br>"
            f"<strong>Urgency:</strong> {safety.get('urgency_override', 'Critical')}"
            "</div>",
            unsafe_allow_html=True,
        )


def _render_provider_card(provider: dict[str, Any]) -> None:
    if not provider:
        return
    if provider.get("provider") and isinstance(provider["provider"], dict):
        provider = provider["provider"]
    elif provider.get("providers") and isinstance(provider["providers"], list):
        providers = provider["providers"]
        if providers:
            provider = providers[0]
        else:
            return
    st.markdown("#### Provider recommendation")
    st.markdown(f"**{provider.get('name', 'Recommended provider')}**")
    if provider.get("address"):
        st.markdown(f"- Address: {provider.get('address')}")
    if provider.get("phone"):
        st.markdown(f"- Phone: {provider.get('phone')}")
    if provider.get("brand_certifications"):
        st.markdown(f"- Brands: {', '.join(provider.get('brand_certifications', []))}")
    if provider.get("subsystem_specialisations"):
        st.markdown(f"- Specialisations: {', '.join(provider.get('subsystem_specialisations', []))}")
    if provider.get("rating") is not None:
        st.markdown(f"- Rating: {provider.get('rating')} ({provider.get('review_count', '0')} reviews)")
    if provider.get("connector_types"):
        st.markdown(f"- Connectors: {', '.join(provider.get('connector_types', []))}")
    if provider.get("description"):
        st.markdown(f"- Description: {provider.get('description')}")


def _render_price_card(price: dict[str, Any]) -> None:
    if not price:
        return
    st.markdown("#### Fair price estimate")
    st.markdown(f"- **Estimated cost:** ₹{price.get('cost_min')} – ₹{price.get('cost_max')}")
    breakdown = price.get('breakdown') or {}
    st.markdown(f"- Parts: ₹{breakdown.get('parts_min')} – ₹{breakdown.get('parts_max')}")
    st.markdown(f"- Labour: ₹{breakdown.get('labour_min')} – ₹{breakdown.get('labour_max')}")
    st.markdown(f"- Disclaimer: {price.get('disclaimer')}")


def _render_range_card(range_result: dict[str, Any]) -> None:
    if not range_result:
        return
    verdict = str(range_result.get('verdict', '')).strip().lower()
    badge = ''
    if verdict == 'comfortable':
        badge = "<span style='color:#ffffff;background:#2e7d32;padding:5px 10px;border-radius:999px;font-weight:bold;'>COMFORTABLE</span>"
    elif verdict == 'tight':
        badge = "<span style='color:#ffffff;background:#f57c00;padding:5px 10px;border-radius:999px;font-weight:bold;'>TIGHT</span>"
    elif verdict == 'not advisable':
        badge = "<span style='color:#ffffff;background:#d32f2f;padding:5px 10px;border-radius:999px;font-weight:bold;'>NOT ADVISABLE</span>"
    st.markdown("#### Range verdict")
    if badge:
        st.markdown(badge, unsafe_allow_html=True)
    if range_result.get('verdict_text'):
        st.markdown(f"**Recommendation:** {range_result.get('verdict_text')}")
    st.markdown(f"- **Distance:** {range_result.get('route', {}).get('distance_km')} km")
    st.markdown(f"- **Estimated consumption:** {range_result.get('consumption_kwh')} kWh")
    st.markdown(f"- **Battery remaining:** {range_result.get('available_kwh')} kWh")
    st.markdown(f"- **Arrival confidence:** {range_result.get('confidence', {}).get('worst_case')}% - {range_result.get('confidence', {}).get('best_case')}%")


__all__ = [
    'inject_ui_styles',
    '_render_welcome_panel',
    '_render_issue_flow',
    '_render_tool_status_banner',
    '_render_safety_alert_banner',
    '_compose_service_brief',
    '_render_triage_card',
    '_render_safety_card',
    '_render_provider_card',
    '_render_price_card',
    '_render_range_card',
]
