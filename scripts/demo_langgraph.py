#!/usr/bin/env python3
"""
Interactive LangGraph Demo Script.

This script demonstrates the complete LangGraph-orchestrated workflow
with options for different input files and modes.

Usage:
    python scripts/demo_langgraph.py [--input FILE] [--create-jira] [--thread-id ID]
"""

import argparse
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
from rich.prompt import Confirm

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


def display_banner():
    """Display welcome banner."""
    console.print("\n" + "=" * 80)
    console.print("[bold cyan]🚀 BACKLOG SYNTHESIZER - LangGraph Demo[/bold cyan]")
    console.print("=" * 80)
    console.print("\n[dim]Multi-Agent AI System for Customer Transcript → JIRA Stories[/dim]\n")


def display_requirements(requirements):
    """Display extracted requirements."""
    console.print("\n[bold cyan]📋 Extracted Requirements[/bold cyan]\n")

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("#", style="dim", width=3)
    table.add_column("Requirement", min_width=50)
    table.add_column("Type", width=15)
    table.add_column("Priority", width=10)

    for i, req in enumerate(requirements[:15], 1):  # Show first 15
        req_text = req.get('requirement', 'N/A')
        if len(req_text) > 80:
            req_text = req_text[:77] + "..."

        table.add_row(
            str(i),
            req_text,
            req.get('type', 'N/A'),
            req.get('priority_signal', 'N/A')
        )

    console.print(table)

    if len(requirements) > 15:
        console.print(f"\n[dim]... and {len(requirements) - 15} more requirements[/dim]")


def display_stories(stories):
    """Display generated user stories."""
    console.print("\n[bold cyan]📝 Generated User Stories[/bold cyan]\n")

    # Summary stats
    total_points = sum(story.get('story_points', 0) for story in stories)
    epics = set(story.get('epic_link') for story in stories if story.get('epic_link'))

    console.print(f"[green]Total Stories:[/green] {len(stories)}")
    console.print(f"[green]Total Story Points:[/green] {total_points}")
    console.print(f"[green]Epics:[/green] {len(epics)}\n")

    # Stories table
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("#", style="dim", width=3)
    table.add_column("Title", min_width=40)
    table.add_column("Epic", min_width=20)
    table.add_column("Pri", width=4)
    table.add_column("Pts", width=4)

    for i, story in enumerate(stories[:15], 1):  # Show first 15
        title = story.get('title', 'N/A')
        if len(title) > 60:
            title = title[:57] + "..."

        epic = story.get('epic_link', 'N/A')
        if len(epic) > 25:
            epic = epic[:22] + "..."

        table.add_row(
            str(i),
            title,
            epic,
            story.get('priority', 'N/A'),
            str(story.get('story_points', 0))
        )

    console.print(table)

    if len(stories) > 15:
        console.print(f"\n[dim]... and {len(stories) - 15} more stories[/dim]")


def display_jira_results(jira_issues, dry_run=False):
    """Display JIRA creation results."""
    if dry_run:
        console.print("\n[bold yellow]🔍 JIRA Dry-Run Results[/bold yellow]")
        console.print("[dim]No issues were actually created in JIRA[/dim]\n")
    else:
        console.print("\n[bold green]✅ JIRA Issues Created[/bold green]\n")

    if not jira_issues:
        console.print("[yellow]No JIRA issues created (dry-run mode)[/yellow]")
        return

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("#", style="dim", width=3)
    table.add_column("Key", width=12)
    table.add_column("Summary", min_width=50)

    for i, issue in enumerate(jira_issues[:10], 1):
        summary = issue.get('summary', 'N/A')
        if len(summary) > 70:
            summary = summary[:67] + "..."

        table.add_row(
            str(i),
            issue.get('key', 'N/A'),
            summary
        )

    console.print(table)

    if len(jira_issues) > 10:
        console.print(f"\n[dim]... and {len(jira_issues) - 10} more issues[/dim]")

    # Display URLs
    if not dry_run and jira_issues:
        console.print("\n[cyan]Issue URLs (first 3):[/cyan]")
        for issue in jira_issues[:3]:
            console.print(f"  • {issue.get('url', 'N/A')}")


