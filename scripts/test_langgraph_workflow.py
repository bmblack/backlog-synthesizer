#!/usr/bin/env python3
"""
Test script for LangGraph workflow.

This script tests the complete LangGraph-orchestrated workflow:
1. Document ingestion
2. Requirement extraction
3. Story generation
4. Human approval (auto-approved)
5. JIRA integration

Usage:
    python scripts/test_langgraph_workflow.py
"""

import logging
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from src.orchestration.graph import BacklogSynthesizerGraph

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Rich console for pretty output
console = Console()


def main():
    """Run the LangGraph workflow test."""
    console.print("\n" + "=" * 80)
    console.print("[bold cyan]LangGraph Workflow Test[/bold cyan]")
    console.print("=" * 80 + "\n")

    # Configuration
    input_file = "tests/fixtures/small_transcript.txt"
    thread_id = "test-run-002"

    # Check if input file exists
    if not Path(input_file).exists():
        console.print(f"[red]❌ Input file not found: {input_file}[/red]")
        return

    console.print(f"[cyan]Input file:[/cyan] {input_file}")
    console.print(f"[cyan]Thread ID:[/cyan] {thread_id}\n")

    # =========================================================================
    # STEP 1: Initialize LangGraph
    # =========================================================================
    console.print(Panel("[bold]Step 1: Initialize LangGraph Orchestrator[/bold]"))

    try:
        graph = BacklogSynthesizerGraph(enable_checkpointing=True)
        console.print("[green]✅ LangGraph initialized with checkpointing enabled[/green]\n")
    except Exception as e:
        console.print(f"[red]❌ Failed to initialize LangGraph: {e}[/red]")
        return

    # =========================================================================
    # STEP 2: Run Workflow
    # =========================================================================
    console.print(Panel("[bold]Step 2: Run Complete Workflow[/bold]"))

    try:
        # Run the workflow
        final_state = graph.run(
            input_file_path=input_file,
            context={
                "project": "Backlog Synthesizer",
                "source": "customer transcript",
                "jira_dry_run": True  # Don't actually create JIRA issues in test
            },
            thread_id=thread_id,
        )

        console.print("[green]✅ Workflow completed successfully[/green]\n")

    except Exception as e:
        console.print(f"[red]❌ Workflow failed: {e}[/red]")
        import traceback
        console.print(traceback.format_exc())
        return

    # =========================================================================
    # STEP 3: Display Results
    # =========================================================================
    console.print(Panel("[bold]Step 3: Workflow Results[/bold]"))

    # Check for errors
    if final_state.errors:
        console.print("[red]⚠️  Errors encountered during workflow:[/red]")
        for error in final_state.errors:
            console.print(f"  • Step: {error.get('step')}")
            console.print(f"    Error: {error.get('error')}\n")
    else:
        console.print("[green]✅ No errors encountered[/green]\n")

    # Requirements
    console.print(f"[cyan]Requirements Extracted:[/cyan] {len(final_state.requirements)}")
    if final_state.extraction_metadata:
        console.print(f"  • Model: {final_state.extraction_metadata.get('model', 'unknown')}")
        tokens = final_state.extraction_metadata.get('tokens_used', {})
        console.print(f"  • Tokens: {tokens.get('input', 0)} input, {tokens.get('output', 0)} output\n")

    # Stories
    console.print(f"[cyan]User Stories Generated:[/cyan] {len(final_state.stories)}")
    if final_state.generation_metadata:
        console.print(f"  • Model: {final_state.generation_metadata.get('model', 'unknown')}")
        tokens = final_state.generation_metadata.get('tokens_used', {})
        console.print(f"  • Tokens: {tokens.get('input', 0)} input, {tokens.get('output', 0)} output")
        total_points = sum(story.get('story_points', 0) for story in final_state.stories)
        console.print(f"  • Total Story Points: {total_points}\n")

    # JIRA Issues
    console.print(f"[cyan]JIRA Issues Created:[/cyan] {len(final_state.jira_issues)}")
    if final_state.jira_metadata:
        console.print(f"  • Project: {final_state.jira_metadata.get('project_key', 'unknown')}")
        console.print(f"  • JIRA URL: {final_state.jira_metadata.get('jira_url', 'unknown')}\n")

    # Approval Status
    console.print(f"[cyan]Approval Status:[/cyan] {final_state.approval_status}")
    console.print(f"[cyan]Final Step:[/cyan] {final_state.current_step}\n")

    # =========================================================================
    # STEP 4: Display Story Details
    # =========================================================================
    if final_state.stories:
        console.print(Panel("[bold]Step 4: Generated Stories Summary[/bold]"))

        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("#", style="dim", width=3)
        table.add_column("Title", min_width=40)
        table.add_column("Epic", min_width=20)
        table.add_column("Priority", width=8)
        table.add_column("Points", width=6)

        for i, story in enumerate(final_state.stories[:10], 1):  # Show first 10
            table.add_row(
                str(i),
                story.get('title', 'N/A')[:60],
                story.get('epic_link', 'N/A')[:25],
                story.get('priority', 'N/A'),
                str(story.get('story_points', 0))
            )

        console.print(table)

        if len(final_state.stories) > 10:
            console.print(f"\n[dim]... and {len(final_state.stories) - 10} more stories[/dim]\n")

    # =========================================================================
    # STEP 5: Display JIRA Issues
    # =========================================================================
    if final_state.jira_issues:
        console.print(Panel("[bold]Step 5: Created JIRA Issues[/bold]"))

        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("#", style="dim", width=3)
        table.add_column("Key", width=12)
        table.add_column("Summary", min_width=50)

        for i, issue in enumerate(final_state.jira_issues[:10], 1):  # Show first 10
            table.add_row(
                str(i),
                issue.get('key', 'N/A'),
                issue.get('summary', 'N/A')[:70]
            )

        console.print(table)

        if len(final_state.jira_issues) > 10:
            console.print(f"\n[dim]... and {len(final_state.jira_issues) - 10} more issues[/dim]\n")

        # Display URLs for first few issues
        console.print("[cyan]Issue URLs (first 3):[/cyan]")
        for issue in final_state.jira_issues[:3]:
            console.print(f"  • {issue.get('url', 'N/A')}")
        console.print()

    # =========================================================================
    # STEP 6: Test Checkpoint Retrieval
    # =========================================================================
    console.print(Panel("[bold]Step 6: Test Checkpoint Retrieval[/bold]"))

    try:
        retrieved_state = graph.get_state(thread_id=thread_id)
        if retrieved_state:
            console.print(f"[green]✅ Successfully retrieved checkpoint for thread: {thread_id}[/green]")
            console.print(f"  • Current step: {retrieved_state.current_step}")
            console.print(f"  • Requirements: {len(retrieved_state.requirements)}")
            console.print(f"  • Stories: {len(retrieved_state.stories)}")
            console.print(f"  • JIRA Issues: {len(retrieved_state.jira_issues)}\n")
        else:
            console.print(f"[yellow]⚠️  No checkpoint found for thread: {thread_id}[/yellow]\n")
    except Exception as e:
        console.print(f"[red]❌ Failed to retrieve checkpoint: {e}[/red]\n")

    # =========================================================================
    # Summary
    # =========================================================================
    console.print("=" * 80)
    console.print("[bold green]✅ LangGraph Workflow Test Complete![/bold green]")
    console.print("=" * 80)

    # Print summary statistics
    console.print("\n[bold]Summary:[/bold]")
    console.print(f"  • Input: {len(final_state.input_content or '')} characters")
    console.print(f"  • Requirements: {len(final_state.requirements)}")
    console.print(f"  • Stories: {len(final_state.stories)}")
    console.print(f"  • JIRA Issues: {len(final_state.jira_issues)}")
    console.print(f"  • Errors: {len(final_state.errors)}")
    console.print(f"  • Final Status: {final_state.current_step}\n")


if __name__ == "__main__":
    main()
