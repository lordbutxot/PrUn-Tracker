# Web Apps — Deployment Options

This folder contains the Google Apps Script web apps for PrUn-Tracker. We support **two deployment patterns**:

## Option 1: Standalone Deployments (Recommended)

Each app gets its own Apps Script project and URL. This is the **most reliable approach**.

**Pros:**
- ✅ Complete isolation—no routing complexity
- ✅ Independent updates without affecting other apps
- ✅ Clear separation and easy debugging
- ✅ No URL parameter confusion or caching issues

**Setup:** See `ARBITRAGE_STANDALONE_DEPLOYMENT.md` for step-by-step instructions.

**Files:**
- `ArbitrageCalculator_StandaloneCode.gs` — Server code for standalone arbitrage deployment
- `ArbitrageCalculator_Index.html` — Arbitrage UI
- `AppsScript_PriceAnalyser.js` — Server code for Price Analyser (existing project)
- `AppsScript_Index.html` — Price Analyser UI

**URLs after deployment:**
- Price Analyser: `https://script.google.com/.../exec` (existing)
- Arbitrage Calculator: `https://script.google.com/.../exec` (new project, different URL)

---

## Option 2: Single Project with Router

Both apps in one Apps Script project, routed by `?page=` parameter.

**Pros:**
- Single codebase to maintain
- One deployment to manage

**Cons:**
- Requires exact `page` parameter
- More complex debugging
- Browser caching can cause issues

**Files:**
- `AppsScript_PriceAnalyser.js` — Server code with router. Copy to `Code.gs`.
- `AppsScript_Index.html` — Price Analyser UI. Add as `Index` HTML file.
- `ArbitrageCalculator_Index.html` — Arbitrage UI. Add as `ArbitrageCalculator` HTML file.

**URLs (same deployment):**
- Price Analyser: `.../exec?page=price`
- Arbitrage Calculator: `.../exec?page=arbitrage`

**Setup:**
1. Open your Google Sheet → Extensions → Apps Script
2. Replace `Code.gs` with `web/AppsScript_PriceAnalyser.js`
3. Add `Index` HTML from `web/AppsScript_Index.html`
4. Add `ArbitrageCalculator` HTML from `web/ArbitrageCalculator_Index.html`
5. Deploy: Deploy → Manage deployments → New version
6. Update `index.html` iframes with `?page=price` and `?page=arbitrage`

## Data Requirements

Both pages read from the same Google Spreadsheet:
- `Price Analyser Data` — Main dataset (Ticker, Name, Exchange, Ask/Bid, Supply, Demand, Traded Volume, etc.)
- `Metadata` — Key-value pairs (e.g., `Last Data Update`) used for display

## Troubleshooting

- Script function not found: Ensure `doGet(e)` exists in `Code.gs`.
- Sheet not found: Verify sheet names match exactly and data is populated by the pipeline.
- Old version after deploy: Hard-refresh and deploy a new version (not just save).

## Notes

- The GitHub landing page already embeds the same Apps Script URL and switches pages via `?page=arbitrage`.
- Extra markdown setup guides previously here were removed to reduce clutter; this README reflects the current single-project setup.

Last Updated: December 15, 2025
