"""
AI Analyzer using Claude API for event analysis.
"""

import structlog
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path

import anthropic

from config import get_anthropic_config, AnthropicConfig

logger = structlog.get_logger(__name__)


class AIAnalyzer:
    """AI-powered analyzer for user events using Claude API."""

    def __init__(self, config: Optional[AnthropicConfig] = None):
        """
        Initialize the AI Analyzer.

        Args:
            config: Anthropic configuration. If None, loads from environment.
        """
        self.config = config or get_anthropic_config()
        self._client = None
        self._user_prompt = None
        self._aggregate_prompt = None

    @property
    def client(self) -> anthropic.Anthropic:
        """Lazy initialization of Anthropic client."""
        if self._client is None:
            self._client = anthropic.Anthropic(api_key=self.config.api_key)
            logger.info("Anthropic client initialized", model=self.config.model)
        return self._client

    def load_prompts(self, prompts_dir: str = "prompts") -> None:
        """
        Load custom prompts from files.

        Args:
            prompts_dir: Directory containing prompt files
        """
        prompts_path = Path(prompts_dir)

        # Load user analysis prompt
        user_prompt_file = prompts_path / "user_analysis_prompt.txt"
        if user_prompt_file.exists():
            self._user_prompt = user_prompt_file.read_text()
            logger.info("Loaded custom user analysis prompt")
        else:
            self._user_prompt = self._get_default_user_prompt()
            logger.info("Using default user analysis prompt")

        # Load aggregate analysis prompt
        aggregate_prompt_file = prompts_path / "aggregate_analysis_prompt.txt"
        if aggregate_prompt_file.exists():
            self._aggregate_prompt = aggregate_prompt_file.read_text()
            logger.info("Loaded custom aggregate analysis prompt")
        else:
            self._aggregate_prompt = self._get_default_aggregate_prompt()
            logger.info("Using default aggregate analysis prompt")

    def _get_default_user_prompt(self) -> str:
        """Get the default user analysis prompt."""
        return """You are an expert at analyzing user behavior and identifying potential bugs, issues, and patterns in application usage.

Analyze the following user events and provide insights about:
1. Potential bugs or errors encountered
2. Unusual behavior patterns
3. User journey friction points
4. Any signals that indicate problems

User ID: {user_id}
Events Data:
{events_data}

Provide your analysis in the following JSON format:
{{
    "user_id": "{user_id}",
    "bugs_detected": [
        {{"type": "...", "description": "...", "severity": "high|medium|low", "evidence": "..."}}
    ],
    "behavior_patterns": [
        {{"pattern": "...", "description": "...", "significance": "..."}}
    ],
    "friction_points": [
        {{"location": "...", "description": "...", "impact": "..."}}
    ],
    "signals": [
        {{"type": "new|known", "signal": "...", "description": "..."}}
    ],
    "summary": "..."
}}"""

    def _get_default_aggregate_prompt(self) -> str:
        """Get the default aggregate analysis prompt."""
        return """You are an expert data analyst specializing in identifying patterns across multiple users and detecting systemic issues.

Analyze the following collection of individual user analyses and provide an aggregated report identifying:
1. Common patterns across users
2. New signals (issues appearing for the first time)
3. Known signals (recurring issues)
4. Severity trends
5. Recommendations for prioritization

Individual User Analyses:
{user_analyses}

Total Users Analyzed: {user_count}
Analysis Period: {analysis_period}

Provide your aggregate analysis in the following JSON format:
{{
    "summary": {{
        "total_users": {user_count},
        "users_with_issues": 0,
        "total_bugs_detected": 0,
        "critical_issues": 0
    }},
    "patterns": [
        {{"pattern": "...", "frequency": 0, "affected_users": 0, "description": "...", "priority": "high|medium|low"}}
    ],
    "new_signals": [
        {{"signal": "...", "first_detected": "...", "affected_users": [], "description": "..."}}
    ],
    "known_signals": [
        {{"signal": "...", "occurrence_count": 0, "trend": "increasing|stable|decreasing", "description": "..."}}
    ],
    "recommendations": [
        {{"priority": 1, "action": "...", "reason": "...", "affected_users": 0}}
    ],
    "report_narrative": "..."
}}"""

    def analyze_user(
        self,
        user_id: str,
        events: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyze events for a single user.

        Args:
            user_id: The user ID being analyzed
            events: List of events for this user

        Returns:
            Analysis results dictionary
        """
        if self._user_prompt is None:
            self.load_prompts()

        # Format events data for the prompt
        events_data = json.dumps(events, indent=2, default=str)

        # Build the prompt
        prompt = self._user_prompt.format(
            user_id=user_id,
            events_data=events_data
        )

        logger.info("Analyzing user events", user_id=user_id, event_count=len(events))

        try:
            message = self.client.messages.create(
                model=self.config.model,
                max_tokens=4096,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            response_text = message.content[0].text

            # Try to parse JSON from response
            analysis = self._parse_json_response(response_text)

            if analysis:
                analysis["user_id"] = user_id
                analysis["analyzed_at"] = datetime.utcnow().isoformat()
                analysis["event_count"] = len(events)

            logger.info("User analysis complete", user_id=user_id)

            return analysis

        except Exception as e:
            logger.error("User analysis failed", user_id=user_id, error=str(e))
            return {
                "user_id": user_id,
                "error": str(e),
                "analyzed_at": datetime.utcnow().isoformat()
            }

    def analyze_aggregate(
        self,
        user_analyses: List[Dict[str, Any]],
        analysis_period: str
    ) -> Dict[str, Any]:
        """
        Perform aggregate analysis across all user analyses.

        Args:
            user_analyses: List of individual user analysis results
            analysis_period: Description of the analysis time period

        Returns:
            Aggregate analysis results
        """
        if self._aggregate_prompt is None:
            self.load_prompts()

        # Format user analyses for the prompt
        analyses_data = json.dumps(user_analyses, indent=2, default=str)

        prompt = self._aggregate_prompt.format(
            user_analyses=analyses_data,
            user_count=len(user_analyses),
            analysis_period=analysis_period
        )

        logger.info("Performing aggregate analysis", user_count=len(user_analyses))

        try:
            message = self.client.messages.create(
                model=self.config.model,
                max_tokens=8192,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            response_text = message.content[0].text

            # Try to parse JSON from response
            analysis = self._parse_json_response(response_text)

            if analysis:
                analysis["generated_at"] = datetime.utcnow().isoformat()
                analysis["analysis_period"] = analysis_period

            logger.info("Aggregate analysis complete")

            return analysis

        except Exception as e:
            logger.error("Aggregate analysis failed", error=str(e))
            return {
                "error": str(e),
                "generated_at": datetime.utcnow().isoformat()
            }

    def _parse_json_response(self, response_text: str) -> Optional[Dict[str, Any]]:
        """
        Parse JSON from Claude's response.

        Args:
            response_text: The raw response text

        Returns:
            Parsed JSON dictionary or None
        """
        # Try to find JSON in the response
        try:
            # First, try direct parsing
            return json.loads(response_text)
        except json.JSONDecodeError:
            pass

        # Try to extract JSON from markdown code blocks
        import re
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response_text)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # Try to find JSON object in the text
        brace_start = response_text.find('{')
        brace_end = response_text.rfind('}')
        if brace_start != -1 and brace_end != -1:
            try:
                return json.loads(response_text[brace_start:brace_end + 1])
            except json.JSONDecodeError:
                pass

        logger.warning("Could not parse JSON from response")
        return {"raw_response": response_text}

    def generate_report_html(self, aggregate_analysis: Dict[str, Any]) -> str:
        """
        Generate an HTML report from the aggregate analysis.

        Args:
            aggregate_analysis: The aggregate analysis results

        Returns:
            HTML string for the report
        """
        summary = aggregate_analysis.get("summary", {})
        patterns = aggregate_analysis.get("patterns", [])
        new_signals = aggregate_analysis.get("new_signals", [])
        known_signals = aggregate_analysis.get("known_signals", [])
        recommendations = aggregate_analysis.get("recommendations", [])
        narrative = aggregate_analysis.get("report_narrative", "")

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Daily Bug Report - {aggregate_analysis.get('analysis_period', 'Today')}</title>
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 900px; margin: 0 auto; padding: 20px; }}
        h1 {{ color: #333; border-bottom: 2px solid #007bff; padding-bottom: 10px; }}
        h2 {{ color: #555; margin-top: 30px; }}
        .summary-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin: 20px 0; }}
        .summary-card {{ background: #f8f9fa; padding: 15px; border-radius: 8px; text-align: center; }}
        .summary-card h3 {{ margin: 0; font-size: 24px; color: #007bff; }}
        .summary-card p {{ margin: 5px 0 0; color: #666; }}
        .priority-high {{ border-left: 4px solid #dc3545; }}
        .priority-medium {{ border-left: 4px solid #ffc107; }}
        .priority-low {{ border-left: 4px solid #28a745; }}
        .item {{ background: #fff; border: 1px solid #ddd; padding: 15px; margin: 10px 0; border-radius: 5px; }}
        .badge {{ display: inline-block; padding: 3px 8px; border-radius: 3px; font-size: 12px; margin-right: 5px; }}
        .badge-new {{ background: #dc3545; color: white; }}
        .badge-known {{ background: #6c757d; color: white; }}
        .narrative {{ background: #e9ecef; padding: 20px; border-radius: 8px; font-style: italic; }}
    </style>
</head>
<body>
    <h1>🐛 Daily Bug Analysis Report</h1>
    <p><strong>Generated:</strong> {aggregate_analysis.get('generated_at', 'N/A')}</p>
    <p><strong>Period:</strong> {aggregate_analysis.get('analysis_period', 'Last 24 hours')}</p>

    <h2>📊 Summary</h2>
    <div class="summary-grid">
        <div class="summary-card">
            <h3>{summary.get('total_users', 0)}</h3>
            <p>Users Analyzed</p>
        </div>
        <div class="summary-card">
            <h3>{summary.get('users_with_issues', 0)}</h3>
            <p>Users with Issues</p>
        </div>
        <div class="summary-card">
            <h3>{summary.get('total_bugs_detected', 0)}</h3>
            <p>Bugs Detected</p>
        </div>
        <div class="summary-card">
            <h3>{summary.get('critical_issues', 0)}</h3>
            <p>Critical Issues</p>
        </div>
    </div>

    <h2>📝 Executive Summary</h2>
    <div class="narrative">{narrative}</div>

    <h2>🔴 New Signals</h2>
    {''.join(f'''
    <div class="item priority-high">
        <span class="badge badge-new">NEW</span>
        <strong>{signal.get('signal', 'Unknown')}</strong>
        <p>{signal.get('description', '')}</p>
        <small>First detected: {signal.get('first_detected', 'Today')} | Affected users: {len(signal.get('affected_users', []))}</small>
    </div>
    ''' for signal in new_signals) or '<p>No new signals detected.</p>'}

    <h2>🟡 Known Signals</h2>
    {''.join(f'''
    <div class="item priority-medium">
        <span class="badge badge-known">KNOWN</span>
        <strong>{signal.get('signal', 'Unknown')}</strong>
        <p>{signal.get('description', '')}</p>
        <small>Occurrences: {signal.get('occurrence_count', 0)} | Trend: {signal.get('trend', 'stable')}</small>
    </div>
    ''' for signal in known_signals) or '<p>No known signals in this period.</p>'}

    <h2>📈 Patterns Detected</h2>
    {''.join(f'''
    <div class="item priority-{pattern.get('priority', 'medium')}">
        <strong>{pattern.get('pattern', 'Unknown')}</strong>
        <p>{pattern.get('description', '')}</p>
        <small>Frequency: {pattern.get('frequency', 0)} | Affected users: {pattern.get('affected_users', 0)}</small>
    </div>
    ''' for pattern in patterns) or '<p>No significant patterns detected.</p>'}

    <h2>✅ Recommendations</h2>
    <ol>
    {''.join(f'''
    <li class="item">
        <strong>{rec.get('action', 'N/A')}</strong>
        <p>{rec.get('reason', '')}</p>
        <small>Affected users: {rec.get('affected_users', 0)}</small>
    </li>
    ''' for rec in sorted(recommendations, key=lambda x: x.get('priority', 99)))}
    </ol>

    <hr>
    <p style="color: #888; font-size: 12px;">
        This report was automatically generated by the Event Automation System using AI analysis.
    </p>
</body>
</html>
        """

        return html
