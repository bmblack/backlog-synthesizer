#!/usr/bin/env python3
"""
Checkpoint Inspection Tool.

This script allows you to inspect checkpoints stored in the SQLite database.
Useful for debugging, state recovery, and understanding workflow execution.

Usage:
    python scripts/inspect_checkpoints.py [--db PATH] [--thread-id ID] [--list]
"""

import argparse
import json
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.json import JSON

from src.orchestration.graph import BacklogSynthesizerGraph

# Load environment variables
load_dotenv()

# Rich console for pretty output
console = Console()


def list_threads(db_path: str):
    """List all thread IDs in the database."""
    import sqlite3

    console.print(f"\n[cyan]📂 Inspecting database:[/cyan] {db_path}\n")

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Query for unique thread IDs
        cursor.execute("""
            SELECT DISTINCT thread_id, COUNT(*) as checkpoint_count
            FROM checkpoints
            GROUP BY thread_id
            ORDER BY MAX(checkpoint_id) DESC
        """)

        threads = cursor.fetchall()

        if not threads:
            console.print("[yellow]No checkpoints found in database[/yellow]")
            return

        # Display table
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Thread ID", style="cyan", width=30)
        table.add_column("Checkpoints", style="green", width=15)

        for thread_id, count in threads:
            table.add_row(thread_id, str(count))

        console.print(table)
        console.print(f"\n[dim]Total threads: {len(threads)}[/dim]\n")

        conn.close()

    except Exception as e:
        console.print(f"[red]❌ Error reading database: {e}[/red]")
        sys.exit(1)


def inspect_checkpoint(thread_id: str):
    """Inspect a specific checkpoint by thread ID."""
    console.print(f"\n[cyan]🔍 Inspecting checkpoint:[/cyan] {thread_id}\n")

    try:
        # Initialize graph
        graph = BacklogSynthesizerGraph(enable_checkpointing=True)

        # Retrieve state
        state = graph.get_state(thread_id=thread_id)

        if not state:
            console.print(f"[yellow]❌ No checkpoint found for thread: {thread_id}[/yellow]")
            return

        # Display state summary
        console.print(Panel.fit(
            f"[bold]Workflow State Summary[/bold]\n\n"
            f"[cyan]Thread ID:[/cyan] {thread_id}\n"
            f"[cyan]Current Step:[/cyan] {state.current_step}\n"
            f"[cyan]Approval Status:[/cyan] {state.approval_status}\n"
            f"[cyan]Requirements:[/cyan] {len(state.requirements)}\n"
            f"[cyan]Stories:[/cyan] {len(state.stories)}\n"
            f"[cyan]JIRA Issues:[/cyan] {len(state.jira_issues)}\n"
            f"[cyan]Errors:[/cyan] {len(state.errors)}",
            title="Checkpoint Info"
        ))

        # Display requirements
        if state.requirements:
            console.print("\n[bold cyan]📋 Requirements:[/bold cyan]\n")
            req_table = Table(show_header=True, header_style="bold magenta")
            req_table.add_column("#", width=4)
            req_table.add_column("Requirement", min_width=40)
            req_table.add_column("Type", width=15)

            for i, req in enumerate(state.requirements[:10], 1):
                req_text = req.get('requirement', 'N/A')
                if len(req_text) > 80:
                    req_text = req_text[:77] + "..."

                req_table.add_row(
                    str(i),
                    req_text,
                    req.get('type', 'N/A')
                )

            console.print(req_table)

            if len(state.requirements) > 10:
                console.print(f"[dim]... and {len(state.requirements) - 10} more[/dim]")

        # Display stories
        if state.stories:
            console.print("\n[bold cyan]📝 Stories:[/bold cyan]\n")
            story_table = Table(show_header=True, header_style="bold magenta")
            story_table.add_column("#", width=4)
            story_table.add_column("Title", min_width=40)
            story_table.add_column("Epic", min_width=20)
            story_table.add_column("Points", width=8)

            for i, story in enumerate(state.stories[:10], 1):
                title = story.get('title', 'N/A')
                if len(title) > 60:
                    title = title[:57] + "..."

                epic = story.get('epic_link', 'N/A')
                if len(epic) > 25:
                    epic = epic[:22] + "..."

                story_table.add_row(
                    str(i),
                    title,
                    epic,
                    str(story.get('story_points', 0))
                )

            console.print(story_table)

            if len(state.stories) > 10:
                console.print(f"[dim]... and {len(state.stories) - 10} more[/dim]")

        # Display JIRA issues
        if state.jira_issues:
            console.print("\n[bold cyan]✅ JIRA Issues:[/bold cyan]\n")
            jira_table = Table(show_header=True, header_style="bold magenta")
            jira_table.add_column("#", width=4)
            jira_table.add_column("Key", width=12)
            jira_table.add_column("Summary", min_width=50)

            for i, issue in enumerate(state.jira_issues[:10], 1):
                summary = issue.get('summary', 'N/A')
                if len(summary) > 70:
                    summary = summary[:67] + "..."

                jira_table.add_row(
                    str(i),
                    issue.get('key', 'N/A'),
                    summary
                )

            console.print(jira_table)

            if len(state.jira_issues) > 10:
                console.print(f"[dim]... and {len(state.jira_issues) - 10} more[/dim]")

        # Display errors
        if state.errors:
            console.print("\n[bold yellow]⚠️  Errors:[/bold yellow]\n")
            for error in state.errors:
                console.print(f"  • [red]{error.get('step')}:[/red] {error.get('error')}")

        # Display metadata
        if state.extraction_metadata or state.generation_metadata:
            console.print("\n[bold cyan]📊 Metadata:[/bold cyan]\n")

            if state.extraction_metadata:
                tokens = state.extraction_metadata.get('tokens_used', {})
                console.print(f"[cyan]Extraction:[/cyan] {tokens.get('input', 0)} in / {tokens.get('output', 0)} out")

            if state.generation_metadata:
                tokens = state.generation_metadata.get('tokens_used', {})
                console.print(f"[cyan]Generation:[/cyan] {tokens.get('input', 0)} in / {tokens.get('output', 0)} out")

        console.print("\n")

    except Exception as e:
        console.print(f"[red]❌ Error inspecting checkpoint: {e}[/red]")
        import traceback
        console.print(traceback.format_exc())
        sys.exit(1)


