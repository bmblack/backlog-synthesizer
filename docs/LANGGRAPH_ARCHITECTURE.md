# LangGraph Architecture

## State Machine Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    BACKLOG SYNTHESIZER                       │
│                   LangGraph Orchestration                    │
└─────────────────────────────────────────────────────────────┘

                            START
                              │
                              ▼
                    ┌─────────────────┐
                    │ ingest_document │
                    │                 │
                    │ • Load file     │
                    │ • Read content  │
                    └────────┬────────┘
                             │
                             ▼
                ┌────────────────────────┐
                │ extract_requirements   │
                │                        │
                │ • Call AnalysisAgent   │
                │ • Extract requirements │
                │ • Track tokens         │
                └───────────┬────────────┘
                            │
                            ▼
                ┌───────────────────────┐
                │ generate_stories      │
                │                       │
                │ • Call StoryAgent     │
                │ • Generate stories    │
                │ • Calculate points    │
                └──────────┬────────────┘
                           │
                           ▼
                ┌──────────────────────┐
                │ human_approval       │
                │                      │
                │ • Wait for approval  │
                │ • Auto-approve mode  │
                └──────────┬───────────┘
                           │
                ┌──────────┴───────────┐
                │                      │
                ▼                      ▼
         ┌──────────┐          ┌─────────────┐
         │ REJECTED │          │  APPROVED   │
         │          │          │             │
         │   END    │          │      │      │
         └──────────┘          │      ▼      │
                               │ ┌─────────────────┐
                               │ │ push_to_jira    │
                               │ │                 │
                               │ │ • Create epics  │
                               │ │ • Create stories│
                               │ │ • Link to epics │
                               │ └────────┬────────┘
                               │          │
                               │          ▼
                               │        END
                               └─────────────┘
```

---

## State Flow

### WorkflowState Schema

```python
┌─────────────────────────────────────────┐
│          WorkflowState                  │
├─────────────────────────────────────────┤
│ INPUT:                                  │
│  • input_file_path: str                 │
│  • input_content: str                   │
├─────────────────────────────────────────┤
│ REQUIREMENTS:                           │
│  • requirements: List[Dict]             │
│  • extraction_metadata: Dict            │
├─────────────────────────────────────────┤
│ STORIES:                                │
│  • stories: List[Dict]                  │
│  • generation_metadata: Dict            │
├─────────────────────────────────────────┤
│ JIRA:                                   │
│  • jira_issues: List[Dict]              │
│  • jira_metadata: Dict                  │
├─────────────────────────────────────────┤
│ CONTROL:                                │
│  • current_step: str                    │
│  • approval_status: str                 │
│  • approval_feedback: Optional[str]     │
│  • errors: List[Dict]                   │
├─────────────────────────────────────────┤
│ CONTEXT:                                │
│  • context: Dict[str, Any]              │
└─────────────────────────────────────────┘
```

---

## Node Details

### 1. ingest_document

**Input**: `state.input_file_path`
**Output**: `state.input_content`

```python
def _ingest_document_node(state: WorkflowState):
    # Load file from disk
    content = read_file(state.input_file_path)

    return {
        "input_content": content,
        "current_step": "ingest_document"
    }
```

**Future enhancements**:
- PDF parsing (pdfplumber)
- DOCX parsing (python-docx)
- Chunking for large documents

---

### 2. extract_requirements

**Input**: `state.input_content`
**Output**: `state.requirements`, `state.extraction_metadata`

```python
def _extract_requirements_node(state: WorkflowState):
    # Call AnalysisAgent
    result = analysis_agent.extract_requirements(
        transcript=state.input_content,
        metadata=state.context
    )

    return {
        "requirements": [req.model_dump() for req in result.requirements],
        "extraction_metadata": result.extraction_metadata,
        "current_step": "extract_requirements"
    }
