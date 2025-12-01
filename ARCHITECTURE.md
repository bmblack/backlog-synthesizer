# Backlog Synthesizer Architecture

> **📊 Visual Diagrams**: See [docs/diagrams.md](./docs/diagrams.md) for interactive Mermaid diagrams of the architecture.

## System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         BACKLOG SYNTHESIZER                         │
│                    AI-Powered Requirements Pipeline                 │
└─────────────────────────────────────────────────────────────────────┘

INPUT LAYER
┌──────────────────┐
│  Meeting         │
│  Transcripts     │───┐
└──────────────────┘   │
                       │
┌──────────────────┐   │
│  Stakeholder     │   │
│  Interviews      │───┤
└──────────────────┘   │
                       ├──► Document Ingestion
┌──────────────────┐   │
│  Product         │   │
│  Specs           │───┘
└──────────────────┘

═══════════════════════════════════════════════════════════════════════

ORCHESTRATION LAYER (LangGraph)
┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│  ┌──────────┐    ┌───────────┐    ┌──────────┐    ┌──────────┐      │
│  │ Ingest   │───►│ Confluence│───►│ Extract  │───►│  Fetch   │      │
│  │ Document │    │  Context  │    │   Reqs   │    │   JIRA   │      │
│  └──────────┘    └───────────┘    └──────────┘    └──────────┘      │
│                                          │              │           │
│                                          ▼              ▼           │
│                                    [Vector Memory] [Vector Memory]  │
│                                          │              │           │
│                                          └──────┬───────┘           │
│                                                 ▼                   │
│  ┌──────────┐    ┌───────────┐    ┌──────────┐                      │
│  │ Push to  │◄───│  Human    │◄───│ Generate │◄──-─┐                │
│  │   JIRA   │    │ Approval  │    │ Stories  │     │                │
│  └──────────┘    └───────────┘    └──────────┘     │                │
│       │                                  │         │                │
│       ▼                                  ▼         │                │
│  [Audit Log]                       [Vector Memory] │                │
│                                          │         │                │
│                                    ┌──────────┐    │                │
│                                    │  Detect  │────┘                │
│                                    │   Gaps   │                     │
│                                    └──────────┘                     │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘

═══════════════════════════════════════════════════════════════════════

AGENT LAYER
┌──────────────────────┐  ┌──────────────────────┐  ┌──────────────────┐
│   AnalysisAgent      │  │ StoryGenerationAgent │  │ JIRAIntegration  │
│                      │  │                      │  │     Agent        │
│ • Extract reqs       │  │ • Generate stories   │  │                  │
│ • Identify types     │  │ • INVEST criteria    │  │ • Fetch backlog  │
│ • Priority signals   │  │ • Story points       │  │ • Create issues  │
│ • Impact analysis    │  │ • Epic links         │  │ • Update issues  │
│                      │  │ • Acceptance tests   │  │ • Link issues    │
└──────────────────────┘  └──────────────────────┘  └──────────────────┘
         │                          │                         │
         └──────────────────────────┴─────────────────────────┘
                                    │
                              ┌─────▼─────┐
                              │ Claude AI │
                              │ (Sonnet)  │
                              └───────────┘

═══════════════════════════════════════════════════════════════════════

MEMORY & STORAGE LAYER
┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────-┐
│  Vector Memory      │  │  Checkpointing      │  │   Audit Logging      │
│   (ChromaDB)        │  │    (SQLite)         │  │     (SQLite)         │
│                     │  │                     │  │                      │
│ • Embeddings        │  │ • Workflow state    │  │ • Execution trace    │
│ • Semantic search   │  │ • Resumability      │  │ • Node history       │
│ • Gap detection     │  │ • Thread tracking   │  │ • Input/output logs  │
│ • Deduplication     │  │                     │  │ • Decision provenance│
└─────────────────────┘  └─────────────────────┘  └─────────────────────-┘
         │                        │                          │
         └────────────────────────┴──────────────────────────┘
                                  │
                         ┌────────▼────────┐
                         │  data/          │
                         │  • chroma/      │
                         │  • checkpoints/ │
                         │  • audit.db     │
                         └─────────────────┘

═══════════════════════════════════════════════════════════════════════

INTEGRATION LAYER
┌──────────────────────┐  ┌──────────────────────┐
│   Confluence MCP     │  │      JIRA API        │
│                      │  │                      │
│ • Fetch ADRs         │  │ • REST API client    │
│ • Search docs        │  │ • Issue management   │
│ • Context enrichment │  │ • JQL queries        │
└──────────────────────┘  └──────────────────────┘

═══════════════════════════════════════════════════════════════════════

OUTPUT LAYER
┌─────────────────────────────────────────────────────────────────────┐
│                          JIRA BACKLOG                               │
│  ┌────────────┐  ┌────────────┐  ┌───────────-─┐  ┌────────────┐    │
│  │  Epic:     │  │  Story:    │  │  Story:     │  │  Story:    │    │
│  │  Auth      │  │  Login     │  │  OAuth      │  │  2FA       │    │
│  │  System    │  │  Page      │  │  Integration│  │  Setup     │    │
│  └────────────┘  └────────────┘  └───────────-─┘  └────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
```

## Data Flow

### 1. Ingestion Flow
```
Transcript → Ingest Node → WorkflowState.input_content
```

### 2. Context Enrichment Flow
```
Input → Extract Topics → Confluence MCP → Fetch ADRs/Docs →
WorkflowState.context["confluence_context"]
```

### 3. Requirements Extraction Flow
```
Input + Confluence Context → AnalysisAgent (Claude) →
Requirements List → Vector Memory (embeddings) →
WorkflowState.requirements
```

### 4. Gap Detection Flow
```
JIRA Backlog → Vector Memory (source='jira') ─-─┐
                                                ├─► Semantic Comparison (70% threshold)
