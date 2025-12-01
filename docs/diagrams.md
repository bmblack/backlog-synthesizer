# Backlog Synthesizer Architecture Diagrams

This document contains Mermaid diagrams for the Backlog Synthesizer system architecture.

## System Architecture Overview

```mermaid
graph TB
    subgraph "INPUT LAYER"
        A[Meeting Transcripts]
        B[Stakeholder Interviews]
        C[Product Specs]
    end

    subgraph "ORCHESTRATION LAYER - LangGraph"
        D[Ingest Document]
        E[Fetch Confluence Context]
        F[Extract Requirements]
        G[Fetch JIRA Backlog]
        H[Detect Gaps]
        I[Generate Stories]
        J[Human Approval]
        K[Push to JIRA]
    end

    subgraph "AGENT LAYER"
        L[AnalysisAgent<br/>Extract Requirements<br/>Identify Types<br/>Priority Signals]
        M[StoryGenerationAgent<br/>Generate Stories<br/>INVEST Criteria<br/>Story Points]
        N[JIRAIntegrationAgent<br/>Fetch Backlog<br/>Create Issues<br/>Link Issues]
    end

    subgraph "MEMORY & STORAGE"
        O[(Vector Memory<br/>ChromaDB)]
        P[(Checkpointing<br/>SQLite)]
        Q[(Audit Logging<br/>SQLite)]
    end

    subgraph "EXTERNAL SERVICES"
        R[Claude Sonnet 4.5]
        S[JIRA Cloud]
        T[Confluence]
    end

    A --> D
    B --> D
    C --> D
    D --> E
    E --> F
    F --> G
    G --> H
    H --> I
    I --> J
    J -->|Approved| K
    J -->|Rejected| END1[END]
    K --> END2[END]

    F -.-> L
    I -.-> M
    G -.-> N
    K -.-> N

    L -.-> R
    M -.-> R

    F --> O
    G --> O
    H --> O
    I --> O

    D --> P
    F --> P
    I --> P
    K --> P

    D --> Q
    F --> Q
    G --> Q
    H --> Q
    I --> Q
    J --> Q
    K --> Q

    E -.-> T
    G -.-> S
    K -.-> S

    style D fill:#4A90E2,stroke:#2E5C8A,stroke-width:2px,color:#fff
    style E fill:#4A90E2,stroke:#2E5C8A,stroke-width:2px,color:#fff
    style F fill:#4A90E2,stroke:#2E5C8A,stroke-width:2px,color:#fff
    style G fill:#4A90E2,stroke:#2E5C8A,stroke-width:2px,color:#fff
    style H fill:#4A90E2,stroke:#2E5C8A,stroke-width:2px,color:#fff
    style I fill:#4A90E2,stroke:#2E5C8A,stroke-width:2px,color:#fff
    style J fill:#F5A623,stroke:#C77E1A,stroke-width:2px,color:#fff
    style K fill:#4A90E2,stroke:#2E5C8A,stroke-width:2px,color:#fff

    style L fill:#9013FE,stroke:#6B0FC2,stroke-width:2px,color:#fff
    style M fill:#9013FE,stroke:#6B0FC2,stroke-width:2px,color:#fff
    style N fill:#9013FE,stroke:#6B0FC2,stroke-width:2px,color:#fff

    style O fill:#50E3C2,stroke:#3AB39B,stroke-width:2px,color:#000
    style P fill:#50E3C2,stroke:#3AB39B,stroke-width:2px,color:#000
    style Q fill:#50E3C2,stroke:#3AB39B,stroke-width:2px,color:#000
```

## LangGraph Workflow State Machine

```mermaid
stateDiagram-v2
    [*] --> ingest_document

    ingest_document --> fetch_confluence_context: Load transcript
    note right of ingest_document
        • Load file from path
        • Read content
        • Initialize state
    end note

    fetch_confluence_context --> extract_requirements: Fetch ADRs & specs
    note right of fetch_confluence_context
        • Query Confluence (MCP)
        • Get ADRs
        • Get technical specs
    end note

    extract_requirements --> fetch_jira_backlog: Extract reqs with LLM
    note right of extract_requirements
        • Call AnalysisAgent
        • Extract requirements
        • Classify types
        • Store in vector memory
    end note

    fetch_jira_backlog --> detect_gaps: Fetch existing issues
    note right of fetch_jira_backlog
        • Query JIRA backlog
        • Get existing stories
        • Store in vector memory
    end note

    detect_gaps --> generate_stories: Semantic search
    note right of detect_gaps
        • Vector similarity search
        • 70% threshold
        • Classify novel vs covered
    end note

    generate_stories --> human_approval: Generate with LLM
    note right of generate_stories
        • Call StoryGenerationAgent
        • INVEST-compliant stories
        • Story points estimation
        • Acceptance criteria
    end note

    human_approval --> push_to_jira: Approved
    human_approval --> [*]: Rejected
    note right of human_approval
        • Review generated stories
        • Auto-approve mode available
        • Manual approval gate
    end note

    push_to_jira --> [*]: Complete
    note right of push_to_jira
        • Create JIRA issues
        • Link to epics
        • Set metadata
        • Dry-run mode available
    end note
```

