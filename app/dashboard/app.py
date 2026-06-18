"""
Streamlit Dashboard for the Multi-Agent Procurement Negotiation Platform.

Provides:
- Real-time buyer/seller offer tracking
- Price convergence charts
- Negotiation transcript view
- Human override controls
- Aggregate analytics
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st

# ── Configuration ─────────────────────────────────────────────────
API_BASE = "http://localhost:8000"

st.set_page_config(
    page_title="Procurement Negotiation Platform",
    page_icon="🤝",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ═══════════════════════════════════════════════════════════════════
#  Styling
# ═══════════════════════════════════════════════════════════════════

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 16px;
        color: white;
        margin-bottom: 2rem;
        text-align: center;
    }

    .main-header h1 {
        font-size: 2.2rem;
        font-weight: 700;
        margin: 0;
    }

    .main-header p {
        opacity: 0.85;
        font-size: 1rem;
        margin-top: 0.5rem;
    }

    .metric-card {
        background: linear-gradient(145deg, #1e1e2e, #2d2d44);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 12px;
        padding: 1.5rem;
        text-align: center;
        transition: transform 0.2s;
    }

    .metric-card:hover {
        transform: translateY(-2px);
    }

    .metric-value {
        font-size: 2rem;
        font-weight: 700;
        color: #667eea;
    }

    .metric-label {
        font-size: 0.85rem;
        color: rgba(255,255,255,0.6);
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-top: 0.3rem;
    }

    .status-active { color: #4ade80; }
    .status-paused { color: #fbbf24; }
    .status-success { color: #22d3ee; }
    .status-failure { color: #f87171; }
    .status-terminated { color: #a78bfa; }

    .transcript-row {
        background: rgba(255,255,255,0.03);
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 0.5rem;
        border-left: 3px solid #667eea;
    }

    div[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%);
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ═══════════════════════════════════════════════════════════════════
#  Helper Functions
# ═══════════════════════════════════════════════════════════════════

def api_call(method: str, endpoint: str, **kwargs) -> dict | None:
    """Make an API call and handle errors gracefully."""
    try:
        url = f"{API_BASE}{endpoint}"
        resp = getattr(requests, method)(url, timeout=120, **kwargs)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.ConnectionError:
        st.error("⚠️ Cannot connect to the API server. Make sure it's running on port 8000.")
        return None
    except requests.exceptions.HTTPError as e:
        st.error(f"❌ API Error: {e.response.text}")
        return None
    except Exception as e:
        st.error(f"❌ Unexpected error: {e}")
        return None


def get_status_class(status: str) -> str:
    """Return CSS class for status badge."""
    return f"status-{status.lower()}"


# ═══════════════════════════════════════════════════════════════════
#  Header
# ═══════════════════════════════════════════════════════════════════

st.markdown(
    """
    <div class="main-header">
        <h1>🤝 Procurement Negotiation Platform</h1>
        <p>Multi-Agent AI System with Human-in-the-Loop Controls</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ═══════════════════════════════════════════════════════════════════
#  Sidebar — Start New Negotiation
# ═══════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("## 🚀 New Negotiation")

    with st.expander("Buyer Constraints", expanded=True):
        buyer_budget = st.number_input("Budget Ceiling ($)", value=50000, step=1000)
        buyer_target = st.number_input("Target Price ($)", value=35000, step=1000)
        buyer_category = st.text_input("Product Category", value="IT Equipment")
        buyer_quantity = st.number_input("Quantity", value=100, step=10)
        buyer_priorities = st.text_input("Priorities", value="lowest price, quality")

    with st.expander("Seller Constraints", expanded=True):
        seller_min = st.number_input("Minimum Price ($)", value=30000, step=1000)
        seller_target = st.number_input("Seller Target ($)", value=48000, step=1000)
        seller_cost = st.number_input("Cost Basis ($)", value=25000, step=1000)
        seller_category = st.text_input("Seller Product", value="IT Equipment")
        seller_quantity = st.number_input("Seller Quantity", value=100, step=10)

    max_rounds = st.slider("Max Rounds", 3, 30, 10)

    if st.button("🎯 Start Negotiation", use_container_width=True):
        payload = {
            "buyer_constraints": {
                "budget_ceiling": buyer_budget,
                "target_price": buyer_target,
                "product_category": buyer_category,
                "quantity": buyer_quantity,
                "priorities": buyer_priorities,
            },
            "seller_constraints": {
                "minimum_price": seller_min,
                "target_price": seller_target,
                "cost_basis": seller_cost,
                "product_category": seller_category,
                "quantity": seller_quantity,
            },
            "max_rounds": max_rounds,
        }

        with st.spinner("Starting negotiation..."):
            result = api_call("post", "/start_negotiation", json=payload)

        if result:
            st.session_state["active_session"] = result["session_id"]
            st.success(f"✅ Session started: `{result['session_id'][:8]}...`")
            st.info(result.get("message", ""))
            st.rerun()

    st.markdown("---")
    st.markdown("## 📋 Session Lookup")
    lookup_id = st.text_input("Session ID")
    if st.button("🔍 Load Session") and lookup_id:
        st.session_state["active_session"] = lookup_id
        st.rerun()


