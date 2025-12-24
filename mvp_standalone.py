#!/usr/bin/env python3
"""
STANDALONE MVP - Simplest possible version that works.

This script demonstrates the core flow without all the integrations.
It uses:
- Mock data instead of Mixpanel (you can replace later)
- Claude AI for analysis (real)
- Console output instead of Gmail (you can replace later)
- No database (you can add later)

Run with: python mvp_standalone.py
"""

import os
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def get_mock_events():
    """
    MVP: Return mock events simulating Mixpanel data.
    LATER: Replace with real Mixpanel API call.
    """
    print("📥 Fetching events (using mock data for MVP)...")

    # Simulate events from 3 users
    mock_data = {
        "user_001": [
            {"event": "app_open", "time": "2024-01-15 09:00:00", "properties": {"platform": "ios"}},
            {"event": "login", "time": "2024-01-15 09:01:00", "properties": {"method": "google"}},
            {"event": "error", "time": "2024-01-15 09:02:00", "properties": {"type": "network_timeout", "screen": "dashboard"}},
            {"event": "retry_action", "time": "2024-01-15 09:02:30", "properties": {"action": "load_dashboard"}},
            {"event": "page_view", "time": "2024-01-15 09:03:00", "properties": {"page": "dashboard"}},
        ],
        "user_002": [
            {"event": "app_open", "time": "2024-01-15 10:00:00", "properties": {"platform": "android"}},
            {"event": "page_view", "time": "2024-01-15 10:01:00", "properties": {"page": "settings"}},
            {"event": "crash", "time": "2024-01-15 10:02:00", "properties": {"reason": "null_pointer", "screen": "settings"}},
        ],
        "user_003": [
            {"event": "app_open", "time": "2024-01-15 11:00:00", "properties": {"platform": "ios"}},
            {"event": "purchase_started", "time": "2024-01-15 11:05:00", "properties": {"item": "premium"}},
            {"event": "error", "time": "2024-01-15 11:06:00", "properties": {"type": "payment_failed", "reason": "card_declined"}},
            {"event": "support_contact", "time": "2024-01-15 11:10:00", "properties": {"reason": "payment_issue"}},
        ],
    }

    print(f"   Found {len(mock_data)} users with events")
    return mock_data


def analyze_user_with_ai(user_id: str, events: list) -> dict:
    """
    Analyze a single user's events with Claude AI.
    This is the REAL AI call - the core of the system.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")

    if not api_key:
        print("   ⚠️  No ANTHROPIC_API_KEY - using mock analysis")
        return {
            "user_id": user_id,
            "bugs": ["Mock bug detected"],
            "summary": "This is a mock analysis. Set ANTHROPIC_API_KEY for real AI analysis."
        }

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)

        prompt = f"""You are analyzing user behavior events to find bugs and issues.

User ID: {user_id}
Events (chronological order):
{json.dumps(events, indent=2)}

Analyze these events and respond with JSON only (no markdown):
{{
    "user_id": "{user_id}",
    "bugs_found": [
        {{"type": "error type", "description": "what happened", "severity": "high/medium/low"}}
    ],
    "user_journey": "brief description of what the user tried to do",
    "friction_points": ["any issues the user encountered"],
    "recommendation": "what should be fixed"
}}"""

        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        )

        response_text = message.content[0].text

        # Parse JSON from response
        try:
            # Try to find JSON in response
            if "{" in response_text:
                start = response_text.find("{")
                end = response_text.rfind("}") + 1
                return json.loads(response_text[start:end])
        except json.JSONDecodeError:
            pass

        return {"user_id": user_id, "raw_analysis": response_text}

    except Exception as e:
        return {"user_id": user_id, "error": str(e)}


def aggregate_analyses(user_analyses: list) -> dict:
    """
    Combine all user analyses to find patterns.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")

    if not api_key:
        return {
            "total_users": len(user_analyses),
            "summary": "Mock aggregate analysis",
            "patterns": ["Mock pattern"],
        }

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)

        prompt = f"""You are creating a daily bug report from individual user analyses.

Individual User Analyses:
{json.dumps(user_analyses, indent=2)}

Create an aggregate report. Respond with JSON only:
{{
    "total_users_analyzed": {len(user_analyses)},
    "users_with_bugs": 0,
    "critical_bugs": [
        {{"bug": "description", "affected_users": ["user_ids"], "priority": "high/medium/low"}}
    ],
    "patterns_detected": [
        {{"pattern": "description", "frequency": "how often"}}
    ],
    "top_recommendations": [
        "recommendation 1",
        "recommendation 2"
    ],
    "executive_summary": "2-3 sentence summary for stakeholders"
}}"""

        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}]
        )

        response_text = message.content[0].text

        try:
            if "{" in response_text:
                start = response_text.find("{")
                end = response_text.rfind("}") + 1
                return json.loads(response_text[start:end])
        except json.JSONDecodeError:
            pass

        return {"raw_analysis": response_text}

    except Exception as e:
        return {"error": str(e)}


