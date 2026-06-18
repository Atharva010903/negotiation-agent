"""
Mediator Agent — evaluates the negotiation state and makes a routing decision.

Uses Groq (llama-3.1-8b-instant) for fast, lightweight analysis.
Returns structured MediatorAnalysis via LangChain's with_structured_output.

Also responsible for triggering LangGraph interrupt() when HUMAN_CHECKPOINT
is the decision.
"""

from __future__ import annotations

import logging
from typing import Any

from langchain_groq import ChatGroq
from langgraph.types import interrupt

from app.config import GROQ_API_KEY, MEDIATOR_MODEL, MEDIATOR_TEMPERATURE
from app.graph.state import NegotiationState
from app.models.schemas import MediatorAnalysis, MediatorDecision
from app.prompts.templates import MEDIATOR_PROMPT

logger = logging.getLogger(__name__)


def _build_mediator_llm() -> Any:
    """Instantiate the Mediator LLM with structured output."""
    llm = ChatGroq(
        model=MEDIATOR_MODEL,
        api_key=GROQ_API_KEY,
        temperature=MEDIATOR_TEMPERATURE,
    )
    return llm.with_structured_output(MediatorAnalysis)


def _format_history(history: list[dict]) -> str:
    """Format negotiation history into a readable string."""
    if not history:
        return "No previous rounds."
    lines = []
    for h in history:
        lines.append(
            f"Round {h.get('round', '?')}: "
            f"Buyer ${h.get('buyer_offer', 'N/A')} | "
            f"Seller ${h.get('seller_offer', 'N/A')} | "
            f"Gap {h.get('price_gap_pct', 'N/A')}%"
        )
    return "\n".join(lines)


def _compute_price_gap(
    buyer_offer: float | None, seller_offer: float | None
) -> tuple[float, float]:
    """
    Compute absolute price gap and percentage gap.

    Returns
    -------
    tuple[float, float]
        (absolute_gap, pct_gap)
    """
    if buyer_offer is None or seller_offer is None:
        return 0.0, 0.0
    gap = abs(seller_offer - buyer_offer)
    pct = (gap / seller_offer * 100) if seller_offer > 0 else 0.0
    return round(gap, 2), round(pct, 2)


def mediator_node(state: NegotiationState) -> dict:
    """
    LangGraph node for the Mediator agent.

    Evaluates offers, computes convergence metrics, invokes the LLM,
    and triggers interrupt() if HUMAN_CHECKPOINT is decided.
    """
    current_round = state.get("current_round", 0)
    buyer_offer = state.get("buyer_offer")
    seller_offer = state.get("seller_offer")
    max_rounds = state.get("max_rounds", 10)

    logger.info("[Mediator] Evaluating round %d …", current_round)

    # Compute metrics
    price_gap, price_gap_pct = _compute_price_gap(buyer_offer, seller_offer)
    history_text = _format_history(state.get("negotiation_history", []))

    # Build prompt inputs
    prompt_input = {
        "current_round": current_round,
        "max_rounds": max_rounds,
        "buyer_offer": buyer_offer if buyer_offer is not None else "N/A",
        "seller_offer": seller_offer if seller_offer is not None else "N/A",
        "price_gap": price_gap,
        "price_gap_pct": price_gap_pct,
        "negotiation_history": history_text,
    }

    # Invoke LLM
    chain = MEDIATOR_PROMPT | _build_mediator_llm()
    analysis: MediatorAnalysis = chain.invoke(prompt_input)

    logger.info(
        "[Mediator] Decision: %s | Gap: $%.2f (%.1f%%) | Velocity: %.2f",
        analysis.decision.value,
        analysis.price_gap,
        analysis.price_gap_pct,
        analysis.concession_velocity,
    )

    # Build the history record for this round
    round_record = {
        "round": current_round,
        "buyer_offer": buyer_offer,
        "seller_offer": seller_offer,
        "buyer_reasoning": state.get("buyer_reasoning", ""),
        "seller_reasoning": state.get("seller_reasoning", ""),
        "price_gap": analysis.price_gap,
        "price_gap_pct": analysis.price_gap_pct,
        "mediator_decision": analysis.decision.value,
    }

    updated_history = list(state.get("negotiation_history", []))
    updated_history.append(round_record)

    # Determine status
    status = "ACTIVE"
    if analysis.decision == MediatorDecision.SUCCESS:
        status = "SUCCESS"
    elif analysis.decision == MediatorDecision.FAILURE:
        status = "FAILURE"
    elif analysis.decision == MediatorDecision.HUMAN_CHECKPOINT:
        status = "PAUSED"

    result = {
        "mediator_decision": analysis.decision.value,
        "mediator_reasoning": analysis.reasoning,
        "price_gap": analysis.price_gap,
        "price_gap_pct": analysis.price_gap_pct,
        "convergence_trend": analysis.convergence_trend,
        "concession_velocity": analysis.concession_velocity,
        "negotiation_history": updated_history,
        "current_round": current_round + 1,
        "status": status,
    }

    # Trigger human-in-the-loop interrupt if needed
    if analysis.decision == MediatorDecision.HUMAN_CHECKPOINT:
        logger.info("[Mediator] Triggering HUMAN_CHECKPOINT — pausing for review.")
        human_response = interrupt(
            {
                "reason": analysis.reasoning,
                "current_state": {
                    "round": current_round,
                    "buyer_offer": buyer_offer,
                    "seller_offer": seller_offer,
                    "price_gap": analysis.price_gap,
                    "price_gap_pct": analysis.price_gap_pct,
                },
                "options": [
                    "approve",
                    "reject",
                    "modify_buyer",
                    "modify_seller",
                    "inject",
                    "terminate",
                ],
            }
        )

        # Process the human response
        action = human_response.get("action", "approve") if isinstance(human_response, dict) else "approve"

        if action == "terminate":
            result["status"] = "TERMINATED"
            result["human_override"] = "Human terminated the negotiation."
        elif action == "approve":
            result["status"] = "ACTIVE"
            result["mediator_decision"] = MediatorDecision.CONTINUE.value
            result["human_override"] = "Human approved continuation."
        elif action == "modify_buyer" and "buyer_constraints" in human_response:
            result["buyer_constraints"] = human_response["buyer_constraints"]
            result["status"] = "ACTIVE"
            result["mediator_decision"] = MediatorDecision.CONTINUE.value
            result["human_override"] = "Human modified buyer constraints."
        elif action == "modify_seller" and "seller_constraints" in human_response:
            result["seller_constraints"] = human_response["seller_constraints"]
            result["status"] = "ACTIVE"
            result["mediator_decision"] = MediatorDecision.CONTINUE.value
            result["human_override"] = "Human modified seller constraints."
        elif action == "inject":
            result["human_instructions"] = human_response.get("instructions", "")
            result["status"] = "ACTIVE"
            result["mediator_decision"] = MediatorDecision.CONTINUE.value
            result["human_override"] = f"Human injected instructions: {result['human_instructions']}"
        else:
            result["status"] = "ACTIVE"
            result["mediator_decision"] = MediatorDecision.CONTINUE.value
            result["human_override"] = f"Human action: {action}"

    return result
