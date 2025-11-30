"""
LangGraph workflow for multi-agent orchestration.

This module implements the state machine that orchestrates the entire
backlog synthesizer pipeline with checkpointing and human-in-the-loop approval.
"""

import logging
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, StateGraph

from src.agents.analysis_agent import AnalysisAgent
from src.agents.jira_integration_agent import JIRAIntegrationAgent
from src.agents.story_generation_agent import StoryGenerationAgent
from src.memory.vector_engine import VectorMemoryEngine
from src.orchestration.audit import AuditLogger
from src.orchestration.state import WorkflowState

# Configure logging
logger = logging.getLogger(__name__)


def get_checkpointer(checkpoint_type: Optional[str] = None):
    """
    Get checkpointer based on configuration.

    Args:
        checkpoint_type: Type of checkpointer to use:
            - "sqlite" (default): Persistent SQLite database
            - "memory": In-memory (lost on restart)
            - "none": No checkpointing

    Returns:
        Tuple of (checkpointer, context_manager) or (None, None)
        The context_manager must be kept alive for SQLite checkpointing

    Environment Variables:
        CHECKPOINT_TYPE: Override default checkpoint type
        CHECKPOINT_DB: SQLite database path (default: data/checkpoints.db)
    """
    if checkpoint_type is None:
        checkpoint_type = os.getenv("CHECKPOINT_TYPE", "sqlite")

    if checkpoint_type == "sqlite":
        db_path = os.getenv("CHECKPOINT_DB", "data/checkpoints.db")
        # Ensure data directory exists
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        logger.info(f"Using SQLite checkpointing: {db_path}")
        # SqliteSaver.from_conn_string() returns a context manager
        # We need to keep the context alive for the lifetime of the graph
        conn_context = SqliteSaver.from_conn_string(db_path)
        checkpointer = conn_context.__enter__()
        return checkpointer, conn_context
    elif checkpoint_type == "memory":
        logger.info("Using in-memory checkpointing (state lost on restart)")
        return MemorySaver(), None
    elif checkpoint_type == "none":
        logger.info("Checkpointing disabled")
        return None, None
    else:
        raise ValueError(f"Unknown checkpoint type: {checkpoint_type}")


