"""
BigQuery client for retrieving bug data and storing analysis results.
"""

import structlog
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from google.cloud import bigquery
from google.oauth2 import service_account

from config import get_bigquery_config, BigQueryConfig

logger = structlog.get_logger(__name__)


class BigQueryClient:
    """Client for interacting with BigQuery for bug data operations."""

    def __init__(self, config: Optional[BigQueryConfig] = None):
        """
        Initialize the BigQuery client.

        Args:
            config: BigQuery configuration. If None, loads from environment.
        """
        self.config = config or get_bigquery_config()
        self._client = None

    @property
    def client(self) -> bigquery.Client:
        """Lazy initialization of BigQuery client."""
        if self._client is None:
            if self.config.credentials_path:
                credentials = service_account.Credentials.from_service_account_file(
                    self.config.credentials_path
                )
                self._client = bigquery.Client(
                    project=self.config.project_id,
                    credentials=credentials
                )
            else:
                # Use default credentials (e.g., from environment)
                self._client = bigquery.Client(project=self.config.project_id)

            logger.info("BigQuery client initialized", project=self.config.project_id)

        return self._client

    def get_bugs_in_timeframe(
        self,
        hours: int = 24,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve bugs from the specified timeframe.

        Args:
            hours: Number of hours to look back (default: 24)
            start_time: Optional specific start time
            end_time: Optional specific end time

        Returns:
            List of bug records as dictionaries
        """
        if end_time is None:
            end_time = datetime.utcnow()
        if start_time is None:
            start_time = end_time - timedelta(hours=hours)

        table_ref = f"{self.config.project_id}.{self.config.dataset}.{self.config.table}"

        query = f"""
        SELECT *
        FROM `{table_ref}`
        WHERE created_at >= @start_time
          AND created_at < @end_time
        ORDER BY created_at DESC
        """

        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("start_time", "TIMESTAMP", start_time),
                bigquery.ScalarQueryParameter("end_time", "TIMESTAMP", end_time),
            ]
        )

        logger.info(
            "Querying bugs from BigQuery",
            start_time=start_time.isoformat(),
            end_time=end_time.isoformat()
        )

        query_job = self.client.query(query, job_config=job_config)
        results = query_job.result()

        bugs = [dict(row) for row in results]
        logger.info("Retrieved bugs from BigQuery", count=len(bugs))

        return bugs

    def get_users_with_events(self, hours: int = 24) -> List[str]:
        """
        Get distinct user IDs that have events in the specified timeframe.

        Args:
            hours: Number of hours to look back

        Returns:
            List of distinct user IDs
        """
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)

        table_ref = f"{self.config.project_id}.{self.config.dataset}.{self.config.table}"

        query = f"""
        SELECT DISTINCT user_id
        FROM `{table_ref}`
        WHERE created_at >= @start_time
          AND created_at < @end_time
          AND user_id IS NOT NULL
        """

        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("start_time", "TIMESTAMP", start_time),
                bigquery.ScalarQueryParameter("end_time", "TIMESTAMP", end_time),
            ]
        )

        query_job = self.client.query(query, job_config=job_config)
        results = query_job.result()

        user_ids = [row.user_id for row in results]
        logger.info("Retrieved distinct users", count=len(user_ids))

        return user_ids

    def get_events_for_user(
        self,
        user_id: str,
        hours: int = 24
    ) -> List[Dict[str, Any]]:
        """
        Get all events for a specific user in the timeframe.

        Args:
            user_id: The user ID to query
            hours: Number of hours to look back

        Returns:
            List of event records for the user
        """
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)

        table_ref = f"{self.config.project_id}.{self.config.dataset}.{self.config.table}"

        query = f"""
        SELECT *
        FROM `{table_ref}`
        WHERE user_id = @user_id
          AND created_at >= @start_time
          AND created_at < @end_time
        ORDER BY created_at ASC
        """

        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("user_id", "STRING", user_id),
                bigquery.ScalarQueryParameter("start_time", "TIMESTAMP", start_time),
                bigquery.ScalarQueryParameter("end_time", "TIMESTAMP", end_time),
            ]
        )

        query_job = self.client.query(query, job_config=job_config)
        results = query_job.result()

        events = [dict(row) for row in results]
        logger.debug("Retrieved events for user", user_id=user_id, count=len(events))

        return events

    def save_user_analysis(
        self,
        user_id: str,
        analysis: Dict[str, Any],
        analysis_date: datetime
    ) -> None:
        """
        Save individual user analysis results to BigQuery.

        Args:
            user_id: The user ID analyzed
            analysis: The analysis results dictionary
            analysis_date: The date of analysis
        """
        table_ref = f"{self.config.project_id}.{self.config.dataset}.user_analyses"

        rows_to_insert = [{
            "user_id": user_id,
            "analysis_date": analysis_date.isoformat(),
            "analysis_result": str(analysis),
            "created_at": datetime.utcnow().isoformat(),
        }]

        errors = self.client.insert_rows_json(table_ref, rows_to_insert)

        if errors:
            logger.error("Failed to insert user analysis", errors=errors)
            raise Exception(f"BigQuery insert failed: {errors}")

        logger.debug("Saved user analysis", user_id=user_id)

    def save_daily_report(
        self,
        report_date: datetime,
        summary: Dict[str, Any],
        patterns: List[Dict[str, Any]],
        signals: Dict[str, List[str]]
    ) -> None:
        """
        Save daily aggregated report to BigQuery.

        Args:
            report_date: The date of the report
            summary: Summary statistics
            patterns: Identified patterns
            signals: New and known signals
        """
        table_ref = f"{self.config.project_id}.{self.config.dataset}.daily_reports"

        rows_to_insert = [{
            "report_date": report_date.isoformat(),
            "summary": str(summary),
            "patterns": str(patterns),
            "new_signals": str(signals.get("new", [])),
            "known_signals": str(signals.get("known", [])),
            "created_at": datetime.utcnow().isoformat(),
        }]

        errors = self.client.insert_rows_json(table_ref, rows_to_insert)

        if errors:
            logger.error("Failed to insert daily report", errors=errors)
            raise Exception(f"BigQuery insert failed: {errors}")

        logger.info("Saved daily report", report_date=report_date.isoformat())

    def create_analysis_tables_if_not_exist(self) -> None:
        """Create the analysis result tables if they don't exist."""
        dataset_ref = f"{self.config.project_id}.{self.config.dataset}"

        # User analyses table
        user_analyses_schema = [
            bigquery.SchemaField("user_id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("analysis_date", "TIMESTAMP", mode="REQUIRED"),
            bigquery.SchemaField("analysis_result", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("created_at", "TIMESTAMP", mode="REQUIRED"),
        ]

        user_analyses_table = bigquery.Table(
            f"{dataset_ref}.user_analyses",
            schema=user_analyses_schema
        )

        try:
            self.client.create_table(user_analyses_table)
            logger.info("Created user_analyses table")
        except Exception as e:
            if "Already Exists" in str(e):
                logger.debug("user_analyses table already exists")
            else:
                raise

        # Daily reports table
        daily_reports_schema = [
            bigquery.SchemaField("report_date", "TIMESTAMP", mode="REQUIRED"),
            bigquery.SchemaField("summary", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("patterns", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("new_signals", "STRING"),
            bigquery.SchemaField("known_signals", "STRING"),
            bigquery.SchemaField("created_at", "TIMESTAMP", mode="REQUIRED"),
        ]

        daily_reports_table = bigquery.Table(
            f"{dataset_ref}.daily_reports",
            schema=daily_reports_schema
        )

        try:
            self.client.create_table(daily_reports_table)
            logger.info("Created daily_reports table")
        except Exception as e:
            if "Already Exists" in str(e):
                logger.debug("daily_reports table already exists")
            else:
                raise
