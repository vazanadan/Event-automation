#!/usr/bin/env python3
"""
MVP Test Script - Test each component step by step.
Run this to verify your setup is working.
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def print_step(step_num, title):
    """Print a formatted step header."""
    print(f"\n{'='*60}")
    print(f"  STEP {step_num}: {title}")
    print(f"{'='*60}\n")

def print_result(success, message):
    """Print success or failure."""
    icon = "✅" if success else "❌"
    print(f"{icon} {message}")
    return success

def test_step_1_environment():
    """Test that environment variables are configured."""
    print_step(1, "CHECK ENVIRONMENT VARIABLES")

    required_vars = {
        "ANTHROPIC_API_KEY": "Claude AI API key",
        "MIXPANEL_PROJECT_ID": "Mixpanel project ID",
        "GMAIL_SENDER_EMAIL": "Gmail sender address",
        "BIGQUERY_PROJECT_ID": "BigQuery project ID",
    }

    all_good = True
    for var, description in required_vars.items():
        value = os.getenv(var)
        if value:
            # Show partial value for security
            masked = value[:8] + "..." if len(value) > 8 else "***"
            print_result(True, f"{var}: {masked}")
        else:
            print_result(False, f"{var}: NOT SET ({description})")
            all_good = False

    return all_good

def test_step_2_anthropic():
    """Test connection to Claude API."""
    print_step(2, "TEST CLAUDE AI CONNECTION")

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print_result(False, "ANTHROPIC_API_KEY not set - skipping")
        return False

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)

        # Simple test message
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=100,
            messages=[
                {"role": "user", "content": "Say 'Hello, Event Automation!' in exactly those words."}
            ]
        )

        response = message.content[0].text
        print_result(True, f"Claude responded: {response[:50]}...")
        return True

    except Exception as e:
        print_result(False, f"Claude connection failed: {str(e)}")
        return False

def test_step_3_mock_analysis():
    """Test the AI analysis with mock data."""
    print_step(3, "TEST AI ANALYSIS WITH MOCK DATA")

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print_result(False, "ANTHROPIC_API_KEY not set - skipping")
        return False

    # Mock user events (simulating Mixpanel data)
    mock_events = [
        {"event": "page_view", "properties": {"page": "/home", "distinct_id": "user_123"}, "time": 1703000000},
        {"event": "button_click", "properties": {"button": "signup", "distinct_id": "user_123"}, "time": 1703000060},
        {"event": "error", "properties": {"message": "Network timeout", "distinct_id": "user_123"}, "time": 1703000120},
        {"event": "page_view", "properties": {"page": "/signup", "distinct_id": "user_123"}, "time": 1703000180},
        {"event": "error", "properties": {"message": "Form validation failed", "distinct_id": "user_123"}, "time": 1703000240},
    ]

    print("Mock events created:")
    for event in mock_events:
        print(f"  - {event['event']}: {event.get('properties', {})}")

    try:
        import anthropic
        import json

        client = anthropic.Anthropic(api_key=api_key)

        prompt = f"""Analyze these user events and identify any bugs or issues.

User ID: user_123
Events:
{json.dumps(mock_events, indent=2)}

Provide a brief analysis in JSON format with:
- bugs_detected: list of any bugs/errors found
- summary: one sentence summary

