"""
FastAPI backend for the Multi-Agent Procurement Negotiation Platform.

Endpoints:
    POST /start_negotiation  — Start a new negotiation session
    POST /next_round         — Resume/continue a paused session
    POST /human_override     — Apply human intervention to a session
    GET  /status/{session_id} — Get current session status
    GET  /transcript/{session_id} — Get full negotiation transcript
    GET  /analytics          — Get aggregate analytics
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Dict

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.db.database import get_analytics, get_session_status, get_transcript
from app.graph.workflow import build_negotiation_graph
from app.models.schemas import (
    AnalyticsResponse,
    HumanOverrideRequest,
    NegotiationRoundRecord,
    SessionStatus,
    SessionStatusResponse,
    StartNegotiationRequest,
    StartNegotiationResponse,
)

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# ═══════════════════════════════════════════════════════════════════
#  App Setup
# ═══════════════════════════════════════════════════════════════════

app = FastAPI(
    title="Multi-Agent Procurement Negotiation Platform",
    description=(
        "A production-ready multi-agent system for automated procurement "
        "negotiations with human-in-the-loop support."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── In-memory session store ───────────────────────────────────────
# Maps session_id → {"graph": compiled_graph, "thread_config": {...}}
_sessions: Dict[str, Dict[str, Any]] = {}


# ═══════════════════════════════════════════════════════════════════
#  Endpoints
# ═══════════════════════════════════════════════════════════════════

@app.post("/start_negotiation", response_model=StartNegotiationResponse)
async def start_negotiation(request: StartNegotiationRequest):
    """
    Start a new negotiation session.

    Creates a LangGraph workflow instance, initialises state with
    buyer/seller constraints, and runs until the first mediator
    decision (or interrupt).
    """
    session_id = str(uuid.uuid4())
    logger.info("[API] Starting negotiation session %s", session_id)

    try:
        # Build a fresh graph for this session
        graph = build_negotiation_graph()

        thread_config = {"configurable": {"thread_id": session_id}}

        # Initial state
        initial_state = {
            "session_id": session_id,
            "buyer_constraints": request.buyer_constraints.model_dump(),
            "seller_constraints": request.seller_constraints.model_dump(),
            "max_rounds": request.max_rounds,
        }

        # Run the graph — it will execute until it hits an interrupt or END
        result = graph.invoke(initial_state, config=thread_config)

        # Store session
        _sessions[session_id] = {
            "graph": graph,
            "thread_config": thread_config,
        }

        # Determine response status
        status_str = result.get("status", "ACTIVE")
        try:
            status = SessionStatus(status_str)
        except ValueError:
            status = SessionStatus.ACTIVE

        current_round = result.get("current_round", 1)

        message = f"Negotiation running. Current status: {status_str}"
        if status == SessionStatus.PAUSED:
            message = (
                f"Negotiation paused for human review at round {current_round}. "
                f"Reason: {result.get('mediator_reasoning', 'N/A')}"
            )
        elif status in (SessionStatus.SUCCESS, SessionStatus.FAILURE):
            message = f"Negotiation completed with status: {status_str}"

        return StartNegotiationResponse(
            session_id=session_id,
            status=status,
            message=message,
            current_round=current_round,
        )

    except Exception as e:
        logger.exception("[API] Failed to start negotiation: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/next_round")
async def next_round(session_id: str):
    """
    Resume a paused negotiation session (continue after interrupt).
    This simply approves the current state and lets the graph continue.
    """
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session = _sessions[session_id]
    graph = session["graph"]
    thread_config = session["thread_config"]

    try:
        # Resume with approval
        result = graph.invoke(
            {"action": "approve"},
            config=thread_config,
        )

        status_str = result.get("status", "ACTIVE")
        return {
            "session_id": session_id,
            "status": status_str,
            "current_round": result.get("current_round", 0),
            "buyer_offer": result.get("buyer_offer"),
            "seller_offer": result.get("seller_offer"),
            "mediator_decision": result.get("mediator_decision"),
            "message": f"Round completed. Status: {status_str}",
        }

    except Exception as e:
        logger.exception("[API] Failed to resume session %s: %s", session_id, e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/human_override")
async def human_override(request: HumanOverrideRequest):
    """
    Apply a human override to a paused negotiation session.

    Supported actions:
    - approve: Continue the negotiation as-is
    - reject: Mark the negotiation as failed
    - modify_buyer: Update buyer constraints and continue
    - modify_seller: Update seller constraints and continue
    - inject: Inject custom instructions for the next round
    - terminate: Force-terminate the negotiation
    """
    session_id = request.session_id

    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session = _sessions[session_id]
    graph = session["graph"]
    thread_config = session["thread_config"]

    try:
        # Build the resume payload
        resume_payload: Dict[str, Any] = {"action": request.action}

        if request.action == "modify_buyer" and request.buyer_constraints:
            resume_payload["buyer_constraints"] = request.buyer_constraints.model_dump()
        elif request.action == "modify_seller" and request.seller_constraints:
            resume_payload["seller_constraints"] = request.seller_constraints.model_dump()
        elif request.action == "inject" and request.instructions:
            resume_payload["instructions"] = request.instructions

        # Resume graph execution with the human response
        from langgraph.types import Command

        result = graph.invoke(
            Command(resume=resume_payload),
            config=thread_config,
        )

        status_str = result.get("status", "ACTIVE")
        return {
            "session_id": session_id,
            "status": status_str,
            "current_round": result.get("current_round", 0),
            "buyer_offer": result.get("buyer_offer"),
            "seller_offer": result.get("seller_offer"),
            "mediator_decision": result.get("mediator_decision"),
            "human_override": result.get("human_override"),
            "message": f"Human override applied. Status: {status_str}",
        }

    except Exception as e:
        logger.exception("[API] Human override failed for %s: %s", session_id, e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/status/{session_id}", response_model=SessionStatusResponse)
async def get_status(session_id: str):
    """Get the current status of a negotiation session."""
    record = get_session_status(session_id)
    if not record:
        raise HTTPException(status_code=404, detail="Session not found")

    try:
        status = SessionStatus(record.get("final_status", "ACTIVE"))
    except ValueError:
        status = SessionStatus.ACTIVE

    return SessionStatusResponse(
        session_id=session_id,
        status=status,
        current_round=record.get("round_number", 0),
        buyer_offer=record.get("buyer_offer"),
        seller_offer=record.get("seller_offer"),
        mediator_decision=record.get("mediator_decision"),
        message=f"Session is {status.value}",
    )


@app.get("/transcript/{session_id}")
async def get_session_transcript(session_id: str):
    """Get the full negotiation transcript for a session."""
    transcript = get_transcript(session_id)
    if not transcript:
        raise HTTPException(status_code=404, detail="Session not found")

    return {"session_id": session_id, "transcript": transcript}


@app.get("/analytics", response_model=AnalyticsResponse)
async def get_negotiation_analytics():
    """Get aggregate analytics across all negotiation sessions."""
    analytics = get_analytics()
    return AnalyticsResponse(**analytics)


# ═══════════════════════════════════════════════════════════════════
#  Health Check
# ═══════════════════════════════════════════════════════════════════

@app.get("/health")
async def health():
    """Simple health check endpoint."""
    return {"status": "healthy", "service": "negotiation-platform"}
