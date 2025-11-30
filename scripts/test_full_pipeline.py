#!/usr/bin/env python3
"""
End-to-end test: Extract requirements → Generate user stories

This script demonstrates the full pipeline from customer transcript to JIRA-ready user stories.

Usage:
    python scripts/test_full_pipeline.py

Requirements:
    - ANTHROPIC_API_KEY environment variable must be set
    - Virtual environment must be activated
"""

import json
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables
from dotenv import load_dotenv

env_path = project_root / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    print(f"⚠️  Warning: .env file not found at {env_path}")
    print("   Using environment variables from shell")
    print()

from src.agents.analysis_agent import AnalysisAgent
from src.agents.jira_integration_agent import JIRAIntegrationAgent
from src.agents.story_generation_agent import StoryGenerationAgent


def main():
    """Run end-to-end pipeline test."""
    # Check for API key
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ Error: ANTHROPIC_API_KEY environment variable not set")
        print("\nSet it with:")
        print("  export ANTHROPIC_API_KEY='your-key-here'")
        sys.exit(1)

    print("=" * 80)
    print("🚀 Backlog Synthesizer - Full Pipeline Test")
    print("=" * 80)
    print()

    # Load sample transcript
    transcript_path = project_root / "tests" / "fixtures" / "sample_transcript_001.txt"
    if not transcript_path.exists():
        print(f"❌ Error: Sample transcript not found at {transcript_path}")
        sys.exit(1)

    with open(transcript_path, "r") as f:
        transcript = f.read()

    print(f"📄 Loaded transcript: {transcript_path.name}")
    print(f"   Length: {len(transcript)} characters")
    print()

    # STEP 1: Extract Requirements
    print("=" * 80)
    print("STEP 1: Extract Requirements from Transcript")
    print("=" * 80)
    print()

    analysis_agent = AnalysisAgent(api_key=api_key)
    print(f"🔧 Initialized AnalysisAgent (model: {analysis_agent.model})")
    print("🔍 Extracting requirements...")
    print()

    try:
        extraction_result = analysis_agent.extract_requirements(
            transcript, metadata={"source": "sample_transcript_001.txt"}
        )

        print(f"✅ Extracted {extraction_result.total_count} requirements")
        print(
            f"   Tokens: {extraction_result.extraction_metadata['tokens_used']['input']} in, "
            f"{extraction_result.extraction_metadata['tokens_used']['output']} out"
        )
        if extraction_result.extraction_metadata.get("chunked"):
            print(
                f"   Chunked: {extraction_result.extraction_metadata['num_chunks']} chunks"
            )
        print()

        # Show requirements summary
        print("📋 Requirements Summary:")
        for i, req in enumerate(extraction_result.requirements[:5], 1):
            print(f"   {i}. [{req.priority_signal.upper()}] {req.requirement[:60]}...")
        if len(extraction_result.requirements) > 5:
            print(f"   ... and {len(extraction_result.requirements) - 5} more")
        print()

    except Exception as e:
        print(f"❌ Error during requirement extraction: {e}")
        sys.exit(1)

    # STEP 2: Generate User Stories
    print("=" * 80)
    print("STEP 2: Generate User Stories from Requirements")
    print("=" * 80)
    print()

    story_agent = StoryGenerationAgent(api_key=api_key)
    print(f"🔧 Initialized StoryGenerationAgent (model: {story_agent.model})")
    print(f"📝 Generating stories from {len(extraction_result.requirements)} requirements...")
    print("   (Processing in batches to avoid token limits...)")
    print()

    try:
        # Convert requirements to dicts for story generation
        requirements_dicts = [req.model_dump() for req in extraction_result.requirements]

        # Process in batches of 5 requirements (Haiku has 4096 token output limit)
        batch_size = 5
        all_stories = []
        total_input_tokens = 0
        total_output_tokens = 0

        for i in range(0, len(requirements_dicts), batch_size):
            batch = requirements_dicts[i : i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (len(requirements_dicts) + batch_size - 1) // batch_size

            print(f"   📦 Processing batch {batch_num}/{total_batches} ({len(batch)} requirements)...")

            batch_result = story_agent.generate_stories(
                batch, metadata={"source": "extracted_requirements", "batch": batch_num}
            )

            all_stories.extend(batch_result.stories)
            total_input_tokens += batch_result.generation_metadata["tokens_used"]["input"]
            total_output_tokens += batch_result.generation_metadata["tokens_used"]["output"]

        # Create combined result
        from src.agents.story_generation_agent import StoryGenerationResult

        story_result = StoryGenerationResult(
            stories=all_stories,
            total_count=len(all_stories),
            generation_metadata={
                "model": story_agent.model,
                "tokens_used": {"input": total_input_tokens, "output": total_output_tokens},
                "num_batches": total_batches,
            },
        )

        print()
        print(f"✅ Generated {story_result.total_count} user stories")
        print(
            f"   Tokens: {story_result.generation_metadata['tokens_used']['input']} in, "
            f"{story_result.generation_metadata['tokens_used']['output']} out"
        )
        print(f"   Batches: {story_result.generation_metadata['num_batches']}")
        print()

    except Exception as e:
        print(f"❌ Error during story generation: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

    # STEP 3: Push to JIRA
    print("=" * 80)
    print("STEP 3: Push Stories to JIRA")
    print("=" * 80)
    print()

    # Check if JIRA is configured
    jira_url = os.getenv("JIRA_URL")
    jira_token = os.getenv("JIRA_API_TOKEN")

    if not jira_url or not jira_token or jira_token == "your_jira_api_token_here":
        print("⚠️  JIRA not configured - skipping integration")
        print("   Set JIRA_URL and JIRA_API_TOKEN in .env to enable")
        print()
        jira_result = None
    else:
        try:
            jira_agent = JIRAIntegrationAgent()
            print(f"🔧 Initialized JIRAIntegrationAgent (project: {jira_agent.project_key})")
            print(f"📤 Pushing {len(story_result.stories)} stories to JIRA...")
            print()

            # Push stories (with dry_run=True for safety in test)
            # Set dry_run=False to actually create issues
            dry_run = os.getenv("JIRA_DRY_RUN", "true").lower() == "true"
            if dry_run:
                print("   [DRY RUN MODE - No issues will be created]")
                print("   Set JIRA_DRY_RUN=false in .env to create real issues")
                print()

            jira_result = jira_agent.push_stories(
                story_result.stories,
                dry_run=dry_run,
                stop_on_error=False,
            )

            if dry_run:
                print(f"✅ [DRY RUN] Would create {jira_result.total_created} JIRA issues")
            else:
                print(f"✅ Created {jira_result.total_created} JIRA issues")
                if jira_result.failed_count > 0:
                    print(f"⚠️  {jira_result.failed_count} issues failed")

            print()

        except Exception as e:
            print(f"❌ Error during JIRA integration: {e}")
            import traceback

            traceback.print_exc()
            jira_result = None

    # STEP 4: Display Results
    print("=" * 80)
    print("📊 GENERATED USER STORIES")
    print("=" * 80)
    print()

    for i, story in enumerate(story_result.stories, 1):
        print(f"{'─' * 80}")
        print(f"Story #{i}: {story.title}")
        print(f"{'─' * 80}")
        print(f"📌 User Story: {story.user_story}")
        print(f"📝 Story Points: {story.story_points}")
        print(f"⚡ Priority: {story.priority}")
        print(f"🏷️  Labels: {', '.join(story.labels)}")
        if story.epic_link:
            print(f"📂 Epic: {story.epic_link}")

        # Show JIRA link if created
        if jira_result and i <= len(jira_result.issues):
            jira_issue = jira_result.issues[i - 1]
            print(f"🔗 JIRA: {jira_issue.url}")

        print()
        print("✅ Acceptance Criteria:")
        for j, ac in enumerate(story.acceptance_criteria, 1):
            print(f"   {j}. {ac}")
        print()

        # Calculate INVEST score
        invest_score = story.calculate_invest_score()
        print(
            f"🎯 INVEST Score: {invest_score['total']}/12 "
            f"(I:{invest_score['independent']}, N:{invest_score['negotiable']}, "
            f"V:{invest_score['valuable']}, E:{invest_score['estimable']}, "
            f"S:{invest_score['small']}, T:{invest_score['testable']})"
        )
        print()

    # Group by priority
    print("=" * 80)
    print("📊 STORIES BY PRIORITY")
    print("=" * 80)
    print()

    by_priority = {}
    for story in story_result.stories:
        by_priority.setdefault(story.priority, []).append(story)

    for priority in ["P1", "P2", "P3", "P4"]:
        if priority in by_priority:
            stories = by_priority[priority]
            print(f"{priority} ({len(stories)} {'story' if len(stories) == 1 else 'stories'}):")
            for story in stories:
                print(f"  - {story.title} ({story.story_points} pts)")
            print()

    # Group by epic
    print("=" * 80)
    print("📊 STORIES BY EPIC")
    print("=" * 80)
    print()

    by_epic = {}
    for story in story_result.stories:
        epic = story.epic_link or "No Epic"
        by_epic.setdefault(epic, []).append(story)

    for epic, stories in sorted(by_epic.items()):
        print(f"{epic} ({len(stories)} {'story' if len(stories) == 1 else 'stories'}):")
        for story in stories:
            print(f"  - {story.title} ({story.story_points} pts, {story.priority})")
        print()

    # Calculate total story points
    total_points = sum(story.story_points for story in story_result.stories)
    print(f"💯 Total Story Points: {total_points}")
    print()

    # Save to JSON
    output_dir = project_root / "tests" / "output"
    output_dir.mkdir(exist_ok=True)

    # Save requirements
    req_output_path = output_dir / "extracted_requirements.json"
    req_output_data = {
        "summary": {
            "total_count": extraction_result.total_count,
            "model": extraction_result.extraction_metadata["model"],
            "tokens_used": extraction_result.extraction_metadata["tokens_used"],
        },
        "requirements": [req.model_dump() for req in extraction_result.requirements],
    }
    with open(req_output_path, "w") as f:
        json.dump(req_output_data, f, indent=2)

    # Save stories
    story_output_path = output_dir / "generated_stories.json"
    story_output_data = {
        "summary": {
            "total_count": story_result.total_count,
            "total_story_points": total_points,
            "model": story_result.generation_metadata["model"],
            "tokens_used": story_result.generation_metadata["tokens_used"],
        },
        "stories": [story.model_dump() for story in story_result.stories],
    }
    with open(story_output_path, "w") as f:
        json.dump(story_output_data, f, indent=2)

    print("=" * 80)
    print(f"💾 Results saved:")
    print(f"   Requirements: {req_output_path}")
    print(f"   Stories: {story_output_path}")
    print("=" * 80)
    print()
    print("✅ Full pipeline test completed successfully!")


if __name__ == "__main__":
    main()
