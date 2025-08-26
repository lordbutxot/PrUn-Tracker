import requests
import os

def main():
    """Main function to fetch materials data."""
    url = "https://rest.fnar.net/csv/materials"
    response = requests.get(url)
    response.raise_for_status()

    cache_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'cache'))
    os.makedirs(cache_dir, exist_ok=True)
    output_path = os.path.join(cache_dir, "materials.csv")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(response.text)

    print(f"Downloaded materials.csv to {output_path}")

if __name__ == "__main__":
    main()