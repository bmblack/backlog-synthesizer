# Backlog Synthesizer - Comprehensive Implementation Plan

## Executive Summary

This document provides a detailed 9-week implementation plan for the Backlog Synthesizer multi-agent system. The plan addresses all required project components including AI-enhanced problem framing, multi-agent architecture, evaluation framework, and comprehensive AI usage documentation.

**Timeline:** 9 weeks (MVP in 2 weeks)
**Stories:** 38 user stories across 9 epics + 6 phases
**Target Metrics:** 90% completeness, 0.85 F1 conflict detection, 8/10 story quality

---

## Tech Stack Evaluation

### 1. LLM Selection

**Options Compared:**

| Model | Context Window | Reasoning Quality | Structured Output | Cost/1M tokens | Best For |
|-------|---------------|-------------------|-------------------|----------------|----------|
| **Claude 3.5 Sonnet** | 200K | Excellent | Native (JSON mode) | $3 in / $15 out | Complex reasoning, long documents |
| **GPT-4o** | 128K | Very Good | Function calling | $2.50 in / $10 out | Speed, integration ecosystem |
| **Gemini 1.5 Pro** | 1M | Good | JSON mode | $1.25 in / $5 out | Massive context, multimodal |
| **Claude 3 Opus** | 200K | Best | Native | $15 in / $75 out | Highest quality (expensive) |

**✅ Recommendation: Claude 3.5 Sonnet**

**Justification:**
1. **Reasoning Quality**: Requirement extraction and conflict detection need deep semantic understanding - Claude excels here
2. **Long Context**: Processing 50-page transcripts + architecture docs + backlog requires 50k+ tokens
3. **Instruction Following**: Story generation needs precise format adherence - Claude is most reliable
4. **Cost/Performance**: Better value than Opus, higher quality than GPT-4o for reasoning tasks

**Alternative Path**: Use **Gemini 1.5 Pro** if budget is tight - 1M context is overkill but cost is 60% lower

---

### 2. Multi-Agent Orchestration Framework

**Options Compared:**

| Framework | State Management | Learning Curve | Production Ready | Control Level | Monitoring |
|-----------|-----------------|----------------|------------------|---------------|------------|
| **LangGraph** | Built-in checkpointing | Steep | High | Medium | LangSmith integration |
| **CrewAI** | Basic | Easy | Medium | Low | Limited |
| **AutoGen** | Conversation-based | Medium | Low (research) | Medium | Basic |
| **Custom (Python + Redis)** | Full control | Low (if simple) | You build it | Complete | You build it |

**✅ Recommendation: LangGraph**

**Justification:**
1. **State Persistence**: Your project requires checkpointing (workflow can take hours) - LangGraph has this built-in
2. **Complex Workflows**: You have conditional branching:
   - If gaps detected → generate new stories
   - If conflicts detected → flag for review
   - If quality low → regenerate
3. **Human-in-the-Loop**: Need to approve stories before JIRA creation - LangGraph supports this natively
4. **Error Handling**: Built-in retry and fallback mechanisms
5. **Production Battle-Tested**: Used by major companies, active development

**Visual Comparison:**

```
LangGraph State Machine for Backlog Synthesizer:

┌─────────────┐
│   START     │
└──────┬──────┘
       │
       ▼
┌─────────────────┐
│  Ingest Docs    │──┐
│  (Agent 1)      │  │ Success
└─────────────────┘  │
       │             │
       │ Failure     │
       ▼             ▼
    [Retry 3x]   ┌──────────────────┐
                 │  Analyze Reqs    │
                 │  (Agent 2)       │
                 └────────┬─────────┘
                          │
                ┌─────────┴─────────┐
                ▼                   ▼
         ┌─────────────┐     ┌──────────────┐
         │ Detect Gaps │     │ Find Conflicts│
         │ (Agent 3)   │     │ (Agent 4)     │
         └──────┬──────┘     └───────┬───────┘
                │                    │
                └──────────┬─────────┘
                           ▼
                  ┌─────────────────┐
                  │ Generate Stories│
                  │ (Agent 5)       │
                  └────────┬────────┘
                           │
                           ▼
                  ┌─────────────────┐
                  │ Human Review    │◄──── Checkpoint
                  │ (Approval Gate) │
                  └────────┬────────┘
                           │
                    ┌──────┴──────┐
                    ▼             ▼
              [Approve]      [Reject/Edit]
                    │             │
                    ▼             └──► [Regenerate]
            ┌──────────────┐
            │ Push to JIRA │
            └──────┬───────┘
                   ▼
                [END]
```

**Why Not Custom?** You'd spend 40% of dev time building state management, checkpointing, and retry logic that LangGraph provides out of the box.

**Why Not CrewAI?** Too simplistic for this workflow - lacks conditional branching and checkpointing.

---

### 3. Integration Layer: Atlassian MCP Server

**✅ Recommendation: Use Atlassian MCP Server for JIRA & Confluence**

**Why MCP Over Direct API Calls:**

