"""
Tests for the LangGraph workflow — graph compilation and state transitions.
"""

import pytest

from app.graph.state import NegotiationState
from app.models.schemas import MediatorDecision


class TestNegotiationState:
    """Tests for the graph state definition."""

    def test_state_creation(self):
        state: NegotiationState = {
            "session_id": "test-123",
            "current_round": 1,
            "max_rounds": 10,
            "buyer_constraints": {
                "budget_ceiling": 50000,
                "target_price": 35000,
                "product_category": "IT Equipment",
            },
            "seller_constraints": {
                "minimum_price": 30000,
                "target_price": 48000,
                "cost_basis": 25000,
                "product_category": "IT Equipment",
            },
            "negotiation_history": [],
            "status": "ACTIVE",
        }
        assert state["session_id"] == "test-123"
        assert state["current_round"] == 1

    def test_state_supports_optional_fields(self):
        state: NegotiationState = {
            "session_id": "test-456",
            "current_round": 0,
            "max_rounds": 10,
            "status": "ACTIVE",
        }
        assert state.get("buyer_offer") is None
        assert state.get("human_override") is None


class TestRouting:
    """Tests for the routing logic."""

    def test_route_continue(self):
        from app.graph.workflow import route_after_mediator

        state: NegotiationState = {
            "mediator_decision": MediatorDecision.CONTINUE.value,
            "status": "ACTIVE",
        }
        assert route_after_mediator(state) == "continue"

    def test_route_success(self):
        from app.graph.workflow import route_after_mediator

        state: NegotiationState = {
            "mediator_decision": MediatorDecision.SUCCESS.value,
            "status": "SUCCESS",
        }
        assert route_after_mediator(state) == "finish"

    def test_route_failure(self):
        from app.graph.workflow import route_after_mediator

        state: NegotiationState = {
            "mediator_decision": MediatorDecision.FAILURE.value,
            "status": "FAILURE",
        }
        assert route_after_mediator(state) == "finish"

    def test_route_terminated(self):
        from app.graph.workflow import route_after_mediator

        state: NegotiationState = {
            "mediator_decision": "",
            "status": "TERMINATED",
        }
        assert route_after_mediator(state) == "finish"