# ═══════════════════════════════════════════════════════════════════
#  Main Content
# ═══════════════════════════════════════════════════════════════════

active_session = st.session_state.get("active_session")

if active_session:
    # ── Status ────────────────────────────────────────────────
    status_data = api_call("get", f"/status/{active_session}")
    transcript_data = api_call("get", f"/transcript/{active_session}")

    if status_data:
        status = status_data.get("status", "UNKNOWN")

        # KPI Cards
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.markdown(
                f"""<div class="metric-card">
                    <div class="metric-value">{status_data.get('current_round', 0)}</div>
                    <div class="metric-label">Current Round</div>
                </div>""",
                unsafe_allow_html=True,
            )

        with col2:
            buyer_offer = status_data.get("buyer_offer", "—")
            st.markdown(
                f"""<div class="metric-card">
                    <div class="metric-value" style="color: #4ade80;">
                        ${buyer_offer if buyer_offer != '—' else '—'}
                    </div>
                    <div class="metric-label">Buyer Offer</div>
                </div>""",
                unsafe_allow_html=True,
            )

        with col3:
            seller_offer = status_data.get("seller_offer", "—")
            st.markdown(
                f"""<div class="metric-card">
                    <div class="metric-value" style="color: #f87171;">
                        ${seller_offer if seller_offer != '—' else '—'}
                    </div>
                    <div class="metric-label">Seller Offer</div>
                </div>""",
                unsafe_allow_html=True,
            )

        with col4:
            st.markdown(
                f"""<div class="metric-card">
                    <div class="metric-value {get_status_class(status)}">{status}</div>
                    <div class="metric-label">Status</div>
                </div>""",
                unsafe_allow_html=True,
            )

        st.markdown("<br>", unsafe_allow_html=True)

        # ── Price Convergence Chart ───────────────────────────
        if transcript_data and transcript_data.get("transcript"):
            transcript = transcript_data["transcript"]
            st.markdown("### 📈 Price Convergence")

            rounds = [r.get("round_number", i + 1) for i, r in enumerate(transcript)]
            buyer_offers = [r.get("buyer_offer") for r in transcript]
            seller_offers = [r.get("seller_offer") for r in transcript]

            fig = go.Figure()

            fig.add_trace(
                go.Scatter(
                    x=rounds,
                    y=buyer_offers,
                    mode="lines+markers",
                    name="Buyer Offer",
                    line=dict(color="#4ade80", width=3),
                    marker=dict(size=10, symbol="circle"),
                    fill="tonexty" if len(rounds) > 1 else None,
                )
            )

            fig.add_trace(
                go.Scatter(
                    x=rounds,
                    y=seller_offers,
                    mode="lines+markers",
                    name="Seller Offer",
                    line=dict(color="#f87171", width=3),
                    marker=dict(size=10, symbol="diamond"),
                )
            )

            fig.update_layout(
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                xaxis_title="Round",
                yaxis_title="Price ($)",
                font=dict(family="Inter"),
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1,
                ),
                margin=dict(l=40, r=20, t=40, b=40),
                hovermode="x unified",
            )

            st.plotly_chart(fig, use_container_width=True)

            # ── Transcript Table ──────────────────────────────
            st.markdown("### 📜 Negotiation Transcript")

            for record in transcript:
                with st.expander(
                    f"Round {record.get('round_number', '?')} — "
                    f"Mediator: {record.get('mediator_decision', 'N/A')}",
                    expanded=False,
                ):
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.markdown("**🟢 Buyer**")
                        st.write(f"Offer: **${record.get('buyer_offer', 'N/A')}**")
                        st.caption(record.get("buyer_reasoning", ""))
                    with col_b:
                        st.markdown("**🔴 Seller**")
                        st.write(f"Offer: **${record.get('seller_offer', 'N/A')}**")
                        st.caption(record.get("seller_reasoning", ""))

                    if record.get("human_override"):
                        st.info(f"👤 Human Override: {record['human_override']}")

        # ── Human Override Controls ───────────────────────────
        if status == "PAUSED":
            st.markdown("### 👤 Human Intervention Required")
            st.warning(
                "The mediator has paused the negotiation. Please review and take action."
            )

            action = st.selectbox(
                "Action",
                ["approve", "reject", "modify_buyer", "modify_seller", "inject", "terminate"],
            )

            override_payload: dict = {
                "session_id": active_session,
                "action": action,
            }

            if action == "inject":
                instructions = st.text_area("Instructions to inject")
                override_payload["instructions"] = instructions

            if action == "modify_buyer":
                st.markdown("**Update Buyer Constraints:**")
                new_budget = st.number_input("New Budget Ceiling", value=50000)
                new_target = st.number_input("New Target Price", value=35000)
                override_payload["buyer_constraints"] = {
                    "budget_ceiling": new_budget,
                    "target_price": new_target,
                    "product_category": buyer_category,
                    "quantity": buyer_quantity,
                    "priorities": buyer_priorities,
                }

            if action == "modify_seller":
                st.markdown("**Update Seller Constraints:**")
                new_min = st.number_input("New Minimum Price", value=30000)
                new_starget = st.number_input("New Seller Target", value=48000)
                override_payload["seller_constraints"] = {
                    "minimum_price": new_min,
                    "target_price": new_starget,
                    "cost_basis": seller_cost,
                    "product_category": seller_category,
                    "quantity": seller_quantity,
                }

            if st.button("✅ Submit Override", use_container_width=True):
                with st.spinner("Applying override..."):
                    result = api_call("post", "/human_override", json=override_payload)
                if result:
                    st.success(f"Override applied: {result.get('message', '')}")
                    st.rerun()

    else:
        st.info("Session not found or API unavailable.")

