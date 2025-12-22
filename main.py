#!/usr/bin/env python3
"""
Event Automation - Daily Bug Report System

Main orchestration script that:
1. Fetches events from Mixpanel
2. Queries bug data from BigQuery
3. Analyzes each user's events with AI (Claude)
4. Saves individual user analyses to BigQuery
5. Performs aggregate analysis across all users
6. Generates and sends daily email report
"""

import sys
import argparse
import signal
import structlog
from datetime import datetime, timedelta
from typing import List, Dict, Any

from config import (
    validate_config,
    get_scheduler_config,
    get_bigquery_config,
)
from src.bigquery_client import BigQueryClient
from src.mixpanel_client import MixpanelClient
from src.ai_analyzer import AIAnalyzer
from src.email_sender import GmailSender
from src.scheduler import ReportScheduler

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.dev.ConsoleRenderer()
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True
)

logger = structlog.get_logger(__name__)


class EventAutomation:
    """Main orchestrator for the event automation pipeline."""

    def __init__(self):
        """Initialize all components."""
        self.bigquery = BigQueryClient()
        self.mixpanel = MixpanelClient()
        self.analyzer = AIAnalyzer()
        self.email_sender = GmailSender()
        self.scheduler_config = get_scheduler_config()

    def run_daily_report(self) -> bool:
        """
        Execute the full daily report pipeline.

        Returns:
            True if successful, False otherwise
        """
        logger.info("Starting daily report pipeline")
        start_time = datetime.utcnow()
        lookback_hours = self.scheduler_config.lookback_hours

        try:
            # Step 1: Ensure analysis tables exist
            logger.info("Setting up analysis tables")
            self.bigquery.create_analysis_tables_if_not_exist()

            # Step 2: Get events grouped by user from Mixpanel
            logger.info("Fetching events from Mixpanel", hours=lookback_hours)
            events_by_user = self.mixpanel.get_events_grouped_by_user(
                hours=lookback_hours
            )

            if not events_by_user:
                logger.warning("No events found in the specified timeframe")
                return self._send_empty_report()

            # Step 3: Analyze each user individually
            logger.info("Analyzing individual users", user_count=len(events_by_user))
            user_analyses = self._analyze_all_users(events_by_user)

            # Step 4: Perform aggregate analysis
            analysis_period = f"Last {lookback_hours} hours ({start_time.strftime('%Y-%m-%d')})"
            logger.info("Performing aggregate analysis")
            aggregate_analysis = self.analyzer.analyze_aggregate(
                user_analyses,
                analysis_period
            )

            # Step 5: Save daily report to BigQuery
            logger.info("Saving report to BigQuery")
            self._save_report(aggregate_analysis)

            # Step 6: Generate and send email report
            logger.info("Generating email report")
            html_report = self.analyzer.generate_report_html(aggregate_analysis)

            logger.info("Sending email report")
            success = self.email_sender.send_daily_report(html_report)

            duration = (datetime.utcnow() - start_time).total_seconds()
            logger.info(
                "Daily report pipeline completed",
                success=success,
                duration_seconds=duration,
                users_analyzed=len(user_analyses)
            )

            return success

        except Exception as e:
            logger.exception("Daily report pipeline failed")
            self._send_error_notification(str(e))
            return False

    def _analyze_all_users(
        self,
        events_by_user: Dict[str, List[Dict[str, Any]]]
    ) -> List[Dict[str, Any]]:
        """
        Analyze events for all users.

        Args:
            events_by_user: Dictionary mapping user IDs to their events

        Returns:
            List of user analysis results
        """
        analyses = []
        total_users = len(events_by_user)

        for idx, (user_id, events) in enumerate(events_by_user.items(), 1):
            logger.info(
                "Analyzing user",
                user_id=user_id,
                progress=f"{idx}/{total_users}",
                event_count=len(events)
            )

            try:
                analysis = self.analyzer.analyze_user(user_id, events)

                # Save individual user analysis to BigQuery
                self.bigquery.save_user_analysis(
                    user_id=user_id,
                    analysis=analysis,
                    analysis_date=datetime.utcnow()
                )

                analyses.append(analysis)

            except Exception as e:
                logger.error(
                    "Failed to analyze user",
                    user_id=user_id,
                    error=str(e)
                )
                analyses.append({
                    "user_id": user_id,
                    "error": str(e)
                })

        return analyses

    def _save_report(self, aggregate_analysis: Dict[str, Any]) -> None:
        """
        Save the aggregate report to BigQuery.

        Args:
            aggregate_analysis: The aggregate analysis results
        """
        summary = aggregate_analysis.get("summary", {})
        patterns = aggregate_analysis.get("patterns", [])
        signals = {
            "new": aggregate_analysis.get("new_signals", []),
            "known": aggregate_analysis.get("known_signals", [])
        }

        self.bigquery.save_daily_report(
            report_date=datetime.utcnow(),
            summary=summary,
            patterns=patterns,
            signals=signals
        )

    def _send_empty_report(self) -> bool:
        """Send a notification when no events were found."""
        html_content = """
        <html>
        <body>
            <h2>Daily Bug Analysis Report</h2>
            <p>No events were found in the specified timeframe.</p>
            <p>This could mean:</p>
            <ul>
                <li>No user activity in the past 24 hours</li>
                <li>Mixpanel connection issues</li>
                <li>Event filtering excluded all events</li>
            </ul>
        </body>
        </html>
        """
        return self.email_sender.send_daily_report(html_content)

    def _send_error_notification(self, error_message: str) -> None:
        """Send an error notification email."""
        try:
            self.email_sender.send_error_notification(
                error_message=error_message,
                error_details=None
            )
        except Exception as e:
            logger.error("Failed to send error notification", error=str(e))


def run_scheduler():
    """Run the automation on a schedule."""
    logger.info("Starting scheduler mode")

    if not validate_config():
        logger.error("Configuration validation failed")
        sys.exit(1)

    automation = EventAutomation()
    scheduler = ReportScheduler()

    # Handle graceful shutdown
    def signal_handler(signum, frame):
        logger.info("Received shutdown signal")
        scheduler.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Schedule the daily report
    scheduler.schedule_daily_report(automation.run_daily_report)

    logger.info(
        "Scheduler running",
        next_run=scheduler.get_next_run_time().isoformat() if scheduler.get_next_run_time() else "Unknown"
    )

    # Start the scheduler loop
    scheduler.start()


def run_once():
    """Run the report generation once immediately."""
    logger.info("Running single report generation")

    if not validate_config():
        logger.error("Configuration validation failed")
        sys.exit(1)

    automation = EventAutomation()
    success = automation.run_daily_report()

    if success:
        logger.info("Report generation completed successfully")
        sys.exit(0)
    else:
        logger.error("Report generation failed")
        sys.exit(1)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Event Automation - Daily Bug Report System"
    )

    parser.add_argument(
        "--run-once",
        action="store_true",
        help="Run the report generation once and exit"
    )

    parser.add_argument(
        "--schedule",
        action="store_true",
        help="Run in scheduler mode (default)"
    )

    parser.add_argument(
        "--setup-gmail",
        action="store_true",
        help="Run Gmail OAuth setup"
    )

    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate configuration only"
    )

    args = parser.parse_args()

    if args.setup_gmail:
        from src.email_sender import setup_gmail_credentials
        setup_gmail_credentials()
        return

    if args.validate:
        if validate_config():
            print("✅ Configuration is valid")
            sys.exit(0)
        else:
            print("❌ Configuration validation failed")
            sys.exit(1)

    if args.run_once:
        run_once()
    else:
        run_scheduler()


if __name__ == "__main__":
    main()
