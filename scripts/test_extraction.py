#!/usr/bin/env python3
"""
Manual test script for requirement extraction.

Run this script to test the AnalysisAgent on the sample transcript and see
the extracted requirements in a readable format.

Usage:
    python scripts/test_extraction.py

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

# Load environment variables from .env file
from dotenv import load_dotenv

env_path = project_root / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    print(f"⚠️  Warning: .env file not found at {env_path}")
    print("   Using environment variables from shell")
    print()

from src.agents.analysis_agent import AnalysisAgent


def main():
    """Run extraction test on sample transcript."""
    # Check for API key
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ Error: ANTHROPIC_API_KEY environment variable not set")
        print("\nSet it with:")
        print("  export ANTHROPIC_API_KEY='your-key-here'")
        sys.exit(1)

    print("=" * 80)
    print("🤖 Backlog Synthesizer - Requirement Extraction Test")
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
    print(f"   Lines: {len(transcript.splitlines())} lines")
    print()

    # Initialize agent
    print("🔧 Initializing AnalysisAgent...")
    agent = AnalysisAgent(api_key=api_key)
    print(f"   Model: {agent.model}")
    print(f"   Max tokens: {agent.max_tokens}")
    print(f"   Temperature: {agent.temperature}")
    print()

    # Extract requirements
    print("🔍 Extracting requirements from transcript...")
    print("   (This may take 10-30 seconds...)")
    print()

    try:
        result = agent.extract_requirements(
            transcript, metadata={"source": "sample_transcript_001.txt"}
        )

        # Display results
        print("✅ Extraction complete!")
        print()
        print("=" * 80)
        print(f"📊 EXTRACTION SUMMARY")
        print("=" * 80)
        print(f"Total requirements found: {result.total_count}")
        print(f"Model used: {result.extraction_metadata['model']}")
        print(
            f"Tokens used: {result.extraction_metadata['tokens_used']['input']} input, "
            f"{result.extraction_metadata['tokens_used']['output']} output"
        )
        print()

        # Display each requirement
        print("=" * 80)
        print("📋 EXTRACTED REQUIREMENTS")
        print("=" * 80)
        print()

        for i, req in enumerate(result.requirements, 1):
            print(f"{'─' * 80}")
            print(f"Requirement #{i}")
            print(f"{'─' * 80}")
            print(f"📝 Description: {req.requirement}")
            print(f"🏷️  Type: {req.type}")
            print(f"⚡ Priority: {req.priority_signal}")
            print(f"💥 Impact: {req.impact}")
            print(f"👤 Stakeholder: {req.stakeholder}")
            print(f"📍 Location: Paragraph {req.paragraph_number}")
            print(f"💬 Quote: \"{req.source_citation}\"")
            print(f"ℹ️  Context: {req.context}")
            print()

        # Group by type
        print("=" * 80)
        print("📊 REQUIREMENTS BY TYPE")
        print("=" * 80)
        print()

        by_type = {}
        for req in result.requirements:
            by_type.setdefault(req.type, []).append(req)

        for req_type, reqs in sorted(by_type.items()):
            print(f"{req_type}: {len(reqs)} requirement(s)")

        print()

        # Group by priority
        print("=" * 80)
        print("📊 REQUIREMENTS BY PRIORITY")
        print("=" * 80)
        print()

        by_priority = {}
        for req in result.requirements:
            by_priority.setdefault(req.priority_signal, []).append(req)

        # Sort by priority level
        priority_order = ["urgent", "blocker", "critical", "high", "medium", "low", "nice-to-have"]
        for priority in priority_order:
            if priority in by_priority:
                print(f"{priority}: {len(by_priority[priority])} requirement(s)")

        print()

        # Save to JSON
        output_path = project_root / "tests" / "output" / "extracted_requirements.json"
        output_path.parent.mkdir(exist_ok=True)

        output_data = {
            "summary": {
                "total_count": result.total_count,
                "model": result.extraction_metadata["model"],
                "tokens_used": result.extraction_metadata["tokens_used"],
            },
            "requirements": [req.model_dump() for req in result.requirements],
        }

        with open(output_path, "w") as f:
            json.dump(output_data, f, indent=2)

        print("=" * 80)
        print(f"💾 Results saved to: {output_path}")
        print("=" * 80)
        print()
        print("✅ Test completed successfully!")

    except Exception as e:
        print(f"❌ Error during extraction: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