| Aspect | Direct API | MCP Server | Winner |
|--------|-----------|------------|--------|
| **Maintenance** | You maintain | Atlassian maintains | MCP ✅ |
| **Updates** | Manual API changes | Automatic | MCP ✅ |
| **Error Handling** | Custom implementation | Built-in retries | MCP ✅ |
| **Auth** | OAuth flow from scratch | Handled | MCP ✅ |
| **Testing** | Need to mock | Already proven | MCP ✅ |
| **Code Volume** | ~500 lines | ~50 lines | MCP ✅ |

**Justification:**
1. **Best Practice**: Don't reinvent the wheel - MCP is battle-tested
2. **Already Integrated**: Your framework uses MCP successfully
3. **Reduced Risk**: Proven with your 1000+ issue backlogs
4. **Future-Proof**: MCP protocol standard, not vendor lock-in
5. **Time Savings**: 20% of dev time saved vs. building API wrapper

**Confluence Setup:**
```python
# Via MCP - Simple and clean
from mcp_client import MCPClient

confluence = MCPClient("atlassian")

# Fetch architecture docs
pages = confluence.get_space_pages(space_key="ARCH")
for page in pages:
    content = confluence.get_page_content(page.id)
    # Extract ADRs, constraints, technical decisions
    store_in_vector_db(content)
```

**Confluence Content Structure:**
```
Confluence Space: ARCH (Architecture)
├── Architecture Decisions/
│   ├── ADR-001: Monolith-First Strategy
│   ├── ADR-002: Event-Driven for Async Tasks
│   ├── ADR-003: PostgreSQL for Primary DB
│   └── ADR-004: Redis for Caching
├── Technical Constraints/
│   ├── Technology Stack (Python, FastAPI)
│   ├── Security Requirements (OAuth, HTTPS)
│   └── API Standards (REST, versioning)
└── System Design/
    ├── Component Architecture
    ├── Data Flow Diagrams
    └── Integration Points
```

**Alternative**: If Confluence setup is delayed, start with local markdown and migrate later - the agent logic stays the same.

---

## Comprehensive Implementation Plan

### Phase 0: Project Setup & Infrastructure (Week 1, Days 1-2)

#### Story 0.1: Project Initialization
**Tasks:**
- [ ] Create project structure
- [ ] Set up virtual environment
- [ ] Install dependencies: `langchain`, `langgraph`, `anthropic`, `chromadb`, `fastapi`, `redis`
- [ ] Configure environment variables (.env)
- [ ] Set up git repository
- [ ] Create README with quick start

**Deliverables:**
```
backlog-synthesizer/
├── src/
│   ├── agents/          # Agent implementations
│   ├── tools/           # JIRA, GitHub, document parsers
│   ├── memory/          # Vector DB, state management
│   ├── workflows/       # LangGraph workflow definitions
│   ├── evaluation/      # Metrics, golden dataset
│   └── api/             # FastAPI endpoints
├── tests/
│   ├── unit/
│   ├── integration/
│   └── golden_dataset/
├── architecture_docs/   # Replaces Confluence
├── .env.example
├── pyproject.toml
└── README.md
```

#### Story 0.2: Architecture Documentation Setup
**Tasks:**
- [ ] Create 5 sample ADR documents
- [ ] Write technical constraints doc
- [ ] Document system architecture
- [ ] Create sample tech stack constraints

**Why Important**: These docs will be the "Confluence replacement" for constraint validation

---

### Phase 1: MVP - Core Pipeline (Week 1-2)

**Goal**: Ingest transcript → Extract requirements → Generate basic stories

#### Story 1.1: Document Ingestion System
**Agent**: `IngestionAgent`

**Tasks:**
- [ ] PDF parser using `pdfplumber`
- [ ] TXT/DOCX parser
- [ ] Document chunking (512 tokens, 50 token overlap)
- [ ] Metadata extraction (date, source, type)
- [ ] Store in ChromaDB with embeddings

**Tools Created:**
```python
# src/tools/document_parser.py
class DocumentParser:
    def parse_pdf(file_path: str) -> List[Chunk]
    def parse_text(file_path: str) -> List[Chunk]
    def chunk_document(text: str) -> List[Chunk]
```

**Acceptance Criteria:**
- Parse 50-page PDF in <10 seconds
- Extract with >95% text accuracy
- Store chunks in vector DB with embeddings

**Test Data Needed**: 3 sample meeting transcripts (create fake ones or use real sanitized examples)

---

#### Story 1.2: JIRA Integration Setup
**Tool**: `JIRAClient`

**Tasks:**
- [ ] Set up JIRA API authentication (API token)
- [ ] Implement issue fetching (all open issues in project)
- [ ] Parse issue structure: summary, description, labels, status
- [ ] Normalize format for internal processing
- [ ] Handle pagination (>1000 issues)

**Tools Created:**
```python
# src/tools/jira_client.py
class JIRAClient:
    def fetch_backlog(project_key: str) -> List[Issue]
    def create_issue(story: Story) -> str  # returns issue key
    def batch_create(stories: List[Story]) -> List[str]
```

**Note**: Use the MCP JIRA integration you already have or build custom wrapper

