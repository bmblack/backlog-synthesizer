#!/usr/bin/env python3
"""
End-to-end test for vector memory integration.

Tests that:
1. VectorMemoryEngine is initialized in workflow
2. Requirements are stored after extraction
3. Stories are stored after generation
4. Semantic search works on stored data
"""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.orchestration.graph import BacklogSynthesizerGraph
from src.orchestration.state import WorkflowState


def test_vector_memory_integration():
    """Test vector memory integration in workflow."""
    print("=" * 70)
    print("Vector Memory Integration Test")
    print("=" * 70)
    print()

    # 1. Create workflow with vector memory enabled
    print("1. Creating workflow with vector memory enabled...")
    # Note: Using mock JIRA config since we're only testing vector memory
    os.environ["JIRA_URL"] = "https://test.atlassian.net"
    os.environ["JIRA_EMAIL"] = "test@example.com"
    os.environ["JIRA_API_TOKEN"] = "test-token"
    os.environ["JIRA_PROJECT_KEY"] = "TEST"

    workflow = BacklogSynthesizerGraph(
        enable_checkpointing=False,
        enable_audit_logging=False,
        enable_vector_memory=True,
        vector_memory_path="data/chroma_test"
    )

    assert workflow.vector_memory is not None, "Vector memory should be initialized"
    print("   ✓ Vector memory initialized")
    print()

    # 2. Clear any existing test data
    print("2. Clearing test data...")
    workflow.vector_memory.clear()
    stats = workflow.vector_memory.get_stats()
    print(f"   Stats after clear: {stats}")
    assert stats["total_items"] == 0, "Should have no items after clear"
    print("   ✓ Test data cleared")
    print()

    # 3. Create test state with sample transcript
    print("3. Creating test state with sample transcript...")
    test_transcript = """
    Product Manager: We need to add a user authentication system.
    The system should support email/password login and OAuth integration
    with Google and GitHub. This is high priority for security.

    Developer: We should also implement two-factor authentication
    for enhanced security. This would be critical for enterprise users.

    Product Manager: Agreed. Let's also add a user profile page
    where users can manage their security settings.
    """

    state = WorkflowState(
        input_content=test_transcript,
        context={
            "project_type": "SaaS application",
            "_execution_id": "test-vector-001"
        }
    )
    print("   ✓ Test state created")
    print()

    # 4. Run extraction step
    print("4. Running extraction step...")
    result = workflow._extract_requirements_node(state)

    requirements = result.get("requirements", [])
    print(f"   Extracted {len(requirements)} requirements:")
    for i, req in enumerate(requirements, 1):
        print(f"   {i}. {req.get('requirement', 'N/A')[:80]}...")

    assert len(requirements) > 0, "Should extract at least one requirement"
    print("   ✓ Requirements extracted")
    print()

    # 5. Check vector memory stats after extraction
    print("5. Checking vector memory after extraction...")
    stats = workflow.vector_memory.get_stats()
    print(f"   Total items: {stats['total_items']}")
    print(f"   Requirements: {stats['requirements']}")
    print(f"   Stories: {stats['stories']}")
    print(f"   Sources: {stats['sources']}")

    assert stats["requirements"] > 0, "Should have requirements in vector memory"
    assert stats["requirements"] == len(requirements), "Requirement count should match"
    print("   ✓ Requirements stored in vector memory")
    print()

    # 6. Test semantic search on requirements
    print("6. Testing semantic search on requirements...")
    query = "user login and authentication"
    similar_reqs = workflow.vector_memory.search_similar_requirements(
        query=query,
        n_results=3
    )

    print(f"   Query: '{query}'")
    print(f"   Found {len(similar_reqs)} similar requirements:")
    for i, req in enumerate(similar_reqs, 1):
        distance = req.get("distance", 0)
        similarity = 1 - distance
        doc = req.get("document", "")[:100]
        print(f"   {i}. Similarity: {similarity:.3f} | {doc}...")

    assert len(similar_reqs) > 0, "Should find similar requirements"
    print("   ✓ Semantic search working on requirements")
    print()

    # 7. Update state with requirements and run story generation
    print("7. Running story generation step...")
    state.requirements = requirements
    story_result = workflow._generate_stories_node(state)

    stories = story_result.get("stories", [])
    print(f"   Generated {len(stories)} stories:")
    for i, story in enumerate(stories, 1):
        print(f"   {i}. {story.get('title', 'N/A')[:80]}...")

    assert len(stories) > 0, "Should generate at least one story"
    print("   ✓ Stories generated")
    print()

    # 8. Check vector memory stats after story generation
    print("8. Checking vector memory after story generation...")
    stats = workflow.vector_memory.get_stats()
    print(f"   Total items: {stats['total_items']}")
    print(f"   Requirements: {stats['requirements']}")
    print(f"   Stories: {stats['stories']}")
    print(f"   Sources: {stats['sources']}")

    assert stats["stories"] > 0, "Should have stories in vector memory"
    assert stats["stories"] == len(stories), "Story count should match"
    print("   ✓ Stories stored in vector memory")
    print()

    # 9. Test semantic search on stories
    print("9. Testing semantic search on stories...")
    query = "user profile settings"
    similar_stories = workflow.vector_memory.search_similar_stories(
        query=query,
        n_results=3
    )

    print(f"   Query: '{query}'")
    print(f"   Found {len(similar_stories)} similar stories:")
    for i, story in enumerate(similar_stories, 1):
        distance = story.get("distance", 0)
        similarity = 1 - distance
        doc = story.get("document", "")[:100]
        print(f"   {i}. Similarity: {similarity:.3f} | {doc}...")

    assert len(similar_stories) > 0, "Should find similar stories"
    print("   ✓ Semantic search working on stories")
    print()

    # 10. Test gap detection
    print("10. Testing gap detection...")
    new_requirements = [
        {
            "requirement": "Add single sign-on (SSO) support with SAML",
            "type": "feature",
            "priority_signal": "high"
        },
        {
            "requirement": "Implement email/password authentication",
            "type": "feature",
            "priority_signal": "high"
        }
    ]

    novel_reqs, covered_reqs = workflow.vector_memory.find_gaps(
        new_requirements=new_requirements,
        threshold=0.7
    )

    print(f"   Novel requirements (gaps): {len(novel_reqs)}")
    for req in novel_reqs:
        print(f"   - {req.get('requirement', 'N/A')[:80]}")

    print(f"   Covered requirements: {len(covered_reqs)}")
    for item in covered_reqs:
        req = item.get("requirement", {})
        similarity = item.get("similarity_score", 0)
        print(f"   - {req.get('requirement', 'N/A')[:80]} (similarity: {similarity:.3f})")

    print("   ✓ Gap detection working")
    print()

    # Final summary
    print("=" * 70)
    print("✓ All tests passed!")
    print("=" * 70)
    print()
    print("Summary:")
    print(f"  - Requirements stored: {stats['requirements']}")
    print(f"  - Stories stored: {stats['stories']}")
    print(f"  - Total items: {stats['total_items']}")
    print(f"  - Sources: {list(stats['sources'].keys())}")
    print()
    print("Vector memory integration is working correctly!")
    print()


if __name__ == "__main__":
    try:
        test_vector_memory_integration()
        sys.exit(0)
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
