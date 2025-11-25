# Changelog

All notable changes to PrUn-Tracker will be documented in this file.

## [Recent Updates] - November 25, 2025

### 🧹 Code Cleanup
- **Removed Unused Test Files**: Deleted `tests/` directory containing unused unit tests
- **Removed Development Scripts**: Deleted test scripts from `cache/` directory:
  - `test_multi_dimensional.py`
  - `test_multi_output_integration.py` 
  - `test_multi_workforce_costs.py`
- **Removed Commented Script**: Deleted `# remove_emojis.py` utility script

### 📊 UI/UX Enhancements

#### ROI Badges & Color Coding
- **💎 Best ROI Badge**: Automatically highlights the most profitable recipe option
- **Visual Color Coding**:
  - 🟢 Green: Better than selected option (higher ROI)
  - 🔴 Red: Worse than selected option (lower ROI)  
  - 🔵 Blue: Currently selected option
- **Mobile Responsive**: Badges stack vertically on smaller screens for better readability
- **Sorting**: Building comparison recipes now sorted by ROI (descending) instead of profit

#### Timestamp Display
- **Last Update Indicator**: Shows when data was last refreshed
- **Human-Readable Format**: Displays "X minutes/hours ago" with full timestamp
- **UTC Timezone Support**: Consistent timestamps across different server/client timezones
- **Format**: `📊 Data last updated: 5m ago (24/11/2025, 14:30:45 local time)`

### 📊 Enhanced Market Data

#### Traded Volume Integration
- **Market Indicators Section**: Now displays Supply, Demand, AND Traded Volume
- **Building Comparison**: Shows traded volume for each alternative recipe
- **Exchange Comparison**: Includes traded volume across all exchanges
- **Data Pipeline Fix**: Corrected column name from 'Traded' to 'Traded Volume' in data upload

### 🌍 Planet-Based Features

#### Extraction Building Optimization
- **Planet-Specific Alternatives**: When selecting an extraction building (EXT/RIG/COL), the building comparison now shows only materials available on the selected planet
- **Intelligent Filtering**: Uses Planet Resources data to filter viable extraction options
- **Recipe Format Support**: Handles both `BMP:inputs=>outputs` and `EXT=>outputs` formats

#### Corrected Fertility Calculations
- **Official Formula**: Implemented PCT (Prosperous Universe Community Tools) formula
  ```
  Fertility Modifier = RawFertility × (10/33)
  Efficiency = 100% + (Fertility Modifier × 100%)
  ```
- **Example**: ZV-759c with -0.34 raw fertility:
  - Previous (incorrect): 66% efficiency
  - Current (correct): 89.7% efficiency
- **Fertility-Only Planets**: Added planets like Demeter that only have fertility data (no extraction resources)

### 🐛 Bug Fixes

#### Recipe Parsing
- **Materials with Numbers**: Fixed regex to handle H2O, O2, CO2, etc.
- **Changed Pattern**: From `[A-Z]+` to `[A-Z0-9]+` in recipe input/output parsing
- **Example Fix**: Now correctly shows "40 H2O" instead of "40 H"

#### Building Comparison Persistence
- **Hide Logic**: Building comparison section now properly hides when switching to materials with only one recipe
- **Cleanup**: Added else clauses to reset comparison display when not applicable

#### Report Deduplication
- **TOP MATERIALS TO INVEST IN**: Now shows unique materials only (deduplicated by Ticker)
- **Implementation**: `drop_duplicates(subset=['Ticker'], keep='first')` before limiting to top N
- **Result**: No more repeated materials in investment recommendations

### 🔧 Technical Improvements

#### Data Pipeline
- **Metadata Sheet**: New sheet containing Last Data Update timestamp
- **ISO Format Timestamps**: Using `datetime.now(timezone.utc).isoformat()` for consistent timezone handling
- **Fertility Data Upload**: `upload_planet_resources.py` now includes fertility-only planets

#### Frontend Enhancements
- **Client-Side Caching**: All data loaded once with `getAllData()` to reduce API calls
- **Efficient Filtering**: Planet-based material filtering done client-side for instant response
- **Responsive CSS**: Badge stacking with `flex-direction: column` on mobile devices

## [Previous Features]

### Core Functionality
- Multi-recipe comparison with 4 ROI scenarios (Ask/Ask, Ask/Bid, Bid/Ask, Bid/Bid)
- Exchange comparison across AI1, CI1, CI2, IC1, NC1, NC2
- Arbitrage opportunity detection
- Building comparison for alternative outputs
- Cost calculation options (Luxury consumables, Self-produced inputs)
- Planet concentration factors for extraction buildings
- Company HQ and Corp HQ bonuses
- CoGC program and Expert efficiency bonuses

### Data Infrastructure
- Automated data fetching from FIO API
- Google Sheets integration with SheetsManager
- Workforce cost calculations with real market prices
- Planet Resources sheet with concentration and fertility data
- Historical data tracking and analysis

---

## Breaking Changes

None in recent updates. All changes are backwards compatible.

## Migration Notes

If you're updating from an older version:

1. **Run the Pipeline**: Execute `generate_report_tabs.py` to create the new Metadata sheet
2. **Refresh Sheets**: The Metadata sheet will be automatically created on first run
3. **Update Apps Script**: Deploy the latest `AppsScript_Index.html` and `AppsScript_PriceAnalyser.js`
4. **Clear Cache**: Browser cache may need clearing to see CSS changes for badges

## Known Issues

None currently reported.

## Roadmap

Future enhancements under consideration:
- Historical price trending charts
- Profit margin alerts and notifications
- Recipe cost breakdown visualizations
- Advanced filtering and search capabilities
- Export to CSV/PDF functionality
