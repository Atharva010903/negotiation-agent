"""
Strongly-typed LangGraph state definition.
This TypedDict is the single source of truth flowing through every node in the graph.
"""

from __future__ import annotations

from typing import Annotated, Any, Optional

from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


class NegotiationState(TypedDict, total=False):
    """
    The state object passed between every node in the LangGraph workflow.

    Attributes
    ----------
    session_id : str
        Unique identifier for this negotiation session.
    current_round : int
        The current round number (starts at 0, incremented each cycle).
    max_rounds : int
        Maximum allowed negotiation rounds before forced termination.

    buyer_constraints : dict
        Buyer parameters (budget_ceiling, target_price, product_category, etc.).
    seller_constraints : dict
        Seller parameters (minimum_price, target_price, cost_basis, etc.).

    buyer_offer : float | None
        Latest price offered by the buyer.
    seller_offer : float | None
        Latest price offered by the seller.
    buyer_reasoning : str
        Buyer's reasoning for the current offer.
    seller_reasoning : str
        Seller's reasoning for the current offer.

    buyer_benchmark_refs : list[str]
        Benchmark documents referenced by the buyer.
    seller_benchmark_refs : list[str]
        Benchmark documents referenced by the seller.

    negotiation_history : list[dict]
        Full history of all rounds [{round, buyer_offer, seller_offer, ...}].

    retrieved_documents : list[str]
        RAG-retrieved benchmark texts for the current round.

    mediator_decision : str
        The mediator's latest decision (CONTINUE / HUMAN_CHECKPOINT / SUCCESS / FAILURE).
    mediator_reasoning : str
        The mediator's latest analysis narrative.
    price_gap : float
        Latest absolute gap between offers.
    price_gap_pct : float
        Latest gap as percentage of seller offer.
    convergence_trend : str
        Textual convergence assessment.
    concession_velocity : float
        Average concession rate.

    human_override : str | None
        Description of any human intervention applied.
    human_instructions : str | None
        Free-text instructions injected by a human.

    status : str
        Overall session status (ACTIVE / PAUSED / SUCCESS / FAILURE / TERMINATED).
    error : str | None
        Error message if something goes wrong.

    messages : list
        LangGraph message accumulator (used by add_messages reducer).
    """

    # ── Session metadata ──────────────────────────────────────────
    session_id: str
    current_round: int
    max_rounds: int

    # ── Constraints ───────────────────────────────────────────────
    buyer_constraints: dict[str, Any]
    seller_constraints: dict[str, Any]

    # ── Current round data ────────────────────────────────────────
    buyer_offer: Optional[float]
    seller_offer: Optional[float]
    buyer_reasoning: str
    seller_reasoning: str
    buyer_benchmark_refs: list[str]
    seller_benchmark_refs: list[str]

    # ── History ───────────────────────────────────────────────────
    negotiation_history: list[dict[str, Any]]

    # ── RAG ───────────────────────────────────────────────────────
    retrieved_documents: list[str]

    # ── Mediator ──────────────────────────────────────────────────
    mediator_decision: str
    mediator_reasoning: str
    price_gap: float
    price_gap_pct: float
    convergence_trend: str
    concession_velocity: float

    # ── Human-in-the-loop ─────────────────────────────────────────
    human_override: Optional[str]
    human_instructions: Optional[str]

    # ── Session lifecycle ─────────────────────────────────────────
    status: str
    error: Optional[str]

    # ── LangGraph messages (reducer-aware) ────────────────────────
    messages: Annotated[list, add_messages]
