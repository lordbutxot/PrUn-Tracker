import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CACHE_DIR = ROOT / "pu-tracker" / "cache"


PROCESSED_DATA_COLUMNS = [
    "Ticker",
    "Exchange",
    "Category",
    "Tier",
    "Ask_Price",
    "Bid_Price",
    "Supply",
    "Demand",
    "Traded Volume",
    "Saturation",
    "Input_Cost",
    "Profit per Unit",
    "ROI Ask %",
    "ROI Bid %",
    "Investment_Score",
    "Risk",
    "Viability",
    "Input Cost per Unit",
    "Input Cost per Stack",
    "Input Cost per Hour",
    "Recipe",
    "Building",
]

EXCHANGES = ["AI1", "CI1", "CI2", "NC1", "NC2", "IC1"]
MARKET_METRICS = ["Average", "AskAmt", "AskPrice", "AskAvail", "BidAmt", "BidPrice", "BidAvail"]


def read_csv_rows(path):
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def test_committed_cache_contains_core_reference_files():
    expected_files = [
        "materials.csv",
        "market_data.csv",
        "processed_data.csv",
        "recipe_inputs.csv",
        "recipe_outputs.csv",
        "recipes.json",
        "chains.json",
    ]

    missing = [name for name in expected_files if not (CACHE_DIR / name).exists()]

    assert missing == []


def test_processed_data_schema_is_stable():
    processed_path = CACHE_DIR / "processed_data.csv"

    with processed_path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.reader(handle)
        columns = next(reader)
        first_row = next(reader)

    assert columns == PROCESSED_DATA_COLUMNS
    assert len(first_row) == len(PROCESSED_DATA_COLUMNS)


def test_market_data_has_all_exchange_columns():
    market_path = CACHE_DIR / "market_data.csv"

    with market_path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.reader(handle)
        columns = next(reader)

    expected_columns = ["Ticker", "MMBuy", "MMSell"]
    expected_columns.extend(f"{exchange}-{metric}" for exchange in EXCHANGES for metric in MARKET_METRICS)

    assert columns == expected_columns


def test_recipe_inputs_and_outputs_have_matching_recipe_keys():
    input_rows = read_csv_rows(CACHE_DIR / "recipe_inputs.csv")
    output_rows = read_csv_rows(CACHE_DIR / "recipe_outputs.csv")

    input_keys = {row["Key"] for row in input_rows}
    output_keys = {row["Key"] for row in output_rows}

    assert input_keys
    assert output_keys
    assert input_keys <= output_keys


def test_processed_recipes_are_known_recipe_outputs():
    processed_rows = read_csv_rows(CACHE_DIR / "processed_data.csv")
    output_rows = read_csv_rows(CACHE_DIR / "recipe_outputs.csv")
    output_keys = {row["Key"] for row in output_rows}

    unknown_recipes = {
        row["Recipe"]
        for row in processed_rows
        if row["Recipe"] and row["Recipe"] != "N/A" and row["Recipe"] not in output_keys
    }

    assert unknown_recipes == set()


def test_recipe_json_contains_valid_recipe_records():
    recipes_path = CACHE_DIR / "recipes.json"

    with recipes_path.open(encoding="utf-8") as handle:
        recipes = json.load(handle)

    assert isinstance(recipes, dict)
    assert recipes
    assert all("=>" in recipe_key for recipe_key in recipes)


def test_recipe_inputs_can_measure_downstream_criticality():
    input_rows = read_csv_rows(CACHE_DIR / "recipe_inputs.csv")
    use_counts = {}

    for row in input_rows:
        use_counts.setdefault(row["Material"], set()).add(row["Key"])

    counts = {ticker: len(recipe_keys) for ticker, recipe_keys in use_counts.items()}

    assert counts
    assert max(counts.values()) > 1


def test_enhanced_analysis_schema_includes_logistics_metrics():
    import sys

    historical_data_dir = ROOT / "pu-tracker" / "historical_data"
    sys.path.insert(0, str(historical_data_dir))

    from config import ENHANCED_ANALYSIS_COLUMNS

    assert "Profit per m3" in ENHANCED_ANALYSIS_COLUMNS
    assert "Downstream Uses" in ENHANCED_ANALYSIS_COLUMNS
