"""
Mixpanel client for retrieving event data.
"""

import structlog
import requests
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from base64 import b64encode

from config import get_mixpanel_config, MixpanelConfig

logger = structlog.get_logger(__name__)


class MixpanelClient:
    """Client for interacting with Mixpanel Data Export API."""

    BASE_URL = "https://data.mixpanel.com/api/2.0"
    QUERY_URL = "https://mixpanel.com/api/2.0"

    def __init__(self, config: Optional[MixpanelConfig] = None):
        """
        Initialize the Mixpanel client.

        Args:
            config: Mixpanel configuration. If None, loads from environment.
        """
        self.config = config or get_mixpanel_config()
        self._session = None

    @property
    def session(self) -> requests.Session:
        """Lazy initialization of requests session with auth."""
        if self._session is None:
            self._session = requests.Session()

            # Use service account authentication
            auth_string = f"{self.config.service_account_username}:{self.config.service_account_secret}"
            encoded_auth = b64encode(auth_string.encode()).decode()

            self._session.headers.update({
                "Authorization": f"Basic {encoded_auth}",
                "Content-Type": "application/json",
            })

            logger.info("Mixpanel session initialized")

        return self._session

    def _make_request(
        self,
        endpoint: str,
        params: Dict[str, Any],
        base_url: Optional[str] = None
    ) -> Any:
        """
        Make an authenticated request to the Mixpanel API.

        Args:
            endpoint: API endpoint
            params: Query parameters
            base_url: Optional base URL override

        Returns:
            Parsed JSON response
        """
        url = f"{base_url or self.BASE_URL}/{endpoint}"

        logger.debug("Making Mixpanel API request", endpoint=endpoint, params=params)

        response = self.session.get(url, params=params)
        response.raise_for_status()

        return response

    def get_events_in_timeframe(
        self,
        hours: int = 24,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        event_names: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Export raw events from Mixpanel for the specified timeframe.

        Args:
            hours: Number of hours to look back (default: 24)
            start_time: Optional specific start time
            end_time: Optional specific end time
            event_names: Optional list of specific event names to filter

        Returns:
            List of event records
        """
        if end_time is None:
            end_time = datetime.utcnow()
        if start_time is None:
            start_time = end_time - timedelta(hours=hours)

        params = {
            "project_id": self.config.project_id,
            "from_date": start_time.strftime("%Y-%m-%d"),
            "to_date": end_time.strftime("%Y-%m-%d"),
        }

        if event_names:
            params["event"] = json.dumps(event_names)

        logger.info(
            "Exporting events from Mixpanel",
            from_date=params["from_date"],
            to_date=params["to_date"]
        )

        response = self._make_request("export", params)

        # Parse JSONL response (one JSON object per line)
        events = []
        for line in response.text.strip().split("\n"):
            if line:
                try:
                    event = json.loads(line)
                    events.append(event)
                except json.JSONDecodeError as e:
                    logger.warning("Failed to parse event line", error=str(e))

        logger.info("Retrieved events from Mixpanel", count=len(events))

        return events

    def get_events_for_user(
        self,
        user_id: str,
        hours: int = 24
    ) -> List[Dict[str, Any]]:
        """
        Get all events for a specific user.

        Args:
            user_id: The distinct_id of the user
            hours: Number of hours to look back

        Returns:
            List of events for the user
        """
        all_events = self.get_events_in_timeframe(hours=hours)

        # Filter events for the specific user
        user_events = [
            event for event in all_events
            if event.get("properties", {}).get("distinct_id") == user_id
        ]

        logger.debug(
            "Filtered events for user",
            user_id=user_id,
            total_events=len(all_events),
            user_events=len(user_events)
        )

        return user_events

    def get_distinct_users(self, hours: int = 24) -> List[str]:
        """
        Get list of distinct user IDs with events in the timeframe.

        Args:
            hours: Number of hours to look back

        Returns:
            List of distinct user IDs
        """
        events = self.get_events_in_timeframe(hours=hours)

        user_ids = set()
        for event in events:
            distinct_id = event.get("properties", {}).get("distinct_id")
            if distinct_id:
                user_ids.add(distinct_id)

        logger.info("Found distinct users", count=len(user_ids))

        return list(user_ids)

    def get_events_grouped_by_user(
        self,
        hours: int = 24
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get all events grouped by user ID.

        Args:
            hours: Number of hours to look back

        Returns:
            Dictionary mapping user IDs to their events
        """
        events = self.get_events_in_timeframe(hours=hours)

        grouped = {}
        for event in events:
            distinct_id = event.get("properties", {}).get("distinct_id")
            if distinct_id:
                if distinct_id not in grouped:
                    grouped[distinct_id] = []
                grouped[distinct_id].append(event)

        logger.info(
            "Grouped events by user",
            total_events=len(events),
            unique_users=len(grouped)
        )

        return grouped

    def get_event_names(self, hours: int = 24) -> List[str]:
        """
        Get list of unique event names in the timeframe.

        Args:
            hours: Number of hours to look back

        Returns:
            List of unique event names
        """
        events = self.get_events_in_timeframe(hours=hours)

        event_names = set()
        for event in events:
            name = event.get("event")
            if name:
                event_names.add(name)

        return sorted(list(event_names))

    def get_event_counts(self, hours: int = 24) -> Dict[str, int]:
        """
        Get count of each event type in the timeframe.

        Args:
            hours: Number of hours to look back

        Returns:
            Dictionary mapping event names to counts
        """
        events = self.get_events_in_timeframe(hours=hours)

        counts = {}
        for event in events:
            name = event.get("event", "unknown")
            counts[name] = counts.get(name, 0) + 1

        return dict(sorted(counts.items(), key=lambda x: x[1], reverse=True))

    def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user profile data from Mixpanel.

        Args:
            user_id: The distinct_id of the user

        Returns:
            User profile data or None if not found
        """
        params = {
            "project_id": self.config.project_id,
            "distinct_id": user_id,
        }

        try:
            response = self._make_request(
                "engage",
                params,
                base_url=self.QUERY_URL
            )
            data = response.json()

            if data.get("results"):
                return data["results"][0]

            return None
        except Exception as e:
            logger.warning("Failed to get user profile", user_id=user_id, error=str(e))
            return None