Respond with ONLY valid JSON, no markdown."""

        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}]
        )

        response = message.content[0].text
        print(f"\nClaude's analysis:")
        print(response[:500])

        print_result(True, "AI analysis working!")
        return True

    except Exception as e:
        print_result(False, f"AI analysis failed: {str(e)}")
        return False

def test_step_4_mixpanel():
    """Test Mixpanel connection."""
    print_step(4, "TEST MIXPANEL CONNECTION")

    project_id = os.getenv("MIXPANEL_PROJECT_ID")
    username = os.getenv("MIXPANEL_SERVICE_ACCOUNT_USERNAME")
    secret = os.getenv("MIXPANEL_SERVICE_ACCOUNT_SECRET")

    if not all([project_id, username, secret]):
        print_result(False, "Mixpanel credentials not fully configured - skipping")
        print("  Set: MIXPANEL_PROJECT_ID, MIXPANEL_SERVICE_ACCOUNT_USERNAME, MIXPANEL_SERVICE_ACCOUNT_SECRET")
        return False

    try:
        from src.mixpanel_client import MixpanelClient

        client = MixpanelClient()
        # Try to get event names (lightweight call)
        event_names = client.get_event_names(hours=24)

        print_result(True, f"Connected! Found {len(event_names)} event types")
        if event_names:
            print(f"  Sample events: {event_names[:5]}")
        return True

    except Exception as e:
        print_result(False, f"Mixpanel connection failed: {str(e)}")
        return False

def test_step_5_bigquery():
    """Test BigQuery connection."""
    print_step(5, "TEST BIGQUERY CONNECTION")

    project_id = os.getenv("BIGQUERY_PROJECT_ID")
    creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

    if not project_id:
        print_result(False, "BIGQUERY_PROJECT_ID not set - skipping")
        return False

    if creds_path and not os.path.exists(creds_path):
        print_result(False, f"Credentials file not found: {creds_path}")
        return False

    try:
        from google.cloud import bigquery

        client = bigquery.Client(project=project_id)

        # Simple query to test connection
        query = "SELECT 1 as test"
        result = list(client.query(query).result())

        print_result(True, f"Connected to BigQuery project: {project_id}")
        return True

    except Exception as e:
        print_result(False, f"BigQuery connection failed: {str(e)}")
        return False

def test_step_6_gmail():
    """Test Gmail setup."""
    print_step(6, "TEST GMAIL SETUP")

    sender = os.getenv("GMAIL_SENDER_EMAIL")
    creds_path = os.getenv("GMAIL_CREDENTIALS_PATH", "credentials.json")
    token_path = os.getenv("GMAIL_TOKEN_PATH", "token.json")

    if not sender:
        print_result(False, "GMAIL_SENDER_EMAIL not set - skipping")
        return False

    print(f"  Sender email: {sender}")
    print(f"  Credentials file: {creds_path}")
    print(f"  Token file: {token_path}")

    if not os.path.exists(creds_path):
        print_result(False, f"Gmail credentials.json not found at: {creds_path}")
        print("\n  To set up Gmail:")
        print("  1. Go to https://console.cloud.google.com")
        print("  2. Create a project and enable Gmail API")
        print("  3. Create OAuth 2.0 credentials (Desktop app)")
        print("  4. Download and save as 'credentials.json'")
        print("  5. Run: python main.py --setup-gmail")
        return False

    if os.path.exists(token_path):
        print_result(True, "Gmail is configured and authenticated!")
        return True
    else:
        print_result(False, "Gmail not yet authenticated")
        print("  Run: python main.py --setup-gmail")
        return False

def run_all_tests():
    """Run all tests and show summary."""
    print("\n" + "="*60)
    print("  EVENT AUTOMATION - MVP TEST SUITE")
    print("  " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("="*60)

    results = {
        "Environment": test_step_1_environment(),
        "Claude AI": test_step_2_anthropic(),
        "AI Analysis": test_step_3_mock_analysis(),
        "Mixpanel": test_step_4_mixpanel(),
        "BigQuery": test_step_5_bigquery(),
        "Gmail": test_step_6_gmail(),
    }

    # Summary
    print("\n" + "="*60)
    print("  SUMMARY")
    print("="*60 + "\n")

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for name, result in results.items():
        icon = "✅" if result else "❌"
        print(f"  {icon} {name}")

    print(f"\n  {passed}/{total} tests passed")

    if passed == total:
        print("\n  🎉 All systems ready! Run: python main.py --run-once")
    else:
        print("\n  ⚠️  Some components need configuration.")
        print("  Fix the issues above and run this test again.")

    return passed == total

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