def generate_report(aggregate: dict) -> str:
    """
    Generate a simple text report.
    MVP: Console output. LATER: HTML email.
    """
    report = f"""
╔══════════════════════════════════════════════════════════════╗
║              DAILY BUG ANALYSIS REPORT                       ║
║              {datetime.now().strftime('%Y-%m-%d %H:%M')}                              ║
╚══════════════════════════════════════════════════════════════╝

📊 SUMMARY
─────────────────────────────────────────────────────────────────
Users Analyzed: {aggregate.get('total_users_analyzed', 'N/A')}
Users with Bugs: {aggregate.get('users_with_bugs', 'N/A')}

📝 EXECUTIVE SUMMARY
─────────────────────────────────────────────────────────────────
{aggregate.get('executive_summary', 'No summary available')}

🔴 CRITICAL BUGS
─────────────────────────────────────────────────────────────────"""

    bugs = aggregate.get('critical_bugs', [])
    if bugs:
        for bug in bugs:
            report += f"\n• [{bug.get('priority', '?').upper()}] {bug.get('bug', 'Unknown')}"
            report += f"\n  Affected: {', '.join(bug.get('affected_users', []))}"
    else:
        report += "\nNo critical bugs detected."

    report += """

📈 PATTERNS DETECTED
─────────────────────────────────────────────────────────────────"""

    patterns = aggregate.get('patterns_detected', [])
    if patterns:
        for pattern in patterns:
            report += f"\n• {pattern.get('pattern', 'Unknown')} ({pattern.get('frequency', '?')})"
    else:
        report += "\nNo significant patterns detected."

    report += """

✅ RECOMMENDATIONS
─────────────────────────────────────────────────────────────────"""

    recommendations = aggregate.get('top_recommendations', [])
    if recommendations:
        for i, rec in enumerate(recommendations, 1):
            report += f"\n{i}. {rec}"
    else:
        report += "\nNo recommendations."

    report += "\n\n" + "═" * 65 + "\n"

    return report


def send_report(report: str, recipient: str = None):
    """
    Send the report.
    MVP: Print to console. LATER: Send via Gmail.
    """
    print("\n📧 SENDING REPORT...")
    print("   (MVP mode: printing to console instead of email)\n")
    print(report)

    # Save to file as backup
    filename = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(filename, 'w') as f:
        f.write(report)
    print(f"📁 Report saved to: {filename}")


def main():
    """Run the MVP pipeline."""
    print("\n" + "="*60)
    print("  EVENT AUTOMATION - MVP")
    print("  " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("="*60)

    # Step 1: Get events
    print("\n📌 STEP 1: Collect Events")
    events_by_user = get_mock_events()

    # Step 2: Analyze each user
    print("\n📌 STEP 2: Analyze Each User")
    user_analyses = []
    for user_id, events in events_by_user.items():
        print(f"   Analyzing {user_id}...")
        analysis = analyze_user_with_ai(user_id, events)
        user_analyses.append(analysis)
        print(f"   ✓ {user_id} done")

    # Step 3: Aggregate analyses
    print("\n📌 STEP 3: Find Patterns Across Users")
    aggregate = aggregate_analyses(user_analyses)
    print("   ✓ Aggregate analysis complete")

    # Step 4: Generate report
    print("\n📌 STEP 4: Generate Report")
    report = generate_report(aggregate)

    # Step 5: Send report
    print("\n📌 STEP 5: Send Report")
    send_report(report)

    print("\n✅ MVP Pipeline Complete!")
    print("\nNext steps to make this production-ready:")
    print("  1. Replace mock data with real Mixpanel API")
    print("  2. Add BigQuery to save analyses")
    print("  3. Add Gmail to send email reports")
    print("  4. Add scheduler for daily runs")


if __name__ == "__main__":
    main()