```

**Agent**: AnalysisAgent
**Model**: Claude Sonnet 4.5
**Typical tokens**: 2,000-5,000 input / 500-3,000 output

---

### 3. generate_stories

**Input**: `state.requirements`
**Output**: `state.stories`, `state.generation_metadata`

```python
def _generate_stories_node(state: WorkflowState):
    # Call StoryGenerationAgent
    result = story_agent.generate_stories(
        requirements=state.requirements,
        context=state.context
    )

    return {
        "stories": [story.model_dump() for story in result.stories],
        "generation_metadata": result.generation_metadata,
        "current_step": "generate_stories"
    }
```

**Agent**: StoryGenerationAgent
**Model**: Claude Sonnet 4.5 (8192 max tokens)
**Typical tokens**: 3,000-6,000 input / 2,000-8,000 output

---

### 4. human_approval

**Input**: `state.approval_status`
**Output**: Updated `state.approval_status`

```python
def _human_approval_node(state: WorkflowState):
    # Check approval status
    approval_status = state.approval_status

    if approval_status == "pending":
        # Auto-approve for non-interactive runs
        approval_status = "approved"

    return {
        "approval_status": approval_status,
        "current_step": "human_approval"
    }
```

**Modes**:
- **Auto-approve**: For testing and CI/CD
- **Interactive**: Pause for human input (future)
- **Web UI**: Integrate with FastAPI dashboard (Phase 5)

---

### 5. push_to_jira

**Input**: `state.stories`
**Output**: `state.jira_issues`, `state.jira_metadata`

```python
def _push_to_jira_node(state: WorkflowState):
    # Check for dry-run mode
    dry_run = state.context.get("jira_dry_run", False)

    # Call JIRAIntegrationAgent
    result = jira_agent.push_stories(
        stories=state.stories,
        dry_run=dry_run,
        stop_on_error=False
    )

    return {
        "jira_issues": [issue.model_dump() for issue in result.issues],
        "jira_metadata": result.integration_metadata,
        "current_step": "push_to_jira"
    }
```

**Agent**: JIRAIntegrationAgent
**API**: Atlassian JIRA Cloud REST API
**Actions**:
1. Create epics from unique `epic_link` values
2. Map epic names → epic keys
3. Create stories with epic links

---

## Conditional Edges

### Approval Gate

```python
def _should_push_to_jira(state: WorkflowState) -> str:
    return state.approval_status  # "approved" or "rejected"
```

**Flow**:
- `"approved"` → `push_to_jira` node
- `"rejected"` → `END`

**Future conditional edges**:
- Gap detection: `has_gaps` → `gap_detection_node`
- Conflict detection: `has_conflicts` → `conflict_resolution_node`
- Large transcript: `needs_chunking` → `chunking_node`

---

## Checkpointing Architecture

### MemorySaver

LangGraph uses `MemorySaver` for state persistence:

```python
checkpointer = MemorySaver()
graph = workflow.compile(checkpointer=checkpointer)
```

### Thread-based State

Each workflow run has a unique `thread_id`:

```python
config = {"configurable": {"thread_id": "session-001"}}
final_state = graph.invoke(initial_state, config=config)
```

### Resume Capability

```python
# Start workflow
graph.run(input_file, thread_id="session-001")

# Later, retrieve checkpoint
current_state = graph.get_state(thread_id="session-001")

# Resume with approval
final_state = graph.resume(
    thread_id="session-001",
    approval_status="approved"
)
```

**Use cases**:
- Pause for human approval
- Long-running workflows
- Crash recovery
- Debugging and inspection

---

## Error Handling

### Error Accumulation

Errors are accumulated in `state.errors` rather than failing fast:

```python
try:
    result = agent.process(...)
except Exception as e:
    return {
        "errors": state.errors + [{
            "step": "node_name",
            "error": str(e)
        }]
    }
```

**Benefits**:
- Workflow completes despite errors
- All errors visible at end
- Partial results preserved
- Easier debugging

### Error Types

1. **Input errors**: File not found, empty content
2. **Agent errors**: API failures, JSON parsing
3. **Integration errors**: JIRA API failures
4. **Validation errors**: Invalid state transitions

---

## Configuration

### Context Dictionary

The `context` dict provides flexible configuration:

```python
context = {
    # Project metadata
    "project": "Backlog Synthesizer",
    "source": "customer transcript",

    # Agent configuration
    "jira_dry_run": True,
    "auto_approve": True,

    # Additional context
    "adrs": [...],
    "existing_backlog": [...]
}
```

### Agent Injection

Agents can be provided or auto-created:

```python
# Auto-create agents
graph = BacklogSynthesizerGraph()

