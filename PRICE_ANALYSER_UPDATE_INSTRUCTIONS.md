# Price Analyser Data Update Instructions

## Problem
The current "Price Analyser Data" sheet doesn't have all the columns needed for the comprehensive cost breakdown (Ask/Bid workforce costs, separate input costs, etc.).

## Solution

### Option 1: Calculate Workforce Costs in Python (RECOMMENDED)

Update `generate_report_tabs.py` to include workforce cost calculations:

```python
def create_price_analyser_tab(sheets_manager, all_df):
    # Filter clean data
    clean_df = all_df.dropna(subset=['Ticker', 'Exchange']).copy()
    
    # Load workforce cost data if available
    cache_dir = Path('pu-tracker/cache')
    workforceneeds_file = cache_dir / "workforceneeds.json"
    workforce_needs = {}
    if workforceneeds_file.exists():
        with open(workforceneeds_file, 'r') as f:
            workforce_needs = json.load(f)
    
    # Calculate workforce costs for each row
    def calculate_workforce_cost(row, price_type='ask'):
        """Calculate workforce consumables cost at ask or bid prices"""
        # This would need to query market prices for workforce items
        # For now, estimate as 10% of input cost
        input_cost = row.get('Input Cost per Unit', 0)
        return input_cost * 0.10  # Placeholder - needs real calculation
    
    clean_df['Workforce Cost Ask'] = clean_df.apply(lambda r: calculate_workforce_cost(r, 'ask'), axis=1)
    clean_df['Workforce Cost Bid'] = clean_df.apply(lambda r: calculate_workforce_cost(r, 'bid'), axis=1)
    
    # Create reference data with ALL needed columns
    reference_df = clean_df[['Ticker', 'Material Name', 'Exchange', 
                           'Ask_Price', 'Bid_Price', 
                           'Input Cost per Unit',  # This is at average price
                           'Workforce Cost Ask', 'Workforce Cost Bid',
                           'Amount per Recipe',
                           'Supply', 'Demand']].copy()
    
    # Add lookup key
    reference_df.insert(0, 'LookupKey', reference_df['Ticker'].astype(str) + reference_df['Exchange'].astype(str))
    
    # Upload to Google Sheets
    sheets_manager.upload_dataframe_to_sheet("Price Analyser Data", reference_df)
```

### Option 2: Use Estimates in AppsScript (CURRENT SOLUTION)

Since we don't have separate Ask/Bid columns for input costs and workforce costs, I've updated the AppsScript to:

1. **Use the same Input Cost per Unit** for both Ask and Bid scenarios
2. **Estimate workforce costs** as 10-15% of input costs
3. **Calculate all 4 profitability scenarios** based on these estimates

The calculations now work like this:
- `inputCostAsk = inputCostBid = Input Cost per Unit` (from column G)
- `workforceCostAsk = inputCostAsk * 0.10` (10% estimate)
- `workforceCostBid = inputCostBid * 0.10` (10% estimate)
- Then all 4 profit scenarios are calculated properly

## Column Mapping in "Price Analyser Data" Sheet

Current structure:
- **Column A**: LookupKey (Ticker + Exchange, e.g., "AARCI1")
- **Column B**: Ticker (e.g., "AAR")
- **Column C**: Material Name
- **Column D**: Exchange (e.g., "CI1")
- **Column E**: Ask_Price
- **Column F**: Bid_Price
- **Column G**: Input Cost per Unit
- **Column H**: Input Cost per Stack
- **Column I**: Amount per Recipe
- **Column J**: Supply
- **Column K**: Demand

## Next Steps

### To get accurate workforce costs:

1. **Add workforce cost calculation** to your Python pipeline (`data_analyzer.py`)
2. **Export separate columns** for:
   - Input Cost (Ask Prices) - cost if buying all inputs at Ask
   - Input Cost (Bid Prices) - cost if buying all inputs at Bid
   - Workforce Cost (Ask Prices) - workforce consumables at Ask
   - Workforce Cost (Bid Prices) - workforce consumables at Bid
   
3. **Update generate_report_tabs.py** to include these columns in the "Price Analyser Data" sheet

4. **Update AppsScript** column indices to match the new structure

### For now:

The current implementation uses reasonable estimates and provides all the analysis views you requested. The percentages and calculations are mathematically correct, they just use estimated workforce costs instead of precise market-based costs.

## Testing

After deploying the updated AppsScript:
1. Select a material (e.g., "AAR")
2. Select an exchange (e.g., "CI1")
3. Verify all sections populate with data
4. Check that the 4 profit scenarios show different values
5. Verify breakeven calculations make sense

