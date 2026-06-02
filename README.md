# PrUn-Tracker

**Advanced data pipeline and analytics suite for [Prosperous Universe](https://prosperousuniverse.com/)**

[![GitHub Actions](https://img.shields.io/badge/Automated-Every%202%20Hours-success)](https://github.com/lordbutxot/PrUn-Tracker/actions)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green)](#)

## 🎯 What is PrUn-Tracker?

PrUn-Tracker automates the entire workflow of collecting, processing, analyzing, and reporting in-game economic and production data for Prosperous Universe. It provides:

- ✅ **True Production Costs** - Complete workforce consumable calculations (RAT, DW, OVE, etc.)
- ✅ **Planet Optimization** - Extraction concentration & farming fertility factors
- ✅ **Advanced Efficiency** - Worker luxury, CoGC programs, experts (cumulative bonuses)
- ✅ **Real-Time Market Data** - Automated fetching every hour via GitHub Actions
- ✅ **Interactive Web Tool** - Price Analyser with profit calculations & scenario comparisons
- ✅ **Google Sheets Integration** - Auto-updated spreadsheets with analytics

## 🚀 Quick Start

### Option 1: Use the Live Web App (Easiest)
👉 **[Open Price Analyser](https://script.google.com/your-app-url)** *(Deploy your own from this repo)*

### Option 2: Run Locally
```bash
# Clone repository
git clone https://github.com/lordbutxot/PrUn-Tracker.git
cd PrUn-Tracker

# Install dependencies
pip install -r requirements.txt

# Run pipeline
cd pu-tracker/historical_data
python main.py
```

### Run Regression Tests
```bash
pip install -r requirements-dev.txt
python -m pytest
```

The test suite validates the committed cache schema and core calculation helpers without calling the FIO API or Google Sheets.

### Option 3: Fork & Deploy with GitHub Actions
1. Fork this repository
2. Add `GOOGLE_CREDENTIALS_JSON` secret (see [Setup Guide](GITHUB_ACTIONS_SETUP.md))
3. Enable GitHub Actions
4. Data updates automatically every 2 hours!

## 📊 Key Features

### Price Analyser Web App
- **Multi-Recipe Comparison** - Find the most profitable production method with 💎 Best ROI badges
- **Visual ROI Indicators** - Color-coded comparison (🟢 better, 🔴 worse, 🔵 selected)
- **Planet Selection** - Optimize for extraction concentration or farming fertility
- **Planet-Based Filtering** - Extraction buildings show only planet-available materials
- **Efficiency Modeling** - Toggle luxury, CoGC (+25%), experts (up to +28.4%)
- **HQ Bonuses** - Company HQ (faction bonuses × specialization) & Corp HQ (+10%)
- **4 ROI Scenarios** - Ask/Ask, Ask/Bid, Bid/Ask, Bid/Bid
- **Exchange Comparison** - See profitability across all exchanges with supply/demand/volume
- **Arbitrage Detection** - Cross-exchange trading opportunities
- **Real-Time Updates** - Timestamp showing last data refresh with timezone support
- **Mobile Responsive** - Optimized layout with badge stacking for smaller screens

### Automated Data Pipeline
- Fetches from Prosperous Universe FIO API
- Processes 15,000+ market records
- Calculates workforce costs with real market prices
- Uploads to Google Sheets (DATA tabs, Planet Resources, Reports)
- Runs every hour via GitHub Actions

### Advanced Calculations
- **Hybrid Efficiency System** - Additive (Worker + Planet + CoGC + Experts) then Multiplicative (HQ × Corp HQ)
- **Company HQ Bonuses** - Faction-specific industry bonuses (4-10%) × specialization multiplier (1.0-3.0)
- **Three HQ Input Methods** - Enter bases, permits, or multiplier directly for maximum flexibility
- **Corp HQ Bonuses** - Planet-specific +10% multiplicative bonus
- **28 Farmable Planets** - Only 0.8% of planets support farming with corrected PCT fertility formula
- **Official Fertility Formula** - `Fertility = RawFertility × (10/33)` from PCT reference
- **Self-Production Costs** - Recursive calculation for vertical integration
- **Investment Scoring** - Proprietary algorithm ranking unique opportunities (deduplicated)

## 📈 Sample Results

**Workforce Cost Calculation:**
```
Recipe: CHP producing BAC (8 hours)
Worker: Technician
Consumables: DW, RAT, OVE, PWO, COF
Market Prices: DW=10, RAT=15, OVE=8, PWO=12, COF=5
Workforce Cost: 20 ICA
```

**Efficiency Stacking:**
```
Additive Bonuses:
  Base: 100% (luxury)
  Planet Concentration: +100% (2.0 factor)
  CoGC Program: +25%
  5 Experts: +28.4%
  Subtotal: 253.4%

Multiplicative Bonuses:
  Company HQ: 10% × 2.6 multiplier = +26%
  Corp HQ: +10%
  
Total: 253.4% × 1.26 × 1.10 = 351.2%
Effective Cost: 28.5% of base (71.5% savings!)
```

**Farming Optimization:**
```
Material: GRN (Grains)
28 Farmable Planets:
  Best: +40% fertility → 71% cost
  Worst: -50% fertility → 200% cost
Optimal savings: 65% vs worst planet
```

## 📚 Documentation

**Complete Documentation:** See **[WIKI.md](WIKI.md)** for:
- Full calculation formulas
- Architecture & data flow diagrams
- Setup & installation guide
- Troubleshooting & FAQ
- API reference
- Advanced features

**Feature Guide:** See **[FEATURES.md](FEATURES.md)** for detailed guide to all features:
- ROI badges and color coding system
- Planet-based extraction filtering
- Fertility calculations and farming
- Market indicators and timestamp display
- UI/UX features and mobile responsiveness
- Cost calculation options
- Bug fixes and technical details

**Recent Changes:** See **[CHANGELOG.md](CHANGELOG.md)** for latest features and bug fixes

**GitHub Actions Setup:** See **[GITHUB_ACTIONS_SETUP.md](GITHUB_ACTIONS_SETUP.md)**

## 🗂️ Project Structure

```
PrUn-Tracker/
├── pu-tracker/
│   ├── cache/                    # Cached data (CSV/JSON)
│   ├── historical_data/          # Python pipeline scripts
│   │   ├── main.py               # Pipeline orchestrator
│   │   ├── catch_data.py         # API data fetcher
│   │   ├── unified_processor.py  # Data processor
│   │   ├── data_analyzer.py      # Analytics engine
│   │   ├── workforce_costs.py    # Workforce calculator
│   │   └── sheets_manager.py     # Google Sheets uploader
│   └── logs/                     # Execution logs
├── AppsScript_PriceAnalyser.js  # Web app backend
├── AppsScript_Index.html         # Web app frontend
├── WIKI.md                       # Complete documentation
├── GITHUB_ACTIONS_SETUP.md       # Automation setup guide
└── README.md                     # This file
```

## 🎮 Use Cases

**Solo Entrepreneur:**
- Calculate exact production costs including workforce
- Find most profitable recipes for your setup
- Optimize planet selection for extraction/farming

**Corporation Logistics Manager:**
- Identify arbitrage opportunities across exchanges
- Coordinate production with real-time market data
- Share live Google Sheets with team

**Market Analyst:**
- Track supply/demand trends
- Monitor liquidity and market cap
- Detect market inefficiencies

## 🔧 Technology Stack

- **Backend:** Python 3.10+ (pandas, requests, gspread)
- **Frontend:** Google Apps Script (JavaScript + HTML)
- **Data Source:** Prosperous Universe FIO REST API
- **Storage:** Google Sheets + Local CSV cache
- **Automation:** GitHub Actions (cron schedule)

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Add tests for new features
4. Submit a pull request

## 📝 License

This project is provided as-is for use with Prosperous Universe.  
Not affiliated with Simulogics or Prosperous Universe.

## 🙏 Credits

- **Developer:** lordbutxot
- **Game:** [Prosperous Universe](https://prosperousuniverse.com/) by Simulogics
- **API:** FIO REST API (PrUn community)

---

**Ready to optimize your Prosperous Universe gameplay?**

👉 **[Feature Guide (FEATURES.md)](FEATURES.md)** - Complete guide to all features  
👉 **[Read Full Documentation (WIKI.md)](WIKI.md)** - Technical documentation  
👉 **[Recent Changes (CHANGELOG.md)](CHANGELOG.md)** - Latest updates  
👉 **[Setup GitHub Actions (GITHUB_ACTIONS_SETUP.md)](GITHUB_ACTIONS_SETUP.md)** - Automation guide  
👉 **[Open Issues](https://github.com/lordbutxot/PrUn-Tracker/issues)** - Report bugs or request features