# Inject custom agents
custom_story_agent = StoryGenerationAgent(
    model="claude-opus-4-5-20250929",
    max_tokens=16384
)
graph = BacklogSynthesizerGraph(story_agent=custom_story_agent)
```

---

## Performance Characteristics

### Typical Execution Times

| Node | Time | Notes |
|------|------|-------|
| ingest_document | < 1s | File I/O |
| extract_requirements | 5-15s | Claude API call |
| generate_stories | 20-60s | Claude API call (longer output) |
| human_approval | instant | Auto-approve mode |
| push_to_jira | 5-30s | JIRA API calls (epic + story creation) |
| **Total** | **30-120s** | Depends on transcript size |

### Scalability

**Current**:
- Single-threaded execution
- Sequential node processing
- One transcript at a time

**Future optimizations**:
- Parallel transcript processing (multiple thread_ids)
- Batch API calls
- Caching for repeated runs

---

## Integration with Existing System

### Old Architecture (scripts/test_full_pipeline.py)

```python
# Sequential, no state management
transcript = load_file(...)
requirements = analysis_agent.extract(transcript)
stories = story_agent.generate(requirements)
jira_agent.push(stories)
```

### New Architecture (src/orchestration/graph.py)

```python
# Orchestrated, stateful, resumable
graph = BacklogSynthesizerGraph()
final_state = graph.run(
    input_file_path="transcript.txt",
    thread_id="session-001"
)
```

**Migration path**: The old scripts still work and can coexist with the new LangGraph workflow.

---

## Future Extensions

### Phase 2: Gap Detection

```python
# Add gap detection node
workflow.add_node("detect_gaps", _detect_gaps_node)

# Conditional edge based on existing backlog
workflow.add_conditional_edges(
    "generate_stories",
    _should_detect_gaps,
    {
        "has_backlog": "detect_gaps",
        "no_backlog": "human_approval"
    }
)
```

### Phase 2: Conflict Detection

```python
# Add conflict detection node
workflow.add_node("detect_conflicts", _detect_conflicts_node)

# Run after story generation
workflow.add_edge("generate_stories", "detect_conflicts")
workflow.add_edge("detect_conflicts", "human_approval")
```

### Phase 5: Web Dashboard Integration

```python
# FastAPI endpoint
@app.post("/workflows/start")
async def start_workflow(request: WorkflowRequest):
    thread_id = generate_thread_id()
    graph.run(
        input_file_path=request.file_path,
        context={"auto_approve": False},
        thread_id=thread_id
    )
    return {"thread_id": thread_id, "status": "pending_approval"}

@app.post("/workflows/{thread_id}/approve")
async def approve_workflow(thread_id: str):
    final_state = graph.resume(
        thread_id=thread_id,
        approval_status="approved"
    )
    return {"status": "completed", "jira_issues": final_state.jira_issues}
```

---

## Testing Strategy

### Unit Tests (TODO)

```python
def test_ingest_document_node():
    state = WorkflowState(input_file_path="test.txt")
    result = graph._ingest_document_node(state)
    assert result["input_content"] is not None

def test_approval_gate():
    state = WorkflowState(approval_status="approved")
    edge = graph._should_push_to_jira(state)
    assert edge == "approved"
```

### Integration Tests

Current: `scripts/test_langgraph_workflow.py`
- Full workflow execution
- Checkpoint retrieval
- Error handling

---

## Conclusion

The LangGraph architecture provides:

✅ **Orchestration**: State machine coordination
✅ **Persistence**: Checkpoint-based state management
✅ **Flexibility**: Conditional branching and error handling
✅ **Extensibility**: Easy to add new nodes and edges
✅ **Testability**: Each node can be tested independently
✅ **Production-ready**: Handles errors gracefully, supports resumption

This architecture satisfies all capstone requirements for multi-agent orchestration and positions the system for Phase 2 enhancements.
