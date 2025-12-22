"""
Gmail email sender for delivering reports.
"""

import structlog
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import List, Optional
from pathlib import Path
import os

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from config import get_gmail_config, GmailConfig

logger = structlog.get_logger(__name__)

# Gmail API scopes
SCOPES = ['https://www.googleapis.com/auth/gmail.send']


class GmailSender:
    """Gmail client for sending email reports."""

    def __init__(self, config: Optional[GmailConfig] = None):
        """
        Initialize the Gmail sender.

        Args:
            config: Gmail configuration. If None, loads from environment.
        """
        self.config = config or get_gmail_config()
        self._service = None

    def _get_credentials(self) -> Credentials:
        """
        Get or refresh Gmail API credentials.

        Returns:
            Valid credentials object
        """
        creds = None

        # Check if token file exists
        if os.path.exists(self.config.token_path):
            creds = Credentials.from_authorized_user_file(
                self.config.token_path, SCOPES
            )

        # If no valid credentials, authenticate
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(self.config.credentials_path):
                    raise FileNotFoundError(
                        f"Gmail credentials file not found: {self.config.credentials_path}\n"
                        "Please download OAuth credentials from Google Cloud Console."
                    )

                flow = InstalledAppFlow.from_client_secrets_file(
                    self.config.credentials_path, SCOPES
                )
                creds = flow.run_local_server(port=0)

            # Save credentials for future runs
            with open(self.config.token_path, 'w') as token:
                token.write(creds.to_json())

            logger.info("Gmail credentials refreshed")

        return creds

    @property
    def service(self):
        """Lazy initialization of Gmail API service."""
        if self._service is None:
            creds = self._get_credentials()
            self._service = build('gmail', 'v1', credentials=creds)
            logger.info("Gmail service initialized")
        return self._service

    def send_report(
        self,
        subject: str,
        html_content: str,
        recipients: Optional[List[str]] = None,
        text_content: Optional[str] = None
    ) -> bool:
        """
        Send an HTML email report.

        Args:
            subject: Email subject line
            html_content: HTML body of the email
            recipients: List of recipient emails. If None, uses config.
            text_content: Optional plain text version

        Returns:
            True if sent successfully, False otherwise
        """
        recipients = recipients or self.config.recipient_emails

        if not recipients:
            logger.error("No recipients specified for email")
            return False

        try:
            # Create multipart message
            message = MIMEMultipart('alternative')
            message['Subject'] = subject
            message['From'] = self.config.sender_email
            message['To'] = ', '.join(recipients)

            # Add plain text version (optional fallback)
            if text_content:
                text_part = MIMEText(text_content, 'plain')
                message.attach(text_part)

            # Add HTML version
            html_part = MIMEText(html_content, 'html')
            message.attach(html_part)

            # Encode the message
            raw_message = base64.urlsafe_b64encode(
                message.as_bytes()
            ).decode('utf-8')

            # Send the email
            self.service.users().messages().send(
                userId='me',
                body={'raw': raw_message}
            ).execute()

            logger.info(
                "Email sent successfully",
                subject=subject,
                recipients=recipients
            )
            return True

        except Exception as e:
            logger.error("Failed to send email", error=str(e))
            return False

    def send_daily_report(
        self,
        html_content: str,
        report_date: Optional[datetime] = None
    ) -> bool:
        """
        Send the daily bug analysis report.

        Args:
            html_content: The HTML report content
            report_date: Date of the report (default: today)

        Returns:
            True if sent successfully
        """
        if report_date is None:
            report_date = datetime.utcnow()

        subject = f"🐛 Daily Bug Analysis Report - {report_date.strftime('%Y-%m-%d')}"

        return self.send_report(
            subject=subject,
            html_content=html_content
        )

    def send_error_notification(
        self,
        error_message: str,
        error_details: Optional[str] = None
    ) -> bool:
        """
        Send an error notification email.

        Args:
            error_message: Brief error description
            error_details: Detailed error information

        Returns:
            True if sent successfully
        """
        html_content = f"""
        <html>
        <body>
            <h2>⚠️ Event Automation Error</h2>
            <p><strong>Error:</strong> {error_message}</p>
            {f'<pre>{error_details}</pre>' if error_details else ''}
            <p>Please check the logs for more details.</p>
            <hr>
            <small>Sent by Event Automation System at {datetime.utcnow().isoformat()}</small>
        </body>
        </html>
        """

        return self.send_report(
            subject=f"⚠️ Event Automation Error - {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}",
            html_content=html_content
        )


def setup_gmail_credentials():
    """
    Interactive setup for Gmail OAuth credentials.
    Run this once to authorize the application.
    """
    config = get_gmail_config()

    print("Gmail OAuth Setup")
    print("=" * 50)
    print(f"Credentials file: {config.credentials_path}")
    print(f"Token will be saved to: {config.token_path}")
    print()

    if not os.path.exists(config.credentials_path):
        print("ERROR: Credentials file not found!")
        print()
        print("Please follow these steps:")
        print("1. Go to Google Cloud Console (https://console.cloud.google.com)")
        print("2. Create a new project or select existing one")
        print("3. Enable the Gmail API")
        print("4. Create OAuth 2.0 credentials (Desktop application)")
        print("5. Download the credentials JSON file")
        print(f"6. Save it as: {config.credentials_path}")
        return False

    sender = GmailSender(config)

    try:
        # This will trigger the OAuth flow
        _ = sender.service
        print("✅ Gmail authentication successful!")
        print(f"Token saved to: {config.token_path}")
        return True
    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        return False


if __name__ == "__main__":
    setup_gmail_credentials()
