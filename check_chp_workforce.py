import csv
import json

# Check buildingrecipes.csv for CHP recipes
print('=== CHP Recipes in buildingrecipes.csv ===')
with open('buildingrecipes.csv', 'r') as f:
    reader = csv.DictReader(f)
    chp_recipes = []
    for row in reader:
        if 'CHP' in row.get('Key', ''):
            chp_recipes.append(row)
            print(f"Recipe: {row.get('Key', 'N/A')}")
            print(f"  Building: {row.get('Building', 'N/A')}")
            print(f"  Workforce: {row.get('Workforce', 'N/A')}")
            print(f"  WorkforceAmount: {row.get('WorkforceAmount', 'N/A')}")
            print(f"  Time: {row.get('Time', 'N/A')}")
            print()

print(f'Total CHP recipes found: {len(chp_recipes)}')
print()

# Check workforceneeds.json for CHP workforce requirements
print('=== Workforce Requirements ===')
with open('workforceneeds.json', 'r') as f:
    workforceneeds = json.load(f)

print('workforceneeds type:', type(workforceneeds))

if isinstance(workforceneeds, dict):
    print('Available workforce types:')
    for wf_type in workforceneeds.keys():
        print(f'  {wf_type}')
    
    print()
    print('CHP workforce requirements:')
    if 'CHP' in workforceneeds:
        print(json.dumps(workforceneeds['CHP'], indent=2))
    else:
        print('CHP not found in workforceneeds.json')
    
    # Check if there are any workforce types that might be related to CHP
    print()
    print('Checking for similar workforce types:')
    for wf_type in workforceneeds.keys():
        if 'CHEM' in wf_type.upper() or 'CHP' in wf_type.upper():
            print(f'Found related type: {wf_type}')
            print(json.dumps(workforceneeds[wf_type], indent=2))
            print()
elif isinstance(workforceneeds, list):
    print('workforceneeds is a list with', len(workforceneeds), 'entries')
    print('First few entries:')
    for i, entry in enumerate(workforceneeds[:5]):
        print(f'  {i}: {entry}')
        
    # Look for CHP in the list
    chp_entries = [entry for entry in workforceneeds if isinstance(entry, dict) and 'CHP' in str(entry)]
    print(f'CHP-related entries found: {len(chp_entries)}')
    for entry in chp_entries:
        print(json.dumps(entry, indent=2))
else:
    print('workforceneeds is neither dict nor list, type:', type(workforceneeds))