---

#### Story 1.3: Requirement Extraction Agent
**Agent**: `AnalysisAgent` (First capability)

**Tasks:**
- [ ] Design extraction prompt with few-shot examples
- [ ] Implement Claude call with structured output
- [ ] Extract: feature_request, pain_point, priority_signal
- [ ] Include source citation (quote + paragraph number)
- [ ] Store extracted requirements in state

**Prompt Template:**
```python
EXTRACTION_PROMPT = """
You are analyzing a customer meeting transcript to extract product requirements.

For each requirement you find, output:
- requirement: Clear description
- type: feature_request | bug_report | enhancement | question
- priority_signal: urgent | high | medium | low (based on language intensity)
- source_citation: Direct quote from transcript
- paragraph_number: Location in document

Transcript:
{transcript_text}

Output JSON array of requirements.
"""
```

**Acceptance Criteria:**
- Extract 90%+ of obvious requirements (test on golden dataset)
- Include source citations for traceability
- Classify priority with >80% accuracy

---

#### Story 1.4: Basic Story Generation Agent
**Agent**: `GenerationAgent`

**Tasks:**
- [ ] Design story generation prompt with template
- [ ] Implement Claude call with structured output
- [ ] Generate: title, description (As a... I want... So that...), acceptance_criteria[]
- [ ] Validate INVEST criteria (basic checks)
- [ ] Link story to source requirements

**Prompt Template:**
```python
GENERATION_PROMPT = """
You are a product manager writing user stories from requirements.

Requirements:
{requirements_json}

For each requirement, create a user story with:

Format:
**As a** [user type]
**I want** [goal]
**So that** [benefit]

**Acceptance Criteria:**
- [Specific, testable criterion 1]
- [Specific, testable criterion 2]
- [Specific, testable criterion 3]

Ensure each story:
- Is Independent (can be built separately)
- Is Valuable (delivers user benefit)
- Is Estimable (can be sized)
- Is Small (completable in 1 sprint)
- Is Testable (clear success criteria)

Output JSON array of stories.
"""
```

**Acceptance Criteria:**
- Generate stories for all requirements
- Stories pass basic INVEST validation
- Human-readable format

---

#### Story 1.5: LangGraph Workflow Setup
**Workflow**: `BasicPipeline`

**Tasks:**
- [ ] Define state schema (TypedDict with documents, requirements, stories)
- [ ] Create workflow graph: Ingest → Extract → Generate
- [ ] Implement checkpointing with SQLite
- [ ] Add basic error handling (retry 3x)
- [ ] Create CLI command to run workflow

**LangGraph Implementation:**
```python
# src/workflows/basic_pipeline.py
from langgraph.graph import StateGraph, END
from typing import TypedDict, List

class WorkflowState(TypedDict):
    documents: List[Document]
    requirements: List[Requirement]
    stories: List[Story]
    errors: List[str]

def create_workflow():
    workflow = StateGraph(WorkflowState)

    # Add nodes
    workflow.add_node("ingest", ingest_documents)
    workflow.add_node("extract", extract_requirements)
    workflow.add_node("generate", generate_stories)

    # Add edges
    workflow.add_edge("ingest", "extract")
    workflow.add_edge("extract", "generate")
    workflow.add_edge("generate", END)

    # Set entry point
    workflow.set_entry_point("ingest")

    return workflow.compile(
        checkpointer=SqliteSaver("checkpoints.db")
    )
```

**Acceptance Criteria:**
- Workflow runs end-to-end
- State persists across restarts
- Errors trigger retries

---

### Phase 2: Intelligence - Gap & Conflict Detection (Week 3-4)

**Goal**: Analyze stories against existing backlog and architecture docs

#### Story 2.1: Architecture Document Loader
**Task**: Load ADR markdown files into vector DB

**Tasks:**
- [ ] Scan `architecture_docs/` directory
- [ ] Parse markdown files
- [ ] Extract architecture decisions and constraints
- [ ] Store in vector DB with metadata (doc_type: "architecture")
- [ ] Create search interface for constraint lookup

**Tools Created:**
```python
# src/memory/architecture_store.py
class ArchitectureStore:
    def load_adrs(directory: str) -> None
    def search_constraints(query: str, top_k=5) -> List[Constraint]
```

---

#### Story 2.2: Gap Detection Agent
**Agent**: `AnalysisAgent` (Second capability)

**Tasks:**
- [ ] Load existing JIRA backlog
- [ ] Compare extracted requirements to existing stories (using embeddings)
- [ ] Identify requirements with no matching story (similarity < 0.7)
- [ ] Rank gaps by importance (based on transcript emphasis)
- [ ] Generate gap report

**Implementation:**
```python
# src/agents/gap_detector.py
def detect_gaps(requirements: List[Requirement], backlog: List[Issue]) -> GapReport:
    gaps = []
    for req in requirements:
        # Embed requirement
        req_embedding = embed(req.description)

        # Find most similar backlog item
        max_similarity = max([
            cosine_sim(req_embedding, embed(issue.summary))
            for issue in backlog
        ])

        if max_similarity < 0.7:
            gaps.append(Gap(
                requirement=req,
                reason="No similar backlog item found",
                max_similarity=max_similarity
            ))

    return GapReport(gaps=sorted(gaps, key=lambda g: g.requirement.priority))
```

