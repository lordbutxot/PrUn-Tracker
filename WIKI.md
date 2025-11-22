# PrUn-Tracker Complete Documentation

**Version:** 2.0  
**Last Updated:** November 2025  
**Game:** [Prosperous Universe](https://prosperousuniverse.com/)

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Core Features](#core-features)
3. [Architecture & Data Flow](#architecture--data-flow)
4. [Calculation Systems](#calculation-systems)
5. [Price Analyser Web App](#price-analyser-web-app)
6. [Data Pipeline](#data-pipeline)
7. [Google Sheets Integration](#google-sheets-integration)
8. [GitHub Actions Automation](#github-actions-automation)
9. [Installation & Setup](#installation--setup)
10. [Usage Guide](#usage-guide)
11. [Advanced Features](#advanced-features)
12. [Troubleshooting](#troubleshooting)

---

## Project Overview

**PrUn-Tracker** is an advanced, modular data pipeline and analytics suite for Prosperous Universe that automates the entire workflow of collecting, processing, analyzing, and reporting in-game economic and production data.

### What Makes PrUn-Tracker Unique

- **True Cost Calculation:** Calculates complete production costs including workforce consumables (RAT, DW, OVE, etc.) based on market prices
- **Planet-Specific Optimization:** Factors in extraction concentration and farming fertility for accurate location-based profitability
- **Efficiency Modeling:** Full efficiency system including worker luxury, CoGC programs, experts, and planet bonuses
- **Real-Time Market Data:** Automated fetching from Prosperous Universe FIO API
- **Web-Based Interface:** Interactive Price Analyser tool with recipe selection and profit calculations
- **Automated Deployment:** GitHub Actions pipeline runs every 2 hours to update data

---

## Core Features

### Data Collection & Processing
- ✅ **Automated API Fetching:** Market prices, building recipes, materials, planet resources, fertility data
- ✅ **Smart Caching:** Minimizes API calls, only refetches when data changes
- ✅ **Rate Limiting:** Respects API rate limits with intelligent backoff
- ✅ **Data Validation:** Ensures data integrity with comprehensive error handling
- ✅ **Historical Tracking:** Maintains historical data for trend analysis

### Economic Analysis
- ✅ **Profit Calculations:** Ask/Bid pricing with ROI percentages
- ✅ **Arbitrage Detection:** Cross-exchange opportunities with transfer cost modeling
- ✅ **Market Metrics:** Supply, Demand, Traded Volume, Market Cap, Liquidity Ratio
- ✅ **Investment Scoring:** Proprietary algorithm ranking production opportunities
- ✅ **Breakeven Analysis:** Units needed to recover setup costs

### Production Optimization
- ✅ **Multi-Recipe Support:** Compare all production methods for a material
- ✅ **Workforce Cost Modeling:** Complete consumable costs per recipe
- ✅ **Self-Production Costing:** Recursive cost calculation for vertically integrated production
- ✅ **Planet-Specific Calculations:** Extraction concentration and farming fertility factors
- ✅ **Building Type Support:** Manufacturing (CHP, WEL, etc.), Extraction (COL, EXT, RIG), Farming (FRM, ORC, VIN)

### Efficiency Systems
- ✅ **Worker Efficiency:** Luxury (100%) vs Essential-only (79%) consumables
- ✅ **Custom Efficiency:** Manual percentage override (1-100%)
- ✅ **CoGC Programs:** +25% efficiency bonus
- ✅ **Expert Bonuses:** 1-5 experts with cumulative synergy (3.06% to 28.40%)
- ✅ **Planet Bonuses:** Concentration and fertility add directly to total efficiency
- ✅ **Additive System:** All bonuses stack additively for maximum benefit

---

## Architecture & Data Flow

### Pipeline Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    GitHub Actions (Every 2 hours)                │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Step 1: Fetch Raw Data (catch_data.py)        │
│  - Market prices (market_data.csv)                              │
│  - Building recipes (buildingrecipes.csv)                       │
│  - Materials & tiers (materials.csv)                            │
│  - Planet resources (planetresources.csv)                       │
│  - Planet fertility (planet_fertility.csv)                      │
│  - Workforce needs (workforceneeds.json)                        │
│  - Orders & Bids (orders.csv, bids.csv)                         │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│              Step 2: Process Data (unified_processor.py)        │
│  - Merge market prices with recipes                             │
│  - Calculate workforce costs (workforce_costs.py)               │
│  - Compute input costs from recipe components                   │
│  - Generate processed_data.csv                                  │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│           Step 3: Enhanced Analysis (data_analyzer.py)          │
│  - ROI calculations (Ask/Ask, Ask/Bid, Bid/Ask, Bid/Bid)       │
│  - Market metrics (Market Cap, Liquidity Ratio)                 │
│  - Investment scoring                                            │
│  - Arbitrage detection                                           │
│  - Generate daily_analysis_enhanced.csv                         │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│       Step 4: Upload to Google Sheets (sheets_manager.py)       │
│  - DATA AI1/CI1/CI2/IC1/NC1/NC2 tabs                           │
│  - Planet Resources tab (with Fertility column)                 │
│  - Report tabs with enhanced analytics                          │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│         Step 5: Serve Web App (Google Apps Script)              │
│  - AppsScript_PriceAnalyser.js (Backend API)                   │
│  - AppsScript_Index.html (Frontend UI)                         │
│  - Interactive calculations with user preferences               │
└─────────────────────────────────────────────────────────────────┘
```

### File Structure

```
PrUn-Tracker/
├── pu-tracker/
│   ├── cache/                          # Cached CSV/JSON data
│   │   ├── market_data.csv             # Market prices (Ask/Bid)
│   │   ├── buildingrecipes.csv         # Recipe definitions with durations
│   │   ├── materials.csv               # Material tickers and categories
│   │   ├── planetresources.csv         # Planet extraction factors
│   │   ├── planet_fertility.csv        # Farming fertility (28 planets)
│   │   ├── workforceneeds.json         # Worker type consumables
│   │   ├── processed_data.csv          # Merged production data
│   │   └── daily_analysis_enhanced.csv # Final analysis for upload
│   │
│   ├── historical_data/                # Python pipeline scripts
│   │   ├── main.py                     # Pipeline orchestrator
│   │   ├── catch_data.py               # API data fetcher
│   │   ├── unified_processor.py        # Data merger & processor
│   │   ├── data_analyzer.py            # Advanced analytics
│   │   ├── workforce_costs.py          # Workforce cost calculator
│   │   ├── sheets_manager.py           # Google Sheets uploader
│   │   ├── upload_planet_resources.py  # Planet Resources uploader
│   │   ├── fetch_planet_fertility.py   # Fertility data fetcher
│   │   └── generate_report_tabs.py     # Report tab generator
│   │
│   └── logs/                           # Execution logs
│
├── AppsScript_PriceAnalyser.js        # Backend: Data loading API
├── AppsScript_Index.html               # Frontend: Web UI
├── .github/workflows/
│   └── update-tracker.yml              # GitHub Actions config
├── requirements.txt                    # Python dependencies
└── WIKI.md                            # This file
```

---

## Calculation Systems

### 1. Workforce Cost Calculation

**Formula:**
```
Workforce Cost = Sum of (Worker Type Consumable Prices × Hours × Efficiency Factor)
```

**Process:**
1. **Identify Recipe:** Parse building recipe (e.g., `CHP:1xC-1xH2O=>1xBAC`)
2. **Extract Duration:** Get production time from `buildingrecipes.csv` (seconds → hours)
3. **Lookup Workforce:** Map building to worker type (e.g., CHP → Technician)
4. **Get Consumables:** Retrieve consumable list from `workforceneeds.json`
   - Essential: DW, RAT, OVE (always required)
   - Luxury: PWO, COF, etc. (optional, for 100% efficiency)
5. **Fetch Prices:** Get current market Ask/Bid prices for each consumable
6. **Calculate Cost:**
   ```
   For each consumable:
     ConsumableUnits = Consumable_Per_Day × (Hours / 24)
     ConsumableCost = ConsumableUnits × Market_Price
   
   Total_Workforce_Cost = Sum(ConsumableCost for all consumables)
   ```

**Example: CHP producing BAC**
- Building: CHP
- Recipe: `CHP:1xC-1xH2O=>1xBAC`
- Duration: 8 hours
- Worker: Technician
- Consumables (per day): 2 DW, 1 RAT, 1 OVE, 1 PWO, 1 COF
- Prices (Ask): DW=10, RAT=15, OVE=8, PWO=12, COF=5
- Calculation (8h = 0.333 days):
  ```
  DW:  2 × 0.333 × 10 = 6.67 ICA
  RAT: 1 × 0.333 × 15 = 5.00 ICA
  OVE: 1 × 0.333 × 8  = 2.67 ICA
  PWO: 1 × 0.333 × 12 = 4.00 ICA
  COF: 1 × 0.333 × 5  = 1.67 ICA
  ──────────────────────────────
  Total: 20.00 ICA
  ```

### 2. Total Production Cost

**Formula:**
```
Total Cost = Input Material Costs + Workforce Costs
```

**Components:**

**Input Costs:**
- Parse recipe inputs (e.g., `1xC-1xH2O` means 1 Carbon + 1 Water)
- Lookup current market prices (Ask or Bid)
- Sum: `InputCost = (1 × C_Price) + (1 × H2O_Price)`

**Total:**
```
Total_Cost_Ask = Input_Cost_Ask + Workforce_Cost_Ask
Total_Cost_Bid = Input_Cost_Bid + Workforce_Cost_Bid
```

**Self-Production Mode:**
- If enabled, recursively calculate input costs using their production recipes
- Prevents circular dependencies with visited set
- Falls back to market price if circular reference detected

### 3. Efficiency System (Additive)

**Formula:**
```
Total Efficiency = Base Worker Efficiency 
                 + Planet Factor Bonus
                 + CoGC Program Bonus
                 + Expert Bonus

Effective Cost = Base Cost × (1 / Total Efficiency)
```

**Components:**

**Base Worker Efficiency:**
- **With Luxury** (100%): All consumables provided → `1.0`
- **Essential Only** (79%): Only DW, RAT, OVE → `0.79`
- **Custom**: User-defined percentage (1-100%) → `custom / 100`

**Planet Factor Bonus:**
- **Extraction:** Concentration factor minus 1.0
  - Example: 2.0 concentration → `+1.0` (100% bonus)
  - Example: 0.5 concentration → `-0.5` (50% penalty)
- **Farming:** Fertility value directly
  - Example: 0.4 fertility → `+0.40` (40% bonus)
  - Example: -0.5 fertility → `-0.50` (50% penalty)

**CoGC Program Bonus:**
- **Enabled:** `+0.25` (25% bonus)
- **Disabled:** `0`

**Expert Bonus (Verified Game Values):**
| Experts | Bonus   |
|---------|---------|
| 0       | 0%      |
| 1       | 3.06%   |
| 2       | 6.96%   |
| 3       | 12.48%  |
| 4       | 19.74%  |
| 5       | 28.40%  |

**Example Calculation:**
```
Scenario: Farming GRN with all bonuses
- Base: 100% (luxury enabled)
- Fertility: +40% (0.4)
- CoGC: +25%
- 3 Experts: +12.48%
──────────────────────────────
Total Efficiency: 177.48%

Base Workforce Cost: 50 ICA
Effective Cost: 50 × (1 / 1.7748) = 28.16 ICA
Savings: 43.7%
```

### 4. Profit & ROI Calculations

**Four Scenarios:**

1. **Ask/Ask:** Sell at Ask price, buy inputs at Ask price
   ```
   Profit_AA = Ask_Price - (Input_Cost_Ask + Workforce_Cost_Ask)
   ROI_AA = (Profit_AA / Total_Cost_Ask) × 100%
   ```

2. **Ask/Bid:** Sell at Ask price, buy inputs at Bid price
   ```
   Profit_AB = Ask_Price - (Input_Cost_Bid + Workforce_Cost_Bid)
   ROI_AB = (Profit_AB / Total_Cost_Bid) × 100%
   ```

3. **Bid/Ask:** Sell at Bid price, buy inputs at Ask price
   ```
   Profit_BA = Bid_Price - (Input_Cost_Ask + Workforce_Cost_Ask)
   ROI_BA = (Profit_BA / Total_Cost_Ask) × 100%
   ```

4. **Bid/Bid:** Sell at Bid price, buy inputs at Bid price
   ```
   Profit_BB = Bid_Price - (Input_Cost_Bid + Workforce_Cost_Bid)
   ROI_BB = (Profit_BB / Total_Cost_Bid) × 100%
   ```

**Breakeven Units:**
```
For each scenario, calculate units needed to cover building construction cost:
Breakeven = Building_Cost / Profit_Per_Unit
```

### 5. Planet-Specific Adjustments

**Extraction (COL, EXT, RIG):**
- **Base Times:** COL=6h, EXT=12h, RIG=4.8h
- **Concentration Effect:** Adds to efficiency (additive, not divisor)
- **Formula:** `Total_Efficiency += (Concentration - 1.0)`
- **Example:** 
  - 2.0 concentration → Total efficiency +100%
  - 0.5 concentration → Total efficiency -50%

**Farming (FRM, ORC, VIN):**
- **Base Times:** Vary by recipe (12h-48h typical)
- **Fertility Effect:** Adds directly to efficiency
- **Formula:** `Total_Efficiency += Fertility`
- **28 Farmable Planets:** Only 0.8% of planets support farming
- **Negative Fertility:** Represents penalty (slower growth)
- **Example:**
  - 0.4 fertility → Total efficiency +40%
  - -0.5 fertility → Total efficiency -50%

### 6. Market Metrics

**Supply & Demand:**
- **Supply:** AskAvail (units available for sale)
- **Demand:** BidAvail (units wanted for purchase)
- **Traded Volume:** AskAmt (units sold in last period)

**Market Cap:**
```
Market_Cap = (Supply + Demand) × Current_Price
```

**Liquidity Ratio:**
```
Liquidity_Ratio = Traded_Volume / (Supply + Demand)
```
- High ratio (>0.5): Active, liquid market
- Low ratio (<0.1): Illiquid, risky market

**Investment Score:**
```
Investment_Score = (ROI × 10) + (Liquidity × 100) - (Risk_Factor × 20)
```
- Proprietary algorithm considering profitability, liquidity, and risk
- Higher score = better investment opportunity

---

## Price Analyser Web App

### Overview

Interactive web-based tool deployed as Google Apps Script web app, providing real-time profit calculations with user-customizable parameters.

### Features

#### Material & Recipe Selection
- **Material Dropdown:** All producible materials from market data
- **Recipe Dropdown:** Shows all production methods for selected material
  - Manufacturing recipes: `CHP:1xC-1xH2O=>1xBAC`
  - Extraction recipes: `COL=>1xFE`
  - Farming recipes: `FRM:1xH2O=>4xGRN`
- **Exchange Dropdown:** All active exchanges (AI1, CI1, CI2, IC1, NC1, NC2)

#### Planet Selection (Context-Aware)
- **Extraction Mode:** Shows when COL/EXT/RIG recipe selected
  - Displays planets with material concentration
  - Sorted by concentration (highest first)
  - Format: "Planet Name (X.XX concentration)"
- **Farming Mode:** Shows when FRM/ORC/VIN recipe selected
  - Displays 28 farmable planets with fertility
  - Sorted by fertility (highest first)
  - Format: "Planet Name (X.XX fertility)"
- **Hidden:** For manufacturing recipes (planet doesn't affect cost)

#### Cost Calculation Options

**Worker Efficiency:**
- ☑️ **Provide Luxury Consumables** (Default: ON)
  - ON: 100% efficiency, includes PWO, COF, etc.
  - OFF: 79% efficiency, only DW, RAT, OVE
- ⚙️ **Use Custom Workforce Efficiency** (Default: OFF)
  - Manual override: 1-100%
  - Useful for testing scenarios

**Self-Production:**
- ☑️ **Use Self-Production Costs for Inputs**
  - ON: Calculates input costs using their production recipes (recursive)
  - OFF: Uses market prices for inputs

**CoGC Program:**
- ☑️ **CoGC Program Active (+25% Efficiency)**
  - Adds 25% to total efficiency when enabled

**Experts:**
- 👨‍🔬 **Experts Assigned (Cumulative Bonus)**
  - Number input: 0-5 experts
  - Live display shows current bonus (e.g., "+12.48% efficiency (3 experts)")
  - Bonuses: 3.06%, 6.96%, 12.48%, 19.74%, 28.40%

#### Results Display

**Production Summary:**
- Material name and ticker
- Recipe details with inputs/outputs
- Selected exchange and planet (if applicable)

**Cost Breakdown:**
- Input Material Costs (Ask & Bid)
- Workforce Costs (Ask & Bid) - with efficiency applied
- Total Production Costs

**Profitability (4 Scenarios):**
- Ask/Ask: Sell Ask, Buy Ask
- Ask/Bid: Sell Ask, Buy Bid (Best case)
- Bid/Ask: Sell Bid, Buy Ask (Worst case)
- Bid/Bid: Sell Bid, Buy Bid

**For Each Scenario:**
- Profit per unit (ICA)
- ROI percentage
- Breakeven units needed

**Market Data:**
- Current Ask/Bid prices
- Supply available
- Demand wanted
- Traded volume

**Exchange Comparison:**
- All exchanges ranked by ROI
- Shows best exchange to produce/sell

**Arbitrage Opportunities:**
- Cross-exchange buy/sell opportunities
- Minimum 5% profit threshold after transfer costs

### User Workflow

1. **Select Material** → Recipes populate
2. **Select Recipe** → Planet selector appears (if extraction/farming)
3. **Select Exchange** → Prices load
4. **Select Planet** (optional) → Concentration/fertility applied
5. **Adjust Options:**
   - Toggle luxury consumables
   - Enable CoGC program
   - Add experts (0-5)
6. **Click Calculate** → Results display with all scenarios

### Technology Stack

- **Backend:** Google Apps Script (JavaScript)
  - `AppsScript_PriceAnalyser.js`: Server-side API
  - Reads from Google Sheets (DATA tabs, Planet Resources)
  - Returns JSON with all data
- **Frontend:** HTML + CSS + JavaScript
  - `AppsScript_Index.html`: Single-page app
  - Client-side calculations for instant feedback
  - Responsive design

---

## Data Pipeline

### Pipeline Execution

**Automated (GitHub Actions):**
```bash
# Runs every 2 hours via .github/workflows/update-tracker.yml
1. Checkout repository
2. Set up Python 3.13
3. Install dependencies (requirements.txt)
4. Create Google credentials from GitHub secret
5. Run main.py pipeline
6. Upload logs on failure
7. Clean up credentials
```

**Manual (Local):**
```bash
# Windows
cd pu-tracker/historical_data
python main.py

# Or use batch script
cd pu-tracker
run_pipeline.bat
```

### Pipeline Steps

**Step 1: Data Fetching (catch_data.py)**
- Fetches from FIO API endpoints
- Implements rate limiting and retry logic
- Saves raw CSV/JSON to `cache/`
- Creates cache metadata for change detection

**Step 2: Data Processing (unified_processor.py)**
- Merges market data with recipes
- Calculates workforce costs for each recipe
- Computes input material costs
- Generates `processed_data.csv`

**Step 3: Advanced Analysis (data_analyzer.py)**
- Calculates ROI for all scenarios
- Computes market metrics (Market Cap, Liquidity)
- Assigns investment scores
- Detects arbitrage opportunities
- Generates `daily_analysis_enhanced.csv`

**Step 4: Google Sheets Upload**
- **DATA Tabs:** `upload_enhanced_analysis.py`
  - AI1, CI1, CI2, IC1, NC1, NC2
  - Includes: Ticker, Recipe, Prices, Costs, ROI, Market Metrics
- **Planet Resources:** `upload_planet_resources.py`
  - Merges `planetresources.csv` + `planet_fertility.csv`
  - Columns: Key, Planet, Ticker, Type, Factor, Fertility
- **Report Tabs:** `generate_report_tabs.py`
  - Advanced analytics and summaries

### Data Sources (FIO API)

| Endpoint | Output File | Purpose |
|----------|-------------|---------|
| `/csv/planetdetail` | `planet_fertility.csv` | Farming fertility data |
| `/csv/planetresources` | `planetresources.csv` | Extraction concentration |
| `/csv/buildings` | `buildings.json` | Building types & workforce |
| `/csv/buildingrecipes` | `buildingrecipes.csv` | Recipe durations |
| `/csv/materials` | `materials.csv` | Material tickers & tiers |
| `/csv/workforceneeds` | `workforceneeds.json` | Worker consumables |
| `/exchange/all` | `market_data.csv` | Market prices (Ask/Bid) |
| `/exchange/orders` | `orders.csv` | Buy orders |
| `/exchange/shipping/sources` | `bids.csv` | Shipping bids |

### Cache System

**Smart Caching:**
- Detects data changes using hash comparison
- Only refetches when upstream data changes
- Stores metadata in `cache_metadata.json`
- Reduces API load and improves performance

**Cache Files:**
```
cache/
├── market_data.csv              # Current market prices
├── buildingrecipes.csv          # Recipe definitions
├── materials.csv                # Material metadata
├── planetresources.csv          # Extraction factors
├── planet_fertility.csv         # Farming fertility (28 planets)
├── workforceneeds.json          # Worker consumables
├── processed_data.csv           # Merged production data
├── daily_analysis_enhanced.csv  # Final analysis
└── cache_metadata.json          # Change tracking
```

---

## Google Sheets Integration

### Spreadsheet Structure

**Main Spreadsheet ID:** `1-9vXBU43YjU6LMdivpVwL2ysLHANShHzrCW6MmmGvoI`

**Sheet Tabs:**

**DATA Tabs (One per exchange):**
- DATA AI1, DATA CI1, DATA CI2, DATA IC1, DATA NC1, DATA NC2
- **Columns:**
  - Ticker (Material)
  - Recipe
  - Exchange
  - Ask Price, Bid Price
  - Input Cost (Ask), Input Cost (Bid)
  - Workforce Cost (Ask), Workforce Cost (Bid)
  - Total Cost (Ask), Total Cost (Bid)
  - Profit (AA, AB, BA, BB)
  - ROI % (AA, AB, BA, BB)
  - Breakeven Units (AA, AB, BA, BB)
  - Supply, Demand, Traded Volume
  - Market Cap, Liquidity Ratio
  - Investment Score

**Planet Resources Tab:**
- **Columns:**
  - Key (Planet-Material pair, e.g., "AJ-768a-H2O")
  - Planet
  - Ticker (Material)
  - Type (LIQUID, GASEOUS, MINERAL)
  - Factor (Extraction concentration)
  - Fertility (Farming fertility, -0.7 to +0.4)

**Report Tabs:**
- Enhanced analytics and summaries
- Generated by `generate_report_tabs.py`

### Upload Process

**Rate Limiting:**
- 1.5 second delay between operations
- Batch updates when possible
- Respects Google Sheets API quotas

**Error Handling:**
- Automatic retry on transient failures
- Detailed logging for debugging
- Graceful degradation (continues on non-critical errors)

**Data Validation:**
- Numeric columns converted to proper types
- Empty values handled (fillna(0))
- Column ordering preserved

---

## GitHub Actions Automation

### Workflow Configuration

**File:** `.github/workflows/update-tracker.yml`

**Trigger:**
- **Schedule:** Every 2 hours (`cron: '0 */2 * * *'`)
- **Manual:** Via GitHub UI (workflow_dispatch)

**Environment:**
- **Runner:** ubuntu-latest
- **Python:** 3.13
- **Secrets:**
  - `GOOGLE_CREDENTIALS_JSON`: Service account credentials

**Steps:**
1. **Checkout:** Clone repository
2. **Setup Python:** Install Python 3.13
3. **Cache Dependencies:** Cache pip packages
4. **Install Dependencies:** `pip install -r requirements.txt`
5. **Create Credentials:** Write secret to JSON file
6. **Run Pipeline:** Execute `main.py` with environment variables
7. **Cleanup:** Delete credentials file (security)
8. **Upload Logs:** Artifact upload on failure (7-day retention)

### GitHub Secrets Setup

**Required Secret:**
```
Name: GOOGLE_CREDENTIALS_JSON
Value: {
  "type": "service_account",
  "project_id": "prun-profit",
  "private_key_id": "...",
  "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
  "client_email": "prun-profit@prun-profit.iam.gserviceaccount.com",
  "client_id": "...",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "..."
}
```

**How to Create:**
1. Go to Google Cloud Console
2. Create new project (or use existing)
3. Enable Google Sheets API and Google Drive API
4. Create Service Account
5. Generate JSON key
6. Share Google Sheet with service account email
7. Copy JSON content to GitHub secret

---

## Installation & Setup

### Prerequisites

- **Python:** 3.10 or higher
- **Git:** For cloning repository
- **Google Account:** For Sheets integration
- **GitHub Account:** For automated deployment (optional)

### Local Setup

**1. Clone Repository:**
```bash
git clone https://github.com/lordbutxot/PrUn-Tracker.git
cd PrUn-Tracker
```

**2. Install Dependencies:**
```bash
pip install -r requirements.txt
```

**3. Configure Google Sheets:**
```bash
# Create credentials file
cp pu-tracker/historical_data/prun-profit-SAMPLE.json pu-tracker/historical_data/prun-profit-42c5889f620d.json
# Edit with your service account credentials
```

**4. Set Environment Variables:**
```bash
# Windows (PowerShell)
$env:PRUN_SPREADSHEET_ID = "1-9vXBU43YjU6LMdivpVwL2ysLHANShHzrCW6MmmGvoI"
$env:GOOGLE_APPLICATION_CREDENTIALS = "pu-tracker/historical_data/prun-profit-42c5889f620d.json"

# Linux/Mac
export PRUN_SPREADSHEET_ID="1-9vXBU43YjU6LMdivpVwL2ysLHANShHzrCW6MmmGvoI"
export GOOGLE_APPLICATION_CREDENTIALS="pu-tracker/historical_data/prun-profit-42c5889f620d.json"
```

**5. Run Pipeline:**
```bash
cd pu-tracker/historical_data
python main.py
```

### GitHub Actions Setup

**1. Fork Repository**

**2. Add Secret:**
- Go to Settings → Secrets and variables → Actions
- Click "New repository secret"
- Name: `GOOGLE_CREDENTIALS_JSON`
- Value: (Paste your service account JSON)

**3. Enable Actions:**
- Go to Actions tab
- Click "I understand my workflows, go ahead and enable them"

**4. Manual Trigger:**
- Actions → Update PrUn Tracker Data → Run workflow

### Apps Script Deployment

**1. Open Apps Script Editor:**
- Open your Google Sheet
- Extensions → Apps Script

**2. Replace Files:**
- Delete existing Code.gs
- Create new `Code.gs` → Paste `AppsScript_PriceAnalyser.js` content
- Create new `Index.html` → Paste `AppsScript_Index.html` content

**3. Deploy as Web App:**
- Click Deploy → New deployment
- Type: Web app
- Execute as: Me
- Who has access: Anyone
- Deploy
- Copy web app URL

**4. Test:**
- Open web app URL
- Verify data loads correctly

---

## Usage Guide

### Running the Pipeline

**Full Pipeline:**
```bash
# Windows
cd pu-tracker
run_pipeline.bat

# Linux/Mac
cd pu-tracker/historical_data
python main.py
```

**Individual Steps:**
```bash
cd pu-tracker/historical_data

# Step 1: Fetch data
python catch_data.py

# Step 2: Process data
python unified_processor.py

# Step 3: Analyze data
python data_analyzer.py

# Step 4: Upload to Sheets
python upload_enhanced_analysis.py
python upload_planet_resources.py
python generate_report_tabs.py
```

### Using the Price Analyser

**1. Open Web App:**
- Navigate to deployed Apps Script URL
- Wait for data to load

**2. Select Production:**
- Choose material (e.g., "BAC")
- Choose recipe (e.g., "CHP:1xC-1xH2O=>1xBAC")
- Choose exchange (e.g., "AI1")

**3. Configure Options:**
- ☑️ Toggle luxury consumables (100% vs 79% efficiency)
- ☑️ Enable CoGC program (+25%)
- 👨‍🔬 Add experts (0-5) for cumulative bonuses
- ⚙️ Set custom efficiency (optional)

**4. Planet Selection (if applicable):**
- For extraction: Select planet with best concentration
- For farming: Select planet with best fertility

**5. Calculate:**
- Click "Calculate Profit" button
- View results for all scenarios
- Check exchange comparison
- Review arbitrage opportunities

**6. Interpret Results:**
- **Green profit:** Profitable at current market
- **Red profit:** Losing money, avoid production
- **High ROI:** Good investment (>20% ideal)
- **Breakeven:** Units needed to recover building cost
- **Best Exchange:** Highest ROI location

### Reading Google Sheets Data

**DATA Tabs:**
- Sort by ROI columns to find best opportunities
- Filter by Ticker to see all recipes for a material
- Check Investment Score for overall ranking
- Monitor Supply/Demand/Traded for market health

**Planet Resources:**
- Sort by Factor (concentration) for extraction
- Sort by Fertility for farming
- Filter by Ticker to find planets for specific material

---

## Advanced Features

### Self-Production Cost Calculation

**Concept:**
- Instead of buying inputs at market price, calculate cost to produce them yourself
- Recursively applies production costs through the entire supply chain
- Useful for vertically integrated production

**Example:**
```
Producing BAC (Bacon)
├── Direct Inputs: 1×C (Carbon), 1×H2O (Water)
│   ├── Market Price: C=100, H2O=50 → 150 ICA
│   └── Self-Production:
│       ├── C Production: 80 ICA (cheaper to make)
│       └── H2O: 50 ICA (no recipe, use market)
│       └── Total: 130 ICA (20 ICA savings!)
└── Workforce: 20 ICA
└── Total Self-Production Cost: 150 ICA vs Market Input Cost: 170 ICA
```

**Circular Dependency Handling:**
- Detects loops (e.g., Material A needs B, B needs A)
- Falls back to market price for circular references
- Prevents infinite recursion

### Arbitrage Detection

**Algorithm:**
```
For each material:
  For each exchange pair (Buy Exchange, Sell Exchange):
    Profit = Sell_Exchange_Bid - Buy_Exchange_Ask - Transfer_Cost
    ROI = (Profit / Buy_Exchange_Ask) × 100%
    
    If ROI > 5%:
      Add to arbitrage opportunities
```

**Transfer Cost Modeling:**
- Assumes 5% transfer fee between exchanges
- Can be customized in code

**Filtering:**
- Minimum 5% profit after fees
- Excludes same-exchange trades
- Sorted by ROI descending

### Multi-Recipe Comparison

**How It Works:**
1. User selects material without specifying recipe
2. System calculates profitability for ALL recipes producing that material
3. Ranks by ROI (Ask/Bid scenario typically)
4. Recommends best recipe

**Use Cases:**
- Finding most efficient production method
- Comparing different building types (CHP vs ASM)
- Evaluating trade-offs (input cost vs workforce cost)

### Planet Optimization

**Extraction:**
```
Material: FE (Iron)
Planets with FE:
  ├── Planet A: 2.0 concentration → 179% total efficiency → 56% cost
  ├── Planet B: 1.5 concentration → 129% total efficiency → 78% cost
  └── Planet C: 0.5 concentration → 29% total efficiency → 345% cost

Best Choice: Planet A (2.0 concentration)
Savings vs Average: 44% reduction in workforce cost
```

**Farming:**
```
Material: GRN (Grains)
Farmable Planets (28 total):
  ├── Planet X: 0.40 fertility → 140% efficiency → 71% cost
  ├── Planet Y: 0.20 fertility → 120% efficiency → 83% cost
  ├── Planet Z: -0.50 fertility → 50% efficiency → 200% cost
  └── Most planets: -1 fertility → Cannot farm

Best Choice: Planet X (0.40 fertility)
Savings vs Worst: 65% reduction in workforce cost
```

### Efficiency Stacking

**Maximum Efficiency Example:**
```
Base: 100% (with luxury)
+ Planet: 100% (2.0 concentration)
+ CoGC: 25%
+ 5 Experts: 28.40%
─────────────────────────
Total: 253.40%

Production Time: Base_Time / 2.534 = 39.5% of base
Workforce Cost: Base_Cost / 2.534 = 39.5% of base
Savings: 60.5%!
```

---

## Troubleshooting

### Common Issues

**1. "No data found" in Price Analyser**
- **Cause:** Google Sheets not updated or Apps Script not deployed
- **Fix:**
  - Run pipeline: `python main.py`
  - Check DATA tabs have data
  - Redeploy Apps Script

**2. "Not connected to Google Sheets" in pipeline**
- **Cause:** Missing credentials or environment variable
- **Fix:**
  - Check `GOOGLE_APPLICATION_CREDENTIALS` env var
  - Verify credentials file exists
  - Ensure service account has Sheet access

**3. GitHub Actions failing**
- **Cause:** Secret not configured or expired
- **Fix:**
  - Check `GOOGLE_CREDENTIALS_JSON` secret exists
  - Verify service account key not expired
  - Review workflow logs for specific error

**4. Workforce costs showing 0**
- **Cause:** Missing workforceneeds.json or buildingrecipes.csv
- **Fix:**
  - Delete cache files
  - Re-run `catch_data.py`
  - Verify API endpoints accessible

**5. Planet selector empty for farming**
- **Cause:** Fertility data not uploaded to Sheets
- **Fix:**
  - Run `upload_planet_resources.py`
  - Verify "Planet Resources" tab has Fertility column
  - Check planet_fertility.csv has 28 planets

**6. Efficiency calculations seem wrong**
- **Cause:** Using old multiplicative system instead of additive
- **Fix:**
  - Update to latest AppsScript_Index.html
  - Verify efficiency formula uses addition, not multiplication
  - Check total efficiency = sum of all bonuses

### Debug Tools

**Pipeline Logging:**
```bash
# Check latest log
cd pu-tracker/logs
cat pipeline_YYYYMMDD_HHMMSS.log

# View real-time
tail -f pipeline_YYYYMMDD_HHMMSS.log
```

**Browser Console (Price Analyser):**
```javascript
// Check loaded data
console.log('allData:', allData);
console.log('fertilityData:', fertilityData);
console.log('planetData:', planetData);

// Check efficiency calculation
console.log('Total Efficiency:', totalEfficiency);
console.log('Expert Bonus:', calculateExpertBonus(3));
```

**Python Debug:**
```python
# Add to any script
import logging
logging.basicConfig(level=logging.DEBUG)

# Or use print statements
print(f"[DEBUG] Variable: {variable_name}")
```

### Getting Help

**Issues:**
- GitHub Issues: https://github.com/lordbutxot/PrUn-Tracker/issues
- Include log files and error messages

**Feature Requests:**
- GitHub Discussions: https://github.com/lordbutxot/PrUn-Tracker/discussions

**Documentation:**
- This Wiki: WIKI.md
- Code comments in each file
- Individual MD files for specific features

---

## Appendix

### Glossary

**Terms:**
- **ICA:** In-game currency (Inter-Colonial Astra)
- **Ticker:** 3-letter material code (e.g., FE, H2O, BAC)
- **Ask Price:** Seller's asking price
- **Bid Price:** Buyer's offered price
- **ROI:** Return on Investment (Profit / Cost × 100%)
- **CoGC:** Chamber of Global Commerce (game organization)
- **FIO:** FIO REST API (game data source)

**Building Types:**
- **Manufacturing:** CHP, WEL, ASM, etc.
- **Extraction:** COL (Collector), EXT (Extractor), RIG (Rig)
- **Farming:** FRM (Farm), ORC (Orchard), VIN (Vineyard)

**Worker Types:**
- **Pioneer:** Basic workers
- **Settler:** Advanced workers
- **Technician:** Specialized workers
- **Engineer:** Expert workers
- **Scientist:** Research workers

### API Endpoints Reference

**Base URL:** `https://rest.fnar.net`

| Endpoint | Method | Response | Rate Limit |
|----------|--------|----------|------------|
| `/csv/planetdetail` | GET | CSV | 10/min |
| `/csv/planetresources` | GET | CSV | 10/min |
| `/csv/buildings` | GET | JSON | 10/min |
| `/csv/buildingrecipes` | GET | CSV | 10/min |
| `/csv/materials` | GET | CSV | 10/min |
| `/csv/workforceneeds` | GET | JSON | 10/min |
| `/exchange/all` | GET | CSV | 60/min |
| `/exchange/orders/{ticker}` | GET | JSON | 60/min |

### File Size Estimates

| File | Typical Size | Records |
|------|-------------|---------|
| market_data.csv | 500 KB | 15,000 |
| buildingrecipes.csv | 200 KB | 3,000 |
| materials.csv | 50 KB | 500 |
| planetresources.csv | 800 KB | 7,161 |
| planet_fertility.csv | 1 KB | 28 |
| processed_data.csv | 1.5 MB | 15,000 |
| daily_analysis_enhanced.csv | 2 MB | 15,000 |

### Performance Metrics

**Pipeline Execution:**
- **Full Run:** 2-5 minutes
- **Data Fetch:** 30-60 seconds
- **Processing:** 60-120 seconds
- **Upload:** 30-60 seconds

**Web App Load:**
- **Initial Load:** 2-4 seconds
- **Calculation:** <100ms (client-side)
- **Data Refresh:** 1-2 seconds

---

## Version History

### v2.0 (November 2025)
- ✅ Additive efficiency system (replaces multiplicative)
- ✅ CoGC program support (+25%)
- ✅ Expert bonuses (1-5 with verified values)
- ✅ Farming fertility integration (28 planets)
- ✅ Fixed numeric type issues in uploads
- ✅ Planet Resources tab with Fertility column
- ✅ GitHub Actions authentication fix

### v1.5
- ✅ Custom efficiency override
- ✅ Planet-specific extraction calculations
- ✅ Multi-recipe selector
- ✅ Exchange comparison

### v1.0
- ✅ Initial release
- ✅ Basic profit calculator
- ✅ Google Sheets integration
- ✅ Automated pipeline

---

## Contributing

**How to Contribute:**
1. Fork repository
2. Create feature branch
3. Make changes with tests
4. Submit pull request

**Code Style:**
- Python: PEP 8
- JavaScript: Airbnb style guide
- Comments: Explain "why", not "what"

**Testing:**
- Add unit tests for new features
- Verify pipeline runs successfully
- Check Google Sheets upload

---

## License

This project is provided as-is for use with Prosperous Universe. Not affiliated with Simulogics or Prosperous Universe.

---

## Credits

**Developer:** lordbutxot  
**Game:** Prosperous Universe by Simulogics  
**API:** FIO REST API (Prosperous Universe community)  
**Tools:** Python, Google Apps Script, GitHub Actions

---

**End of Documentation**

For the most up-to-date information, check the GitHub repository:  
https://github.com/lordbutxot/PrUn-Tracker
