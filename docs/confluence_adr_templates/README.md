# Confluence Architecture Decision Records (ADRs)

This directory contains sample ADR templates for your Confluence ARCH space. These documents define the architecture constraints that the Backlog Synthesizer will validate against when generating user stories.

## 📁 Available ADRs

### ADR-001: Monolith-First Strategy
**Purpose**: Defines the architectural approach (monolith vs microservices)

**Key Constraints**:
- All features MUST be developed within monolithic codebase
- NO microservices or separate deployable units
- Maintain clear module boundaries for future extraction

**Use Case**: System will reject stories proposing new microservices

---

### ADR-002: Technology Stack Decisions
**Purpose**: Standardizes programming languages, frameworks, and infrastructure

**Key Constraints**:
- Backend: Python 3.11+ with FastAPI (NO Flask, Django, Java, .NET)
- Database: PostgreSQL (NO MySQL, MongoDB as primary)
- Frontend: React 18+ with TypeScript (NO Vue, Angular)
- All services MUST be containerized with Docker

**Use Case**: System will reject stories using prohibited technologies

---

### ADR-003: API Standards and Versioning
**Purpose**: Defines RESTful API design patterns and versioning strategy

**Key Constraints**:
- REST only (NO GraphQL, gRPC without approval)
- Version in URL path: `/v1/resource` (NOT in headers)
- Plural nouns for resources: `/users` not `/user`
- OAuth 2.0 + JWT for authentication
- Standard error response format

**Use Case**: System will flag stories with non-standard API designs

---

### ADR-004: Security Requirements
**Purpose**: Establishes baseline security standards (OWASP, encryption, auth)

**Key Constraints**:
- HTTPS/TLS 1.3 for all external communication (NO HTTP in production)
- bcrypt/Argon2 for password hashing (NO MD5, SHA1, plain text)
- Parameterized queries only (NO SQL string concatenation)
- NO secrets in version control
- MFA required for admin accounts

**Use Case**: System will reject stories with security violations

---

### ADR-005: Event-Driven Architecture for Async Tasks
**Purpose**: Defines when to use event-driven patterns for async operations

**Key Constraints**:
- Long-running operations (>3s) MUST use events (Redis Streams)
- NO blocking API responses for email/notifications
- Retry policy: Max 3 attempts with exponential backoff
- Failed events MUST go to Dead Letter Queue

**Use Case**: System will flag stories performing sync operations that should be async

---

## 🚀 How to Use These Templates

### Step 1: Copy to Confluence

For each ADR file:

1. Open your Confluence space: `https://brandonblack.atlassian.net/wiki/spaces/ARCH`
2. Create a new page
3. Copy the content from the markdown file
4. Format as needed (Confluence will preserve most markdown)
5. Publish

### Step 2: Organize in Confluence

**Recommended Structure**:
```
ARCH Space (Confluence)
├── 📄 Home (overview)
├── 📁 Architecture Decisions/
│   ├── ADR-001: Monolith-First Strategy
│   ├── ADR-002: Technology Stack Decisions
│   ├── ADR-003: API Standards and Versioning
│   ├── ADR-004: Security Requirements
│   └── ADR-005: Event-Driven Architecture
├── 📁 Technical Constraints/
│   ├── Approved Technologies
│   ├── Security Policies
│   └── Performance Requirements
└── 📁 System Design/
    ├── Component Architecture
    ├── Data Flow Diagrams
    └── Integration Points
```

### Step 3: Test MCP Integration

Once uploaded, test that the Backlog Synthesizer can read them:

```python
from mcp_client import MCPClient

confluence = MCPClient("atlassian")

# Fetch all pages from ARCH space
pages = confluence.get_space_pages(space_key="ARCH")
print(f"Found {len(pages)} pages")

# Read ADR-001 content
content = confluence.get_page_content(
    space_key="ARCH",
    title="ADR-001: Monolith-First Strategy"
)
print(content[:500])  # First 500 chars
```

---

## 🎯 How the System Uses ADRs

### During Story Generation

When analyzing customer requirements, the system will:

1. **Fetch ADRs from Confluence** via MCP
2. **Extract constraints** from each ADR (MUST/MUST NOT/SHOULD sections)
3. **Validate generated stories** against constraints
4. **Flag violations** for review

