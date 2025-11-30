"""
State management for LangGraph workflow.

This module defines the state schema that flows through the multi-agent workflow.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class WorkflowState(BaseModel):
    """
    State schema for the backlog synthesizer workflow.

    This state is passed through each node in the LangGraph state machine,
    accumulating data and tracking progress through the pipeline.

    Attributes:
        # Input
        input_file_path: Path to the input document (transcript, PDF, etc.)
        input_content: Raw content from the input document

        # Requirements Extraction
        requirements: List of extracted requirements (from AnalysisAgent)
        extraction_metadata: Metadata about the extraction process

        # Story Generation
        stories: List of generated user stories (from StoryGenerationAgent)
        generation_metadata: Metadata about story generation

        # JIRA Integration
        jira_issues: List of created JIRA issues
        jira_metadata: Metadata about JIRA push operation

        # Workflow Control
        current_step: Current workflow step
        approval_status: Human approval status (approved/rejected/pending)
        approval_feedback: Optional feedback from human reviewer
        errors: List of errors encountered during workflow

        # Context
        context: Additional context (ADRs, project info, etc.)
    """

    # Input
    input_file_path: Optional[str] = Field(default=None, description="Path to input document")
    input_content: Optional[str] = Field(default=None, description="Raw input content")

    # Requirements Extraction
    requirements: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Extracted requirements from AnalysisAgent"
    )
    extraction_metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Metadata about extraction (tokens, model, etc.)"
    )

    # Story Generation
    stories: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Generated user stories from StoryGenerationAgent"
    )
    generation_metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Metadata about story generation"
    )

    # JIRA Integration
    jira_issues: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Created JIRA issues from JIRAIntegrationAgent"
    )
    jira_metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Metadata about JIRA push operation"
    )

    # JIRA Backlog & Gap Detection
    jira_backlog: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Existing JIRA backlog issues (fetched for gap detection)"
    )
    gap_analysis: Dict[str, Any] = Field(
        default_factory=dict,
        description="Gap detection results (novel vs covered requirements)"
    )

    # Workflow Control
    current_step: str = Field(
        default="start",
        description="Current workflow step"
    )
    approval_status: str = Field(
        default="pending",
        description="Human approval status (approved/rejected/pending)"
    )
    approval_feedback: Optional[str] = Field(
        default=None,
        description="Optional feedback from human reviewer"
    )
    errors: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Errors encountered during workflow"
    )

    # Context
    context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context (ADRs, project info, etc.)"
    )

    class Config:
        """Pydantic config."""
        arbitrary_types_allowed = True