**Acceptance Criteria:**
- Detect 90%+ of true gaps (test on golden dataset)
- Precision >0.8 (minimize false positives)
- Generate ranked list with explanations

---

#### Story 2.3: Conflict Detection Agent
**Agent**: `AnalysisAgent` (Third capability)

**Tasks:**
- [ ] Implement keyword-based conflict detection (fast first pass)
- [ ] Implement LLM-based conflict reasoning (deep analysis)
- [ ] Check pairwise story combinations
- [ ] Flag architectural constraint violations
- [ ] Generate conflict report with resolution suggestions

**Two-Stage Approach:**
```python
# Stage 1: Fast keyword detection
CONFLICT_KEYWORDS = [
    ("add", "remove"),
    ("enable", "disable"),
    ("always", "never"),
    ("increase", "decrease"),
    ("synchronous", "asynchronous")
]

# Stage 2: LLM reasoning for complex conflicts
CONFLICT_PROMPT = """
Analyze if these two stories conflict:

Story A: {story_a}
Story B: {story_b}

Architecture Constraints:
{constraints}

Do they conflict? If yes, explain why and suggest resolution.
Output JSON: {conflicting: bool, reason: str, resolution: str}
"""
```

**Acceptance Criteria:**
- Detect obvious keyword conflicts in <100ms per pair
- LLM reasoning for complex cases with >0.85 F1 score
- Suggest actionable resolutions

---

#### Story 2.4: Architecture Constraint Validation
**Agent**: `AnalysisAgent` (Fourth capability)

**Tasks:**
- [ ] Search ADR docs for relevant constraints
- [ ] Check if story violates any constraints
- [ ] Flag violations with explanation
- [ ] Suggest alternative implementations

**Example:**
```
Story: "Add new microservice for user notifications"

Constraint Found (ADR-001):
"All new features must be built within the monolith until we reach 100k users"

Violation: YES
Explanation: Story proposes new microservice, but architecture mandates monolith
Resolution: Implement notification feature as module within existing user service
```

**Acceptance Criteria:**
- Find relevant constraints with >0.8 recall
- Flag violations with clear explanations
- Suggest alternatives for 80%+ of violations

---

#### Story 2.5: Enhance Workflow with Analysis Stages
**Workflow**: Add analysis nodes to graph

**Tasks:**
- [ ] Add `detect_gaps` node
- [ ] Add `detect_conflicts` node
- [ ] Add `validate_constraints` node
- [ ] Add conditional branching: if gaps/conflicts found → flag for review
- [ ] Update state schema to include analysis results

**Updated Workflow:**
```
Ingest → Extract → Generate → Detect Gaps → Find Conflicts → Validate Constraints → Review Gate → Push to JIRA
```

---

### Phase 3: Multi-Agent Orchestration & Memory (Week 5-6)

**Goal**: Robust multi-agent system with memory and audit trail

#### Story 3.1: Agent Memory System
**Infrastructure**: Persistent memory for agents

**Tasks:**
- [ ] Implement episodic memory (recent conversation history)
- [ ] Implement semantic memory (facts extracted from docs)
- [ ] Implement procedural memory (rules and patterns)
- [ ] Store in Redis (fast) + ChromaDB (semantic search)
- [ ] Add memory retrieval to agent prompts

**Memory Types:**
```python
# Episodic: What happened recently
episodic_memory.store({
    "timestamp": "2025-11-26T10:15:00",
    "event": "Extracted 12 requirements from Q4_customer_feedback.pdf",
    "agent": "AnalysisAgent"
})

# Semantic: Facts learned
semantic_memory.store({
    "fact": "Users frequently request dark mode feature",
    "source": "5 different transcripts",
    "confidence": 0.95
})

# Procedural: Rules learned
procedural_memory.store({
    "rule": "When transcript mentions 'urgent', set priority to high",
    "success_rate": 0.87
})
```

**Acceptance Criteria:**
- Memory persists across workflow runs
- Agents retrieve relevant context (top-5 memories)
- Memory improves quality over time (track metrics)

---

#### Story 3.2: Audit Trail System
**Infrastructure**: Track all decisions with provenance

**Tasks:**
- [ ] Log every agent decision with reasoning
- [ ] Link stories back to source documents (transcript paragraphs)
- [ ] Log all LLM calls (prompt, response, tokens)
- [ ] Generate human-readable audit report
- [ ] Create web UI to view audit trail

**Audit Log Structure:**
```json
{
  "decision_id": "dec_001",
  "timestamp": "2025-11-26T10:15:00",
  "agent": "GenerationAgent",
  "decision": "Generated story BS-142",
  "reasoning": "Extracted from requirement req_005 about dark mode",
  "source_documents": [
    {
      "doc_id": "transcript_q4_2024",
      "paragraph": 12,
      "quote": "Our users really need a dark mode option"
    }
  ],
  "llm_call": {
    "model": "claude-3-5-sonnet-20241022",
    "prompt_tokens": 3241,
    "completion_tokens": 512,
    "cost": 0.0124
  }
}
```