## Multi-Agent Architecture

```mermaid
graph TB
    subgraph "Orchestration Layer"
        GRAPH[LangGraph State Machine]
    end

    subgraph "Agent Layer"
        subgraph "AnalysisAgent"
            AA1[Extract Requirements]
            AA2[Classify Types]
            AA3[Priority Signals]
            AA4[Impact Analysis]
        end

        subgraph "StoryGenerationAgent"
            SG1[Generate User Stories]
            SG2[INVEST Compliance]
            SG3[Story Points]
            SG4[Acceptance Criteria]
            SG5[Epic Links]
        end

        subgraph "JIRAIntegrationAgent"
            JI1[Fetch Backlog]
            JI2[Create Issues]
            JI3[Update Issues]
            JI4[Link Issues]
        end
    end

    subgraph "LLM Layer"
        CLAUDE[Claude Sonnet 4.5<br/>200K Context Window]
    end

    subgraph "Memory Layer"
        VM[(Vector Memory<br/>ChromaDB<br/>Semantic Search)]
        CP[(Checkpoints<br/>SQLite<br/>Resumability)]
        AL[(Audit Log<br/>SQLite<br/>Provenance)]
    end

    subgraph "External APIs"
        JIRA[JIRA Cloud API]
        CONF[Confluence API<br/>via MCP]
    end

    GRAPH -->|extract_requirements| AA1
    GRAPH -->|generate_stories| SG1
    GRAPH -->|fetch_jira_backlog| JI1
    GRAPH -->|push_to_jira| JI2

    AA1 --> AA2
    AA2 --> AA3
    AA3 --> AA4

    SG1 --> SG2
    SG2 --> SG3
    SG3 --> SG4
    SG4 --> SG5

    JI1 --> JI3
    JI3 --> JI4

    AA1 -.->|API Call| CLAUDE
    SG1 -.->|API Call| CLAUDE

    AA4 --> VM
    SG5 --> VM
    JI1 --> VM

    GRAPH --> CP
    GRAPH --> AL

    JI1 -.->|JQL Query| JIRA
    JI2 -.->|Create Issue| JIRA
    JI3 -.->|Update Issue| JIRA
    JI4 -.->|Link Issue| JIRA

    GRAPH -.->|MCP Query| CONF

    style AA1 fill:#4A90E2,stroke:#2E5C8A,stroke-width:2px,color:#fff
    style AA2 fill:#4A90E2,stroke:#2E5C8A,stroke-width:2px,color:#fff
    style AA3 fill:#4A90E2,stroke:#2E5C8A,stroke-width:2px,color:#fff
    style AA4 fill:#4A90E2,stroke:#2E5C8A,stroke-width:2px,color:#fff

    style SG1 fill:#9013FE,stroke:#6B0FC2,stroke-width:2px,color:#fff
    style SG2 fill:#9013FE,stroke:#6B0FC2,stroke-width:2px,color:#fff
    style SG3 fill:#9013FE,stroke:#6B0FC2,stroke-width:2px,color:#fff
    style SG4 fill:#9013FE,stroke:#6B0FC2,stroke-width:2px,color:#fff
    style SG5 fill:#9013FE,stroke:#6B0FC2,stroke-width:2px,color:#fff

    style JI1 fill:#F5A623,stroke:#C77E1A,stroke-width:2px,color:#fff
    style JI2 fill:#F5A623,stroke:#C77E1A,stroke-width:2px,color:#fff
    style JI3 fill:#F5A623,stroke:#C77E1A,stroke-width:2px,color:#fff
    style JI4 fill:#F5A623,stroke:#C77E1A,stroke-width:2px,color:#fff

    style CLAUDE fill:#E74C3C,stroke:#C0392B,stroke-width:2px,color:#fff
    style VM fill:#50E3C2,stroke:#3AB39B,stroke-width:2px,color:#000
    style CP fill:#50E3C2,stroke:#3AB39B,stroke-width:2px,color:#000
    style AL fill:#50E3C2,stroke:#3AB39B,stroke-width:2px,color:#000
```

## Data Flow Diagram