else:
    # ── Analytics Dashboard (when no session is active) ───────
    st.markdown("### 📊 Platform Analytics")

    analytics = api_call("get", "/analytics")

    if analytics:
        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown(
                f"""<div class="metric-card">
                    <div class="metric-value">{analytics.get('total_sessions', 0)}</div>
                    <div class="metric-label">Total Sessions</div>
                </div>""",
                unsafe_allow_html=True,
            )

        with col2:
            st.markdown(
                f"""<div class="metric-card">
                    <div class="metric-value" style="color: #4ade80;">
                        {analytics.get('success_rate', 0)}%
                    </div>
                    <div class="metric-label">Success Rate</div>
                </div>""",
                unsafe_allow_html=True,
            )

        with col3:
            st.markdown(
                f"""<div class="metric-card">
                    <div class="metric-value">{analytics.get('average_rounds', 0)}</div>
                    <div class="metric-label">Avg. Rounds</div>
                </div>""",
                unsafe_allow_html=True,
            )

        st.markdown("<br>", unsafe_allow_html=True)

        col4, col5 = st.columns(2)
        with col4:
            st.metric(
                "Avg. Buyer Concession",
                f"${analytics.get('average_buyer_concession', 0):,.2f}",
            )
        with col5:
            st.metric(
                "Avg. Seller Concession",
                f"${analytics.get('average_seller_concession', 0):,.2f}",
            )

    else:
        st.markdown(
            "> Start a negotiation from the sidebar or ensure the API server is running."
        )
