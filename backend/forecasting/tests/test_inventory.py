"""Unit tests for inventory calculations and classification (pure Python / pytest)."""

import pytest

from forecasting.inventory import (
    classify,
    reorder_point,
    safety_stock,
    suggested_order_qty,
)


def test_safety_stock_known_values():
    """Verify safety stock formula with standard benchmark values.

    Given:
        sigma_daily = 10
        lead_time_days = 4
        service_level = 0.95 (z ≈ 1.64485)
    Expected:
        SS = 1.64485 * 10 * sqrt(4) = 1.64485 * 20 ≈ 32.897 (~32.9)
    """
    ss = safety_stock(sigma_daily=10.0, lead_time_days=4, service_level=0.95)
    assert ss == pytest.approx(32.897, abs=0.05)


def test_safety_stock_monotonic_service_level():
    """Higher target service levels must strictly increase safety stock."""
    ss_90 = safety_stock(sigma_daily=15.0, lead_time_days=7, service_level=0.90)
    ss_95 = safety_stock(sigma_daily=15.0, lead_time_days=7, service_level=0.95)
    ss_99 = safety_stock(sigma_daily=15.0, lead_time_days=7, service_level=0.99)

    assert ss_90 < ss_95 < ss_99


def test_safety_stock_zero_lead_time():
    """Zero lead time means instant replenishment and zero safety stock required."""
    assert safety_stock(sigma_daily=10.0, lead_time_days=0, service_level=0.95) == 0.0


def test_safety_stock_invalid_inputs():
    """Raise ValueError on invalid service level or negative parameters."""
    with pytest.raises(ValueError, match="service_level"):
        safety_stock(sigma_daily=10.0, lead_time_days=4, service_level=1.0)

    with pytest.raises(ValueError, match="service_level"):
        safety_stock(sigma_daily=10.0, lead_time_days=4, service_level=0.0)

    with pytest.raises(ValueError, match="sigma_daily"):
        safety_stock(sigma_daily=-5.0, lead_time_days=4, service_level=0.95)

    with pytest.raises(ValueError, match="lead_time_days"):
        safety_stock(sigma_daily=10.0, lead_time_days=-1, service_level=0.95)


def test_reorder_point_calculation():
    """Reorder point is the sum of lead time demand and safety stock."""
    ltd = 140.0  # 14 days * 10 units/day
    ss = 32.9
    rop = reorder_point(lead_time_demand=ltd, safety_stock=ss)
    assert rop == pytest.approx(172.9)


def test_classify_all_states():
    """Test every branch of inventory classification: stockout_risk, reorder_now, ok, overstock."""
    ltd = 50.0   # Lead time demand
    rop = 80.0   # Reorder point (LTD 50 + SS 30)
    avg_daily = 10.0
    overstock_days = 21.0  # Overstock threshold: > 210 units

    # 1. on_hand < ltd -> stockout_risk
    assert classify(on_hand=40.0, lead_time_demand=ltd, rop=rop, avg_daily_forecast=avg_daily) == "stockout_risk"
    assert classify(on_hand=0.0, lead_time_demand=ltd, rop=rop, avg_daily_forecast=avg_daily) == "stockout_risk"

    # 2. ltd <= on_hand <= rop -> reorder_now
    assert classify(on_hand=50.0, lead_time_demand=ltd, rop=rop, avg_daily_forecast=avg_daily) == "reorder_now"
    assert classify(on_hand=70.0, lead_time_demand=ltd, rop=rop, avg_daily_forecast=avg_daily) == "reorder_now"
    assert classify(on_hand=80.0, lead_time_demand=ltd, rop=rop, avg_daily_forecast=avg_daily) == "reorder_now"

    # 3. rop < on_hand <= overstock_cutoff -> ok
    assert classify(on_hand=85.0, lead_time_demand=ltd, rop=rop, avg_daily_forecast=avg_daily) == "ok"
    assert classify(on_hand=200.0, lead_time_demand=ltd, rop=rop, avg_daily_forecast=avg_daily) == "ok"
    assert classify(on_hand=210.0, lead_time_demand=ltd, rop=rop, avg_daily_forecast=avg_daily) == "ok"

    # 4. on_hand > 21 * avg_daily -> overstock
    assert classify(on_hand=211.0, lead_time_demand=ltd, rop=rop, avg_daily_forecast=avg_daily) == "overstock"
    assert classify(on_hand=500.0, lead_time_demand=ltd, rop=rop, avg_daily_forecast=avg_daily) == "overstock"


def test_classify_zero_demand():
    """Handle edge case where forecasted future demand is zero."""
    assert classify(on_hand=10.0, lead_time_demand=0.0, rop=0.0, avg_daily_forecast=0.0) == "overstock"
    assert classify(on_hand=0.0, lead_time_demand=0.0, rop=0.0, avg_daily_forecast=0.0) == "reorder_now"


def test_suggested_order_qty_positive_and_zero():
    """Calculate target order-up-to quantity and ensure non-negativity."""
    rop = 80.0
    review_demand = 70.0  # 7 days * 10 units/day
    # Target S = 80 + 70 = 150

    # Stock is below ROP: needs replenishment
    qty = suggested_order_qty(on_hand=60.0, rop=rop, review_period_demand=review_demand)
    assert qty == 90.0  # 150 - 60

    # Stock is exactly at ROP
    qty_at_rop = suggested_order_qty(on_hand=80.0, rop=rop, review_period_demand=review_demand)
    assert qty_at_rop == 70.0  # 150 - 80

    # Stock exceeds order-up-to level: order 0 (never negative)
    qty_excess = suggested_order_qty(on_hand=160.0, rop=rop, review_period_demand=review_demand)
    assert qty_excess == 0.0