**Acceptance Criteria:**
- Every story has full provenance chain
- Audit reports generated in <1 second
- Web UI shows decision flow visually

---

#### Story 3.3: Specialized Agent Implementations

**Tasks:**
- [ ] Refactor into specialized agents:
  - `IngestionAgent`: Document parsing
  - `AnalysisAgent`: Requirement extraction + gap/conflict detection
  - `GenerationAgent`: Story creation
  - `OrchestratorAgent`: Workflow coordination
- [ ] Implement agent communication protocol (JSON messages)
- [ ] Add agent health checks
- [ ] Implement graceful degradation (continue if optional agent fails)

**Agent Communication:**
```python
# src/agents/base_agent.py
class Message:
    type: str  # REQUEST, RESPONSE, EVENT, ERROR
    sender: str
    recipient: str
    payload: dict
    metadata: dict

class BaseAgent:
    def handle_message(self, msg: Message) -> Message:
        # Process message and return response
        pass
```

**Acceptance Criteria:**
- Agents communicate via standardized messages
- Failed agents don't crash workflow
- Agent status exposed via API

---

### Phase 4: Evaluation Framework (Week 6-7)

**Goal**: Measure system quality with golden dataset and LLM judge

#### Story 4.1: Create Golden Dataset
**Tasks:**
- [ ] Write 5 sample meeting transcripts (representing different scenarios)
- [ ] Manually create ideal user stories for each
- [ ] Document expected gaps and conflicts
- [ ] Include edge cases (ambiguous requirements, conflicts)
- [ ] Store in `tests/golden_dataset/`

**Dataset Structure:**
```
tests/golden_dataset/
├── scenario_1_greenfield/
│   ├── input_transcript.txt
│   ├── input_backlog.json (empty)
│   ├── expected_stories.json (10 stories)
│   └── metadata.json
├── scenario_2_enhancement/
│   ├── input_transcript.txt
│   ├── input_backlog.json (20 existing stories)
│   ├── expected_stories.json (5 new stories)
│   ├── expected_gaps.json (2 gaps)
│   └── metadata.json
├── scenario_3_conflicts/
│   ├── input_transcript.txt
│   ├── input_backlog.json (conflicting stories)
│   ├── expected_conflicts.json (3 conflicts)
│   └── metadata.json
├── scenario_4_architecture_violations/
│   ├── input_transcript.txt
│   ├── architecture_docs/
│   ├── expected_violations.json
│   └── metadata.json
└── scenario_5_ambiguous/
    ├── input_transcript.txt
    ├── expected_clarification_questions.json
    └── metadata.json
```

**Scenarios:**
1. Greenfield (no existing backlog)
2. Enhancement (add to existing backlog)
3. Conflicts (contradictory requirements)
4. Architecture violations (stories violating constraints)
5. Ambiguous (unclear requirements needing clarification)

---

#### Story 4.2: Implement Evaluation Metrics
**Tasks:**
- [ ] **Completeness**: % of requirements converted to stories
- [ ] **Accuracy**: F1 score for gap detection
- [ ] **Precision/Recall**: For conflict detection
- [ ] **Story Quality**: INVEST score (1-5 scale per criterion)
- [ ] **Efficiency**: Processing time vs baseline

**Metric Implementations:**
```python
# src/evaluation/metrics.py
def calculate_completeness(requirements, generated_stories):
    covered = sum(1 for req in requirements if has_matching_story(req, generated_stories))
    return covered / len(requirements)

def calculate_gap_detection_f1(detected_gaps, true_gaps):
    tp = len(set(detected_gaps) & set(true_gaps))
    fp = len(set(detected_gaps) - set(true_gaps))
    fn = len(set(true_gaps) - set(detected_gaps))

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0

    return 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

def calculate_invest_score(story):
    scores = {
        "independent": check_independent(story),
        "negotiable": check_negotiable(story),
        "valuable": check_valuable(story),
        "estimable": check_estimable(story),
        "small": check_small(story),
        "testable": check_testable(story)
    }
    return sum(scores.values()) / len(scores)
```

**Acceptance Criteria:**
- All metrics implemented and tested
- Baseline measurements recorded (manual process)
- Target metrics defined (e.g., 90% completeness, 0.85 F1)

---

#### Story 4.3: LLM-as-Judge Evaluation
**Tasks:**
- [ ] Design evaluation prompt with rubric
- [ ] Implement Claude judge (separate API instance)
- [ ] Score generated stories on INVEST dimensions (1-5 each)
- [ ] Compare to human baseline scores
- [ ] Generate detailed feedback for low-scoring stories

