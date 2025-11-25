import csv

# Check the Building column in buildingrecipes.csv for CHP recipes
with open('buildingrecipes.csv', 'r') as f:
    reader = csv.DictReader(f)
    count = 0
    for row in reader:
        if 'CHP' in row.get('Key', ''):
            building = row.get('Building', 'N/A')
            workforce = row.get('Workforce', 'N/A')
            workforce_amount = row.get('WorkforceAmount', 'N/A')
            print(f"Recipe: {row.get('Key', 'N/A')}")
            print(f"  Building: {building}")
            print(f"  Workforce: {workforce}")
            print(f"  WorkforceAmount: {workforce_amount}")
            print()
            count += 1
            if count >= 3:  # Just show first few
                break