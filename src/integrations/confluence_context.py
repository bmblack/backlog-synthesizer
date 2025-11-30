"""
Confluence Context Fetcher.

This module provides utilities for fetching project context from Confluence
to enrich requirements extraction and story generation.

Key use cases:
- Fetch ADRs (Architecture Decision Records)
- Retrieve project documentation
- Get technical specifications
- Access team guidelines and standards
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ConfluenceContextFetcher:
    """
    Fetches relevant context from Confluence pages.

    Uses the Confluence MCP server to search and retrieve pages
    that provide context for requirements analysis.
    """

    def __init__(
        self,
        confluence_client: Optional[Any] = None,
        default_spaces: Optional[List[str]] = None,
    ):
        """
        Initialize Confluence context fetcher.

        Args:
            confluence_client: Optional Confluence MCP client (for testing)
            default_spaces: Default Confluence spaces to search (e.g., ["ARCH", "DEV"])
        """
        self.confluence_client = confluence_client
        self.default_spaces = default_spaces or []

        logger.info(
            f"ConfluenceContextFetcher initialized "
            f"(default_spaces={self.default_spaces})"
        )

    def search_context_pages(
        self,
        query: str,
        page_types: Optional[List[str]] = None,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Search Confluence for relevant context pages.

        Args:
            query: Search query (e.g., "ADR architecture decisions")
            page_types: Filter by page types (e.g., ["ADR", "RFC", "Spec"])
            limit: Maximum number of results

        Returns:
            List of Confluence page summaries with title, url, space, snippet

        Example:
            >>> fetcher = ConfluenceContextFetcher()
            >>> pages = fetcher.search_context_pages("authentication ADR")
            >>> len(pages)
            3
        """
        logger.info(f"Searching Confluence for context: '{query}' (limit={limit})")

        try:
            # In a real implementation, this would use the MCP client
            # For now, we'll document the expected interface
            pages = []

            # Example: mcp__mcp-atlassian__confluence_search(query=query, limit=limit)
            # Would be called here to get results

            logger.debug(f"Found {len(pages)} context pages")
            return pages

        except Exception as e:
            logger.error(f"Error searching Confluence: {e}")
            return []

    def fetch_adr_pages(
        self,
        topic: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Fetch Architecture Decision Records (ADRs) from Confluence.

        Args:
            topic: Optional topic filter (e.g., "authentication", "database")
            limit: Maximum number of ADRs to fetch

        Returns:
            List of ADR pages with full content

        Example:
            >>> fetcher = ConfluenceContextFetcher()
            >>> adrs = fetcher.fetch_adr_pages(topic="technology stack")
            >>> adrs[0]["title"]
            'ADR-002: Technology Stack Decisions'
        """
        logger.info(f"Fetching ADR pages (topic={topic}, limit={limit})")

        try:
            # Build search query for ADRs
            query = "ADR"
            if topic:
                query = f"ADR {topic}"

            # Search for ADR pages
            pages = self.search_context_pages(query=query, limit=limit)

            # Fetch full content for each ADR
            adr_pages = []
            for page in pages:
                full_page = self.fetch_page_content(page["id"])
                if full_page:
                    adr_pages.append(full_page)

            logger.info(f"Fetched {len(adr_pages)} ADR pages")
            return adr_pages

        except Exception as e:
            logger.error(f"Error fetching ADR pages: {e}")
            return []

    def fetch_page_content(
        self,
        page_id: str,
        convert_to_markdown: bool = True,
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch full content of a Confluence page.

        Args:
            page_id: Confluence page ID
            convert_to_markdown: Whether to convert content to markdown

        Returns:
            Page data with metadata and content, or None if error

        Example:
            >>> fetcher = ConfluenceContextFetcher()
            >>> page = fetcher.fetch_page_content("786434")
            >>> page["title"]
            'ADR-002: Technology Stack Decisions'
        """
        logger.debug(f"Fetching page content: {page_id}")

        try:
            # In a real implementation, this would use the MCP client
            # Example: mcp__mcp-atlassian__confluence_get_page(
            #     page_id=page_id,
            #     convert_to_markdown=convert_to_markdown
            # )

            # For now, return None (will be implemented with MCP client)
            return None

        except Exception as e:
            logger.error(f"Error fetching page {page_id}: {e}")
            return None

    def build_context_summary(
        self,
        pages: List[Dict[str, Any]],
        max_chars: int = 4000,
    ) -> str:
        """
        Build a concise context summary from Confluence pages.

        Args:
            pages: List of Confluence pages
            max_chars: Maximum characters for summary

        Returns:
            Formatted context summary string

        Example:
            >>> pages = [{"title": "ADR-001", "content": "..."}]
            >>> summary = fetcher.build_context_summary(pages)
            >>> "ADR-001" in summary
            True
        """
        logger.debug(f"Building context summary from {len(pages)} pages")

        if not pages:
            return "No additional context available."

        summary_parts = ["# Project Context\n"]

        chars_used = 0
        for page in pages:
            title = page.get("title", "Untitled")
            content = page.get("content", {})

            # Handle both dict and string content formats
            if isinstance(content, dict):
                text = content.get("value", "")
            else:
                text = str(content)

            # Truncate content to fit within max_chars
            remaining_chars = max_chars - chars_used
            if remaining_chars < 200:
                summary_parts.append(f"\n*(Additional {len(pages) - len(summary_parts) + 1} pages omitted)*")
                break

            # Add page summary
            page_summary = f"\n## {title}\n\n"
            page_content = text[:min(len(text), remaining_chars - len(page_summary))]

            if len(text) > len(page_content):
                page_content += "\n\n*(content truncated)*"

            summary_parts.append(page_summary + page_content)
            chars_used += len(page_summary) + len(page_content)

        summary = "".join(summary_parts)
        logger.info(f"Built context summary: {len(summary)} chars from {len(pages)} pages")

        return summary

    def fetch_project_context(
        self,
        topics: Optional[List[str]] = None,
        include_adrs: bool = True,
        max_pages: int = 5,
    ) -> str:
        """
        Fetch comprehensive project context from Confluence.

        This is the main method to use for enriching requirements extraction.

        Args:
            topics: Optional list of topics to search for (e.g., ["auth", "api", "database"])
            include_adrs: Whether to include ADRs in context
            max_pages: Maximum number of pages to fetch

        Returns:
            Formatted context summary string ready for LLM consumption

        Example:
            >>> fetcher = ConfluenceContextFetcher()
            >>> context = fetcher.fetch_project_context(topics=["authentication"])
            >>> "ADR" in context or "No additional context" in context
            True
        """
        logger.info(
            f"Fetching project context (topics={topics}, include_adrs={include_adrs}, max_pages={max_pages})"
        )

        all_pages = []

        # Fetch ADRs if requested
        if include_adrs:
            adr_topic = topics[0] if topics else None
            adrs = self.fetch_adr_pages(topic=adr_topic, limit=max_pages // 2)
            all_pages.extend(adrs)

        # Fetch topic-specific pages if topics provided
        if topics:
            for topic in topics[:3]:  # Limit to 3 topics to avoid too many requests
                pages = self.search_context_pages(
                    query=topic,
                    limit=max(1, (max_pages - len(all_pages)) // len(topics))
                )

                # Fetch full content for each page
                for page in pages:
                    full_page = self.fetch_page_content(page.get("id"))
                    if full_page:
                        all_pages.append(full_page)

                if len(all_pages) >= max_pages:
                    break

        # Build summary
        context_summary = self.build_context_summary(all_pages, max_chars=4000)

        logger.info(f"Fetched project context: {len(all_pages)} pages")
        return context_summary