**Judge Prompt:**
```python
JUDGE_PROMPT = """
You are evaluating the quality of a user story.

Story:
{story_text}

Evaluate on these dimensions (1-5 scale):

1. Independent: Can this story be developed and deployed independently?
2. Negotiable: Is there room for discussion on implementation?
3. Valuable: Does it deliver clear user/business value?
4. Estimable: Can developers reasonably estimate effort?
5. Small: Can it be completed in one sprint (1-2 weeks)?
6. Testable: Are the acceptance criteria clear and testable?

For each dimension:
- Score (1-5)
- Reasoning (why this score)
- Improvement suggestion (if score < 4)

Output JSON with scores, reasoning, and overall quality assessment.
"""
```

**Acceptance Criteria:**
- Judge scores correlate with human scores (>0.8 correlation)
- Generate actionable feedback for improvements
- Flag stories below 3.5/5 average for human review

---

#### Story 4.4: Evaluation Dashboard
**Tasks:**
- [ ] Create web dashboard showing metrics
- [ ] Real-time quality tracking during generation
- [ ] Compare system performance to golden dataset
- [ ] Show cost metrics (API tokens, latency)
- [ ] Export evaluation reports (PDF/JSON)

**Dashboard Features:**
- Overall metrics: Completeness, F1 scores, Quality
- Per-story breakdown: INVEST scores, citations, conflicts
- Trend over time: Quality improving with memory?
- Cost analysis: Tokens/story, $/story

---

### Phase 5: User Interface & JIRA Integration (Week 7-8)

**Goal**: Production-ready system with UI and automation

#### Story 5.1: Story Review Web UI
**Tasks:**
- [ ] Build FastAPI backend with REST API
- [ ] Create React/HTMX frontend for story review
- [ ] Display generated stories in card view
- [ ] Show provenance (source quotes, decision trail)
- [ ] Enable inline editing
- [ ] Approve/reject/edit workflow
- [ ] Batch actions (approve all, reject all)

**UI Components:**
```
┌─────────────────────────────────────────────────┐
│ Backlog Synthesizer - Story Review              │
├─────────────────────────────────────────────────┤
│                                                 │
│  📊 Summary: 12 stories generated               │
│  ⚠️  Warnings: 2 conflicts detected             │
│  ✅ Quality: 8.2/10 average                     │
│                                                 │
│  ┌─────────────────────────────────────────┐  │
│  │ Story BS-142: Add Dark Mode              │  │
│  │                                           │  │
│  │ As a user, I want...                      │  │
│  │                                           │  │
│  │ Source: Q4_feedback.pdf, paragraph 12    │  │
│  │ Quote: "Our users really need dark mode" │  │
│  │                                           │  │
│  │ Quality: 8.5/10 | No conflicts           │  │
│  │                                           │  │
│  │ [✓ Approve] [✎ Edit] [✗ Reject]         │  │
│  └─────────────────────────────────────────┘  │
│                                                 │
│  [Approve All] [Push to JIRA]                  │
└─────────────────────────────────────────────────┘
```

**Acceptance Criteria:**
- Load 100 stories in <2 seconds
- Inline editing saves immediately
- Keyboard shortcuts (j/k to navigate, e to edit, a to approve)
- Mobile-responsive

---

#### Story 5.2: JIRA Bulk Creation
**Tasks:**
- [ ] Implement batch story creation in JIRA
- [ ] Map internal story format to JIRA fields
- [ ] Apply labels based on tags
- [ ] Link stories to epics
- [ ] Attach provenance (transcript links)
- [ ] Handle errors gracefully (retry, skip, report)

**Mapping:**
```python
# Internal Story → JIRA Issue
{
    "title": story.title,
    "description": format_as_jira_markdown(story),
    "issuetype": "Story",
    "labels": story.tags,
    "epic_link": story.epic_id,
    "customfield_10010": story.provenance_url  # Link to transcript
}
```

**Acceptance Criteria:**
- Create 50 stories in <30 seconds
- 99% success rate (with retry)
- Return JIRA issue keys for tracking

---

#### Story 5.3: CLI for Automation
**Tasks:**
- [ ] Build CLI with commands:
  - `backlog-synth ingest <files>`
  - `backlog-synth analyze --project <key>`
  - `backlog-synth generate --output stories.json`
  - `backlog-synth push --approve-all`
  - `backlog-synth eval --golden`
- [ ] Support configuration via YAML file
- [ ] Output JSON for programmatic use
- [ ] Exit codes for CI/CD integration

**Example Usage:**
```bash
# End-to-end pipeline
backlog-synth run \
  --transcripts "meetings/*.pdf" \
  --architecture-docs "architecture_docs/" \
  --jira-project "PROJ" \
  --auto-push \
  --output report.json

# Output
✓ Ingested 5 transcripts (124 pages)
✓ Extracted 47 requirements
✓ Detected 3 gaps, 2 conflicts
✓ Generated 15 stories (avg quality: 8.4/10)
✓ Pushed 15 stories to JIRA: PROJ-142 to PROJ-156
📊 Report saved to report.json
```

**Acceptance Criteria:**
- All commands work end-to-end
- Help text for every command
- Supports dry-run mode (no JIRA writes)

---

### Phase 6: AI Usage Documentation (Week 9)

**Goal**: Document AI usage throughout SDLC for project submission

