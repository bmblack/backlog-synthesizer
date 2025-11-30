"""
Audit Logging Infrastructure.

This module provides comprehensive audit logging for the workflow execution,
capturing all agent invocations, decisions, and state transitions.

Audit logs are stored in SQLite and can be queried for:
- Debugging workflow execution
- Understanding agent reasoning
- Token usage tracking
- Cost analysis
- Compliance and traceability
"""

import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class AuditLogger:
    """
    Audit logger for workflow execution.

    Stores all agent invocations, decisions, and state transitions in SQLite.
    """

    def __init__(self, db_path: str = "data/audit.db"):
        """
        Initialize audit logger.

        Args:
            db_path: Path to audit SQLite database
        """
        self.db_path = db_path

        # Ensure data directory exists
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        # Initialize database
        self._init_db()

        logger.info(f"AuditLogger initialized: {db_path}")

    def _init_db(self):
        """Initialize audit database schema."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Workflow executions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS workflow_executions (
                    execution_id TEXT PRIMARY KEY,
                    thread_id TEXT NOT NULL,
                    input_file_path TEXT,
                    started_at TIMESTAMP NOT NULL,
                    completed_at TIMESTAMP,
                    status TEXT NOT NULL,
                    final_step TEXT,
                    error_count INTEGER DEFAULT 0
                )
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_workflow_thread_id
                ON workflow_executions(thread_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_workflow_started_at
                ON workflow_executions(started_at)
            """)

            # Agent invocations table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS agent_invocations (
                    invocation_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    execution_id TEXT NOT NULL,
                    agent_type TEXT NOT NULL,
                    step_name TEXT NOT NULL,
                    invoked_at TIMESTAMP NOT NULL,
                    completed_at TIMESTAMP,
                    status TEXT NOT NULL,
                    input_data TEXT,
                    output_data TEXT,
                    error_message TEXT,
                    tokens_input INTEGER DEFAULT 0,
                    tokens_output INTEGER DEFAULT 0,
                    model TEXT,
                    temperature REAL,
                    FOREIGN KEY (execution_id) REFERENCES workflow_executions(execution_id)
                )
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_invocations_execution_id
                ON agent_invocations(execution_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_invocations_agent_type
                ON agent_invocations(agent_type)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_invocations_invoked_at
                ON agent_invocations(invoked_at)
            """)

            # Decision points table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS decision_points (
                    decision_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    execution_id TEXT NOT NULL,
                    step_name TEXT NOT NULL,
                    decision_type TEXT NOT NULL,
                    decision_value TEXT NOT NULL,
                    decided_at TIMESTAMP NOT NULL,
                    context TEXT,
                    FOREIGN KEY (execution_id) REFERENCES workflow_executions(execution_id)
                )
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_decisions_execution_id
                ON decision_points(execution_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_decisions_decided_at
                ON decision_points(decided_at)
            """)

            # State transitions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS state_transitions (
                    transition_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    execution_id TEXT NOT NULL,
                    from_step TEXT,
                    to_step TEXT NOT NULL,
                    transitioned_at TIMESTAMP NOT NULL,
                    state_summary TEXT,
                    FOREIGN KEY (execution_id) REFERENCES workflow_executions(execution_id)
                )
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_transitions_execution_id
                ON state_transitions(execution_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_transitions_transitioned_at
                ON state_transitions(transitioned_at)
            """)

            conn.commit()

    @contextmanager
    def _get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def start_workflow(
        self,
        execution_id: str,
        thread_id: str,
        input_file_path: Optional[str] = None,
    ) -> None:
        """
        Log workflow start.

        Args:
            execution_id: Unique execution ID
            thread_id: Thread ID for checkpointing
            input_file_path: Path to input file
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO workflow_executions (
                    execution_id, thread_id, input_file_path,
                    started_at, status
                ) VALUES (?, ?, ?, ?, ?)
            """, (
                execution_id,
                thread_id,
                input_file_path,
                datetime.now().isoformat(),
                "running"
            ))
            conn.commit()

        logger.debug(f"Workflow started: {execution_id}")

    def complete_workflow(
        self,
        execution_id: str,
        status: str,
        final_step: str,
        error_count: int = 0,
    ) -> None:
        """
        Log workflow completion.

        Args:
            execution_id: Unique execution ID
            status: Final status (success, failed, etc.)
            final_step: Final workflow step
            error_count: Number of errors encountered
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE workflow_executions
                SET completed_at = ?, status = ?, final_step = ?, error_count = ?
                WHERE execution_id = ?
            """, (
                datetime.now().isoformat(),
                status,
                final_step,
                error_count,
                execution_id
            ))
            conn.commit()

        logger.debug(f"Workflow completed: {execution_id} ({status})")

    def log_agent_invocation(
        self,
        execution_id: str,
        agent_type: str,
        step_name: str,
        input_data: Optional[Dict[str, Any]] = None,
        output_data: Optional[Dict[str, Any]] = None,
        status: str = "success",
        error_message: Optional[str] = None,
        tokens_input: int = 0,
        tokens_output: int = 0,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> int:
        """
        Log agent invocation.

        Args:
            execution_id: Unique execution ID
            agent_type: Type of agent (e.g., "AnalysisAgent")
            step_name: Workflow step name
            input_data: Input data to agent (will be JSON-serialized)
            output_data: Output data from agent (will be JSON-serialized)
            status: Invocation status (success, failed)
            error_message: Error message if failed
            tokens_input: Input tokens used
            tokens_output: Output tokens generated
            model: Model name used
            temperature: Temperature setting

        Returns:
            Invocation ID
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO agent_invocations (
                    execution_id, agent_type, step_name, invoked_at,
                    completed_at, status, input_data, output_data,
                    error_message, tokens_input, tokens_output,
                    model, temperature
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                execution_id,
                agent_type,
                step_name,
                datetime.now().isoformat(),
                datetime.now().isoformat(),
                status,
                json.dumps(input_data) if input_data else None,
                json.dumps(output_data) if output_data else None,
                error_message,
                tokens_input,
                tokens_output,
                model,
                temperature
            ))
            conn.commit()
            invocation_id = cursor.lastrowid

        logger.debug(f"Agent invocation logged: {agent_type} ({step_name})")
        return invocation_id

    def log_decision(
        self,
        execution_id: str,
        step_name: str,
        decision_type: str,
        decision_value: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Log decision point.

        Args:
            execution_id: Unique execution ID
            step_name: Step where decision was made
            decision_type: Type of decision (e.g., "approval_gate")
            decision_value: Decision outcome (e.g., "approved")
            context: Additional context for decision
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO decision_points (
                    execution_id, step_name, decision_type,
                    decision_value, decided_at, context
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                execution_id,
                step_name,
                decision_type,
                decision_value,
                datetime.now().isoformat(),
                json.dumps(context) if context else None
            ))
            conn.commit()

        logger.debug(f"Decision logged: {decision_type} = {decision_value}")

    def log_state_transition(
        self,
        execution_id: str,
        from_step: Optional[str],
        to_step: str,
        state_summary: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Log state transition.

        Args:
            execution_id: Unique execution ID
            from_step: Previous step (None if starting)
            to_step: Next step
            state_summary: Summary of current state
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO state_transitions (
                    execution_id, from_step, to_step,
                    transitioned_at, state_summary
                ) VALUES (?, ?, ?, ?, ?)
            """, (
                execution_id,
                from_step,
                to_step,
                datetime.now().isoformat(),
                json.dumps(state_summary) if state_summary else None
            ))
            conn.commit()

        logger.debug(f"State transition: {from_step} → {to_step}")

    def get_workflow_audit(self, execution_id: str) -> Dict[str, Any]:
        """
        Get complete audit trail for a workflow execution.

        Args:
            execution_id: Unique execution ID

        Returns:
            Complete audit trail including:
            - Workflow metadata
            - All agent invocations
            - All decisions
            - All state transitions
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Get workflow info
            cursor.execute("""
                SELECT * FROM workflow_executions
                WHERE execution_id = ?
            """, (execution_id,))
            workflow = dict(cursor.fetchone() or {})

            # Get agent invocations
            cursor.execute("""
                SELECT * FROM agent_invocations
                WHERE execution_id = ?
                ORDER BY invoked_at
            """, (execution_id,))
            invocations = [dict(row) for row in cursor.fetchall()]

            # Get decisions
            cursor.execute("""
                SELECT * FROM decision_points
                WHERE execution_id = ?
                ORDER BY decided_at
            """, (execution_id,))
            decisions = [dict(row) for row in cursor.fetchall()]

            # Get state transitions
            cursor.execute("""
                SELECT * FROM state_transitions
                WHERE execution_id = ?
                ORDER BY transitioned_at
            """, (execution_id,))
            transitions = [dict(row) for row in cursor.fetchall()]

        return {
            "workflow": workflow,
            "invocations": invocations,
            "decisions": decisions,
            "transitions": transitions
        }

    def get_token_usage_summary(
        self,
        execution_id: Optional[str] = None,
        agent_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get token usage summary.

        Args:
            execution_id: Filter by execution ID (optional)
            agent_type: Filter by agent type (optional)

        Returns:
            Token usage summary with total input/output tokens
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            query = """
                SELECT
                    agent_type,
                    COUNT(*) as invocation_count,
                    SUM(tokens_input) as total_input_tokens,
                    SUM(tokens_output) as total_output_tokens,
                    AVG(tokens_input) as avg_input_tokens,
                    AVG(tokens_output) as avg_output_tokens
                FROM agent_invocations
                WHERE 1=1
            """
            params = []

            if execution_id:
                query += " AND execution_id = ?"
                params.append(execution_id)

            if agent_type:
                query += " AND agent_type = ?"
                params.append(agent_type)

            query += " GROUP BY agent_type"

            cursor.execute(query, params)
            results = [dict(row) for row in cursor.fetchall()]

        return {
            "by_agent": results,
            "total_input": sum(r["total_input_tokens"] or 0 for r in results),
            "total_output": sum(r["total_output_tokens"] or 0 for r in results),
        }

    def list_workflow_executions(
        self,
        limit: int = 10,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        List recent workflow executions.

        Args:
            limit: Maximum number of results
            offset: Offset for pagination

        Returns:
            List of workflow execution summaries
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM workflow_executions
                ORDER BY started_at DESC
                LIMIT ? OFFSET ?
            """, (limit, offset))

            return [dict(row) for row in cursor.fetchall()]
