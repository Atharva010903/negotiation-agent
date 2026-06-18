"""
Pydantic schemas used across the platform.
Covers agent outputs, API request/response contracts, and database records.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════════════════════════
#  Enums
# ═══════════════════════════════════════════════════════════════════

class MediatorDecision(str, Enum):
    """Possible outcomes from the Mediator agent."""
    CONTINUE = "CONTINUE"
    HUMAN_CHECKPOINT = "HUMAN_CHECKPOINT"
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"


class SessionStatus(str, Enum):
    """Overall lifecycle status of a negotiation session."""
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"           # Waiting for human input
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    TERMINATED = "TERMINATED"   # Human forced termination


# ═══════════════════════════════════════════════════════════════════
#  Agent Output Schemas  (used by PydanticOutputParser / with_structured_output)
# ═══════════════════════════════════════════════════════════════════

class BuyerResponse(BaseModel):
    """Structured output from the Buyer agent."""
    offer_price: float = Field(
        ..., description="The price the buyer is offering for this round."
    )
    reasoning: str = Field(
        ..., description="Detailed reasoning behind the offer, referencing benchmarks."
    )
    concession_made: float = Field(
        ..., description="How much the buyer increased their offer from the previous round."
    )
    benchmark_references: list[str] = Field(
        default_factory=list,
        description="List of benchmark data points referenced in reasoning.",
    )
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence that a deal can be reached (0-1)."
    )


class SellerResponse(BaseModel):
    """Structured output from the Seller agent."""
    offer_price: float = Field(
        ..., description="The price the seller is offering for this round."
    )
    reasoning: str = Field(
        ..., description="Detailed reasoning behind the offer, referencing benchmarks."
    )
    concession_made: float = Field(
        ..., description="How much the seller reduced their price from the previous round."
    )
    benchmark_references: list[str] = Field(
        default_factory=list,
        description="List of benchmark data points referenced in reasoning.",
    )
    confidence: float = Field(
        ..., ge=0.0, le=1.0,
        description="Confidence that a deal can be reached (0-1).",
    )


class MediatorAnalysis(BaseModel):
    """Structured output from the Mediator agent."""
    price_gap: float = Field(
        ..., description="Absolute difference between buyer and seller offers."
    )
    price_gap_pct: float = Field(
        ..., description="Price gap as a percentage of the seller's offer."
    )
    convergence_trend: str = Field(
        ..., description="Description of convergence trend over recent rounds."
    )
    concession_velocity: float = Field(
        ..., description="Average concession per round across both parties."
    )
    decision: MediatorDecision = Field(
        ..., description="The mediator's routing decision."
    )
    reasoning: str = Field(
        ..., description="Explanation of how the decision was reached."
    )


# ═══════════════════════════════════════════════════════════════════
#  API Request / Response Schemas
# ═══════════════════════════════════════════════════════════════════

class BuyerConstraints(BaseModel):
    """Buyer-side negotiation parameters."""
    budget_ceiling: float = Field(..., description="Maximum price the buyer can pay.")
    target_price: float = Field(..., description="Ideal price the buyer wants to achieve.")
    product_category: str = Field(..., description="Product or service being negotiated.")
    quantity: int = Field(default=1, description="Number of units being procured.")
    priorities: str = Field(
        default="lowest price",
        description="Buyer priorities (e.g. lowest price, fast delivery, quality).",
    )


class SellerConstraints(BaseModel):
    """Seller-side negotiation parameters."""
    minimum_price: float = Field(
        ..., description="Absolute minimum the seller will accept."
    )
    target_price: float = Field(
        ..., description="Ideal price the seller wants to achieve."
    )
    cost_basis: float = Field(..., description="Cost of goods/services to the seller.")
    product_category: str = Field(..., description="Product or service being negotiated.")
    quantity: int = Field(default=1, description="Number of units.")


class StartNegotiationRequest(BaseModel):
    """POST /start_negotiation body."""
    buyer_constraints: BuyerConstraints
    seller_constraints: SellerConstraints
    max_rounds: int = Field(default=10, ge=1, le=50)


class StartNegotiationResponse(BaseModel):
    """Response after initiating a negotiation."""
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    status: SessionStatus = SessionStatus.ACTIVE
    message: str = "Negotiation started."
    current_round: int = 0


class HumanOverrideRequest(BaseModel):
    """POST /human_override body."""
    session_id: str
    action: str = Field(
        ..., description="One of: approve, reject, modify_buyer, modify_seller, inject, terminate."
    )
    buyer_constraints: Optional[BuyerConstraints] = None
    seller_constraints: Optional[SellerConstraints] = None
    instructions: Optional[str] = None


class NegotiationRoundRecord(BaseModel):
    """Represents a single logged round in the database."""
    id: Optional[int] = None
    session_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    round_number: int
    buyer_offer: Optional[float] = None
    seller_offer: Optional[float] = None
    buyer_reasoning: Optional[str] = None
    seller_reasoning: Optional[str] = None
    retrieved_documents: Optional[str] = None  # JSON string
    mediator_decision: Optional[str] = None
    human_override: Optional[str] = None
    final_status: str = SessionStatus.ACTIVE.value


class SessionStatusResponse(BaseModel):
    """GET /status/{session_id} response."""
    session_id: str
    status: SessionStatus
    current_round: int
    buyer_offer: Optional[float] = None
    seller_offer: Optional[float] = None
    mediator_decision: Optional[str] = None
    message: str = ""


class AnalyticsResponse(BaseModel):
    """GET /analytics response."""
    total_sessions: int = 0
    success_rate: float = 0.0
    average_rounds: float = 0.0
    average_final_gap_pct: float = 0.0
    average_buyer_concession: float = 0.0
    average_seller_concession: float = 0.0
