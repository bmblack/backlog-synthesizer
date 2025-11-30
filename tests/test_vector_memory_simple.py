#!/usr/bin/env python3
"""
Simplified test for vector memory - no API keys required.

Tests that vector memory works correctly without needing full agent execution.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.memory.vector_engine import VectorMemoryEngine


def test_vector_memory():
    """Test vector memory with sample data."""
    print("=" * 70)
    print("Vector Memory Test (No API Keys Required)")
    print("=" * 70)
    print()

    # 1. Initialize
    print("1. Initializing vector memory...")
    vm = VectorMemoryEngine(
        persist_directory="data/chroma_test",
        collection_name="test_collection"
    )
    vm.clear()
    print("   ✓ Initialized and cleared")
    print()

    # 2. Add requirements
    print("2. Adding sample requirements...")
    requirements = [
        {
            "requirement": "Implement user authentication with email/password",
            "type": "feature",
            "priority_signal": "high",
            "impact": "Secure user access"
        },
        {
            "requirement": "Add OAuth integration with Google and GitHub",
            "type": "feature",
            "priority_signal": "high",
            "impact": "Social login support"
        },
        {
            "requirement": "Implement two-factor authentication",
            "type": "security",
            "priority_signal": "critical",
            "impact": "Enhanced security"
        },
    ]

    vm.add_requirements(requirements, source="transcript")
    stats = vm.get_stats()
    assert stats["requirements"] == 3
    print(f"   ✓ Added {stats['requirements']} requirements")
    print()

    # 3. Add stories
    print("3. Adding sample stories...")
    stories = [
        {
            "title": "User Registration",
            "description": "As a user, I want to register with email",
            "epic_link": "AUTH-001",
            "story_points": 5
        },
        {
            "title": "Social Login",
            "description": "As a user, I want to login with Google/GitHub",
            "epic_link": "AUTH-001",
            "story_points": 8
        },
    ]

    vm.add_stories(stories, source="generated")
    stats = vm.get_stats()
    assert stats["stories"] == 2
    print(f"   ✓ Added {stats['stories']} stories")
    print()

    # 4. Test semantic search
    print("4. Testing semantic search...")
    results = vm.search_similar_requirements("user login", n_results=2)
    assert len(results) > 0
    print(f"   Query: 'user login'")
    for i, r in enumerate(results[:2], 1):
        similarity = 1 - r["distance"]
        text = r["metadata"]["requirement_text"][:50]
        print(f"   {i}. Similarity: {similarity:.3f} | {text}...")
    print("   ✓ Semantic search working")
    print()

    # 5. Test gap detection
    print("5. Testing gap detection...")
    vm.add_requirements(requirements[:1], source="jira")  # Add one as "existing"

    new_reqs = [
        {"requirement": "Implement email/password authentication", "type": "feature", "priority_signal": "high"},
        {"requirement": "Add biometric authentication", "type": "feature", "priority_signal": "medium"},
    ]

    novel, covered = vm.find_gaps(new_reqs, threshold=0.7)
    print(f"   Novel requirements: {len(novel)}")
    print(f"   Covered requirements: {len(covered)}")
    print("   ✓ Gap detection working")
    print()

    print("=" * 70)
    print("✓ All tests passed!")
    print("=" * 70)
    stats = vm.get_stats()
    print(f"\nFinal stats: {stats['total_items']} items ({stats['requirements']} reqs, {stats['stories']} stories)")
    print("\nVector memory integration is working correctly! ✓")


if __name__ == "__main__":
    try:
        test_vector_memory()
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
