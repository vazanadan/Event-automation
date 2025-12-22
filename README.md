# Event Automation - Daily Bug Report System

An automated system that analyzes Mixpanel events with AI (Claude) and sends daily bug analysis reports via email.

## Features

- **Mixpanel Integration**: Fetches all events from the last 24 hours
- **BigQuery Storage**: Stores bug data and analysis results
- **AI Analysis**: Uses Claude API to analyze each user's events individually
- **Pattern Detection**: Aggregates user analyses to find patterns and signals
- **Email Reports**: Sends beautiful HTML reports via Gmail
- **Scheduling**: Runs automatically at a configured time each day

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Mixpanel   │────▶│   Events    │────▶│  AI Analyzer│
│    API      │     │  by User    │     │  (Claude)   │
└─────────────┘     └─────────────┘     └──────┬──────┘
                                               │
                                               ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Gmail     │◀────│   Report    │◀────│  Aggregate  │
│   Sender    │     │  Generator  │     │  Analysis   │
└─────────────┘     └─────────────┘     └──────┬──────┘
                                               │
                                               ▼
                                        ┌─────────────┐
                                        │  BigQuery   │
                                        │   Storage   │
                                        └─────────────┘
```

## Prerequisites

1. **Python 3.9+**
2. **Google Cloud Project** with BigQuery API enabled
3. **Mixpanel Account** with API access
4. **Anthropic API Key** for Claude
5. **Gmail Account** with OAuth configured

## Installation

### 1. Clone and Setup

```bash
cd Event-automation
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment

Copy the example environment file and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env` with your actual values:

```env
# BigQuery
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
BIGQUERY_PROJECT_ID=your-project-id
BIGQUERY_DATASET=your_dataset
BIGQUERY_TABLE=bugs

# Mixpanel
MIXPANEL_PROJECT_ID=your_project_id
MIXPANEL_SERVICE_ACCOUNT_USERNAME=your_username
MIXPANEL_SERVICE_ACCOUNT_SECRET=your_secret

# Anthropic
ANTHROPIC_API_KEY=sk-ant-...

# Gmail
GMAIL_SENDER_EMAIL=your-email@gmail.com
GMAIL_CREDENTIALS_PATH=credentials.json
GMAIL_TOKEN_PATH=token.json
REPORT_RECIPIENT_EMAILS=recipient1@example.com,recipient2@example.com

# Scheduler
REPORT_TIME=09:00
TIMEZONE=UTC
ANALYSIS_LOOKBACK_HOURS=24
```

### 3. Setup Gmail OAuth

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a project and enable Gmail API
3. Create OAuth 2.0 credentials (Desktop application)
4. Download and save as `credentials.json`
5. Run the setup:

```bash
python main.py --setup-gmail
```

### 4. Setup BigQuery

1. Create a BigQuery dataset in your project
2. Download a service account key JSON file
3. Set `GOOGLE_APPLICATION_CREDENTIALS` to the path

### 5. Customize Prompts (Optional)

Edit the prompt files in `prompts/` to customize the AI analysis:

- `prompts/user_analysis_prompt.txt` - How each user is analyzed
- `prompts/aggregate_analysis_prompt.txt` - How patterns are found across users

## Usage

### Validate Configuration

```bash
python main.py --validate
```

### Run Once (Manual)

```bash
python main.py --run-once
```

### Run with Scheduler

```bash
python main.py --schedule
```

### Run as Background Service

Using systemd (Linux):

```bash
# Generate systemd files
python -c "from src.scheduler import setup_systemd_timer; s, t = setup_systemd_timer(); print(s)"

# Install as service
sudo cp event-automation.service /etc/systemd/system/
sudo cp event-automation.timer /etc/systemd/system/
sudo systemctl enable event-automation.timer
sudo systemctl start event-automation.timer
```

Using cron:

```bash
# Add to crontab
crontab -e

# Add line:
0 9 * * * cd /home/user/Event-automation && /usr/bin/python3 main.py --run-once
```

## Project Structure

```
Event-automation/
├── main.py                 # Main orchestration script
├── config.py               # Configuration management
├── requirements.txt        # Python dependencies
├── .env.example           # Environment template
├── .gitignore
├── README.md
├── src/
│   ├── __init__.py
│   ├── bigquery_client.py  # BigQuery operations
│   ├── mixpanel_client.py  # Mixpanel API client
│   ├── ai_analyzer.py      # Claude AI analysis
│   ├── email_sender.py     # Gmail sender
│   └── scheduler.py        # Job scheduling
├── prompts/
│   ├── user_analysis_prompt.txt
│   └── aggregate_analysis_prompt.txt
├── data/                   # Local data storage (gitignored)
└── logs/                   # Log files (gitignored)
```

## How It Works

1. **Fetch Events**: At the scheduled time, fetches all Mixpanel events from the last 24 hours
2. **Group by User**: Events are grouped by `distinct_id` (user ID)
3. **Analyze Each User**: Each user's events are sent to Claude for individual analysis
4. **Save Analysis**: Individual analyses are saved to BigQuery
5. **Aggregate Analysis**: All user analyses are combined for pattern detection
6. **Generate Report**: An HTML report is generated with findings
7. **Send Email**: Report is emailed to configured recipients

## Troubleshooting

### Gmail Authentication Fails
- Ensure you've enabled Gmail API in Google Cloud Console
- Run `python main.py --setup-gmail` again
- Check that `credentials.json` exists

### BigQuery Connection Issues
- Verify `GOOGLE_APPLICATION_CREDENTIALS` points to valid JSON
- Check service account has BigQuery permissions

### No Events Found
- Verify Mixpanel credentials are correct
- Check that events exist in the specified timeframe
- Try increasing `ANALYSIS_LOOKBACK_HOURS`

### AI Analysis Fails
- Verify `ANTHROPIC_API_KEY` is valid
- Check API rate limits

## License

MIT
