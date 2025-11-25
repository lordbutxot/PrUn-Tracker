import sys
import os
import json

# Simple test to check if workforce requirements are loaded correctly
cache_dir = os.path.join(os.path.dirname(__file__), 'pu-tracker', 'cache')

# Load buildings.json
buildings_path = os.path.join(cache_dir, 'buildings.json')
with open(buildings_path, 'r') as f:
    buildings = json.load(f)

print("=== CHP Building Requirements ===")
if 'CHP' in buildings:
    chp_data = buildings['CHP']
    print(f"CHP building data: {json.dumps(chp_data, indent=2)}")

    # Check workforce requirements
    workforce_reqs = {}
    for wf_type in ['PIONEER', 'SETTLER', 'TECHNICIAN', 'ENGINEER', 'SCIENTIST']:
        wf_key = wf_type.lower() + 's'
        amount = chp_data.get(wf_key, 0)
        if amount > 0:
            workforce_reqs[wf_type] = amount

    print(f"Extracted workforce requirements: {workforce_reqs}")
else:
    print("CHP not found in buildings.json")

# Load workforceneeds.json
workforceneeds_path = os.path.join(cache_dir, 'workforceneeds.json')
with open(workforceneeds_path, 'r') as f:
    workforceneeds_raw = json.load(f)

print("\n=== Workforce Needs Structure ===")
print(f"workforceneeds type: {type(workforceneeds_raw)}")
if isinstance(workforceneeds_raw, list) and len(workforceneeds_raw) > 0:
    print(f"First entry: {workforceneeds_raw[0]}")

# Test the new workforce requirements extraction logic
def get_workforce_requirements(building_ticker):
    """Extract all workforce types and amounts from buildings.json"""
    requirements = {}
    if building_ticker in buildings:
        building = buildings[building_ticker]
        for wf_type in ['PIONEER', 'SETTLER', 'TECHNICIAN', 'ENGINEER', 'SCIENTIST']:
            wf_key = wf_type.lower() + 's'  # pioneers, settlers, etc.
            amount = building.get(wf_key, 0)
            if amount > 0:
                requirements[wf_type] = amount
    return requirements

print("\n=== Testing New Logic ===")
chp_reqs = get_workforce_requirements('CHP')
print(f"CHP workforce requirements: {chp_reqs}")

# Test old logic for comparison
def get_workforce_info_old(building_ticker):
    """Old logic - returns only first workforce type"""
    if building_ticker in buildings:
        building = buildings[building_ticker]
        for wf_type in ['PIONEER', 'SETTLER', 'TECHNICIAN', 'ENGINEER', 'SCIENTIST']:
            wf_key = wf_type.lower() + 's'
            amount = building.get(wf_key, 0)
            if amount > 0:
                return wf_type, amount
    return None, 0

old_type, old_amount = get_workforce_info_old('CHP')
print(f"Old logic result: {old_type}, {old_amount}")
print(f"New logic result: {chp_reqs}")