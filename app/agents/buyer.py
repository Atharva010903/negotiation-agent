"""
Buyer Agent — negotiates the lowest possible price within a budget ceiling.

Uses Groq (qwen/qwen3-32b) with thinking mode enabled.
Returns structured BuyerResponse via LangChain's with_structured_output.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from langchain_groq import ChatGroq

from app.config import BUYER_MODEL, BUYER_TEMPERATURE, GROQ_API_KEY
from app.graph.state import NegotiationState
from app.models.schemas import BuyerResponse
from app.prompts.templates import BUYER_PROMPT
from app.rag.retriever import retrieve_benchmarks

logger = logging.getLogger(__name__)


def _build_buyer_llm() -> Any:
    """Instantiate the Buyer LLM with structured output."""
    llm = ChatGroq(
        model=BUYER_MODEL,
        api_key=GROQ_API_KEY,
        temperature=BUYER_TEMPERATURE,
    )
    return llm.with_structured_output(BuyerResponse)


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


def buyer_node(state: NegotiationState) -> dict:
    """
    LangGraph node for the Buyer agent.

    Retrieves benchmarks, invokes the LLM with structured output,
    and returns updated state fields.
    """
    logger.info("[Buyer] Round %d — generating offer …", state.get("current_round", 0))

    bc = state.get("buyer_constraints", {})
    product_category = bc.get("product_category", "general procurement")

    # RAG retrieval
    query = f"{product_category} procurement negotiation pricing benchmarks"
    benchmarks = retrieve_benchmarks(query)
    benchmark_text = "\n".join(f"- {b}" for b in benchmarks)

    # Determine the seller's current offer (or use "N/A" for first round)
    seller_offer = state.get("seller_offer")
    seller_offer_str = str(seller_offer) if seller_offer is not None else "No offer yet"

    # Format history
    history_text = _format_history(state.get("negotiation_history", []))

    # Human instructions
    human_instructions = ""
    if state.get("human_instructions"):
        human_instructions = (
            f"\nADDITIONAL HUMAN INSTRUCTIONS:\n{state['human_instructions']}"
        )

    # Build prompt inputs
    prompt_input = {
        "budget_ceiling": bc.get("budget_ceiling", 0),
        "target_price": bc.get("target_price", 0),
        "product_category": product_category,
        "quantity": bc.get("quantity", 1),
        "priorities": bc.get("priorities", "lowest price"),
        "benchmark_data": benchmark_text,
        "negotiation_history": history_text,
        "human_instructions": human_instructions,
        "seller_offer": seller_offer_str,
        "current_round": state.get("current_round", 1),
        "max_rounds": state.get("max_rounds", 10),
    }

    # Invoke LLM
    chain = BUYER_PROMPT | _build_buyer_llm()
    response: BuyerResponse = chain.invoke(prompt_input)

    logger.info(
        "[Buyer] Offer: $%.2f | Concession: $%.2f | Confidence: %.2f",
        response.offer_price,
        response.concession_made,
        response.confidence,
    )

    return {
        "buyer_offer": response.offer_price,
        "buyer_reasoning": response.reasoning,
        "buyer_benchmark_refs": response.benchmark_references,
        "retrieved_documents": benchmarks,
    }
