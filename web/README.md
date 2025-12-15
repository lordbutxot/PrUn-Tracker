# Web Apps — Single Apps Script Project (Router)

This folder contains the Google Apps Script web app for PrUn-Tracker. We now use a single Apps Script project with a simple router that serves multiple pages (Price Analyser and Arbitrage Calculator) from the same deployment URL.

## How It Works

- A single `doGet(e)` in `AppsScript_PriceAnalyser.js` routes by URL param `page`.
- Default (no param) serves the Price Analyser.
- `?page=arbitrage` serves the Arbitrage Calculator.

Example URLs (same deployment):
- Price Analyser: `.../exec`
- Arbitrage Calculator: `.../exec?page=arbitrage`

## Files

- `AppsScript_PriceAnalyser.js` — Server-side code AND router. Copy into Apps Script as `Code.gs`.
- `AppsScript_Index.html` — Price Analyser UI. Add to Apps Script as `Index` HTML file.
- `ArbitrageCalculator_Index.html` — Arbitrage UI. Add to Apps Script as `ArbitrageCalculator` HTML file.
- `ArbitrageCalculator_Code.gs` — Reference-only copy of arbitrage server functions (not required; main code is consolidated in `AppsScript_PriceAnalyser.js`).
- `UnifiedRouter_Code.gs` — Reference-only; router is already in `AppsScript_PriceAnalyser.js`.

## Quick Update / Deploy

1) Open your Google Sheet → Extensions → Apps Script (same project as before).
2) In the editor:
   - Replace `Code.gs` with contents of `web/AppsScript_PriceAnalyser.js`.
   - Ensure `Index` HTML exists; paste `web/AppsScript_Index.html`.
   - Create `ArbitrageCalculator` HTML; paste `web/ArbitrageCalculator_Index.html`.
3) Deploy: Deploy → Manage deployments → New version (Web app, Execute as: Me, Access: Anyone).
4) If the exec URL changed, update `index.html` iframes:
   - Price Analyser modal iframe → `.../exec`
   - Arbitrage modal iframe → `.../exec?page=arbitrage`

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