Extracted Requirements (source='transcript') ─-─┘
                                                │
                                                ▼
                        Novel Requirements vs Covered Requirements
                                                │
                                                ▼
                        WorkflowState.gap_analysis
```

### 5. Story Generation Flow
```
Novel Requirements + Context → StoryGenerationAgent (Claude) →
User Stories → Vector Memory (source='generated') →
WorkflowState.stories
```

### 6. Human Approval Flow
```
Stories → Display to User → Approval Input →
WorkflowState.approved (boolean)
```

### 7. JIRA Push Flow
```
Approved Stories → JIRAIntegrationAgent → JIRA REST API →
Created Issues → WorkflowState.jira_issues
```

### 8. Audit Trail Flow
```
Every Node Execution → AuditLogger → SQLite Database
(execution_id, node_name, inputs, outputs, timestamps, status)
```

## Component Details

### LangGraph Workflow State

```python
WorkflowState (TypedDict):
  - input_content: str           # Original transcript
  - context: Dict                # Project context + Confluence
  - requirements: List[Dict]     # Extracted requirements
  - jira_backlog: List[Dict]     # Existing JIRA issues
  - gap_analysis: Dict           # Novel vs covered requirements
  - stories: List[Dict]          # Generated user stories
  - approved: bool               # Human approval flag
  - jira_issues: List[Dict]      # Created JIRA issues
  - current_step: str            # Workflow progress tracker
```

### Vector Memory Schema

```python
Requirements:
  - id: UUID
  - text: str (requirement description)
  - embedding: float[384]
  - metadata:
      - type: "requirement"
      - source: "transcript" | "jira"
      - priority_signal: str
      - impact: str
      - execution_id: str

Stories:
  - id: UUID
  - text: str (story description)
  - embedding: float[384]
  - metadata:
      - type: "story"
      - source: "generated"
      - title: str
      - story_points: int
      - epic_link: str
      - execution_id: str
```

### Audit Log Schema

```sql
-- workflow_executions
(execution_id, workflow_name, thread_id, started_at, completed_at,
 status, total_nodes, input_preview, output_preview)

-- node_executions
(node_execution_id, execution_id, node_name, started_at, completed_at,
 status, error_message, inputs, outputs)
```

## Key Design Patterns

### 1. State Machine Pattern
- LangGraph manages workflow as a state machine
- Each node transitions state deterministically
- Conditional edges for branching logic

### 2. Semantic Search Pattern
- Text → Embeddings (384D vectors)
- Cosine similarity for matching
- Threshold-based deduplication (70%)

### 3. Human-in-the-Loop Pattern
- Automated pipeline with approval gate
- User reviews before JIRA push
- Audit trail for accountability

### 4. Context Enrichment Pattern
- Start with minimal input
- Progressively enrich with external data
- Each stage adds metadata

### 5. Saga Pattern
- Checkpointing enables recovery
- Each node is idempotent
- Workflow can resume from any node

## Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| AI | Anthropic Claude (Sonnet) | Requirements extraction, story generation |
| Orchestration | LangGraph | Workflow state management |
| Vector DB | ChromaDB | Semantic search, embeddings |
| Embeddings | Sentence Transformers | Text → vectors |
| Storage | SQLite | Checkpointing, audit logs |
| Integration | JIRA REST API | Issue management |
| Integration | Confluence MCP | Documentation context |
| Language | Python 3.11+ | Core implementation |

## Performance Characteristics

| Metric | Value | Notes |
|--------|-------|-------|
| Vector Search | <10ms | Sub-millisecond for <1000 items |
| Workflow Latency | 10-30s | Depends on LLM response time |
| Storage (Vector DB) | ~1MB | Per 1000 items |
| Storage (Checkpoints) | ~100KB | Per workflow run |
| Throughput | ~10 transcripts/min | Single-threaded |

## Security Considerations

1. **API Keys**: Stored in environment variables, never in code
2. **Audit Trail**: Complete provenance for compliance
3. **Access Control**: JIRA permissions respected
4. **Data Privacy**: No data sent to third parties except Anthropic/JIRA
5. **Local Storage**: All databases stored locally

## Scalability

### Current Limitations:
- Single-threaded execution
- In-memory state
- Local storage only

### Future Enhancements:
- Multi-threaded batch processing
- Distributed vector database (Weaviate, Pinecone)
- Cloud storage (S3, GCS)
- Web UI for human approval
- Real-time progress tracking

## Deployment Architecture

```
Development:
  - Local Python environment
  - Local ChromaDB
  - Local SQLite databases

Production (Future):
  - Docker containers
  - Cloud vector database
  - PostgreSQL for audit logs
  - Redis for checkpointing
  - Web UI (React)
  - API Gateway (FastAPI)
```

---

**Version**: 1.0  
**Last Updated**: 2024-11-29  
**Author**: Brandon Black
