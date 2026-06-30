"""
Revvive — Streamlit UI: EV range management, issue triage, provider booking approvals.

Run: streamlit run app.py
"""

from __future__ import annotations

from pathlib import Path
from dotenv import load_dotenv
import streamlit as st

from ui import inject_ui_styles, render_approvals_tab, render_chat_tab, render_history_tab, render_setup_tab
import revive_postgres as db
from revive_qdrant import collection_name, ensure_collection, ensure_sample_providers

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


@st.cache_resource
def get_qdrant_client():
    client = ensure_collection()
    ensure_sample_providers(client)
    return client


def check_qdrant_health(client) -> tuple[bool, str]:
    try:
        client.get_collection(collection_name())
        return True, "Qdrant connection established"
    except Exception as exc:
        return False, str(exc)


def check_postgres_health() -> tuple[bool, str]:
    try:
        db.ensure_tables()
        return True, "Postgres schema ready"
    except Exception as exc:
        return False, str(exc)


def main() -> None:
    st.set_page_config(page_title="Revvive", page_icon="⚡", layout="wide")
    inject_ui_styles()
    st.title("Revvive")
    st.caption("EV range, charger support, fault triage, and provider booking approvals — powered by Vayu Do-It template architecture.")

    try:
        client = get_qdrant_client()
    except Exception as e:
        st.error(str(e))
        st.info("Set **QDRANT_URL** + **QDRANT_API_KEY**, or **QDRANT_PATH** for local Qdrant.")
        return

    with st.sidebar:
        st.subheader("Qdrant collection")
        st.code(collection_name(), language="text")
        if st.button("Refresh Qdrant cache"):
            get_qdrant_client.clear()
            st.rerun()

        st.markdown("**Postgres** — modules: `revive_postgres`, `revive_qdrant`, `revive_llm_agent`, `revive_tools`.")
        if st.button("Reload Postgres cache"):
            db.reset_database_url_cache()
            st.rerun()

        st.markdown("---")
        st.subheader("Runtime health")
        q_ok, q_msg = check_qdrant_health(client)
        db_ok, db_msg = check_postgres_health()
        st.write(f"Qdrant: {'✅' if q_ok else '❌'} {q_msg}")
        st.write(f"Postgres: {'✅' if db_ok else '❌'} {db_msg}")
        if not q_ok or not db_ok:
            st.warning("Fix the runtime connection issues before using the Assist or Approvals tabs.")

    tab_setup, tab_chat, tab_approvals, tab_history = st.tabs(["Onboarding", "Assist", "Approvals", "History"])

    with tab_setup:
        render_setup_tab()
    with tab_chat:
        render_chat_tab(client)
    with tab_approvals:
        render_approvals_tab(client)
    with tab_history:
        render_history_tab()


if __name__ == "__main__":
    main()