### Example Validation Flow

**Customer Request**: "We need a new authentication service as a microservice"

**System Analysis**:
1. Generates story: "Create OAuth microservice"
2. Reads ADR-001 (Monolith-First Strategy)
3. Detects violation: "MUST NOT create new microservices"
4. **Flags story for review** with explanation:
   ```
   ⚠️  CONSTRAINT VIOLATION
   Story: "Create OAuth microservice"
   Violated: ADR-001 - Monolith-First Strategy
   Constraint: "All features MUST be developed within monolithic codebase"
   Recommendation: "Implement OAuth as module within monolith"
   ```

---

## 📝 Creating Your Own ADRs

### ADR Template

```markdown
# ADR-XXX: Decision Title

**Status**: Accepted | Proposed | Deprecated
**Date**: YYYY-MM-DD
**Decision Makers**: Team names
**Tags**: category, keywords

---

## Context
What problem are we solving? What's the situation?

## Decision
What did we decide? Clear statement.

## Constraints

### MUST Follow:
- Hard requirements
- Non-negotiable rules

### MUST NOT:
- Prohibited practices
- What to avoid

### SHOULD Consider:
- Recommended practices
- Best practices

## Rationale
Why did we make this decision?
- Reason 1
- Reason 2

## Compliance
How will stories be validated against this?
- Rejection criteria
- Review criteria

## Consequences
What are the trade-offs?
- Positive impacts
- Negative impacts

## Review Date
When will we revisit this decision?

---
**Last Updated**: YYYY-MM-DD
**Version**: 1.0
**Owner**: Team name
```

### Best Practices

1. **Be Specific**: "Use Python 3.11+" not "Use modern Python"
2. **Be Actionable**: Clear MUST/MUST NOT statements
3. **Include Examples**: Show good vs bad patterns
4. **Version ADRs**: Track changes over time
5. **Review Regularly**: Set review dates (6-12 months)
6. **Link to Context**: Reference research, benchmarks, incidents

---

## 🔗 Integration with Backlog Synthesizer

The system expects ADRs in this format:

**Required Sections**:
- `## Context` - Problem statement
- `## Decision` - What was decided
- `## Constraints` - MUST/MUST NOT/SHOULD rules
- `## Compliance` - How to validate stories

**Optional Sections**:
- Rationale
- Consequences
- Examples
- References

**Metadata**:
- Status: Accepted | Proposed | Deprecated
- Date: Last updated
- Tags: For categorization

---

## 🚦 ADR Status Workflow

**Proposed** → New ADR under discussion
**Accepted** → In effect, enforced by system
**Deprecated** → Superseded by newer ADR
**Rejected** → Decided against (keep for context)

---

## 📚 Resources

- **ADR Template**: This README
- **Martin Fowler's ADR Guide**: https://adr.github.io/
- **Confluence Markdown**: https://confluence.atlassian.com/doc/confluence-markdown-223222389.html
- **Internal**: Backlog Synthesizer Documentation (docs/)

---

## 🆘 Quick Setup Commands

```bash
# Navigate to templates directory
cd /Users/bmblack/dev/backlog-synthesizer/docs/confluence_adr_templates

# List all ADR templates
ls -lh *.md

# View a specific ADR
cat ADR-001-Monolith-First-Strategy.md

# Copy content to clipboard (macOS)
cat ADR-001-Monolith-First-Strategy.md | pbcopy
```

---

## ✅ Checklist: Setting Up Confluence ADRs

- [ ] Create Confluence space "ARCH" (if not exists)
- [ ] Create folder structure (Architecture Decisions, Technical Constraints, System Design)
- [ ] Upload ADR-001: Monolith-First Strategy
- [ ] Upload ADR-002: Technology Stack Decisions
- [ ] Upload ADR-003: API Standards and Versioning
- [ ] Upload ADR-004: Security Requirements
- [ ] Upload ADR-005: Event-Driven Architecture
- [ ] Test MCP integration (read pages via API)
- [ ] Update Backlog Synthesizer .env (CONFLUENCE_SPACE_KEY=ARCH)
- [ ] Run test workflow to validate constraint detection

---

**Created**: 2025-11-26
**Version**: 1.0
**Owner**: Backlog Synthesizer Project
