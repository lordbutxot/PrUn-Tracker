# GitHub Actions Setup Guide

This guide explains how to set up automated updates for PrUn-Tracker using GitHub Actions.

## Overview

The GitHub Actions workflow automatically runs the PrUn-Tracker pipeline every 30 minutes, fetching fresh data and updating your Google Sheets.

## Setup Instructions

### Step 1: Prepare Your Google Service Account Credentials

1. **Get your credentials JSON file**: You should have a file named `prun-profit-42c5889f620d.json` in `pu-tracker/historical_data/`

2. **Copy the entire contents** of this JSON file. It should look like:
   ```json
   {
     "type": "service_account",
     "project_id": "your-project-id",
     "private_key_id": "...",
     "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
     "client_email": "...",
     "client_id": "...",
     ...
   }
   ```

   **Important**: Make sure to copy the **entire** JSON including all newlines in the private key.

### Step 2: Add Credentials to GitHub Secrets

1. Go to your GitHub repository: `https://github.com/lordbutxot/PrUn-Tracker`

2. Click on **Settings** (top right)

3. In the left sidebar, click **Secrets and variables** → **Actions**

4. Click **New repository secret**

5. Create the secret:
   - **Name**: `GOOGLE_CREDENTIALS_JSON`
   - **Value**: Paste the entire contents of your credentials JSON file
   - Click **Add secret**

### Step 3: Enable GitHub Actions

1. Go to the **Actions** tab in your repository

2. If Actions are disabled, click **"I understand my workflows, go ahead and enable them"**

3. The workflow is already configured in `.github/workflows/update-tracker.yml`

### Step 4: Test the Workflow

#### Manual Test
1. Go to **Actions** tab
2. Click on **"Update PrUn Tracker Data"** workflow
3. Click **"Run workflow"** button
4. Select the `main` branch
5. Click **"Run workflow"**
6. Watch the workflow execution to ensure it completes successfully

#### Check Scheduled Runs
- The workflow is scheduled to run every 30 minutes: `*/30 * * * *`
- View run history in the **Actions** tab

## Workflow Configuration

### Current Schedule
```yaml
schedule:
  - cron: '*/30 * * * *'  # Every 30 minutes
```

### Change Update Frequency

Edit `.github/workflows/update-tracker.yml` and modify the cron schedule:

```yaml
# Every hour
- cron: '0 * * * *'

# Every 2 hours
- cron: '0 */2 * * *'

# Every 60 minutes (explicit)
- cron: '*/60 * * * *'

# Every 15 minutes
- cron: '*/15 * * * *'

# Daily at midnight UTC
- cron: '0 0 * * *'
```

**Cron format**: `minute hour day month weekday`
- `*/30` = every 30 units
- `*` = any value
- `0` = at zero (e.g., top of the hour)

## Current Configuration Status

✅ **Workflow file configured**: `.github/workflows/update-tracker.yml`
✅ **Credentials filename**: `prun-profit-42c5889f620d.json` (matches expected name)
✅ **Spreadsheet ID**: Set as environment variable in workflow
✅ **Schedule**: Every 30 minutes
✅ **Python version**: 3.13
✅ **Security**: Credentials cleaned up after each run

**Next step**: Add your `GOOGLE_CREDENTIALS_JSON` secret in GitHub repository settings (see Step 2 above).

## How It Works

### Workflow Steps

1. **Checkout repository**: Downloads your code
2. **Set up Python**: Installs Python 3.13
3. **Cache dependencies**: Speeds up runs by caching pip packages
4. **Install dependencies**: Installs packages from `requirements.txt`
5. **Create credentials**: Writes the secret JSON to `prun-profit-42c5889f620d.json`
6. **Run pipeline**: Executes `main.py` with spreadsheet ID environment variable
7. **Clean up**: Removes the credentials file
8. **Upload logs**: Saves logs if the run fails (retained for 7 days)

### Security Features

- ✅ Credentials are stored as encrypted GitHub Secrets
- ✅ Credentials file is created temporarily and deleted after each run
- ✅ `.gitignore` prevents committing credentials files
- ✅ Logs are only uploaded on failure (and auto-deleted after 7 days)

## Monitoring

### View Run History
1. Go to **Actions** tab
2. See all workflow runs with status (✅ success, ❌ failure)
3. Click on any run to see detailed logs

### Email Notifications
GitHub automatically sends email notifications for:
- Failed workflow runs
- First successful run after a failure

Configure in: **Settings** → **Notifications** → **Actions**

## Troubleshooting

### Workflow Fails with "Credentials not found"
- Verify the secret name is exactly `GOOGLE_CREDENTIALS_JSON`
- Check the secret value contains valid JSON
- Ensure the JSON is complete (including all `-----BEGIN/END PRIVATE KEY-----` lines)

### Workflow Fails with "Permission denied"
- Ensure your Google Service Account has access to the spreadsheets
- Check the spreadsheet is shared with the service account email

### Workflow Doesn't Run on Schedule
- GitHub Actions may have a delay of up to 15 minutes
- Workflows in inactive repositories may be paused (manual run reactivates)
- Check the **Actions** tab for any warnings

### Rate Limiting Issues
If you hit API rate limits, consider:
- Increasing the interval (e.g., every 60 minutes instead of 30)
- Reducing the number of API calls in your code
- Adding more delays between requests

## Local Testing

You can test the environment variable approach locally:

### Windows PowerShell
```powershell
$env:GOOGLE_APPLICATION_CREDENTIALS = "pu-tracker\historical_data\prun-profit-42c5889f620d.json"
python pu-tracker\historical_data\main.py
```

### Linux/Mac
```bash
export GOOGLE_APPLICATION_CREDENTIALS="pu-tracker/historical_data/prun-profit-42c5889f620d.json"
python pu-tracker/historical_data/main.py
```

## Best Practices

1. **Never commit credentials**: Always use GitHub Secrets for sensitive data
2. **Test manually first**: Run the workflow manually before relying on the schedule
3. **Monitor initially**: Check the first few scheduled runs to ensure stability
4. **Keep logs**: Failed run logs help diagnose issues
5. **Update regularly**: Keep Python dependencies updated for security

## Additional Configuration

### Update Multiple Spreadsheets
If you need to update different spreadsheets, add more secrets:

1. Add secret `SPREADSHEET_ID_1`, `SPREADSHEET_ID_2`, etc.
2. Modify the workflow to pass these as environment variables
3. Update your Python code to read these environment variables

### Add Slack/Discord Notifications
Use GitHub Actions marketplace integrations:
- [Slack Notify](https://github.com/marketplace/actions/slack-notify)
- [Discord Notify](https://github.com/marketplace/actions/discord-message-notify)

## Support

If you encounter issues:
1. Check the **Actions** tab for detailed error logs
2. Review this documentation
3. Check Google Sheets API quotas and limits
4. Verify your credentials are still valid

---

**Last Updated**: January 2025
