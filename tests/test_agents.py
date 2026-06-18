"""
Unit tests for Pydantic schemas and agent output validation.
"""

import pytest
from pydantic import ValidationError

from app.models.schemas import (
    AnalyticsResponse,
    BuyerConstraints,
    BuyerResponse,
    HumanOverrideRequest,
    MediatorAnalysis,
    MediatorDecision,
    NegotiationRoundRecord,
    SellerConstraints,
    SellerResponse,
    SessionStatus,
    StartNegotiationRequest,
)


class TestBuyerResponse:
    """Tests for BuyerResponse schema."""

    def test_valid_buyer_response(self):
        resp = BuyerResponse(
            offer_price=35000.0,
            reasoning="Based on benchmark data showing 15% average discounts.",
            concession_made=2000.0,
            benchmark_references=["IT Industry avg discount: 15%"],
            confidence=0.75,
        )
        assert resp.offer_price == 35000.0
        assert resp.confidence == 0.75
        assert len(resp.benchmark_references) == 1

    def test_confidence_bounds(self):
        with pytest.raises(ValidationError):
            BuyerResponse(
                offer_price=35000.0,
                reasoning="test",
                concession_made=0,
                confidence=1.5,  # Out of bounds
            )

    def test_missing_required_field(self):
        with pytest.raises(ValidationError):
            BuyerResponse(
                offer_price=35000.0,
                # missing reasoning
                concession_made=0,
                confidence=0.5,
            )


class TestSellerResponse:
    """Tests for SellerResponse schema."""

    def test_valid_seller_response(self):
        resp = SellerResponse(
            offer_price=45000.0,
            reasoning="Market conditions support premium pricing.",
            concession_made=3000.0,
            benchmark_references=["Construction avg discount: 8%"],
            confidence=0.8,
        )
        assert resp.offer_price == 45000.0
        assert resp.concession_made == 3000.0


class TestMediatorAnalysis:
    """Tests for MediatorAnalysis schema."""

    def test_valid_mediator_analysis(self):
        analysis = MediatorAnalysis(
            price_gap=10000.0,
            price_gap_pct=22.2,
            convergence_trend="Converging slowly",
            concession_velocity=1500.0,
            decision=MediatorDecision.CONTINUE,
            reasoning="Both parties making concessions, should continue.",
        )
        assert analysis.decision == MediatorDecision.CONTINUE

    def test_all_decisions(self):
        for decision in MediatorDecision:
            analysis = MediatorAnalysis(
                price_gap=100,
                price_gap_pct=5.0,
                convergence_trend="test",
                concession_velocity=1.0,
                decision=decision,
                reasoning="test",
            )
            assert analysis.decision == decision


class TestConstraints:
    """Tests for BuyerConstraints and SellerConstraints."""

    def test_valid_buyer_constraints(self):
        bc = BuyerConstraints(
            budget_ceiling=50000,
            target_price=35000,
            product_category="IT Equipment",
            quantity=100,
            priorities="lowest price",
        )
        assert bc.budget_ceiling == 50000

    def test_valid_seller_constraints(self):
        sc = SellerConstraints(
            minimum_price=30000,
            target_price=48000,
            cost_basis=25000,
            product_category="IT Equipment",
        )
        assert sc.minimum_price == 30000
        assert sc.quantity == 1  # default


class TestStartNegotiationRequest:
    """Tests for the API request model."""

    def test_valid_request(self):
        req = StartNegotiationRequest(
            buyer_constraints=BuyerConstraints(
                budget_ceiling=50000,
                target_price=35000,
                product_category="IT",
            ),
            seller_constraints=SellerConstraints(
                minimum_price=30000,
                target_price=48000,
                cost_basis=25000,
                product_category="IT",
            ),
            max_rounds=15,
        )
        assert req.max_rounds == 15


class TestSessionStatus:
    """Tests for SessionStatus enum."""

    def test_all_statuses(self):
        assert SessionStatus.ACTIVE.value == "ACTIVE"
        assert SessionStatus.PAUSED.value == "PAUSED"
        assert SessionStatus.SUCCESS.value == "SUCCESS"
        assert SessionStatus.FAILURE.value == "FAILURE"
        assert SessionStatus.TERMINATED.value == "TERMINATED"