#### Story 6.1: Problem Framing Documentation
**Deliverable**: `docs/ai_usage/01_problem_framing.md`

**Content:**
- Prompts used to explore edge cases
- AI-suggested alternative framings
- How AI influenced scope decisions
- Iteration log showing prompt refinements

**Example:**
```markdown
## Problem Framing with AI

### Initial Prompt
"I'm building a system to synthesize customer transcripts into user stories.
What edge cases should I consider?"

### Claude Response (Summary)
- Multiple speakers with conflicting needs
- Poor quality transcripts (crosstalk, jargon)
- Requirements spanning multiple systems
- Existing backlog in inconsistent formats

### Impact on Scope
Added Story 2.4 (conflict detection) and Story 1.1 (robust parsing)

### Refinement Iterations
1. Initial broad question → too generic
2. Refined with context → better edge cases
3. Asked for failure modes → uncovered quality issues
```

---

#### Story 6.2: Design Documentation
**Deliverable**: `docs/ai_usage/02_design.md`

**Content:**
- Architecture diagram generation with AI
- Design alternatives explored
- AI critique of architecture
- Tool interface designs

**Example:**
```markdown
## Design with AI Assistance

### Architecture Review Prompt
"Review this multi-agent architecture for backlog synthesis.
What are the failure modes?"

### Claude Feedback (Summary)
- Single point of failure in orchestrator
- No retry logic for LLM calls
- Memory could grow unbounded

### Changes Made
- Added checkpointing (Story 1.5)
- Implemented retry with exponential backoff (Phase 3)
- Added memory summarization (Story 3.1)
```

---

#### Story 6.3: Implementation Documentation
**Deliverable**: `docs/ai_usage/03_implementation.md`

**Content:**
- Code sections generated by AI (with attribution)
- Prompts used for code generation
- Manual modifications to AI code
- Quality issues found and fixed

**Example:**
```python
# Generated by Claude 3.5 Sonnet (prompt: "Implement gap detection with embeddings")
# Reviewed and modified: Added caching, error handling
def detect_gaps(requirements, backlog, threshold=0.7):
    gaps = []
    for req in requirements:
        req_embedding = embed(req.description)  # MODIFIED: Added caching

        max_similarity = max([
            cosine_sim(req_embedding, embed(issue.summary))
            for issue in backlog
        ])

        if max_similarity < threshold:
            gaps.append(req)

    return gaps
```

---

#### Story 6.4: AI Usage Summary Report
**Deliverable**: `docs/AI_USAGE_REPORT.md`

**Content:**
- AI usage statistics (tokens, costs)
- Decision points where AI influenced direction
- Quality comparison (AI vs manual baseline)
- Lessons learned

**Metrics:**
```markdown
## AI Usage Statistics

### Development Phase
- Total Claude API calls: 2,847
- Total tokens: 8.2M (5.1M input, 3.1M output)
- Total cost: $62.30
- Time saved: ~40 hours (vs manual baseline)

### Code Generation
- Lines of code generated: 3,200
- Acceptance rate: 78% (unchanged)
- Modified rate: 18% (minor edits)
- Rejected rate: 4% (rewritten)

### Quality Impact
- Story generation quality: 8.4/10 (manual baseline: 7.2/10)
- Gap detection F1: 0.87 (manual: 0.65)
- Time per story: 45 seconds (manual: 15 minutes)
```

---

## Summary: Addressing All Required Steps

### ✅ 1. Problem Framing (AI-Enhanced)
- **Phase 6, Story 6.1**: Document all AI exploration prompts
- **Deliverable**: `docs/ai_usage/01_problem_framing.md`
- **AI Usage**: Claude to explore edge cases, alternative framings, failure modes

### ✅ 2. Design
- **Phase 6, Story 6.2**: Architecture diagrams and AI critique
- **Deliverable**: `docs/ai_usage/02_design.md` + Mermaid diagrams
- **AI Usage**: Claude for architecture review, design alternatives

### ✅ 3. Evaluation Plan
- **Phase 4**: Complete evaluation framework
  - **Story 4.1**: Golden dataset (5 scenarios)
  - **Story 4.2**: Metrics (completeness, F1, INVEST)
  - **Story 4.3**: LLM-as-judge
- **Deliverable**: `tests/golden_dataset/` + evaluation reports

### ✅ 4. Implementation
- **Phase 1-5**: Full system implementation
  - **Multi-agent**: LangGraph with 4 specialized agents
  - **Memory**: ChromaDB (vector) + Redis (state)
  - **Error handling**: Retry, circuit breaker, graceful degradation
  - **Tools**: JIRA, GitHub, document parsers
- **Deliverable**: Working system + code

---

## Tech Stack Summary (Final Recommendation)

