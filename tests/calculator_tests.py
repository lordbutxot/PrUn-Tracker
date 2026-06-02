import sys
from pathlib import Path

import pandas as pd
import pytest


ROOT = Path(__file__).resolve().parents[1]
HISTORICAL_DATA_DIR = ROOT / "pu-tracker" / "historical_data"
sys.path.insert(0, str(HISTORICAL_DATA_DIR))

from calculators import (  # noqa: E402
    calculate_material_input_cost,
    calculate_profit,
    calculate_roi,
    calculate_viability,
    calculate_workforce_consumable_cost,
)


def test_material_input_cost_uses_exchange_specific_ask_prices():
    recipe_inputs = pd.DataFrame(
        [
            {"Key": "BMP:1xC-2xH=>200xPE", "Material": "C", "Amount": 1},
            {"Key": "BMP:1xC-2xH=>200xPE", "Material": "H", "Amount": 2},
        ]
    )
    market_prices = pd.DataFrame(
        [
            {"Ticker": "C", "Exchange": "AI1", "Ask_Price": 150, "Bid_Price": 100},
            {"Ticker": "H", "Exchange": "AI1", "Ask_Price": 25, "Bid_Price": 20},
            {"Ticker": "C", "Exchange": "NC1", "Ask_Price": 999, "Bid_Price": 999},
            {"Ticker": "H", "Exchange": "NC1", "Ask_Price": 999, "Bid_Price": 999},
        ]
    )

    result = calculate_material_input_cost(
        "BMP:1xC-2xH=>200xPE",
        recipe_inputs,
        market_prices,
        exchange="AI1",
    )

    assert result == 200


def test_workforce_consumable_cost_converts_rates_to_total_cost():
    market_prices = pd.DataFrame(
        [
            {"Ticker": "DW", "Exchange": "AI1", "Ask_Price": 10, "Bid_Price": 8},
            {"Ticker": "RAT", "Exchange": "AI1", "Ask_Price": 20, "Bid_Price": 16},
        ]
    )
    workforce_needs = {
        "PIONEER": {
            "necessary": {"DW": 0.5},
            "luxury": {"RAT": 0.25},
        }
    }

    result = calculate_workforce_consumable_cost(
        "PIONEER",
        hours=2,
        workforce_amount=10,
        market_prices=market_prices,
        wf_consumables=workforce_needs,
        exchange="AI1",
    )

    assert result == pytest.approx(200)


def test_profit_and_roi_formulas_are_stable():
    profit_ask, profit_bid = calculate_profit(ask_price=125, bid_price=90, input_cost=100)
    roi_ask, roi_bid = calculate_roi(ask_price=125, bid_price=90, input_cost=100)

    assert profit_ask == 25
    assert profit_bid == -10
    assert roi_ask == 25
    assert roi_bid == -10


def test_zero_input_cost_roi_is_zero_not_infinite():
    roi_ask, roi_bid = calculate_roi(ask_price=125, bid_price=90, input_cost=0)

    assert roi_ask == 0
    assert roi_bid == 0


@pytest.mark.parametrize(
    ("profit_ask", "profit_bid", "traded_volume", "supply", "demand", "expected"),
    [
        (10, -1, 100, 1000, 200, "Highly Viable"),
        (10, -1, 0, 1000, 200, "Viable"),
        (10, -1, 0, 1000, 0, "Marginal"),
        (-1, -2, 100, 1000, 200, "Not Viable"),
    ],
)
def test_viability_categories(profit_ask, profit_bid, traded_volume, supply, demand, expected):
    assert calculate_viability(profit_ask, profit_bid, traded_volume, supply, demand) == expected
