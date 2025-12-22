"""
Configuration management for the Event Automation system.
Loads settings from environment variables.
"""

import os
from dataclasses import dataclass
from typing import List
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


@dataclass
class BigQueryConfig:
    """BigQuery configuration settings."""
    project_id: str
    dataset: str
    table: str
    credentials_path: str


@dataclass
class MixpanelConfig:
    """Mixpanel configuration settings."""
    api_secret: str
    project_id: str
    service_account_username: str
    service_account_secret: str


@dataclass
class AnthropicConfig:
    """Anthropic (Claude) API configuration."""
    api_key: str
    model: str = "claude-sonnet-4-20250514"


@dataclass
class GmailConfig:
    """Gmail configuration settings."""
    sender_email: str
    credentials_path: str
    token_path: str
    recipient_emails: List[str]


@dataclass
class SchedulerConfig:
    """Scheduler configuration settings."""
    report_time: str
    timezone: str
    lookback_hours: int


def get_bigquery_config() -> BigQueryConfig:
    """Get BigQuery configuration from environment variables."""
    return BigQueryConfig(
        project_id=os.getenv("BIGQUERY_PROJECT_ID", ""),
        dataset=os.getenv("BIGQUERY_DATASET", ""),
        table=os.getenv("BIGQUERY_TABLE", ""),
        credentials_path=os.getenv("GOOGLE_APPLICATION_CREDENTIALS", ""),
    )


def get_mixpanel_config() -> MixpanelConfig:
    """Get Mixpanel configuration from environment variables."""
    return MixpanelConfig(
        api_secret=os.getenv("MIXPANEL_API_SECRET", ""),
        project_id=os.getenv("MIXPANEL_PROJECT_ID", ""),
        service_account_username=os.getenv("MIXPANEL_SERVICE_ACCOUNT_USERNAME", ""),
        service_account_secret=os.getenv("MIXPANEL_SERVICE_ACCOUNT_SECRET", ""),
    )


def get_anthropic_config() -> AnthropicConfig:
    """Get Anthropic configuration from environment variables."""
    return AnthropicConfig(
        api_key=os.getenv("ANTHROPIC_API_KEY", ""),
        model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514"),
    )


def get_gmail_config() -> GmailConfig:
    """Get Gmail configuration from environment variables."""
    recipient_emails_str = os.getenv("REPORT_RECIPIENT_EMAILS", "")
    recipient_emails = [e.strip() for e in recipient_emails_str.split(",") if e.strip()]

    return GmailConfig(
        sender_email=os.getenv("GMAIL_SENDER_EMAIL", ""),
        credentials_path=os.getenv("GMAIL_CREDENTIALS_PATH", "credentials.json"),
        token_path=os.getenv("GMAIL_TOKEN_PATH", "token.json"),
        recipient_emails=recipient_emails,
    )


def get_scheduler_config() -> SchedulerConfig:
    """Get scheduler configuration from environment variables."""
    return SchedulerConfig(
        report_time=os.getenv("REPORT_TIME", "09:00"),
        timezone=os.getenv("TIMEZONE", "UTC"),
        lookback_hours=int(os.getenv("ANALYSIS_LOOKBACK_HOURS", "24")),
    )


def validate_config() -> bool:
    """Validate that all required configuration is present."""
    required_vars = [
        "BIGQUERY_PROJECT_ID",
        "MIXPANEL_PROJECT_ID",
        "ANTHROPIC_API_KEY",
        "GMAIL_SENDER_EMAIL",
        "REPORT_RECIPIENT_EMAILS",
    ]

    missing = [var for var in required_vars if not os.getenv(var)]

    if missing:
        print(f"Missing required environment variables: {', '.join(missing)}")
        return False

    return True
