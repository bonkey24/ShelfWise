"""Inventory optimization calculations and classification.

Pure Python implementation (no Django imports).
Formulas:
- Safety Stock: SS = z * sigma_daily * sqrt(lead_time_days)
- Reorder Point: ROP = lead_time_demand + safety_stock
- Stock Classification: stockout_risk | reorder_now | overstock | ok
- Suggested Order Quantity: max(0, rop + review_period_demand - on_hand)
"""

import math
from scipy.stats import norm


def safety_stock(
    sigma_daily: float,
    lead_time_days: int | float,
    service_level: float = 0.95,
) -> float:
    """Calculate buffer inventory to protect against demand and lead-time variability.

    Formula:
        SS = z * sigma_daily * sqrt(lead_time_days)

    Where:
        - z: Normal distribution quantile corresponding to the desired cycle service level:
             z = norm.ppf(service_level). E.g. service_level=0.95 -> z ≈ 1.6449.
        - sigma_daily: Standard deviation of daily forecast errors (or daily demand).
        - lead_time_days: Supplier replenishment lead time in days.

    Args:
        sigma_daily: Standard deviation of daily demand.
        lead_time_days: Replenishment lead time in days.
        service_level: Target cycle service level (0 < service_level < 1, default: 0.95).

    Returns:
        float: Computed safety stock units.

    Raises:
        ValueError: If service_level is not in (0, 1) or sigma/lead_time are negative.
    """
    if not (0.0 < service_level < 1.0):
        raise ValueError(f"service_level must be strictly between 0 and 1, got {service_level}")
    if sigma_daily < 0:
        raise ValueError(f"sigma_daily must be non-negative, got {sigma_daily}")
    if lead_time_days < 0:
        raise ValueError(f"lead_time_days must be non-negative, got {lead_time_days}")

    z = float(norm.ppf(service_level))
    return float(z * sigma_daily * math.sqrt(lead_time_days))


def reorder_point(
    lead_time_demand: float,
    safety_stock: float,
) -> float:
    """Calculate the inventory level that triggers a replenishment order.

    Formula:
        ROP = lead_time_demand + safety_stock

    Where:
        - lead_time_demand: Expected units consumed during the replenishment lead time:
          (lead_time_days * avg_daily_demand).
        - safety_stock: Additional buffer units to absorb statistical fluctuations.

    When on-hand inventory drops to or below ROP, a purchase order must be placed
    to avoid stocking out before the shipment arrives.

    Args:
        lead_time_demand: Expected cumulative demand across the supplier lead time.
        safety_stock: Buffer stock units calculated for the target service level.

    Returns:
        float: Reorder point quantity.
    """
    return float(lead_time_demand + safety_stock)


def classify(
    on_hand: float,
    lead_time_demand: float,
    rop: float,
    avg_daily_forecast: float,
    overstock_days: int | float = 21,
) -> str:
    """Classify current inventory status according to demand risk and capital efficiency.

    Classification Rules (evaluated in priority order):
    1. "stockout_risk": on_hand < lead_time_demand
       Current stock is insufficient to satisfy even baseline expected demand during
       lead time, making a stockout imminent unless expedited.
    2. "reorder_now": on_hand <= rop
       Stock has reached or breached the reorder point; an order must be placed immediately
       to prevent depleting the safety buffer.
    3. "overstock": on_hand / avg_daily_forecast > overstock_days
       Days of supply on hand exceeds the overstock threshold (default 21 days),
       indicating excess inventory and trapped working capital.
    4. "ok": otherwise
       Stock is safely above ROP and below the overstock ceiling.

    Args:
        on_hand: Current physical inventory on hand.
        lead_time_demand: Expected demand during supplier lead time.
        rop: Reorder point (lead_time_demand + safety_stock).
        avg_daily_forecast: Expected average daily demand rate.
        overstock_days: Maximum desired days of supply before flagging as overstock (default: 21).

    Returns:
        str: One of ["stockout_risk", "reorder_now", "overstock", "ok"].
    """
    if on_hand < lead_time_demand:
        return "stockout_risk"
    if on_hand <= rop:
        return "reorder_now"
    if avg_daily_forecast > 0:
        if (on_hand / avg_daily_forecast) > overstock_days:
            return "overstock"
    elif on_hand > 0:
        # Zero expected future demand with positive stock on hand is overstocked
        return "overstock"

    return "ok"


def suggested_order_qty(
    on_hand: float,
    rop: float,
    review_period_demand: float,
) -> float:
    """Calculate recommended order quantity under a periodic review policy (R, s, S).

    Formula:
        suggested_order_qty = max(0, rop + review_period_demand - on_hand)

    Where:
        - Target Order-Up-To Level: S = rop + review_period_demand
        - review_period_demand: Expected demand over the review cycle (e.g. 7 days).
        - on_hand: Current stock on hand.

    Ensures that when ordering, enough stock is acquired to cover both the upcoming
    review cycle and the lead time, plus safety buffer, without ordering negative units.

    Args:
        on_hand: Current inventory on hand.
        rop: Reorder point (lead_time_demand + safety_stock).
        review_period_demand: Expected demand across the periodic review interval (e.g. 7 days).

    Returns:
        float: Non-negative recommended order quantity.
    """
    order_up_to = rop + review_period_demand
    return float(max(0.0, order_up_to - on_hand))

