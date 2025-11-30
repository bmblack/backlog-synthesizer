"""
JIRAIntegrationAgent: Pushes generated user stories to JIRA.

This agent takes UserStory objects and creates corresponding JIRA issues
using the JIRA Python library (atlassian-python-api).
"""

import logging
import os
from typing import Any, Dict, List, Optional

from atlassian import Jira
from pydantic import BaseModel, Field

# Configure logging
logger = logging.getLogger(__name__)


class JIRAIssue(BaseModel):
    """Representation of a created JIRA issue."""

    key: str = Field(description="JIRA issue key (e.g., BS-123)")
    id: str = Field(description="JIRA issue ID")
    url: str = Field(description="URL to the JIRA issue")
    summary: str = Field(description="Issue summary/title")


class JIRAIntegrationResult(BaseModel):
    """Result of JIRA integration operation."""

    issues: List[JIRAIssue] = Field(default_factory=list)
    total_created: int = Field(default=0)
    failed_count: int = Field(default=0)
    errors: List[Dict[str, Any]] = Field(default_factory=list)
    integration_metadata: Dict[str, Any] = Field(default_factory=dict)


class JIRAIntegrationAgent:
    """
    Agent responsible for pushing user stories to JIRA.

    This agent converts UserStory objects into JIRA issues using the
    atlassian-python-api library. It handles field mapping, formatting,
    and error handling.

    Attributes:
        jira_client: Atlassian Jira client instance
        project_key: JIRA project key (e.g., "BS")
        jira_url: Base URL for JIRA instance
        priority_mapping: Maps UserStory priority (P1-P4) to JIRA priority names
        story_points_field: Custom field ID for story points
        epic_link_field: Custom field ID for epic linking
    """

    # JIRA priority mapping (P1-P4 to JIRA priority names)
    # Note: JIRA Cloud typically has: Highest, High, Medium, Low, Lowest
    DEFAULT_PRIORITY_MAPPING = {
        "P1": "Highest",  # Critical/Blocker
        "P2": "High",  # High priority
        "P3": "Medium",  # Medium priority
        "P4": "Low",  # Low priority
    }

    def __init__(
        self,
        jira_url: Optional[str] = None,
        jira_email: Optional[str] = None,
        jira_token: Optional[str] = None,
        project_key: Optional[str] = None,
        priority_mapping: Optional[Dict[str, str]] = None,
        story_points_field: Optional[str] = None,
        epic_link_field: Optional[str] = None,
    ):
        """
        Initialize the JIRAIntegrationAgent.

        Args:
            jira_url: JIRA instance URL (defaults to JIRA_URL env var)
            jira_email: JIRA user email (defaults to JIRA_EMAIL env var)
            jira_token: JIRA API token (defaults to JIRA_API_TOKEN env var)
            project_key: JIRA project key (defaults to JIRA_PROJECT_KEY env var)
            priority_mapping: Custom priority mapping (defaults to standard mapping)
            story_points_field: Custom field ID for story points (defaults to env var)
            epic_link_field: Field for epic linking (defaults to env var)
        """
        # Get configuration from environment or parameters
        self.jira_url = jira_url or os.getenv("JIRA_URL")
        jira_email = jira_email or os.getenv("JIRA_EMAIL")
        jira_token = jira_token or os.getenv("JIRA_API_TOKEN")
        self.project_key = project_key or os.getenv("JIRA_PROJECT_KEY")
        self.priority_mapping = priority_mapping or self.DEFAULT_PRIORITY_MAPPING
        self.story_points_field = story_points_field or os.getenv("JIRA_STORY_POINTS_FIELD")
        self.epic_link_field = epic_link_field or os.getenv("JIRA_EPIC_LINK_FIELD")

        # Validate required configuration
        if not self.jira_url:
            raise ValueError("JIRA_URL must be set in environment or passed to constructor")
        if not jira_email:
            raise ValueError("JIRA_EMAIL must be set in environment or passed to constructor")
        if not jira_token:
            raise ValueError("JIRA_API_TOKEN must be set in environment or passed to constructor")
        if not self.project_key:
            raise ValueError("JIRA_PROJECT_KEY must be set in environment or passed to constructor")

        # Initialize JIRA client
        # For JIRA Cloud, use API token as password
        # Note: The library expects username=email, password=api_token for Cloud
        self.jira_client = Jira(
            url=self.jira_url,
            username=jira_email,
            password=jira_token,
            cloud=True,  # Using JIRA Cloud
        )

        # Test connection
        try:
            # Try to get current user to verify authentication
            user = self.jira_client.myself()
            logger.debug(f"Authenticated as: {user.get('displayName', jira_email)}")
        except Exception as e:
            logger.warning(f"Could not verify JIRA authentication: {e}")

        logger.info(
            f"JIRAIntegrationAgent initialized for project {self.project_key} "
            f"at {self.jira_url}"
        )
        logger.debug(
            f"Field mapping: story_points={self.story_points_field}, "
            f"epic_link={self.epic_link_field}"
        )

    def format_story_description(self, story: Any) -> str:
        """
        Format user story into JIRA description markdown.

        Args:
            story: UserStory object (or dict)

        Returns:
            Formatted markdown description for JIRA
        """
        # Extract story fields (handle both dict and object)
        user_story = story.user_story if hasattr(story, "user_story") else story["user_story"]
        description = story.description if hasattr(story, "description") else story["description"]
        acceptance_criteria = (
            story.acceptance_criteria
            if hasattr(story, "acceptance_criteria")
            else story["acceptance_criteria"]
        )
        technical_notes = (
            story.technical_notes if hasattr(story, "technical_notes") else story.get("technical_notes")
        )
        source_requirements = (
            story.source_requirements
            if hasattr(story, "source_requirements")
            else story["source_requirements"]
        )

        # Build formatted description
        parts = []

        # User story at the top
        parts.append(f"*{user_story}*\n")

        # Main description
        parts.append("h3. Description\n")
        parts.append(f"{description}\n")

        # Acceptance criteria
        parts.append("h3. Acceptance Criteria\n")
        for i, criterion in enumerate(acceptance_criteria, 1):
            parts.append(f"# {criterion}")
        parts.append("")

        # Technical notes (if present)
        if technical_notes:
            parts.append("h3. Technical Notes\n")
            parts.append(f"{technical_notes}\n")

        # Source requirements (for traceability)
        parts.append("h3. Source Requirements\n")
        parts.append("{panel:title=Original Customer Requirements|borderStyle=solid}")
        for req in source_requirements:
            parts.append(f"* {req}")
        parts.append("{panel}\n")

        # Add AI generation metadata
        parts.append("----")
        parts.append("_Generated by Backlog Synthesizer AI_")

        return "\n".join(parts)

    def map_priority(self, story_priority: str) -> str:
        """
        Map UserStory priority (P1-P4) to JIRA priority name.

        Args:
            story_priority: Priority from UserStory (P1, P2, P3, P4)

        Returns:
            JIRA priority name (Highest, High, Medium, Low)
        """
        return self.priority_mapping.get(story_priority, "Medium")

    def push_story_to_jira(
        self,
        story: Any,
        dry_run: bool = False,
    ) -> Optional[JIRAIssue]:
        """
        Push a single user story to JIRA.

        Args:
            story: UserStory object to push
            dry_run: If True, only validate but don't create issue

        Returns:
            JIRAIssue object if successful, None if failed

        Raises:
            Exception: If JIRA API call fails
        """
        try:
            # Extract story fields
            title = story.title if hasattr(story, "title") else story["title"]
            story_points = story.story_points if hasattr(story, "story_points") else story["story_points"]
            priority = story.priority if hasattr(story, "priority") else story["priority"]
            labels = story.labels if hasattr(story, "labels") else story["labels"]
            epic_link = story.epic_link if hasattr(story, "epic_link") else story.get("epic_link")

            # Format description
            description = self.format_story_description(story)

            # Map priority
            jira_priority = self.map_priority(priority)

            if dry_run:
                logger.info(f"[DRY RUN] Would create JIRA issue: {title}")
                logger.debug(f"  Priority: {jira_priority}, Points: {story_points}, Labels: {labels}")
                return None

            # Build issue fields
            fields = {
                "project": {"key": self.project_key},
                "summary": title,
                "description": description,
                "issuetype": {"name": "Story"},
                "priority": {"name": jira_priority},
                "labels": labels,
            }

            # Add story points if configured
            if story_points and self.story_points_field:
                fields[self.story_points_field] = story_points
                logger.debug(f"Setting {self.story_points_field} = {story_points}")

            # Add epic link if present
            if epic_link and self.epic_link_field:
                # Epic Link custom field expects just the epic key as a string
                fields[self.epic_link_field] = epic_link
                logger.debug(f"Setting {self.epic_link_field} = {epic_link}")

            # Create JIRA issue
            logger.info(f"Creating JIRA issue: {title}")
            logger.debug(f"JIRA fields: {fields}")
            issue = self.jira_client.create_issue(fields=fields)

            issue_key = issue.get("key")
            issue_id = issue.get("id")

            if not issue_key:
                raise Exception("No issue key returned from JIRA")

            # Construct JIRA URL
            issue_url = f"{self.jira_url}/browse/{issue_key}"

            logger.info(f"✅ Created JIRA issue: {issue_key} - {title}")

            return JIRAIssue(
                key=issue_key,
                id=issue_id,
                url=issue_url,
                summary=title,
            )

        except Exception as e:
            logger.error(f"Failed to create JIRA issue for story '{title}': {e}")
            raise

    def create_epic(
        self,
        epic_name: str,
        description: str = None,
        dry_run: bool = False,
    ) -> Optional[JIRAIssue]:
        """
        Create a JIRA Epic.

        Args:
            epic_name: Name of the epic
            description: Optional description
            dry_run: If True, only validate but don't create

        Returns:
            JIRAIssue object if successful, None if dry_run or failed
        """
        try:
            if dry_run:
                logger.info(f"[DRY RUN] Would create Epic: {epic_name}")
                return None

            # Build epic fields
            fields = {
                "project": {"key": self.project_key},
                "summary": epic_name,
                "issuetype": {"name": "Epic"},
            }

            if description:
                fields["description"] = description

            # For newer JIRA, Epic Name might be a custom field
            # Try setting it if configured
            if self.epic_link_field:
                # Epic Name is often customfield_10011 in JIRA Cloud
                # But we'll just use the summary for now
                pass

            logger.info(f"Creating Epic: {epic_name}")
            logger.debug(f"Epic fields: {fields}")
            issue = self.jira_client.create_issue(fields=fields)

            issue_key = issue.get("key")
            issue_id = issue.get("id")

            if not issue_key:
                raise Exception("No issue key returned from JIRA")

            issue_url = f"{self.jira_url}/browse/{issue_key}"

            logger.info(f"✅ Created Epic: {issue_key} - {epic_name}")

            return JIRAIssue(
                key=issue_key,
                id=issue_id,
                url=issue_url,
                summary=epic_name,
            )

        except Exception as e:
            logger.error(f"Failed to create Epic '{epic_name}': {e}")
            raise

    def create_epics_from_stories(
        self,
        stories: List[Any],
        dry_run: bool = False,
    ) -> Dict[str, str]:
        """
        Extract unique epic names from stories and create them in JIRA.

        Args:
            stories: List of UserStory objects
            dry_run: If True, validate but don't create

        Returns:
            Dictionary mapping epic names to epic keys (e.g., {"Dark Mode Implementation": "BS-123"})
        """
        # Extract unique epic names
        epic_names = set()
        for story in stories:
            epic_link = story.epic_link if hasattr(story, "epic_link") else story.get("epic_link")
            if epic_link:
                epic_names.add(epic_link)

        if not epic_names:
            logger.info("No epics to create")
            return {}

        logger.info(f"Creating {len(epic_names)} epics: {', '.join(epic_names)}")

        epic_map = {}
        for epic_name in sorted(epic_names):
            try:
                epic_issue = self.create_epic(
                    epic_name=epic_name,
                    description=f"Epic for {epic_name} related stories",
                    dry_run=dry_run,
                )

                if epic_issue:
                    epic_map[epic_name] = epic_issue.key
                    logger.info(f"  ✅ {epic_name} → {epic_issue.key}")

            except Exception as e:
                logger.error(f"  ❌ Failed to create epic '{epic_name}': {e}")
                # Continue with other epics

        return epic_map

    def push_stories(
        self,
        stories: List[Any],
        dry_run: bool = False,
        stop_on_error: bool = False,
    ) -> JIRAIntegrationResult:
        """
        Push multiple user stories to JIRA.

        Args:
            stories: List of UserStory objects
            dry_run: If True, validate but don't create issues
            stop_on_error: If True, stop on first error; otherwise continue

        Returns:
            JIRAIntegrationResult with created issues and errors
        """
        if not stories:
            raise ValueError("Stories list cannot be empty")

        logger.info(f"Pushing {len(stories)} user stories to JIRA (dry_run={dry_run})")

        # Step 1: Create epics first
        logger.info("Step 1: Creating epics...")
        epic_map = self.create_epics_from_stories(stories, dry_run=dry_run)

        if epic_map:
            logger.info(f"Created {len(epic_map)} epics")
        else:
            logger.info("No epics needed or dry run mode")

        # Step 2: Update stories with epic keys (instead of epic names)
        for story in stories:
            if hasattr(story, "epic_link"):
                epic_name = story.epic_link
                if epic_name and epic_name in epic_map:
                    story.epic_link = epic_map[epic_name]
                    logger.debug(f"Mapped epic '{epic_name}' → '{epic_map[epic_name]}'")
            elif isinstance(story, dict) and "epic_link" in story:
                epic_name = story["epic_link"]
                if epic_name and epic_name in epic_map:
                    story["epic_link"] = epic_map[epic_name]
                    logger.debug(f"Mapped epic '{epic_name}' → '{epic_map[epic_name]}'")

        # Step 3: Create stories
        logger.info("Step 2: Creating stories...")
        created_issues = []
        errors = []

        for i, story in enumerate(stories, 1):
            title = "Unknown"
            try:
                title = story.title if hasattr(story, "title") else story["title"]
                logger.info(f"[{i}/{len(stories)}] Processing: {title}")

                issue = self.push_story_to_jira(story, dry_run=dry_run)

                if issue:
                    created_issues.append(issue)

            except Exception as e:
                error_info = {
                    "story_index": i,
                    "story_title": title,
                    "error": str(e),
                }
                errors.append(error_info)
                logger.error(f"Error processing story {i}: {e}")

                if stop_on_error:
                    logger.error("Stopping due to error (stop_on_error=True)")
                    break

        # Build result metadata
        metadata = {
            "project_key": self.project_key,
            "jira_url": self.jira_url,
            "dry_run": dry_run,
            "total_stories": len(stories),
        }

        result = JIRAIntegrationResult(
            issues=created_issues,
            total_created=len(created_issues),
            failed_count=len(errors),
            errors=errors,
            integration_metadata=metadata,
        )

        # Log summary
        if dry_run:
            logger.info(f"[DRY RUN] Would create {len(stories)} JIRA issues")
        else:
            logger.info(
                f"JIRA integration complete: {result.total_created} created, "
                f"{result.failed_count} failed"
            )

        return result

    def fetch_backlog(
        self,
        issue_types: Optional[List[str]] = None,
        max_results: int = 100,
        jql_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Fetch existing JIRA backlog issues for gap detection.

        Args:
            issue_types: List of issue types to fetch (e.g., ["Story", "Task"])
                        If None, fetches all issue types
            max_results: Maximum number of issues to fetch
            jql_filter: Optional custom JQL filter to add to the query

        Returns:
            List of JIRA issues as dictionaries with normalized fields

        Example:
            >>> agent = JIRAIntegrationAgent()
            >>> issues = agent.fetch_backlog(issue_types=["Story"], max_results=50)
            >>> len(issues)
            42
        """
        logger.info(
            f"[FETCH] Fetching JIRA backlog from project {self.project_key} "
            f"(max_results={max_results})"
        )

        try:
            # Build JQL query
            jql_parts = [f"project = {self.project_key}"]

            # Add issue type filter
            if issue_types:
                types_str = ", ".join([f'"{t}"' for t in issue_types])
                jql_parts.append(f"issuetype in ({types_str})")

            # Add custom filter if provided
            if jql_filter:
                jql_parts.append(f"({jql_filter})")

            # Order by created date (newest first)
            jql = " AND ".join(jql_parts) + " ORDER BY created DESC"

            logger.debug(f"JQL query: {jql}")

            # Fetch issues from JIRA
            issues = self.jira_client.search_issues(
                jql_str=jql,
                maxResults=max_results,
                fields=[
                    "summary",
                    "description",
                    "issuetype",
                    "status",
                    "priority",
                    "created",
                    "updated",
                    self.story_points_field,
                    self.epic_link_field,
                ],
            )

            # Normalize issues to standard format
            normalized_issues = []
            for issue in issues:
                normalized_issue = {
                    "key": issue.key,
                    "summary": issue.fields.summary,
                    "description": issue.fields.description or "",
                    "issue_type": issue.fields.issuetype.name,
                    "status": issue.fields.status.name,
                    "priority": issue.fields.priority.name if issue.fields.priority else "Medium",
                    "created": issue.fields.created,
                    "updated": issue.fields.updated,
                    "story_points": getattr(issue.fields, self.story_points_field, None),
                    "epic_link": getattr(issue.fields, self.epic_link_field, None),
                    "url": f"{self.jira_url}/browse/{issue.key}",
                }

                normalized_issues.append(normalized_issue)

            logger.info(f"[FETCH] Fetched {len(normalized_issues)} issues from JIRA")

            return normalized_issues

        except Exception as e:
            logger.error(f"[FETCH] Error fetching JIRA backlog: {e}")
            raise