def export_checkpoint(thread_id: str, output_file: str):
    """Export checkpoint to JSON file."""
    console.print(f"\n[cyan]💾 Exporting checkpoint:[/cyan] {thread_id} → {output_file}\n")

    try:
        # Initialize graph
        graph = BacklogSynthesizerGraph(enable_checkpointing=True)

        # Retrieve state
        state = graph.get_state(thread_id=thread_id)

        if not state:
            console.print(f"[yellow]❌ No checkpoint found for thread: {thread_id}[/yellow]")
            return

        # Export to JSON
        with open(output_file, 'w') as f:
            json.dump(state.model_dump(), f, indent=2)

        console.print(f"[green]✅ Exported to {output_file}[/green]\n")

    except Exception as e:
        console.print(f"[red]❌ Error exporting checkpoint: {e}[/red]")
        sys.exit(1)


def main():
    """Run the checkpoint inspector."""
    parser = argparse.ArgumentParser(
        description="Inspect LangGraph checkpoints stored in SQLite"
    )
    parser.add_argument(
        "--db",
        default="data/checkpoints.db",
        help="Path to SQLite database (default: data/checkpoints.db)"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all thread IDs in the database"
    )
    parser.add_argument(
        "--thread-id",
        help="Thread ID to inspect"
    )
    parser.add_argument(
        "--export",
        help="Export checkpoint to JSON file"
    )

    args = parser.parse_args()

    # Check if database exists
    db_path = Path(args.db)
    if not db_path.exists():
        console.print(f"[red]❌ Database not found: {db_path}[/red]")
        console.print("\n[yellow]Run a workflow first to create checkpoints:[/yellow]")
        console.print("  python scripts/demo_langgraph.py")
        return 1

    # Display banner
    console.print("\n" + "=" * 80)
    console.print("[bold cyan]🔍 CHECKPOINT INSPECTOR[/bold cyan]")
    console.print("=" * 80 + "\n")

    # List threads
    if args.list:
        list_threads(str(db_path))
        return 0

    # Inspect specific thread
    if args.thread_id:
        if args.export:
            export_checkpoint(args.thread_id, args.export)
        else:
            inspect_checkpoint(args.thread_id)
        return 0

    # No action specified
    console.print("[yellow]No action specified. Use --list or --thread-id[/yellow]")
    console.print("\n[cyan]Examples:[/cyan]")
    console.print("  # List all threads")
    console.print("  python scripts/inspect_checkpoints.py --list")
    console.print("\n  # Inspect specific thread")
    console.print("  python scripts/inspect_checkpoints.py --thread-id sqlite-test-001")
    console.print("\n  # Export to JSON")
    console.print("  python scripts/inspect_checkpoints.py --thread-id sqlite-test-001 --export state.json")
    console.print("\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