```mermaid
flowchart LR
    subgraph "Input"
        T[Meeting Transcript]
    end

    subgraph "Context Enrichment"
        C[Confluence ADRs]
        A[Architecture Specs]
    end

    subgraph "Requirements Extraction"
        RE[Requirements<br/>21 items<br/>Types + Priorities]
    end

    subgraph "JIRA Backlog"
        JB[Existing Issues<br/>JQL Query]
    end

    subgraph "Vector Memory"
        VM1[Req Embeddings]
        VM2[Story Embeddings]
        VM3[Similarity Search<br/>70% threshold]
    end

    subgraph "Gap Detection"
        GD[Novel: 22<br/>Covered: 0]
    end

    subgraph "Story Generation"
        SG[User Stories<br/>13 items<br/>INVEST-compliant]
    end

    subgraph "Approval"
        AP[Human Review<br/>Auto-approve mode]
    end

    subgraph "Output"
        JO[JIRA Issues<br/>Created with metadata]
    end

    T --> RE
    C --> RE
    A --> RE

    RE --> VM1
    JB --> VM2

    VM1 --> VM3
    VM2 --> VM3

    VM3 --> GD

    GD --> SG
    SG --> AP
    AP -->|Approved| JO

    style T fill:#4A90E2,stroke:#2E5C8A,stroke-width:2px,color:#fff
    style RE fill:#9013FE,stroke:#6B0FC2,stroke-width:2px,color:#fff
    style GD fill:#F5A623,stroke:#C77E1A,stroke-width:2px,color:#fff
    style SG fill:#50E3C2,stroke:#3AB39B,stroke-width:2px,color:#000
    style AP fill:#E74C3C,stroke:#C0392B,stroke-width:2px,color:#fff
    style JO fill:#4A90E2,stroke:#2E5C8A,stroke-width:2px,color:#fff
```

## Vector Memory Architecture

```mermaid
graph TB
    subgraph "Input Data"
        R[Requirements]
        S[Stories]
        J[JIRA Issues]
    end

    subgraph "ChromaDB Vector Database"
        subgraph "Collections"
            C1[requirements_collection]
            C2[stories_collection]
            C3[jira_backlog_collection]
        end

        subgraph "Embeddings"
            E1[Requirement Vectors<br/>768 dimensions]
            E2[Story Vectors<br/>768 dimensions]
            E3[JIRA Vectors<br/>768 dimensions]
        end
    end

    subgraph "Semantic Search"
        SS[Cosine Similarity<br/>Threshold: 0.70]
    end

    subgraph "Gap Detection Results"
        N[Novel Requirements<br/>Similarity < 70%]
        CO[Covered Requirements<br/>Similarity >= 70%]
    end

    R --> C1
    S --> C2
    J --> C3

    C1 --> E1
    C2 --> E2
    C3 --> E3

    E1 --> SS
    E3 --> SS

    SS --> N
    SS --> CO

    style C1 fill:#4A90E2,stroke:#2E5C8A,stroke-width:2px,color:#fff
    style C2 fill:#9013FE,stroke:#6B0FC2,stroke-width:2px,color:#fff
    style C3 fill:#F5A623,stroke:#C77E1A,stroke-width:2px,color:#fff

    style E1 fill:#50E3C2,stroke:#3AB39B,stroke-width:2px,color:#000
    style E2 fill:#50E3C2,stroke:#3AB39B,stroke-width:2px,color:#000
    style E3 fill:#50E3C2,stroke:#3AB39B,stroke-width:2px,color:#000

    style N fill:#E74C3C,stroke:#C0392B,stroke-width:2px,color:#fff
    style CO fill:#27AE60,stroke:#1E8449,stroke-width:2px,color:#fff
```

## Audit & Provenance System

```mermaid
erDiagram
    WORKFLOW_EXECUTIONS ||--o{ NODE_EXECUTIONS : contains
    NODE_EXECUTIONS ||--o{ INPUTS : has
    NODE_EXECUTIONS ||--o{ OUTPUTS : has
    WORKFLOW_EXECUTIONS ||--o{ DECISIONS : makes
    WORKFLOW_EXECUTIONS ||--o{ ERRORS : may_have
    WORKFLOW_EXECUTIONS ||--o{ METRICS : tracks

    WORKFLOW_EXECUTIONS {
        string execution_id PK
        string thread_id
        timestamp start_time
        timestamp end_time
        string status
        json context
    }

    NODE_EXECUTIONS {
        string execution_id FK
        string node_name
        timestamp start_time
        timestamp end_time
        string status
        int attempt_number
    }

    INPUTS {
        string execution_id FK
        string node_name
        json input_data
        timestamp recorded_at
    }

    OUTPUTS {
        string execution_id FK
        string node_name
        json output_data
        timestamp recorded_at
    }

    DECISIONS {
        string execution_id FK
        string decision_point
        string decision
        string reasoning
        timestamp made_at
    }

    ERRORS {
        string execution_id FK
        string node_name
        string error_type
        string error_message
        json stack_trace
        timestamp occurred_at
    }

    METRICS {
        string execution_id FK
        string metric_name
        float metric_value
        string unit
        timestamp recorded_at
    }
```

---

## How to View These Diagrams

### In GitHub
These Mermaid diagrams will render automatically when viewing this file on GitHub.

### In VS Code
Install the "Markdown Preview Mermaid Support" extension:
```bash
code --install-extension bierner.markdown-mermaid
```

### Export to PNG/SVG
Use the Mermaid CLI:
```bash
npm install -g @mermaid-js/mermaid-cli
mmdc -i docs/diagrams.md -o docs/diagrams.png
```

### Online Viewer
Paste the Mermaid code into: https://mermaid.live/

---

## Diagram Maintenance

When updating these diagrams:
1. Keep them synchronized with ARCHITECTURE.md
2. Update node counts if workflow changes
3. Reflect actual implementation details
4. Test rendering before committing
