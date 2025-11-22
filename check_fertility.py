import requests
import pandas as pd

# Check planets endpoint
print("=" * 60)
print("Checking: https://rest.fnar.net/csv/planets")
print("=" * 60)
try:
    response = requests.get("https://rest.fnar.net/csv/planets", timeout=10)
    if response.status_code == 200:
        lines = response.text.split('\n')[:5]
        for line in lines:
            print(line)
    else:
        print(f"Status: {response.status_code}")
except Exception as e:
    print(f"Error: {e}")

print("\n")

# Check planetdetail endpoint
print("=" * 60)
print("Checking: https://rest.fnar.net/csv/planetdetail")
print("=" * 60)
try:
    response = requests.get("https://rest.fnar.net/csv/planetdetail", timeout=10)
    if response.status_code == 200:
        lines = response.text.split('\n')[:5]
        for line in lines:
            print(line)
    else:
        print(f"Status: {response.status_code}")
except Exception as e:
    print(f"Error: {e}")

print("\n")

# Check planetresources (current data we have)
print("=" * 60)
print("Checking: https://rest.fnar.net/csv/planetresources")
print("=" * 60)
try:
    response = requests.get("https://rest.fnar.net/csv/planetresources", timeout=10)
    if response.status_code == 200:
        lines = response.text.split('\n')[:5]
        for line in lines:
            print(line)
    else:
        print(f"Status: {response.status_code}")
except Exception as e:
    print(f"Error: {e}")
