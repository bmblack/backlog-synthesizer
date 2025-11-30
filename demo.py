#!/usr/bin/env python3
"""
Backlog Synthesizer Demo Script.

This demo shows how to use the backlog synthesizer workflow
with a sample requirements gathering transcript.

Usage:
    python demo.py [--dry-run]

Features demonstrated:
- Document ingestion
- Confluence context fetching (ADRs, specs)
- Requirements extraction with LLM
- JIRA backlog fetch
- Gap detection (semantic deduplication)
- User story generation
- Human approval gate
- JIRA push
"""

import argparse
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.orchestration.graph import BacklogSynthesizerGraph

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("data/demo.log")
    ]
)

logger = logging.getLogger(__name__)


def main():
    """Run backlog synthesizer demo."""
    parser = argparse.ArgumentParser(description="Backlog Synthesizer Demo")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run without actually pushing to JIRA"
    )
    parser.add_argument(
        "--input",
        type=str,
        default="examples/sample_transcript.txt",
        help="Path to input transcript file"
    )
    parser.add_argument(
        "--no-checkpoint",
        action="store_true",
        help="Disable checkpointing"
    )
    parser.add_argument(
        "--no-vector-memory",
        action="store_true",
        help="Disable vector memory"
    )

    args = parser.parse_args()

    print("=" * 80)
    print("BACKLOG SYNTHESIZER DEMO")
    print("=" * 80)
    print()

    # Sample transcript if file doesn't exist
    sample_transcript = """
Meeting Transcript: Product Planning Session
Date: 2024-02-15
Attendees: Sarah (PM), Mike (Tech Lead), Alex (UX Designer)

Sarah: Let's discuss the new user authentication feature for Q1.
We've been getting feedback that our current login is too basic.

Mike: Right. I think we should implement OAuth 2.0 with support
for Google and GitHub social logins. That's what users expect now.

Sarah: Agreed. But we still need email/password as the primary method.
Not everyone wants to use social login.

Alex: From a UX perspective, we should have a clean login page with
clear options. Maybe tabs for different login methods?

Mike: That works. For the backend, we'll use FastAPI like our other services.
We need to store passwords securely with bcrypt hashing. We should also
implement rate limiting to prevent brute force attacks.

Sarah: Security is critical. Can we also add two-factor authentication?
At least as an optional feature for users who want extra security.

Mike: Yes, we can use TOTP (Time-based One-Time Passwords). Users can
use apps like Google Authenticator. We'll need a QR code generator for setup.

Alex: We should also have a user profile page where they can:
- Enable/disable 2FA
- Manage connected social accounts
- Change password
- View login history

Sarah: Good idea. For login history, we should show the last 10 logins
with timestamps, IP addresses, and device info. This helps users detect
unauthorized access.

Mike: From a technical standpoint, we need:
- JWT tokens for session management
- Refresh token rotation for security
- Redis for session storage
- Email verification for new accounts
- Password reset functionality with secure tokens

Sarah: This aligns with our Q1 goals. Let's also add:
- Remember me checkbox (30-day sessions)
- Account lockout after 5 failed attempts
- Admin panel to manage user accounts

Alex: For the UI, I'll design:
- Login page (responsive, mobile-first)
- Registration form with validation
- Profile management page
- 2FA setup wizard
- Password reset flow

Mike: We should follow the architecture decisions from ADR-002 about
using Python and FastAPI. Let's make sure this is consistent.

Sarah: Perfect. This should take about 3 sprints. Let's prioritize
the core login functionality first, then social login, then 2FA.

Mike: Sounds good. I'll create the technical design doc this week.
    """

    # Load or use sample transcript
    if Path(args.input).exists():
        print(f"Loading transcript from: {args.input}")
        with open(args.input) as f:
            transcript = f.read()
    else:
        print(f"Input file not found: {args.input}")
        print("Using sample transcript instead...")
        transcript = sample_transcript

    print(f"Transcript length: {len(transcript)} characters")
    print()

    # Initialize workflow
    print("Initializing Backlog Synthesizer...")
    print(f"  - Checkpointing: {'Disabled' if args.no_checkpoint else 'SQLite'}")
    print(f"  - Vector Memory: {'Disabled' if args.no_vector_memory else 'ChromaDB'}")
    print(f"  - Audit Logging: Enabled")
    print(f"  - Dry Run: {args.dry_run}")
    print()

    try:
        workflow = BacklogSynthesizerGraph(
            enable_checkpointing=not args.no_checkpoint,
            checkpoint_type="sqlite" if not args.no_checkpoint else None,
            enable_audit_logging=True,
            enable_vector_memory=not args.no_vector_memory,
        )

        print("✓ Workflow initialized successfully")
        print()

        # Run workflow
        print("Running workflow...")
        print("-" * 80)
        print()

        result = workflow.run(
            input_content=transcript,
            context={
                "project": "SaaS Authentication System",
                "team": "Platform Team",
                "sprint": "Q1 2024",
            },
            thread_id="demo-001",
        )

        print()
        print("-" * 80)
        print("✓ Workflow completed successfully!")
        print()

        # Display results
        print("=" * 80)
        print("RESULTS")
        print("=" * 80)
        print()

        print(f"Requirements Extracted: {len(result.requirements)}")
        for i, req in enumerate(result.requirements, 1):
            req_text = req.get("requirement", "N/A")
            req_type = req.get("type", "unknown")
            priority = req.get("priority_signal", "medium")
            print(f"  {i}. [{req_type}/{priority}] {req_text[:70]}...")

        print()
        print(f"User Stories Generated: {len(result.stories)}")
        for i, story in enumerate(result.stories, 1):
            title = story.get("title", "N/A")
            points = story.get("story_points", "?")
            epic = story.get("epic_link", "N/A")
            print(f"  {i}. [{points}pts] {title}")
            print(f"     Epic: {epic}")

        print()

        if result.gap_analysis:
            gap = result.gap_analysis
            print(f"Gap Analysis:")
            print(f"  - Novel Requirements: {gap.get('total_novel', 0)}")
            print(f"  - Covered Requirements: {gap.get('total_covered', 0)}")
            print()

        if result.jira_issues:
            print(f"JIRA Issues Created: {len(result.jira_issues)}")
            for issue in result.jira_issues:
                key = issue.get("key", "N/A")
                print(f"  - {key}")
        elif args.dry_run:
            print("JIRA Push: Skipped (dry run)")
        else:
            print("JIRA Push: No issues created")

        print()

        # Show stats
        if workflow.vector_memory and not args.no_vector_memory:
            stats = workflow.vector_memory.get_stats()
            print(f"Vector Memory Stats:")
            print(f"  - Total Items: {stats['total_items']}")
            print(f"  - Requirements: {stats['requirements']}")
            print(f"  - Stories: {stats['stories']}")
            print()

        if workflow.audit_logger:
            print("Audit Trail: data/audit.db")
            executions = workflow.audit_logger.list_workflow_executions(limit=1)
            if executions:
                latest = executions[0]
                exec_id = latest.get("execution_id", "N/A")
                status = latest.get("status", "N/A")
                print(f"  - Latest Execution: {exec_id[:20]}... ({status})")
            print()

        print("=" * 80)
        print("✓ DEMO COMPLETED SUCCESSFULLY")
        print("=" * 80)
        print()

        print("Next Steps:")
        print("  1. Review generated user stories")
        print("  2. Check audit log: data/audit.db")
        print("  3. Query vector memory for similarity searches")
        print("  4. Resume workflow from checkpoint if needed")
        print()

        return 0

    except KeyboardInterrupt:
        print("\n\n⚠ Demo interrupted by user")
        return 1

    except Exception as e:
        logger.error(f"Demo failed: {e}", exc_info=True)
        print(f"\n❌ Demo failed: {e}")
        print("\nCheck data/demo.log for details")
        return 1


if __name__ == "__main__":
    sys.exit(main())
