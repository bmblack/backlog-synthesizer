"""
Tests for AnalysisAgent requirement extraction.

Tests the agent's ability to extract structured requirements from customer
transcripts with proper priority signals, impact, and source citations.
"""

import json
import os
from pathlib import Path

import pytest

from src.agents.analysis_agent import AnalysisAgent, ExtractionResult, Requirement


@pytest.fixture
def sample_transcript():
    """Load sample transcript fixture."""
    fixture_path = Path(__file__).parent / "fixtures" / "sample_transcript_001.txt"
    with open(fixture_path, "r") as f:
        return f.read()


@pytest.fixture
def analysis_agent():
    """Create AnalysisAgent instance (requires ANTHROPIC_API_KEY env var)."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        pytest.skip("ANTHROPIC_API_KEY not set")
    return AnalysisAgent(api_key=api_key)


class TestAnalysisAgent:
    """Test suite for AnalysisAgent."""

    def test_initialization(self):
        """Test agent initializes with correct defaults."""
        agent = AnalysisAgent()
        assert agent.model == "claude-sonnet-4-5-20250929"
        assert agent.max_tokens == 4096
        assert agent.temperature == 0.0

    def test_initialization_custom_params(self):
        """Test agent initializes with custom parameters."""
        agent = AnalysisAgent(
            model="claude-3-sonnet-20240229", max_tokens=8192, temperature=0.3
        )
        assert agent.model == "claude-3-sonnet-20240229"
        assert agent.max_tokens == 8192
        assert agent.temperature == 0.3

    def test_extract_requirements_empty_transcript(self, analysis_agent):
        """Test extraction fails with empty transcript."""
        with pytest.raises(ValueError, match="Transcript cannot be empty"):
            analysis_agent.extract_requirements("")

    def test_extract_requirements_sample_transcript(self, analysis_agent, sample_transcript):
        """Test extraction from sample transcript."""
        result = analysis_agent.extract_requirements(sample_transcript)

        # Verify result structure
        assert isinstance(result, ExtractionResult)
        assert isinstance(result.requirements, list)
        assert result.total_count == len(result.requirements)
        assert result.total_count > 0  # Should find multiple requirements

        # Verify extraction metadata
        assert "model" in result.extraction_metadata
        assert "tokens_used" in result.extraction_metadata
        assert "input" in result.extraction_metadata["tokens_used"]
        assert "output" in result.extraction_metadata["tokens_used"]

        # Verify at least one requirement has proper structure
        first_req = result.requirements[0]
        assert isinstance(first_req, Requirement)
        assert first_req.requirement  # Non-empty
        assert first_req.type in [
            "feature_request",
            "bug_report",
            "enhancement",
            "pain_point",
            "question",
        ]
        assert first_req.priority_signal in [
            "urgent",
            "blocker",
            "critical",
            "high",
            "medium",
            "low",
            "nice-to-have",
        ]
        assert first_req.impact  # Non-empty
        assert first_req.source_citation  # Non-empty
        assert first_req.paragraph_number > 0
        assert first_req.stakeholder  # Non-empty
        assert first_req.context  # Non-empty

    def test_extract_requirements_finds_key_requirements(
        self, analysis_agent, sample_transcript
    ):
        """Test that extraction finds expected requirements from transcript."""
        result = analysis_agent.extract_requirements(sample_transcript)

        # Expected requirements based on sample_transcript_001.txt
        expected_keywords = [
            "dark mode",
            "export",
            "search",
            "bulk",
            "keyboard",
            "slack",
            "teams",
            "github",
            "gitlab",
            "mobile",
            "permissions",
            "performance",
        ]

        # Collect all requirement text
        all_text = " ".join([req.requirement.lower() for req in result.requirements])

        # Verify we found most key requirements (allow some flexibility)
        found_count = sum(1 for keyword in expected_keywords if keyword in all_text)
        assert found_count >= len(expected_keywords) * 0.7, (
            f"Expected to find at least 70% of key requirements. "
            f"Found {found_count}/{len(expected_keywords)}"
        )

    def test_extract_requirements_with_metadata(self, analysis_agent, sample_transcript):
        """Test extraction preserves source metadata."""
        metadata = {
            "source": "Q4 2024 Customer Feedback",
            "date": "2024-11-15",
            "attendees": ["Sarah Chen", "Alex Martinez", "Maya Patel", "James Lee"],
        }

        result = analysis_agent.extract_requirements(sample_transcript, metadata)

        assert "source_metadata" in result.extraction_metadata
        assert result.extraction_metadata["source_metadata"] == metadata

    def test_extract_requirements_batch(self, analysis_agent):
        """Test batch extraction from multiple transcripts."""
        transcripts = [
            {
                "text": "[00:00] User: We need dark mode for our app.",
                "metadata": {"source": "Transcript 1"},
            },
            {
                "text": "[00:00] User: The export feature is broken and times out.",
                "metadata": {"source": "Transcript 2"},
            },
        ]

        results = analysis_agent.extract_requirements_batch(transcripts)

        assert len(results) == 2
        assert all(isinstance(r, ExtractionResult) for r in results)
        assert all(r.total_count > 0 for r in results)

    def test_extract_requirements_batch_handles_errors(self, analysis_agent):
        """Test batch extraction continues despite individual failures."""
        transcripts = [
            {"text": "[00:00] User: Valid transcript.", "metadata": {"source": "Valid"}},
            {"text": "", "metadata": {"source": "Empty"}},  # Will be skipped
            {"text": "[00:00] User: Another valid one.", "metadata": {"source": "Valid 2"}},
        ]

        results = analysis_agent.extract_requirements_batch(transcripts)

        # Should still return results (may include error entries)
        assert len(results) >= 2

    def test_consolidate_requirements(self, analysis_agent):
        """Test consolidation of multiple extraction results."""
        # Create mock results
        result1 = ExtractionResult(
            requirements=[
                Requirement(
                    requirement="Add dark mode",
                    type="feature_request",
                    priority_signal="high",
                    impact="Eye strain",
                    source_citation="We need dark mode",
                    paragraph_number=1,
                    stakeholder="User A",
                    context="Night shift",
                )
            ],
            total_count=1,
            extraction_metadata={"tokens_used": {"input": 100, "output": 50}},
        )

        result2 = ExtractionResult(
            requirements=[
                Requirement(
                    requirement="Fix export timeout",
                    type="bug_report",
                    priority_signal="urgent",
                    impact="Blocking reports",
                    source_citation="Export times out",
                    paragraph_number=10,
                    stakeholder="User B",
                    context="2000 issues",
                )
            ],
            total_count=1,
            extraction_metadata={"tokens_used": {"input": 120, "output": 60}},
        )

        consolidated = analysis_agent.consolidate_requirements([result1, result2])

        assert consolidated.total_count == 2
        assert len(consolidated.requirements) == 2
        assert consolidated.extraction_metadata["num_transcripts"] == 2
        assert consolidated.extraction_metadata["tokens_used"]["input"] == 220
        assert consolidated.extraction_metadata["tokens_used"]["output"] == 110


class TestRequirementModel:
    """Test suite for Requirement Pydantic model."""

    def test_requirement_validation(self):
        """Test Requirement model validates correctly."""
        req = Requirement(
            requirement="Add feature X",
            type="feature_request",
            priority_signal="high",
            impact="Users frustrated",
            source_citation="We really need feature X",
            paragraph_number=42,
            stakeholder="John Doe",
            context="For mobile users",
        )

        assert req.requirement == "Add feature X"
        assert req.type == "feature_request"
        assert req.priority_signal == "high"
        assert req.paragraph_number == 42

    def test_requirement_json_serialization(self):
        """Test Requirement can be serialized to JSON."""
        req = Requirement(
            requirement="Add feature X",
            type="feature_request",
            priority_signal="high",
            impact="Users frustrated",
            source_citation="We need X",
            paragraph_number=42,
            stakeholder="John Doe",
            context="Mobile",
        )

        json_str = req.model_dump_json()
        assert "Add feature X" in json_str
        assert "feature_request" in json_str

        # Test deserialization
        req_dict = json.loads(json_str)
        req2 = Requirement(**req_dict)
        assert req2.requirement == req.requirement
        assert req2.type == req.type