def main():
    """Run the interactive demo."""
    parser = argparse.ArgumentParser(description="LangGraph Demo")
    parser.add_argument(
        "--input",
        default="tests/fixtures/small_transcript.txt",
        help="Input transcript file (default: small_transcript.txt)"
    )
    parser.add_argument(
        "--create-jira",
        action="store_true",
        help="Actually create JIRA issues (default: dry-run)"
    )
    parser.add_argument(
        "--thread-id",
        default="demo-001",
        help="Thread ID for checkpointing (default: demo-001)"
    )
    args = parser.parse_args()

    # Display banner
    display_banner()

    # Check if input file exists
    input_file = Path(args.input)
    if not input_file.exists():
        console.print(f"[red]❌ Input file not found: {input_file}[/red]")
        console.print("\n[yellow]Available test files:[/yellow]")
        console.print("  • tests/fixtures/small_transcript.txt (3 requirements)")
        console.print("  • tests/fixtures/sample_transcript_001.txt (13 requirements)")
        return 1

    # Show configuration
    console.print(Panel.fit(
        f"[bold]Configuration[/bold]\n\n"
        f"[cyan]Input File:[/cyan] {input_file}\n"
        f"[cyan]Thread ID:[/cyan] {args.thread_id}\n"
        f"[cyan]JIRA Mode:[/cyan] {'CREATE REAL ISSUES' if args.create_jira else 'DRY-RUN (no issues created)'}\n"
        f"[cyan]Checkpointing:[/cyan] Enabled",
        title="Demo Settings"
    ))

    # Confirm if creating real JIRA issues
    if args.create_jira:
        if not Confirm.ask("\n[yellow]⚠️  You're about to create REAL JIRA issues. Continue?[/yellow]"):
            console.print("[yellow]Cancelled. Run without --create-jira for dry-run mode.[/yellow]")
            return 0

    # Initialize LangGraph
    console.print("\n[cyan]Initializing LangGraph orchestrator...[/cyan]")
    try:
        graph = BacklogSynthesizerGraph(enable_checkpointing=True)
        console.print("[green]✅ LangGraph initialized[/green]\n")
    except Exception as e:
        console.print(f"[red]❌ Failed to initialize: {e}[/red]")
        return 1

    # Run workflow
    console.print("=" * 80)
    console.print("[bold]🏃 Running Complete Workflow[/bold]")
    console.print("=" * 80 + "\n")

    try:
        with console.status("[bold green]Processing transcript...") as status:
            final_state = graph.run(
                input_file_path=str(input_file),
                context={
                    "project": "Backlog Synthesizer Demo",
                    "source": "customer transcript",
                    "jira_dry_run": not args.create_jira
                },
                thread_id=args.thread_id
            )

        console.print("[green]✅ Workflow completed successfully![/green]\n")

    except Exception as e:
        console.print(f"[red]❌ Workflow failed: {e}[/red]")
        import traceback
        console.print(traceback.format_exc())
        return 1

    # Display results
    console.print("=" * 80)
    console.print("[bold]📊 Results Summary[/bold]")
    console.print("=" * 80)

    # Check for errors
    if final_state.errors:
        console.print("\n[yellow]⚠️  Errors encountered:[/yellow]")
        for error in final_state.errors:
            console.print(f"  • [red]{error.get('step')}:[/red] {error.get('error')}")

    # Display requirements
    if final_state.requirements:
        display_requirements(final_state.requirements)

    # Display stories
    if final_state.stories:
        display_stories(final_state.stories)

    # Display JIRA results
    if final_state.current_step == "push_to_jira":
        display_jira_results(final_state.jira_issues, dry_run=not args.create_jira)

    # Checkpoint info
    console.print("\n" + "=" * 80)
    console.print("[bold]💾 Checkpoint Information[/bold]")
    console.print("=" * 80 + "\n")

    console.print(f"[cyan]Thread ID:[/cyan] {args.thread_id}")
    console.print(f"[cyan]Final Step:[/cyan] {final_state.current_step}")
    console.print(f"[cyan]Approval Status:[/cyan] {final_state.approval_status}")
    console.print(f"[cyan]State Persisted:[/cyan] Yes (can be retrieved)")

    # Final summary
    console.print("\n" + "=" * 80)
    console.print("[bold green]✅ Demo Complete![/bold green]")
    console.print("=" * 80 + "\n")

    console.print("[bold]Summary Statistics:[/bold]")
    console.print(f"  • Input: {len(final_state.input_content or '')} characters")
    console.print(f"  • Requirements: {len(final_state.requirements)}")
    console.print(f"  • Stories: {len(final_state.stories)}")
    console.print(f"  • JIRA Issues: {len(final_state.jira_issues)}")
    console.print(f"  • Errors: {len(final_state.errors)}")

    # Token usage
    if final_state.extraction_metadata:
        tokens = final_state.extraction_metadata.get('tokens_used', {})
        console.print(f"\n[cyan]Extraction Tokens:[/cyan] {tokens.get('input', 0)} in / {tokens.get('output', 0)} out")

    if final_state.generation_metadata:
        tokens = final_state.generation_metadata.get('tokens_used', {})
        console.print(f"[cyan]Generation Tokens:[/cyan] {tokens.get('input', 0)} in / {tokens.get('output', 0)} out")

    console.print("\n[dim]State has been checkpointed and can be retrieved with thread_id: " + args.thread_id + "[/dim]\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
