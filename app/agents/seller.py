"""
Seller Agent — negotiates the highest possible price above a minimum floor.

Uses Groq (qwen/qwen3-32b) with thinking mode OFF.
Returns structured SellerResponse via LangChain's with_structured_output.
"""

from __future__ import annotations

import logging
from typing import Any

from langchain_groq import ChatGroq

from app.config import GROQ_API_KEY, SELLER_MODEL, SELLER_TEMPERATURE
from app.graph.state import NegotiationState
from app.models.schemas import SellerResponse
from app.prompts.templates import SELLER_PROMPT
from app.rag.retriever import retrieve_benchmarks

logger = logging.getLogger(__name__)


def _build_seller_llm() -> Any:
    """Instantiate the Seller LLM with structured output (thinking OFF)."""
    llm = ChatGroq(
        model=SELLER_MODEL,
        api_key=GROQ_API_KEY,
        temperature=SELLER_TEMPERATURE,
        model_kwargs={"extra_body": {"reasoning_format": "hidden"}},
    )
    return llm.with_structured_output(SellerResponse)


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


def seller_node(state: NegotiationState) -> dict:
    """
    LangGraph node for the Seller agent.

    Retrieves benchmarks, invokes the LLM with structured output,
    and returns updated state fields.
    """
    logger.info("[Seller] Round %d — generating offer …", state.get("current_round", 0))

    sc = state.get("seller_constraints", {})
    product_category = sc.get("product_category", "general procurement")

    # RAG retrieval
    query = f"{product_category} supplier pricing negotiation benchmarks"
    benchmarks = retrieve_benchmarks(query)
    benchmark_text = "\n".join(f"- {b}" for b in benchmarks)

    # Buyer's current offer
    buyer_offer = state.get("buyer_offer")
    buyer_offer_str = str(buyer_offer) if buyer_offer is not None else "No offer yet"

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
        "minimum_price": sc.get("minimum_price", 0),
        "target_price": sc.get("target_price", 0),
        "cost_basis": sc.get("cost_basis", 0),
        "product_category": product_category,
        "quantity": sc.get("quantity", 1),
        "benchmark_data": benchmark_text,
        "negotiation_history": history_text,
        "human_instructions": human_instructions,
        "buyer_offer": buyer_offer_str,
        "current_round": state.get("current_round", 1),
        "max_rounds": state.get("max_rounds", 10),
    }

    # Invoke LLM
    chain = SELLER_PROMPT | _build_seller_llm()
    response: SellerResponse = chain.invoke(prompt_input)

    logger.info(
        "[Seller] Offer: $%.2f | Concession: $%.2f | Confidence: %.2f",
        response.offer_price,
        response.concession_made,
        response.confidence,
    )

    return {
        "seller_offer": response.offer_price,
        "seller_reasoning": response.reasoning,
        "seller_benchmark_refs": response.benchmark_references,
    }