| Component | Technology | Justification |
|-----------|-----------|---------------|
| **LLM** | Claude 3.5 Sonnet | Best reasoning, long context (200k), reliable structured output |
| **Orchestration** | LangGraph | Production-ready, checkpointing, human-in-loop, error handling |
| **Vector DB** | ChromaDB | Simple setup, good performance, sufficient for <100k docs |
| **State Management** | Redis + SQLite | Redis for fast access, SQLite for checkpoints |
| **API** | FastAPI | Fast, async, great for Python |
| **Frontend** | HTMX + Tailwind | Lightweight, no complex JS framework needed |
| **Confluence Alt** | Local Markdown | Start simple, easy to migrate later |

---

## Timeline & Milestones

### Week 1: MVP Foundation
- ✅ Project setup and architecture docs
- ✅ Document ingestion working
- ✅ JIRA integration connected
- ✅ Basic requirement extraction
- 🎯 **Milestone**: Parse transcript + extract requirements

### Week 2: Story Generation
- ✅ Story generation with Claude
- ✅ LangGraph workflow end-to-end
- ✅ Basic CLI working
- 🎯 **Milestone**: Generate 10 stories from 1 transcript

### Week 3-4: Intelligence Layer
- ✅ Gap detection (F1: 0.8+)
- ✅ Conflict detection (F1: 0.85+)
- ✅ Architecture validation
- 🎯 **Milestone**: Detect gaps/conflicts with 0.8 F1

### Week 5-6: Multi-Agent System
- ✅ Agent memory system
- ✅ Audit trail complete
- ✅ Specialized agents deployed
- 🎯 **Milestone**: Robust workflow with error handling

### Week 7-8: UI & Integration
- ✅ Web dashboard deployed
- ✅ JIRA bulk creation working
- ✅ CLI automation complete
- 🎯 **Milestone**: Production-ready system

### Week 9: Documentation & Demo
- ✅ AI usage docs complete
- ✅ Golden dataset evaluation
- ✅ Demo script prepared
- 🎯 **Milestone**: Project submission ready

---

## Risk Mitigation

### Risk 1: LLM Hallucinations in Story Generation
**Impact**: High | **Probability**: Medium

**Mitigation:**
- Validate stories against source material (citation check)
- Human review before JIRA creation
- LLM judge to catch obvious quality issues
- Confidence scores on all generated content

### Risk 2: API Rate Limits (JIRA, GitHub, Claude)
**Impact**: Medium | **Probability**: High

**Mitigation:**
- Implement exponential backoff and circuit breakers
- Cache frequently accessed data
- Batch API calls where possible
- Monitor usage and set alerts

### Risk 3: Complex Conflict Detection
**Impact**: Medium | **Probability**: Medium

**Mitigation:**
- Start with keyword-based detection (Story 6.4)
- Layer on LLM reasoning for complex cases
- Accept some false negatives, prioritize precision
- Human review for all flagged conflicts

### Risk 4: Large Context Windows
**Impact**: Low | **Probability**: Low

**Mitigation:**
- Chunk documents strategically (512 tokens)
- Use vector DB for relevant context retrieval
- Summarize when context exceeds model limits
- Claude 3.5 handles 200k tokens well

---

## Success Metrics

### Quantitative
1. **Completeness:** 90%+ of transcript requirements captured as stories
2. **Conflict Detection F1:** 0.85+ on golden dataset
3. **Story Quality (INVEST):** Average 8/10 from LLM judge
4. **Time Savings:** 70% reduction vs. manual backlog grooming
5. **Accuracy:** 95%+ correct epic/story organization

### Qualitative
1. **User Satisfaction:** PM/Engineers rate system 4/5+ stars
2. **Trust:** Users approve 80%+ generated stories without edits
3. **Adoption:** 3+ teams using system regularly after pilot

---

## Next Steps

### Option A: Start Phase 0 (Project Setup)
Create project structure, install dependencies, set up architecture docs

### Option B: Create Golden Dataset First
Build evaluation scenarios before implementation to guide development

### Option C: Prototype Single Agent
Build one agent (e.g., requirement extraction) end-to-end before full system

### Option D: Review & Refine Plan
Discuss specific implementation details, adjust timeline, clarify requirements

---

## Appendix: Dependencies

### Python Packages
```bash
# Core
langchain==0.1.0
langgraph==0.0.40
anthropic==0.18.0

# Vector DB & Embeddings
chromadb==0.4.22
openai==1.12.0  # for embeddings

# State Management
redis==5.0.1

# Document Processing
pdfplumber==0.10.3
python-docx==1.1.0

# API & Web
fastapi==0.109.0
uvicorn==0.27.0
pydantic==2.5.0

# JIRA Integration
jira==3.6.0
# or use MCP integration

# Testing & Evaluation
pytest==7.4.4
scikit-learn==1.4.0  # for metrics

# CLI
click==8.1.7
```

### Environment Variables
```bash
# .env.example
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...  # for embeddings

JIRA_URL=https://your-domain.atlassian.net
JIRA_API_TOKEN=...
JIRA_EMAIL=your-email@example.com

REDIS_URL=redis://localhost:6379

# Optional
GITHUB_TOKEN=ghp_...
NOTION_API_KEY=secret_...
```

---

**Document Version:** 1.0
**Last Updated:** 2025-11-26
**Author:** Claude 3.5 Sonnet
**Status:** Ready for Implementation