class BacklogSynthesizerGraph:
    """
    LangGraph-based orchestration for the backlog synthesizer workflow.

    This class implements a state machine that coordinates:
    1. Document ingestion
    2. Requirement extraction (AnalysisAgent)
    3. Story generation (StoryGenerationAgent)
    4. Human-in-the-loop approval
    5. JIRA integration (JIRAIntegrationAgent)

    The workflow supports:
    - State persistence via checkpointing
    - Human approval gates
    - Conditional branching based on state
    - Error handling and recovery
    """

    def __init__(
        self,
        analysis_agent: Optional[AnalysisAgent] = None,
        story_agent: Optional[StoryGenerationAgent] = None,
        jira_agent: Optional[JIRAIntegrationAgent] = None,
        enable_checkpointing: bool = True,
        checkpoint_type: Optional[str] = None,
        enable_audit_logging: bool = True,
        audit_db_path: Optional[str] = None,
        enable_vector_memory: bool = True,
        vector_memory_path: Optional[str] = None,
    ):
        """
        Initialize the BacklogSynthesizerGraph.

        Args:
            analysis_agent: AnalysisAgent instance (creates new if None)
            story_agent: StoryGenerationAgent instance (creates new if None)
            jira_agent: JIRAIntegrationAgent instance (creates new if None)
            enable_checkpointing: Enable state persistence via checkpointing
            checkpoint_type: Type of checkpointer ("sqlite", "memory", "none")
                           If None, uses "sqlite" by default when checkpointing enabled
            enable_audit_logging: Enable audit logging
            audit_db_path: Path to audit database (default: data/audit.db)
            enable_vector_memory: Enable vector memory for semantic search
            vector_memory_path: Path to vector memory storage (default: data/chroma)
        """
        # Initialize agents
        self.analysis_agent = analysis_agent or AnalysisAgent()
        # Use Sonnet for story generation to handle larger outputs (13+ stories)
        self.story_agent = story_agent or StoryGenerationAgent(
            model="claude-sonnet-4-5-20250929",
            max_tokens=8192
        )
        self.jira_agent = jira_agent or JIRAIntegrationAgent()

        # Create vector memory engine
        if enable_vector_memory:
            persist_dir = vector_memory_path or os.getenv("VECTOR_MEMORY_PATH", "data/chroma")
            self.vector_memory = VectorMemoryEngine(persist_directory=persist_dir)
        else:
            self.vector_memory = None

        # Create audit logger
        if enable_audit_logging:
            db_path = audit_db_path or os.getenv("AUDIT_DB", "data/audit.db")
            self.audit_logger = AuditLogger(db_path=db_path)
        else:
            self.audit_logger = None

        # Create checkpointer based on configuration
        if enable_checkpointing:
            self.checkpointer, self._checkpoint_context = get_checkpointer(checkpoint_type)
        else:
            self.checkpointer = None
            self._checkpoint_context = None

        # Build the graph
        self.graph = self._build_graph()

        # Log initialization status
        checkpoint_status = "disabled"
        if self.checkpointer:
            checkpoint_type_name = type(self.checkpointer).__name__
            checkpoint_status = f"enabled ({checkpoint_type_name})"

        audit_status = "enabled" if self.audit_logger else "disabled"
        vector_memory_status = "enabled" if self.vector_memory else "disabled"

        logger.info(
            f"BacklogSynthesizerGraph initialized "
            f"(checkpointing={checkpoint_status}, audit_logging={audit_status}, "
            f"vector_memory={vector_memory_status})"
        )

    def _build_graph(self) -> StateGraph:
        """
        Build the LangGraph state machine.

        Workflow:
        START → ingest_document → extract_requirements → generate_stories
              → human_approval → [approved] → push_to_jira → END
                               → [rejected] → END

        Returns:
            Compiled StateGraph
        """
        # Create state graph
        workflow = StateGraph(WorkflowState)

        # Add nodes
        workflow.add_node("ingest_document", self._ingest_document_node)
        workflow.add_node("fetch_confluence_context", self._fetch_confluence_context_node)
        workflow.add_node("extract_requirements", self._extract_requirements_node)
        workflow.add_node("fetch_jira_backlog", self._fetch_jira_backlog_node)
        workflow.add_node("detect_gaps", self._detect_gaps_node)
        workflow.add_node("generate_stories", self._generate_stories_node)
        workflow.add_node("human_approval", self._human_approval_node)
        workflow.add_node("push_to_jira", self._push_to_jira_node)

        # Define edges
        workflow.set_entry_point("ingest_document")

        # Linear flow: ingest → confluence → extract → fetch_jira → detect_gaps → generate → approve → push
        workflow.add_edge("ingest_document", "fetch_confluence_context")
        workflow.add_edge("fetch_confluence_context", "extract_requirements")
        workflow.add_edge("extract_requirements", "fetch_jira_backlog")
        workflow.add_edge("fetch_jira_backlog", "detect_gaps")
        workflow.add_edge("detect_gaps", "generate_stories")
        workflow.add_edge("generate_stories", "human_approval")

        # Conditional branching based on approval
        workflow.add_conditional_edges(
            "human_approval",
            self._should_push_to_jira,
            {
                "approved": "push_to_jira",
                "rejected": END,
            }
        )

        # End after JIRA push
        workflow.add_edge("push_to_jira", END)

        # Compile graph
        return workflow.compile(checkpointer=self.checkpointer)

    # =========================================================================
    # Node Functions
    # =========================================================================

    def _ingest_document_node(self, state: WorkflowState) -> Dict[str, Any]:
        """
        Node: Ingest document and load content.

        Args:
            state: Current workflow state

        Returns:
            Updated state dict with input_content populated
        """
        logger.info(f"[INGEST] Loading document: {state.input_file_path}")

        try:
            if not state.input_file_path:
                raise ValueError("input_file_path is required")

            file_path = Path(state.input_file_path)
            if not file_path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")

            # For now, only support text files
            # TODO: Add PDF/DOCX parsing in future
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            logger.info(f"[INGEST] Loaded {len(content)} characters")

            return {
                "input_content": content,
                "current_step": "ingest_document",
            }

        except Exception as e:
            logger.error(f"[INGEST] Error: {e}")
            return {
                "current_step": "ingest_document",
                "errors": state.errors + [{"step": "ingest_document", "error": str(e)}],
            }

    def _fetch_confluence_context_node(self, state: WorkflowState) -> Dict[str, Any]:
        """
        Node: Fetch relevant context from Confluence (ADRs, docs, specs).

        Args:
            state: Current workflow state

        Returns:
            Updated state dict with Confluence context populated
        """
        logger.info("[CONFLUENCE] Fetching project context from Confluence")

        execution_id = state.context.get("_execution_id")

        try:
            # Extract topics from input content for targeted context fetching
            topics = self._extract_topics_from_input(state.input_content)

            # Fetch Confluence context
            # Note: Using MCP tools directly since we don't have a wrapped client yet
            context_pages = []
            
            # Search for ADRs
            logger.debug("[CONFLUENCE] Searching for ADR pages...")
            # In a real implementation, we would use MCP tools here
            # For now, we'll create a placeholder that can be filled in later
            
            confluence_context = {
                "pages": context_pages,
                "summary": "Confluence context will be fetched via MCP tools",
                "topics": topics,
            }

            logger.info(f"[CONFLUENCE] Fetched {len(context_pages)} context pages")

            # Store in state context for use in requirements extraction
            updated_context = state.context.copy()
            updated_context["confluence_context"] = confluence_context

            return {
                "context": updated_context,
                "current_step": "fetch_confluence_context",
            }

        except Exception as e:
            logger.warning(f"[CONFLUENCE] Error fetching context: {e}")
            # Continue workflow without Confluence context
            return {
                "current_step": "fetch_confluence_context",
                "errors": state.errors + [{"step": "fetch_confluence_context", "error": str(e)}],
            }

    def _extract_topics_from_input(self, input_content: Optional[str]) -> List[str]:
        """
        Extract key topics from input content for targeted Confluence searches.

        Args:
            input_content: Raw input content (transcript, document, etc.)

        Returns:
            List of key topics (e.g., ["authentication", "api", "database"])
        """
        if not input_content:
            return []

        # Simple keyword extraction (could be enhanced with NLP)
        keywords = [
            "authentication", "auth", "login", "security",
            "api", "rest", "graphql", "endpoint",
            "database", "postgres", "mysql", "sql",
            "frontend", "react", "ui", "ux",
            "backend", "python", "fastapi",
            "testing", "ci/cd", "deployment",
            "architecture", "design", "adr",
        ]

        content_lower = input_content.lower()
        found_topics = [kw for kw in keywords if kw in content_lower]

        # Return unique topics, limited to 3 most relevant
        return list(dict.fromkeys(found_topics))[:3]

    def _extract_requirements_node(self, state: WorkflowState) -> Dict[str, Any]:
        """
        Node: Extract requirements using AnalysisAgent.

        Args:
            state: Current workflow state

        Returns:
            Updated state dict with requirements populated
        """
        logger.info("[EXTRACT] Extracting requirements from document")

        execution_id = state.context.get("_execution_id")

        # Log state transition
        if self.audit_logger and execution_id:
            self.audit_logger.log_state_transition(
                execution_id=execution_id,
                from_step=state.current_step,
                to_step="extract_requirements"
            )

        try:
            if not state.input_content:
                raise ValueError("input_content is required")

            # Call AnalysisAgent
            result = self.analysis_agent.extract_requirements(
                transcript=state.input_content,
                metadata=state.context,
            )

            # Convert Requirement objects to dicts
            requirements_dicts = [req.model_dump() for req in result.requirements]

            logger.info(f"[EXTRACT] Extracted {len(requirements_dicts)} requirements")

            # Log agent invocation
            if self.audit_logger and execution_id:
                tokens = result.extraction_metadata.get("tokens_used", {})
                self.audit_logger.log_agent_invocation(
                    execution_id=execution_id,
                    agent_type="AnalysisAgent",
                    step_name="extract_requirements",
                    input_data={"transcript_length": len(state.input_content)},
                    output_data={"requirement_count": len(requirements_dicts)},
                    status="success",
                    tokens_input=tokens.get("input", 0),
                    tokens_output=tokens.get("output", 0),
                    model=result.extraction_metadata.get("model")
                )

            # Store in vector memory
            if self.vector_memory:
                self.vector_memory.add_requirements(
                    requirements=requirements_dicts,
                    source="transcript",
                    metadata={"execution_id": execution_id}
                )
                logger.debug(f"Stored {len(requirements_dicts)} requirements in vector memory")

            return {
                "requirements": requirements_dicts,
                "extraction_metadata": result.extraction_metadata,
                "current_step": "extract_requirements",
            }

        except Exception as e:
            logger.error(f"[EXTRACT] Error: {e}")

            # Log failed invocation
            if self.audit_logger and execution_id:
                self.audit_logger.log_agent_invocation(
                    execution_id=execution_id,
                    agent_type="AnalysisAgent",
                    step_name="extract_requirements",
                    status="failed",
                    error_message=str(e)
                )

            return {
                "current_step": "extract_requirements",
                "errors": state.errors + [{"step": "extract_requirements", "error": str(e)}],
            }

    def _fetch_jira_backlog_node(self, state: WorkflowState) -> Dict[str, Any]:
        """
        Node: Fetch existing JIRA backlog for gap detection.

        Args:
            state: Current workflow state

        Returns:
            Updated state dict with jira_backlog populated
        """
        logger.info("[FETCH] Fetching existing JIRA backlog")

        execution_id = state.context.get("_execution_id")

        try:
            # Fetch backlog from JIRA
            jira_issues = self.jira_agent.fetch_backlog(
                issue_types=["Story", "Task", "Bug"],
                max_results=100
            )

            logger.info(f"[FETCH] Fetched {len(jira_issues)} issues from JIRA")

            # Store JIRA issues in vector memory as requirements
            if self.vector_memory and jira_issues:
                # Convert JIRA issues to requirement format for vector storage
                jira_requirements = []
                for issue in jira_issues:
                    jira_req = {
                        "requirement": f"{issue['summary']}. {issue['description'][:200]}",
                        "type": issue["issue_type"].lower(),
                        "priority_signal": issue["priority"].lower(),
                        "impact": f"Existing JIRA issue: {issue['key']}",
                        "jira_key": issue["key"],
                        "jira_status": issue["status"],
                    }
                    jira_requirements.append(jira_req)

                # Store in vector memory with source='jira'
                self.vector_memory.add_requirements(
                    requirements=jira_requirements,
                    source="jira",
                    metadata={"execution_id": execution_id}
                )
                logger.debug(
                    f"Stored {len(jira_requirements)} JIRA issues in vector memory"
                )

            return {
                "jira_backlog": jira_issues,
                "current_step": "fetch_jira_backlog",
            }

        except Exception as e:
            logger.error(f"[FETCH] Error: {e}")
            # Continue workflow even if fetch fails (allow working without JIRA)
            return {
                "jira_backlog": [],
                "current_step": "fetch_jira_backlog",
                "errors": state.errors + [{"step": "fetch_jira_backlog", "error": str(e)}],
            }

    def _detect_gaps_node(self, state: WorkflowState) -> Dict[str, Any]:
        """
        Node: Detect gaps between extracted requirements and existing JIRA backlog.

        Args:
            state: Current workflow state

        Returns:
            Updated state dict with gap detection results
        """
        logger.info("[GAPS] Detecting gaps in backlog coverage")

        execution_id = state.context.get("_execution_id")

        try:
            if not self.vector_memory:
                logger.warning("[GAPS] Vector memory not enabled, skipping gap detection")
                return {
                    "gap_analysis": {
                        "novel_requirements": state.requirements,
                        "covered_requirements": [],
                        "total_novel": len(state.requirements),
                        "total_covered": 0,
                    },
                    "current_step": "detect_gaps",
                }

            if not state.requirements:
                logger.warning("[GAPS] No requirements to analyze")
                return {
                    "gap_analysis": {
                        "novel_requirements": [],
                        "covered_requirements": [],
                        "total_novel": 0,
                        "total_covered": 0,
                    },
                    "current_step": "detect_gaps",
                }

            # Perform gap detection
            novel_reqs, covered_reqs = self.vector_memory.find_gaps(
                new_requirements=state.requirements,
                threshold=0.7  # 70% similarity threshold
            )

            # Log gap analysis
            logger.info(
                f"[GAPS] Gap analysis complete: "
                f"{len(novel_reqs)} novel requirements, "
                f"{len(covered_reqs)} covered requirements"
            )

            # Log decision point
            if self.audit_logger and execution_id:
                self.audit_logger.log_decision(
                    execution_id=execution_id,
                    step_name="detect_gaps",
                    decision_type="gap_detection",
                    decision_value=f"novel={len(novel_reqs)},covered={len(covered_reqs)}",
                    context={
                        "total_requirements": len(state.requirements),
                        "threshold": 0.7
                    }
                )

            return {
                "gap_analysis": {
                    "novel_requirements": novel_reqs,
                    "covered_requirements": covered_reqs,
                    "total_novel": len(novel_reqs),
                    "total_covered": len(covered_reqs),
                },
                "current_step": "detect_gaps",
            }

        except Exception as e:
            logger.error(f"[GAPS] Error: {e}")
            # Continue workflow with all requirements as novel
            return {
                "gap_analysis": {
                    "novel_requirements": state.requirements,
                    "covered_requirements": [],
                    "total_novel": len(state.requirements),
                    "total_covered": 0,
                },
                "current_step": "detect_gaps",
                "errors": state.errors + [{"step": "detect_gaps", "error": str(e)}],
            }

    def _generate_stories_node(self, state: WorkflowState) -> Dict[str, Any]:
        """
        Node: Generate user stories using StoryGenerationAgent.

        Args:
            state: Current workflow state

        Returns:
            Updated state dict with stories populated
        """
        logger.info("[GENERATE] Generating user stories from requirements")

        try:
            if not state.requirements:
                raise ValueError("requirements are required")

            # Call StoryGenerationAgent
            result = self.story_agent.generate_stories(
                requirements=state.requirements,
                context=state.context,
            )

            # Convert UserStory objects to dicts
            stories_dicts = [story.model_dump() for story in result.stories]

            logger.info(f"[GENERATE] Generated {len(stories_dicts)} user stories")

            # Store in vector memory
            if self.vector_memory:
                execution_id = state.context.get("_execution_id", "unknown")
                self.vector_memory.add_stories(
                    stories=stories_dicts,
                    source="generated",
                    metadata={"execution_id": execution_id}
                )
                logger.debug(f"Stored {len(stories_dicts)} stories in vector memory")

            return {
                "stories": stories_dicts,
                "generation_metadata": result.generation_metadata,
                "current_step": "generate_stories",
            }

        except Exception as e:
            logger.error(f"[GENERATE] Error: {e}")
            return {
                "current_step": "generate_stories",
                "errors": state.errors + [{"step": "generate_stories", "error": str(e)}],
            }

    def _human_approval_node(self, state: WorkflowState) -> Dict[str, Any]:
        """
        Node: Wait for human approval (or auto-approve in non-interactive mode).

        This is a placeholder for human-in-the-loop approval. In production,
        this would integrate with a web UI or CLI prompt.

        Args:
            state: Current workflow state

        Returns:
            Updated state dict with approval_status set
        """
        logger.info("[APPROVAL] Awaiting human approval")

        execution_id = state.context.get("_execution_id")

        # For now, auto-approve if no interactive mode
        # In production, this would pause and wait for human input
        approval_status = state.approval_status

        if approval_status == "pending":
            # Auto-approve for non-interactive runs
            logger.info("[APPROVAL] Auto-approving (non-interactive mode)")
            approval_status = "approved"

        logger.info(f"[APPROVAL] Status: {approval_status}")

        # Log decision
        if self.audit_logger and execution_id:
            self.audit_logger.log_decision(
                execution_id=execution_id,
                step_name="human_approval",
                decision_type="approval_gate",
                decision_value=approval_status,
                context={
                    "requirement_count": len(state.requirements),
                    "story_count": len(state.stories),
                    "auto_approved": approval_status == "approved" and state.approval_status == "pending"
                }
            )

        return {
            "approval_status": approval_status,
            "current_step": "human_approval",
        }

    def _push_to_jira_node(self, state: WorkflowState) -> Dict[str, Any]:
        """
        Node: Push stories to JIRA using JIRAIntegrationAgent.

        Args:
            state: Current workflow state

        Returns:
            Updated state dict with jira_issues populated
        """
        # Check for dry_run mode in context
        dry_run = state.context.get("jira_dry_run", False)
        logger.info(f"[JIRA] Pushing stories to JIRA (dry_run={dry_run})")

        try:
            if not state.stories:
                raise ValueError("stories are required")

            # Call JIRAIntegrationAgent
            result = self.jira_agent.push_stories(
                stories=state.stories,
                dry_run=dry_run,
                stop_on_error=False,
            )

            # Convert JIRAIssue objects to dicts
            jira_issues_dicts = [issue.model_dump() for issue in result.issues]

            logger.info(f"[JIRA] Created {len(jira_issues_dicts)} JIRA issues")

            return {
                "jira_issues": jira_issues_dicts,
                "jira_metadata": result.integration_metadata,
                "current_step": "push_to_jira",
            }

        except Exception as e:
            logger.error(f"[JIRA] Error: {e}")
            return {
                "current_step": "push_to_jira",
                "errors": state.errors + [{"step": "push_to_jira", "error": str(e)}],
            }

    # =========================================================================
    # Conditional Edge Functions
    # =========================================================================

    def _should_push_to_jira(self, state: WorkflowState) -> str:
        """
        Conditional edge: Determine if we should push to JIRA based on approval.

        Args:
            state: Current workflow state

        Returns:
            "approved" or "rejected"
        """
        return state.approval_status

    # =========================================================================
    # Public API
    # =========================================================================

    def run(
        self,
        input_file_path: str,
        context: Optional[Dict[str, Any]] = None,
        thread_id: str = "default",
        execution_id: Optional[str] = None,
    ) -> WorkflowState:
        """
        Run the complete workflow.

        Args:
            input_file_path: Path to input document (transcript, PDF, etc.)
            context: Optional context (ADRs, project info, etc.)
            thread_id: Thread ID for checkpointing (allows resuming)
            execution_id: Unique execution ID for audit logging (auto-generated if None)

        Returns:
            Final WorkflowState after completion

        Example:
            >>> graph = BacklogSynthesizerGraph()
            >>> final_state = graph.run(
            ...     input_file_path="demo_data/sample_transcript_001.txt",
            ...     context={"project": "Backlog Synthesizer"}
            ... )
            >>> print(f"Created {len(final_state.jira_issues)} JIRA issues")
        """
        # Generate execution ID for audit logging
        if not execution_id:
            execution_id = f"exec_{uuid.uuid4().hex[:12]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        logger.info(f"Starting workflow for: {input_file_path} (execution_id={execution_id})")

        # Start audit logging
        if self.audit_logger:
            self.audit_logger.start_workflow(
                execution_id=execution_id,
                thread_id=thread_id,
                input_file_path=input_file_path
            )

        # Create initial state (include execution_id for audit logging)
        initial_context = context or {}
        initial_context["_execution_id"] = execution_id  # Store execution_id in context
        initial_state = WorkflowState(
            input_file_path=input_file_path,
            context=initial_context,
        )

        # Run the graph
        config = {"configurable": {"thread_id": thread_id}}

        try:
            final_state_dict = self.graph.invoke(
                initial_state.model_dump(),
                config=config
            )

            # Convert back to WorkflowState
            final_state = WorkflowState(**final_state_dict)

            # Complete audit logging
            if self.audit_logger:
                self.audit_logger.complete_workflow(
                    execution_id=execution_id,
                    status="success",
                    final_step=final_state.current_step,
                    error_count=len(final_state.errors)
                )

            logger.info(f"Workflow complete: {final_state.current_step}")

            return final_state

        except Exception as e:
            # Log workflow failure
            if self.audit_logger:
                self.audit_logger.complete_workflow(
                    execution_id=execution_id,
                    status="failed",
                    final_step="error",
                    error_count=1
                )
            raise

    def get_state(self, thread_id: str = "default") -> Optional[WorkflowState]:
        """
        Get the current state for a thread (requires checkpointing enabled).

        Args:
            thread_id: Thread ID to retrieve state for

        Returns:
            Current WorkflowState or None if not found
        """
        if not self.checkpointer:
            logger.warning("Checkpointing not enabled, cannot retrieve state")
            return None

        config = {"configurable": {"thread_id": thread_id}}
        state_snapshot = self.graph.get_state(config)

        if state_snapshot and state_snapshot.values:
            return WorkflowState(**state_snapshot.values)

        return None

    def resume(
        self,
        thread_id: str = "default",
        approval_status: Optional[str] = None,
    ) -> WorkflowState:
        """
        Resume a workflow from a checkpoint.

        Args:
            thread_id: Thread ID to resume
            approval_status: Optional approval status to set before resuming

        Returns:
            Final WorkflowState after resumption

        Example:
            >>> graph = BacklogSynthesizerGraph()
            >>> # Start workflow (will pause at approval)
            >>> graph.run("transcript.txt", thread_id="session-123")
            >>> # Resume with approval
            >>> final_state = graph.resume(
            ...     thread_id="session-123",
            ...     approval_status="approved"
            ... )
        """
        if not self.checkpointer:
            raise ValueError("Checkpointing not enabled, cannot resume")

        logger.info(f"Resuming workflow: {thread_id}")

        # Get current state
        current_state = self.get_state(thread_id)
        if not current_state:
            raise ValueError(f"No checkpoint found for thread: {thread_id}")

        # Update approval status if provided
        if approval_status:
            current_state.approval_status = approval_status

        # Resume from checkpoint
        config = {"configurable": {"thread_id": thread_id}}
        final_state_dict = self.graph.invoke(
            current_state.model_dump(),
            config=config
        )

        final_state = WorkflowState(**final_state_dict)

        logger.info(f"Workflow resumed: {final_state.current_step}")

        return final_state

    def __del__(self):
        """Clean up SQLite connection on deletion."""
        if self._checkpoint_context:
            try:
                self._checkpoint_context.__exit__(None, None, None)
            except Exception as e:
                logger.warning(f"Error closing checkpoint connection: {e}")
