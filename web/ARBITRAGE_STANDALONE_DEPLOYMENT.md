# Arbitrage Calculator - Standalone Deployment Guide

This guide shows you how to deploy the Arbitrage Calculator as a **separate Apps Script project** with its own URL.

## Why Standalone Deployment?

- **Guaranteed isolation**: Arbitrage app is completely independent from Price Analyser
- **Simple routing**: No URL parameters or routing logic needed
- **Easy debugging**: Each app has its own deployment and execution log
- **Reliability**: No risk of one app affecting the other

## Setup Steps

### 1. Create New Apps Script Project

1. Open your Google Sheet: https://docs.google.com/spreadsheets/d/1-9vXBU43YjU6LMdivpVwL2ysLHANShHzrCW6MmmGvoI/edit
2. Click **Extensions** → **Apps Script**
3. Click the **project dropdown** (top left, next to project name)
4. Click **New Project**
5. Name it: **PrUn Arbitrage Calculator**

### 2. Add Server Code

1. In the new project, you'll see `Code.gs`
2. Delete any default code
3. Open `web/ArbitrageCalculator_StandaloneCode.gs` from this repo
4. **Copy all the code**
5. **Paste it into Code.gs** in Apps Script

### 3. Add HTML File

1. Click the **+** button next to Files
2. Select **HTML**
3. Name it exactly: `ArbitrageCalculator` (no extension)
4. Open `web/ArbitrageCalculator_Index.html` from this repo
5. **Copy all the HTML**
6. **Paste it into the ArbitrageCalculator file** in Apps Script

### 4. Deploy as Web App

1. Click **Deploy** → **New deployment**
2. Click the gear icon ⚙️ next to "Select type"
3. Select **Web app**
4. Configure settings:
   - **Description**: Arbitrage Calculator v1.0
   - **Execute as**: Me (your email)
   - **Who has access**: Anyone
5. Click **Deploy**
6. **Authorize** the app when prompted (click "Advanced" → "Go to [app name]")
7. **Copy the Web App URL** (ends with `/exec`)

### 5. Update GitHub Page

1. Open `index.html` in your repository
2. Find the Arbitrage Calculator modal iframe (around line 779)
3. Replace the `src` URL with your new deployment URL:

```html
<iframe
  class="modal-iframe"
  src="YOUR_NEW_ARBITRAGE_URL_HERE"
  allowfullscreen
  sandbox="allow-scripts allow-same-origin allow-popups allow-forms">
</iframe>
```

4. Save and push to GitHub

### 6. Test

1. Open your GitHub page: https://lordbutxot.github.io/PrUn-Tracker/
2. Click the **Arbitrage Calculator** button
3. You should now see the Arbitrage Calculator (not Price Analyser!)
4. Test the functionality:
   - Select origin and destination exchanges
   - Click "Find Opportunities"
   - Verify results display correctly
   - Test "Export to Sheet" button

## URL Structure

After deployment, you'll have two separate URLs:

| App | URL | Purpose |
|-----|-----|---------|
| Price Analyser | `https://script.google.com/.../exec?page=price` | Production analysis with ROI scenarios |
| Arbitrage Calculator | `https://script.google.com/.../exec` | Cross-exchange trading opportunities |

No URL parameters needed for the standalone arbitrage app—it just works!

## Updating the Arbitrage App

When you need to make changes:

1. Edit the files in this repo (`web/` folder)
2. Copy updated code to Apps Script:
   - `ArbitrageCalculator_StandaloneCode.gs` → `Code.gs`
   - `ArbitrageCalculator_Index.html` → `ArbitrageCalculator` HTML file
3. Deploy a new version:
   - **Deploy** → **Manage deployments**
   - Click the pencil icon ✏️ next to your active deployment
   - Click **Version**: New version
   - Add description of changes
   - Click **Deploy**
4. Hard-refresh your GitHub page (Ctrl+Shift+R or Cmd+Shift+R)

## Troubleshooting

### "Sheet not found" Error
- Verify your Google Sheet has a `Price Analyser Data` sheet
- Check that the Python pipeline has populated data

### Authorization Errors
- Click "Advanced" → "Go to [app name] (unsafe)"
- This is safe—it's your own script running with your permissions

### Old Version Showing
- Clear browser cache
- Add a version query parameter: `?v=2` to the iframe src
- Verify you deployed a **new version** (not just saved)

### Modal Shows Wrong App
- Double-check you copied the new deployment URL correctly
- Open the arbitrage URL directly in browser to confirm it works
- Ensure iframe src doesn't have `?page=` parameter (standalone doesn't use routing)

## Data Requirements

Both apps read from the same Google Spreadsheet sheets:

- **Price Analyser Data**: Main dataset with Ticker, Exchange, Ask/Bid prices, Supply, Demand, Traded Volume
- **Metadata**: Key-value pairs including `Last Data Update` timestamp

Make sure your Python pipeline (`pu-tracker/historical_data/main.py`) runs regularly to keep data fresh.

## Benefits of This Approach

✅ **No routing complexity**: Each app is self-contained  
✅ **Independent updates**: Update one app without touching the other  
✅ **Clear separation**: Easy to debug and maintain  
✅ **Reliable URLs**: No parameter confusion or caching issues  
✅ **Simple mental model**: One project = one app  

---

**Last Updated**: December 15, 2025
