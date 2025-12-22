"""
Scheduler for running the daily report automation.
"""

import structlog
import time
from datetime import datetime
from typing import Callable, Optional

import schedule
import pytz

from config import get_scheduler_config, SchedulerConfig

logger = structlog.get_logger(__name__)


class ReportScheduler:
    """Scheduler for running daily report generation."""

    def __init__(self, config: Optional[SchedulerConfig] = None):
        """
        Initialize the scheduler.

        Args:
            config: Scheduler configuration. If None, loads from environment.
        """
        self.config = config or get_scheduler_config()
        self.timezone = pytz.timezone(self.config.timezone)
        self._job = None
        self._running = False

    def schedule_daily_report(self, job_func: Callable) -> None:
        """
        Schedule the daily report job.

        Args:
            job_func: The function to run for generating the report
        """
        # Parse the report time
        report_time = self.config.report_time

        logger.info(
            "Scheduling daily report",
            time=report_time,
            timezone=self.config.timezone
        )

        # Schedule the job
        self._job = schedule.every().day.at(report_time).do(
            self._run_job_with_logging, job_func
        )

        logger.info(
            "Daily report scheduled",
            next_run=self._job.next_run.isoformat()
        )

    def _run_job_with_logging(self, job_func: Callable) -> None:
        """
        Wrapper to run job with logging.

        Args:
            job_func: The job function to run
        """
        logger.info("Starting scheduled report generation")
        start_time = datetime.utcnow()

        try:
            job_func()
            duration = (datetime.utcnow() - start_time).total_seconds()
            logger.info("Scheduled report completed", duration_seconds=duration)
        except Exception as e:
            logger.error("Scheduled report failed", error=str(e))
            raise

    def run_now(self, job_func: Callable) -> None:
        """
        Run the report job immediately.

        Args:
            job_func: The job function to run
        """
        logger.info("Running report job immediately")
        self._run_job_with_logging(job_func)

    def start(self) -> None:
        """Start the scheduler loop."""
        self._running = True
        logger.info("Scheduler started")

        while self._running:
            schedule.run_pending()
            time.sleep(60)  # Check every minute

    def stop(self) -> None:
        """Stop the scheduler loop."""
        self._running = False
        logger.info("Scheduler stopped")

    def get_next_run_time(self) -> Optional[datetime]:
        """
        Get the next scheduled run time.

        Returns:
            Next run datetime or None if no job scheduled
        """
        if self._job:
            return self._job.next_run
        return None

    def clear_schedule(self) -> None:
        """Clear all scheduled jobs."""
        schedule.clear()
        self._job = None
        logger.info("Schedule cleared")


def create_cron_job(command: str, schedule_time: str = "09:00") -> str:
    """
    Generate a cron job entry for system crontab.

    Args:
        command: The command to run
        schedule_time: Time in HH:MM format

    Returns:
        Cron job entry string
    """
    hour, minute = schedule_time.split(":")

    cron_entry = f"{minute} {hour} * * * {command}"

    return cron_entry


def setup_systemd_timer(
    service_name: str = "event-automation",
    working_dir: str = "/home/user/Event-automation",
    schedule_time: str = "09:00"
) -> tuple:
    """
    Generate systemd service and timer unit files.

    Args:
        service_name: Name for the systemd service
        working_dir: Working directory for the script
        schedule_time: Time in HH:MM format

    Returns:
        Tuple of (service_content, timer_content)
    """
    hour, minute = schedule_time.split(":")

    service_content = f"""[Unit]
Description=Event Automation Daily Report
After=network.target

[Service]
Type=oneshot
WorkingDirectory={working_dir}
ExecStart=/usr/bin/python3 {working_dir}/main.py --run-once
User=user
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
"""

    timer_content = f"""[Unit]
Description=Run Event Automation Daily Report

[Timer]
OnCalendar=*-*-* {hour}:{minute}:00
Persistent=true

[Install]
WantedBy=timers.target
"""

    return service_content, timer_content


if __name__ == "__main__":
    # Example: Print systemd unit files
    service, timer = setup_systemd_timer()

    print("=== Service File (/etc/systemd/system/event-automation.service) ===")
    print(service)

    print("\n=== Timer File (/etc/systemd/system/event-automation.timer) ===")
    print(timer)

    print("\n=== Cron Job Entry ===")
    cron = create_cron_job(
        "cd /home/user/Event-automation && /usr/bin/python3 main.py --run-once"
    )
    print(cron)
