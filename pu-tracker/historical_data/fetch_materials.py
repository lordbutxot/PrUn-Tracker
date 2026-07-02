import csv
import json
import os
from io import StringIO


MATERIALS_URL = "https://rest.fnar.net/csv/materials"


def _to_float(value, default=0.0):
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def build_material_catalog(csv_text):
    """Build stable material metadata sidecars from the raw materials CSV."""
    reader = csv.DictReader(StringIO(csv_text))
    catalog = {}
    volume_rows = []

    for row in reader:
        ticker = str(row.get("Ticker", "")).strip().upper()
        if not ticker:
            continue

        name = str(row.get("Name", "")).strip()
        category = str(row.get("Category", "")).strip()
        weight = _to_float(row.get("Weight"))
        volume = _to_float(row.get("Volume"))
        tier = _to_float(row.get("Tier"))

        catalog[ticker] = {
            "ticker": ticker,
            "name": name,
            "category": category,
            "weight": weight,
            "volume": volume,
            "volume_per_unit": volume,
            "tier": tier,
        }
        volume_rows.append({
            "Ticker": ticker,
            "Material Name": name,
            "Volume per Unit": volume,
        })

    volume_rows.sort(key=lambda item: item["Ticker"])
    return catalog, volume_rows


def write_material_sidecars(cache_dir, csv_text):
    catalog, volume_rows = build_material_catalog(csv_text)

    materials_json_path = os.path.join(cache_dir, "materials.json")
    with open(materials_json_path, "w", encoding="utf-8") as handle:
        json.dump(catalog, handle, indent=2, sort_keys=True)

    volume_csv_path = os.path.join(cache_dir, "material_volumes.csv")
    with open(volume_csv_path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["Ticker", "Material Name", "Volume per Unit"])
        writer.writeheader()
        writer.writerows(volume_rows)

    print(f"Generated materials.json with {len(catalog)} entries")
    print(f"Generated material_volumes.csv with {len(volume_rows)} rows")


def main():
    """Fetch materials.csv and build persistent material metadata sidecars."""
    import requests

    response = requests.get(MATERIALS_URL, timeout=30)
    response.raise_for_status()

    cache_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "cache"))
    os.makedirs(cache_dir, exist_ok=True)

    output_path = os.path.join(cache_dir, "materials.csv")
    with open(output_path, "w", encoding="utf-8") as handle:
        handle.write(response.text)

    write_material_sidecars(cache_dir, response.text)
    print(f"Downloaded materials.csv to {output_path}")


if __name__ == "__main__":
    main()
