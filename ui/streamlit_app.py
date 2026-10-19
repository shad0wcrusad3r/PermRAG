"""PermRAG QuickStart Web Interface.

Provides an interactive dashboard that executes, visualizes, and verifies every
step from QUICKSTART.md in the browser without requiring terminal commands.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Ensure project root is on sys.path and current working directory
ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import html
import json
import time
from typing import Any

import pandas as pd
import streamlit as st

try:
    import ui.quickstart_services as s
except ImportError:
    import quickstart_services as s  # fallback if executed directly from ui/

# --------------------------------------------------------------------------- #
# Page Configuration & Styles
# --------------------------------------------------------------------------- #
st.set_page_config(
    page_title="PermRAG · QuickStart Dashboard",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

CUSTOM_CSS = """
<style>
/* Modern styling tokens */
:root {
    --accent: #7C5CFF;
    --accent-glow: rgba(124, 92, 255, 0.25);
    --bg-card: #141A2A;
    --border-color: #263048;
    --success: #10B981;
    --danger: #EF4444;
    --warning: #F59E0B;
}

.stApp {
    background: radial-gradient(circle at top right, #13192B 0%, #0B0F1A 60%);
}

.metric-card {
    background: #141A2A;
    border: 1px solid #263048;
    border-radius: 10px;
    padding: 16px 20px;
    margin-bottom: 12px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
}

.metric-title {
    font-size: 0.8rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #94A3B8;
    margin-bottom: 4px;
}

.metric-value {
    font-size: 1.6rem;
    font-weight: 700;
    color: #F8FAFC;
}

.metric-sub {
    font-size: 0.8rem;
    color: #64748B;
    margin-top: 4px;
}

.badge {
    display: inline-block;
    padding: 3px 8px;
    border-radius: 6px;
    font-size: 0.75rem;
    font-weight: 600;
    letter-spacing: 0.04em;
}
.badge-green { background: rgba(16, 185, 129, 0.15); color: #34D399; border: 1px solid rgba(16, 185, 129, 0.3); }
.badge-red { background: rgba(239, 68, 68, 0.15); color: #F87171; border: 1px solid rgba(239, 68, 68, 0.3); }
.badge-purple { background: rgba(124, 92, 255, 0.15); color: #A78BFA; border: 1px solid rgba(124, 92, 255, 0.3); }
.badge-amber { background: rgba(245, 158, 11, 0.15); color: #FBBF24; border: 1px solid rgba(245, 158, 11, 0.3); }

.chunk-card {
    background: #13192B;
    border-left: 3px solid #7C5CFF;
    border-radius: 0 8px 8px 0;
    padding: 12px 16px;
    margin-bottom: 12px;
}

.citation-source {
    background: #101626;
    border: 1px solid #1F293D;
    border-radius: 8px;
    padding: 10px 14px;
    margin-bottom: 8px;
}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# --------------------------------------------------------------------------- #
# Sidebar - Global Health & Navigation
# --------------------------------------------------------------------------- #
with st.sidebar:
    st.markdown("### 🛡️ **PermRAG**")
    st.caption("Permission-Aware Multi-Tenant RAG · Phase 1")
    st.markdown("---")

    nav_choice = st.radio(
        "Workflow Step",
        [
            "1. Setup & Diagnostics",
            "2. Interactive Retrieval (CLI)",
            "3. End-to-End Query (API)",
            "4. Compare Personas (A/B Test)",
            "5. Tests & Retrieval Evals",
            "6. Audit Log Explorer",
        ],
        index=0,
    )

    st.markdown("---")
    st.markdown("##### ⚙️ Live System Status")

    # Fast status queries
    qdrant_stat = s.docker_qdrant_status()
    api_live = s.api_health()
    try:
        user_cnt = len(s.list_users())
    except Exception:
        user_cnt = 0

    try:
        chunk_cnt = s.chunk_count()
    except Exception:
        chunk_cnt = 0

    col_s1, col_s2 = st.columns(2)
    with col_s1:
        st.markdown(
            f"**Qdrant:**<br>"
            f"<span class='badge {'badge-green' if qdrant_stat.get('ok') else 'badge-red'}'>"
            f"{'RUNNING' if qdrant_stat.get('ok') else 'STOPPED'}</span>",
            unsafe_allow_html=True,
        )
    with col_s2:
        st.markdown(
            f"**API Server:**<br>"
            f"<span class='badge {'badge-green' if api_live else 'badge-amber'}'>"
            f"{':8001 UP' if api_live else 'OFFLINE'}</span>",
            unsafe_allow_html=True,
        )

    st.markdown(
        f"<div style='margin-top:8px; font-size:0.85rem; color:#94A3B8;'>"
        f"👥 <b>Users:</b> {user_cnt} &nbsp;·&nbsp; 🧩 <b>Chunks:</b> {chunk_cnt}<br>"
        f"🤖 <b>LLM:</b> <code>{s.settings.effective_model}</code>"
        f"</div>",
        unsafe_allow_html=True,
    )

    if st.button("🔄 Refresh Status", width="stretch"):
        st.rerun()


# --------------------------------------------------------------------------- #
# PAGE 1: Setup & Diagnostics
# --------------------------------------------------------------------------- #
if nav_choice == "1. Setup & Diagnostics":
    st.title("🛠️ Setup & Environment Diagnostics")
    st.markdown(
        "Verifies the 4 prerequisites and core stores from **QUICKSTART.md Section 3**:"
        " Docker container, SQLite database, seed users, and Qdrant vector chunks."
    )

    # 4 Key metrics cards
    env_info = s.env_summary()
    q_live = s.qdrant_reachable()
    db_ok = s.db_path().exists()

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(
            f"<div class='metric-card'>"
            f"<div class='metric-title'>Vector Store</div>"
            f"<div class='metric-value'>{'Connected' if q_live.get('ok') else 'Error'}</div>"
            f"<div class='metric-sub'>{q_live.get('detail')}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            f"<div class='metric-card'>"
            f"<div class='metric-title'>SQLite DB</div>"
            f"<div class='metric-value'>{'Found' if db_ok else 'Missing'}</div>"
            f"<div class='metric-sub'>{s.db_path().name} ({len(s.list_users())} users)</div>"
            f"</div>",
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            f"<div class='metric-card'>"
            f"<div class='metric-title'>Qdrant Chunks</div>"
            f"<div class='metric-value'>{chunk_cnt}</div>"
            f"<div class='metric-sub'>Expected: ~52 chunks (10 docs)</div>"
            f"</div>",
            unsafe_allow_html=True,
        )
    with c4:
        st.markdown(
            f"<div class='metric-card'>"
            f"<div class='metric-title'>Groq Key & Model</div>"
            f"<div class='metric-value'>{'Configured' if env_info['groq_key_set'] else 'Missing'}</div>"
            f"<div class='metric-sub'>{env_info['groq_model']}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

    st.markdown("---")

    col_left, col_right = st.columns([1, 1])

    with col_left:
        st.subheader("👥 Seed Users (15 users across 3 tenants)")
        st.caption("5 roles per tenant: intern (1), eng_employee (2), eng_manager (3), fin_employee (2), hr_admin (4). Default password: `demo1234`")
        try:
            users = s.list_users()
            df_users = pd.DataFrame(users)
            st.dataframe(df_users, width="stretch", hide_index=True)
        except Exception as e:
            st.error(f"Failed to load users: {e}")
            if st.button("🌱 Migrate & Seed Users"):
                with st.spinner("Running alembic upgrade head && seed-users..."):
                    ok, msg = s.migrate_and_seed()
                    if ok:
                        st.success("Seeding complete!")
                        st.rerun()
                    else:
                        st.error(msg)

    with col_right:
        st.subheader("📚 Ingested Documents Inventory")
        st.caption("Breakdown of documents indexed in Qdrant with department and minimum role levels:")
        try:
            docs = s.document_inventory()
            df_docs = pd.DataFrame(docs)
            st.dataframe(df_docs[["title", "tenant_id", "department", "min_role_level", "chunks", "kind"]], width="stretch", hide_index=True)
        except Exception as e:
            st.error(f"Failed to load documents: {e}")

    with st.expander("🔍 Advanced Environment Details"):
        st.json(env_info)
        if st.button("Query Available Models on Groq API"):
            with st.spinner("Fetching models..."):
                try:
                    models = s.list_groq_models()
                    st.success(f"Found {len(models)} models available:")
                    st.code("\n".join(models))
                except Exception as e:
                    st.error(f"Groq API error: {e}")


# --------------------------------------------------------------------------- #
# PAGE 2: Interactive Retrieval (CLI Ask)
# --------------------------------------------------------------------------- #
elif nav_choice == "2. Interactive Retrieval (CLI)":
    st.title("🔍 Interactive Vector Retrieval (CLI Test)")
    st.markdown(
        "Mirrors `python -m app.cli ask '<question>' --user <email>`. "
        "Demonstrates that permission filtering is executed **inside the vector search** before any generation."
    )

    all_users = s.list_users()
    user_options = [u["email"] for u in all_users]

    sample_questions = [
        "What is the CFO's base salary?",
        "How many days of parental leave do employees get?",
        "What was Q4 2025 revenue?",
        "What companies are M&A targets?",
        "What is the remote work policy?",
        "What are the API naming conventions?",
    ]

    col_u1, col_u2 = st.columns([1, 1])
    with col_u1:
        sel_user = st.selectbox("Select User Persona:", user_options, index=0)
        # Display selected user badge
        user_meta = next(u for u in all_users if u["email"] == sel_user)
        st.markdown(
            f"Tenant: <b>{user_meta['tenant_id']}</b> · "
            f"Department: <b>{user_meta['department']}</b> · "
            f"Role Level: <b>{user_meta['role_level']}</b> "
            f"({'HR Admin (All)' if user_meta['role_level'] == 4 else 'Restricted'})",
            unsafe_allow_html=True,
        )

    with col_u2:
        preset = st.selectbox("Preset Question:", ["Custom..."] + sample_questions, index=1)
        if preset == "Custom...":
            question = st.text_input("Enter Question:", "What is the CFO's base salary?")
        else:
            question = st.text_input("Enter Question:", preset)

    top_k = st.slider("Top K Chunks:", min_value=1, max_value=15, value=6)

    if st.button("🚀 Retrieve Chunks", type="primary", width="stretch"):
        with st.spinner("Retrieving from Qdrant with ACL filter..."):
            try:
                chunks = s.retrieve_for(sel_user, question, top_k=top_k)
                st.subheader(f"Retrieved {len(chunks)} Chunks for {sel_user}")

                if not chunks:
                    st.warning("No chunks matched your query and permission filter.")
                else:
                    for i, ch in enumerate(chunks, 1):
                        acl_badge = (
                            "<span class='badge badge-green'>ACL MATCH: ALLOWED</span>"
                            if ch.get("acl_ok")
                            else "<span class='badge badge-red'>ACL MISMATCH!</span>"
                        )
                        st.markdown(
                            f"<div class='chunk-card'>"
                            f"<div style='display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;'>"
                            f"<b>[{i}] {html.escape(ch['title'])}</b> — <i>{html.escape(ch['heading_path'])}</i>"
                            f"<div>{acl_badge} &nbsp; <span class='badge badge-purple'>Score: {ch['score']:.3f}</span></div>"
                            f"</div>"
                            f"<div style='font-size:0.8rem; color:#94A3B8; margin-bottom:8px;'>"
                            f"Tenant: <code>{ch['tenant_id']}</code> | Dept: <code>{ch['department']}</code> | Min Role: <code>{ch['min_role_level']}</code>"
                            f"</div>"
                            f"<div style='font-size:0.9rem; line-height:1.5; color:#E2E8F0; white-space:pre-wrap;'>{html.escape(ch['text'])}</div>"
                            f"</div>",
                            unsafe_allow_html=True,
                        )
            except Exception as e:
                st.error(f"Retrieval error: {e}")


# --------------------------------------------------------------------------- #
# PAGE 3: End-to-End Query (API)
# --------------------------------------------------------------------------- #
elif nav_choice == "3. End-to-End Query (API)":
    st.title("💬 End-to-End API Query & Generation")
    st.markdown(
        "Mirrors the **Full API Test** in `QUICKSTART.md`: Authenticates via JWT, queries `/query`, "
        "and validates answers, citations `[S#]`, and audit tracking."
    )

    all_users = s.list_users()
    user_options = [u["email"] for u in all_users]

    col_q1, col_q2 = st.columns([1, 1])
    with col_q1:
        sel_user = st.selectbox("User:", user_options, index=4)  # default acme_hr_admin
        u_meta = next(u for u in all_users if u["email"] == sel_user)
        st.caption(f"Tenant: `{u_meta['tenant_id']}` · Dept: `{u_meta['department']}` · Role: Level {u_meta['role_level']}")

    with col_q2:
        exec_mode = st.radio("Execution Mode:", ["Direct Pipeline (in-process)", "HTTP API (:8001)"], horizontal=True)

    question = st.text_input(
        "Question:",
        value="What is the CFO base salary?",
        help="Try asking about executive compensation as an intern vs HR admin to see refusal behavior.",
    )

    col_btn1, col_btn2 = st.columns([1, 1])
    run_clicked = col_btn1.button("⚡ Ask Question", type="primary", width="stretch")

    if run_clicked:
        with st.spinner("Processing query (retrieve -> rerank -> generate -> validate)..."):
            t_start = time.time()
            res: dict[str, Any] = {}
            token_claims = None

            try:
                if exec_mode == "HTTP API (:8001)":
                    if not s.api_health():
                        st.error("API server is offline on port 8001. Start it or switch to Direct Pipeline.")
                        st.stop()
                    token = s.api_login(sel_user)
                    token_claims = s.decode_token(token)
                    res = s.api_query(token, question)
                else:
                    res = s.direct_answer(sel_user, question)

                dur_ms = int((time.time() - t_start) * 1000)

                # Display Results
                st.markdown("---")
                st.subheader("Response")

                refused = res.get("refused", False)
                if refused:
                    st.markdown(
                        "<div class='metric-card' style='border-left: 4px solid #EF4444;'>"
                        "<span class='badge badge-red' style='margin-bottom:8px;'>REFUSED BY ACCESS POLICY</span><br>"
                        f"<p style='font-size:1.1rem; color:#F87171; margin-top:8px;'>{html.escape(res.get('answer', ''))}</p>"
                        "</div>",
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        "<div class='metric-card' style='border-left: 4px solid #10B981;'>"
                        "<span class='badge badge-green' style='margin-bottom:8px;'>AUTHORIZED ANSWER</span><br>"
                        f"<p style='font-size:1.15rem; color:#F8FAFC; margin-top:8px; line-height:1.6;'>{html.escape(res.get('answer', ''))}</p>"
                        "</div>",
                        unsafe_allow_html=True,
                    )

                # Timing & Request ID metrics
                m1, m2, m3, m4 = st.columns(4)
                lat = res.get("latency_ms", {})
                if isinstance(lat, dict):
                    m1.metric("Total Latency", f"{lat.get('total', dur_ms)} ms")
                    m2.metric("Retrieval Time", f"{lat.get('retrieve', 0)} ms")
                    m3.metric("Generation Time", f"{lat.get('generate', 0)} ms")
                else:
                    m1.metric("Latency", f"{lat} ms")
                    m2.metric("Latency Mode", "Single")
                    m3.metric("Status", "Completed")

                m4.metric("Sources Cited", len(res.get("sources", [])))

                # Sources breakdown
                sources = res.get("sources", [])
                if sources:
                    st.markdown("##### 📑 Cited Sources")
                    for s_item in sources:
                        st.markdown(
                            f"<div class='citation-source'>"
                            f"<b>[{s_item.get('ref')}] {html.escape(s_item.get('title', ''))}</b> — <i>{html.escape(s_item.get('heading_path', ''))}</i><br>"
                            f"<span style='font-size:0.8rem; color:#64748B;'>Doc ID: <code>{s_item.get('doc_id')}</code> | Chunk ID: <code>{s_item.get('chunk_id')}</code></span>"
                            f"</div>",
                            unsafe_allow_html=True,
                        )

                with st.expander("🔍 Raw JSON Response & Token Details"):
                    if token_claims:
                        st.markdown("**JWT Claims:**")
                        st.json(token_claims)
                    st.markdown("**Response Payload:**")
                    st.json(res)

            except Exception as e:
                st.error(f"Query error: {e}")


# --------------------------------------------------------------------------- #
# PAGE 4: Compare Personas (A/B Test)
# --------------------------------------------------------------------------- #
elif nav_choice == "4. Compare Personas (A/B Test)":
    st.title("⚖️ Side-by-Side Persona Comparison")
    st.markdown(
        "Directly test the core requirement: **An unauthorized user (Intern) gets 0 restricted results / refusal**, "
        "while **an authorized user (HR Admin)** sees the exact salary details with citations."
    )

    test_question = st.text_input(
        "Test Question:",
        value="What is the CFO's base salary?",
        help="Executive compensation is min_role_level=4 in HR department.",
    )

    col_a, col_b = st.columns(2)

    with col_a:
        st.subheader("🔴 Restricted User (Intern)")
        intern_email = st.selectbox(
            "User A:",
            ["acme_intern@acme.test", "globex_intern@globex.test", "initech_intern@initech.test"],
            index=0,
        )

    with col_b:
        st.subheader("🟢 Authorized User (HR Admin)")
        admin_email = st.selectbox(
            "User B:",
            ["acme_hr_admin@acme.test", "globex_hr_admin@globex.test", "initech_hr_admin@initech.test"],
            index=0,
        )

    if st.button("⚡ Run Comparative A/B Test", type="primary", width="stretch"):
        with st.spinner("Executing simultaneous pipeline runs..."):
            col1, col2 = st.columns(2)

            with col1:
                st.markdown(f"#### Results for `{intern_email}`")
                res_a = s.direct_answer(intern_email, test_question)
                chunks_a = s.retrieve_for(intern_email, test_question, top_k=6)

                if res_a.get("refused"):
                    st.error(f"❌ Refused (Expected):\n{res_a.get('answer')}")
                else:
                    st.success(f"Answer: {res_a.get('answer')}")

                st.caption(f"Retrieved {len(chunks_a)} chunks (none about restricted exec comp).")
                for c_item in chunks_a[:3]:
                    st.markdown(f"- **{c_item['title']}** (Role {c_item['min_role_level']}, Dept: {c_item['department']})")

            with col2:
                st.markdown(f"#### Results for `{admin_email}`")
                res_b = s.direct_answer(admin_email, test_question)
                chunks_b = s.retrieve_for(admin_email, test_question, top_k=6)

                if not res_b.get("refused"):
                    st.success(f"✅ Authorized (Expected):\n{res_b.get('answer')}")
                else:
                    st.error(f"Refused: {res_b.get('answer')}")

                st.caption(f"Retrieved {len(chunks_b)} chunks (including Executive Compensation).")
                for c_item in chunks_b[:3]:
                    st.markdown(f"- **{c_item['title']}** (Role {c_item['min_role_level']}, Dept: {c_item['department']})")


# --------------------------------------------------------------------------- #
# PAGE 5: Tests & Retrieval Evals
# --------------------------------------------------------------------------- #
elif nav_choice == "5. Tests & Retrieval Evals":
    st.title("🧪 Automated Tests & Retrieval Evaluations")
    st.markdown(
        "Run the unit test suite and sample retrieval evals (**Recall@6, Hit@6, MRR@6**) directly from the UI."
    )

    tab_eval, tab_test, tab_ingest = st.tabs(["📊 Retrieval Evals", "✅ Unit Tests", "📦 Ingestion Verification"])

    with tab_eval:
        st.subheader("Retrieval Evaluation on Sample QA Dataset")
        st.caption("Runs all 10 persona queries with gold document verification.")

        if st.button("🚀 Run Retrieval Evaluation", type="primary"):
            with st.spinner("Running retrieval metrics across all 10 QA queries..."):
                try:
                    eval_res = s.run_retrieval_eval(dataset="sample")
                    summ = eval_res["summary"]

                    # Display top metrics
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Recall@6", f"{summ['recall@6']:.3f}", delta="Target: ≥ 0.70")
                    c2.metric("Hit Rate@6", f"{summ['hit@6']:.3f}")
                    c3.metric("MRR@6", f"{summ['mrr@6']:.3f}")
                    c4.metric("Recall@20", f"{summ['recall@20']:.3f}")

                    st.markdown("##### Per-Query Results")
                    df_eval = pd.DataFrame(eval_res["rows"])
                    st.dataframe(df_eval, width="stretch", hide_index=True)

                except Exception as e:
                    st.error(f"Evaluation error: {e}")

    with tab_test:
        st.subheader("Pytest Unit Test Suite")
        st.caption("Runs truth-table tests across 3 tenants × 5 depts × 4 roles, Hypothesis property tests, and citation validator tests.")

        if st.button("🧪 Run `pytest tests/unit`"):
            with st.spinner("Running pytest tests/unit..."):
                t_res = s.run_unit_tests()
                if t_res["returncode"] == 0:
                    st.success(f"All {len(t_res['cases'])} tests PASSED in {t_res['duration_s']}s!")
                else:
                    st.error(f"Tests failed with exit code {t_res['returncode']}")

                if t_res["cases"]:
                    df_cases = pd.DataFrame(t_res["cases"])
                    st.dataframe(df_cases[["status", "module", "test", "time_s"]], width="stretch", hide_index=True)

                with st.expander("Full Test Console Output"):
                    st.code(t_res["output"])

    with tab_ingest:
        st.subheader("Idempotent Ingestion Verification")
        st.caption("Tests that re-ingesting the sample corpus is a no-op (0 added, 0 updated, 10 skipped).")

        if st.button("🔄 Test Re-Ingestion (Should Skip 10)"):
            with st.spinner("Running app.ingest.pipeline..."):
                stats = s.run_ingest_sample()
                st.markdown(
                    f"<div class='metric-card'>"
                    f"<b>Added:</b> {stats['added']} &nbsp;·&nbsp; "
                    f"<b>Updated:</b> {stats['updated']} &nbsp;·&nbsp; "
                    f"<b>Deleted:</b> {stats['deleted']} &nbsp;·&nbsp; "
                    f"<b>Skipped:</b> <span class='badge badge-green'>{stats['skipped']}</span>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
                if stats["skipped"] == 10 and stats["added"] == 0 and stats["updated"] == 0:
                    st.success("✅ Perfect Idempotency: All 10 unchanged documents were skipped!")
                else:
                    st.info("Ingestion completed with updates.")


# --------------------------------------------------------------------------- #
# PAGE 6: Audit Log Explorer
# --------------------------------------------------------------------------- #
elif nav_choice == "6. Audit Log Explorer":
    st.title("📋 Live Audit Log Explorer")
    st.markdown("Inspect every query processed by PermRAG, tracking access mode, timestamps, refusal status, and latency.")

    cnt = s.audit_count()
    st.markdown(f"Total Audit Entries Recorded: **{cnt}**")

    col_f1, col_f2 = st.columns([1, 1])
    with col_f1:
        limit = st.slider("Max Rows to Fetch:", min_value=10, max_value=200, value=50)
    with col_f2:
        filter_refused = st.selectbox("Filter Refusal Status:", ["All", "Refused Only", "Authorized Only"])

    rows = s.audit_rows(limit=limit)
    if filter_refused == "Refused Only":
        rows = [r for r in rows if r["refused"]]
    elif filter_refused == "Authorized Only":
        rows = [r for r in rows if not r["refused"]]

    if not rows:
        st.info("No audit logs match the current filter.")
    else:
        df_audit = pd.DataFrame(rows)
        st.dataframe(
            df_audit[["ts", "user", "role_level", "question", "refused", "latency_ms", "retrieved", "cited", "model"]],
            width="stretch",
            hide_index=True,
        )

    with st.expander("📜 Server Log Tail (`data/api_server.log`)"):
        tail_text = s.server_log_tail(lines=50)
        if tail_text:
            st.code(tail_text)
        else:
            st.caption("No server log found yet or log is empty.")
