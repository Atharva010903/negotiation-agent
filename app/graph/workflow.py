"""
LangGraph workflow for the Multi-Agent Procurement Negotiation.

Builds a StateGraph with:
- Setup node (initialises state)
- RAG retrieval node
- Buyer agent node
- Seller agent node
- Mediator agent node (with conditional routing and interrupt)
- Conditional edges for looping, human checkpoints, and termination
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from app.agents.buyer import buyer_node
from app.agents.mediator import mediator_node
from app.agents.seller import seller_node
from app.db.database import persist_round
from app.graph.state import NegotiationState
from app.models.schemas import MediatorDecision
from app.rag.retriever import retrieve_benchmarks

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
#  Node Functions
# ═══════════════════════════════════════════════════════════════════

def setup_node(state: NegotiationState) -> dict:
    """
    Initialises session metadata and validates constraints.
    This is the entry point of the graph.
    """
    session_id = state.get("session_id") or str(uuid.uuid4())
    logger.info("[Setup] Initialising session %s", session_id)

    return {
        "session_id": session_id,
        "current_round": 1,
        "negotiation_history": [],
        "status": "ACTIVE",
        "buyer_offer": None,
        "seller_offer": None,
        "mediator_decision": "",
        "human_override": None,
        "human_instructions": None,
        "error": None,
        "messages": [],
    }


def rag_node(state: NegotiationState) -> dict:
    """
    Retrieves relevant benchmark documents for the current negotiation context.
    Both buyer and seller agents will use these in their reasoning.
    """
    bc = state.get("buyer_constraints", {})
    sc = state.get("seller_constraints", {})
    product = bc.get("product_category") or sc.get("product_category", "procurement")

    query = f"{product} procurement negotiation pricing discount benchmarks"
    docs = retrieve_benchmarks(query)

    logger.info("[RAG] Retrieved %d benchmark documents for '%s'", len(docs), product)

    return {"retrieved_documents": docs}


def persistence_node(state: NegotiationState) -> dict:
    """
    Persists the current round data to SQLite after the mediator has decided.
    This runs after every mediator evaluation.
    """
    import json

    try:
        persist_round(
            session_id=state.get("session_id", ""),
            round_number=state.get("current_round", 0),
            buyer_offer=state.get("buyer_offer"),
            seller_offer=state.get("seller_offer"),
            buyer_reasoning=state.get("buyer_reasoning", ""),
            seller_reasoning=state.get("seller_reasoning", ""),
            retrieved_documents=json.dumps(state.get("retrieved_documents", [])),
            mediator_decision=state.get("mediator_decision", ""),
            human_override=state.get("human_override"),
            final_status=state.get("status", "ACTIVE"),
        )
        logger.info(
            "[Persist] Round %d saved to database.", state.get("current_round", 0)
        )
    except Exception as e:
        logger.error("[Persist] Failed to save round: %s", e)

    return {}


# ═══════════════════════════════════════════════════════════════════
#  Routing Functions
# ═══════════════════════════════════════════════════════════════════

def route_after_mediator(state: NegotiationState) -> str:
    """
    Conditional edge after the Mediator node.
    Routes to:
    - 'rag' (loop back) if CONTINUE
    - END if SUCCESS, FAILURE, or TERMINATED
    """
    decision = state.get("mediator_decision", "")
    status = state.get("status", "ACTIVE")

    if status in ("SUCCESS", "FAILURE", "TERMINATED"):
        return "finish"

    if decision == MediatorDecision.CONTINUE.value:
        return "continue"

    # Default: continue
    return "continue"


# ═══════════════════════════════════════════════════════════════════
#  Graph Builder
# ═══════════════════════════════════════════════════════════════════

def build_negotiation_graph() -> StateGraph:
    """
    Construct and compile the negotiation LangGraph workflow.

    Returns
    -------
    CompiledGraph
        A compiled, runnable LangGraph state machine with checkpointing.
    """
    workflow = StateGraph(NegotiationState)

    # Add nodes
    workflow.add_node("setup", setup_node)
    workflow.add_node("rag", rag_node)
    workflow.add_node("buyer", buyer_node)
    workflow.add_node("seller", seller_node)
    workflow.add_node("mediator", mediator_node)
    workflow.add_node("persist", persistence_node)

    # Set entry point
    workflow.set_entry_point("setup")

    # Linear flow: setup → rag → buyer → seller → mediator → persist
    workflow.add_edge("setup", "rag")
    workflow.add_edge("rag", "buyer")
    workflow.add_edge("buyer", "seller")
    workflow.add_edge("seller", "mediator")
    workflow.add_edge("mediator", "persist")

    # Conditional routing after persistence
    workflow.add_conditional_edges(
        "persist",
        route_after_mediator,
        {
            "continue": "rag",   # Loop back for next round
            "finish": END,       # Terminate
        },
    )

    # Compile with memory-based checkpointing (supports interrupt/resume)
    checkpointer = MemorySaver()
    compiled = workflow.compile(checkpointer=checkpointer)

    logger.info("[Graph] Negotiation workflow compiled successfully.")
    return compiled
