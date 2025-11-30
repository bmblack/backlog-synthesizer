"""
Prompt templates for generating user stories from requirements.

This module contains prompts for the StoryGenerationAgent to convert extracted
requirements into well-structured JIRA user stories following INVEST principles.
"""

STORY_GENERATION_SYSTEM_PROMPT = """You are an expert product manager and agile coach specializing in writing high-quality user stories.

Your task is to convert customer requirements into well-structured JIRA user stories that follow INVEST criteria:
- **I**ndependent: Story can be developed and delivered independently
- **N**egotiable: Details can be discussed and refined
- **V**aluable: Provides clear value to users/business
- **E**stimable: Team can estimate effort required
- **S**mall: Can be completed within a sprint (1-2 weeks)
- **T**estable: Has clear acceptance criteria

## Story Format

Each user story should include:

1. **Title**: Brief, action-oriented summary (5-10 words)
   - Format: "[Feature Area] Action/Goal"
   - Example: "Dark Mode: Add theme toggle with system preference detection"

2. **User Story**: Classic format
   - "As a [persona], I want to [action], so that [benefit]"
   - Be specific about the persona (e.g., "night shift developer", "mobile executive")

3. **Description**: Detailed explanation
   - Context and background
   - Current pain points
   - Proposed solution
   - Technical considerations
   - References to source requirements

4. **Acceptance Criteria**: 3-5 testable conditions
   - Must be specific and measurable
   - Use "Given/When/Then" format when appropriate
   - Cover happy path and edge cases
   - Example: "Given a user with macOS dark mode enabled, When they open the app, Then the interface automatically applies dark theme"

5. **Story Points**: Fibonacci scale (1, 2, 3, 5, 8, 13)
   - 1-2: Simple UI changes, config updates
   - 3-5: New features with moderate complexity
   - 8: Complex features requiring multiple components
   - 13: Epic-sized (should be split)

6. **Priority**: Based on customer signals
   - P1 (Critical/Blocker): Blocking users, urgent business need
   - P2 (High): Important for user experience, multiple customers want it
   - P3 (Medium): Nice to have, single customer request
   - P4 (Low): Future enhancement

7. **Labels**: Categorize for filtering
   - Feature area: frontend, backend, api, mobile, etc.
   - Type: enhancement, bug-fix, new-feature, tech-debt
   - Customer: customer-requested, internal
   - Other: performance, security, accessibility

8. **Epic Link**: Group related stories
   - Identify logical groupings
   - Example: "Dark Mode Implementation", "Export Performance", "Search Improvements"

## Guidelines

### Story Sizing
- **Split large stories**: If story points > 8, break into smaller stories
- **Identify dependencies**: Note if story requires other stories first
- **Consider spikes**: Complex/uncertain work may need research spike first

### Acceptance Criteria Best Practices
- **Be specific**: "Export completes in < 10 seconds for 2,000 issues" not "Export is fast"
- **Cover edge cases**: What happens with 0 issues? 10,000 issues? No network?
- **Include non-functional**: Performance, security, accessibility requirements
- **Make testable**: QA should be able to verify each criterion

### Technical Considerations
- **Architecture constraints**: Reference ADRs when relevant
- **Integration points**: Note APIs, databases, external services affected
- **Performance requirements**: Specific targets from customer feedback
- **Security implications**: Authentication, authorization, data privacy

### Priority Mapping
- **Urgent/Blocker** from customer → P1
- **High/Must-have** from customer → P2
- **Medium** from customer → P3
- **Low/Nice-to-have** from customer → P4

## Output Format

Return a JSON array of user story objects:

```json
[
  {
    "title": "Story title",
    "user_story": "As a [persona], I want to [action], so that [benefit]",
    "description": "Detailed description with context, pain points, solution, and technical notes",
    "acceptance_criteria": [
      "Given/When/Then format or specific measurable condition",
      "Another acceptance criterion",
      "Edge case or non-functional requirement"
    ],
    "story_points": 5,
    "priority": "P2",
    "labels": ["frontend", "enhancement", "customer-requested", "accessibility"],
    "epic_link": "Epic name or null",
    "source_requirements": ["Requirement text 1", "Requirement text 2"],
    "technical_notes": "Architecture decisions, dependencies, risks, or other technical context"
  }
]
```

## Important Rules

1. **One story per requirement** unless requirements are tightly coupled
2. **Split stories > 8 points** into multiple smaller stories
3. **Preserve customer language** in descriptions and acceptance criteria
4. **Be specific with metrics** when customers provided numbers
5. **Reference source requirements** to maintain traceability
6. **Consider technical constraints** from ADRs and architecture
7. **Make stories actionable** - clear what to build, not just what's wrong
"""

FEW_SHOT_EXAMPLES = [
    {
        "input_requirement": {
            "requirement": "Add dark mode theme with manual toggle and automatic system-level theme preference detection (macOS, Windows)",
            "type": "feature_request",
            "priority_signal": "medium-high",
            "impact": "Affecting productivity - 15-30 min/developer/day lost to eye strain and context switching for night shift engineers. App feels broken when it's the only bright interface on screen.",
            "stakeholder": "Alex Martinez (TechCorp), Maya Patel (DesignHub)",
        },
        "generated_story": {
            "title": "Dark Mode: Add theme toggle with system preference detection",
            "user_story": "As a night shift developer, I want the app to support dark mode with automatic system preference detection, so that I can reduce eye strain during late-hour work sessions",
            "description": """**Context**: Multiple enterprise customers report eye strain and productivity loss for engineers working late hours. The bright white interface is harsh on eyes and feels "broken" when it's the only bright app on screen.

**Current Pain**:
- Night shift developers losing 15-30 min/day to eye strain and context switching
- App doesn't respect macOS/Windows system theme preferences
- Only bright app on screen when user has dark mode enabled system-wide

**Proposed Solution**:
Implement dark mode theme with two capabilities:
1. Manual toggle: Users can explicitly switch between light/dark themes
2. System preference detection: Default to user's OS-level theme setting (macOS, Windows)

**Customers Affected**: TechCorp (night shift developers), DesignHub (designers using macOS dark mode)""",
            "acceptance_criteria": [
                "Given a user with macOS dark mode enabled, When they open the app for the first time, Then the interface automatically applies dark theme",
                "Given a user viewing the app, When they click the theme toggle, Then the interface switches between light and dark themes within 200ms",
                "Given a user has selected a theme preference, When they refresh or reopen the app, Then their chosen theme persists",
                "All UI components (buttons, inputs, cards, modals) render correctly in both light and dark themes",
                "Color contrast meets WCAG AA standards (4.5:1 for text) in both themes"
            ],
            "story_points": 5,
            "priority": "P2",
            "labels": ["frontend", "enhancement", "customer-requested", "accessibility", "ux"],
            "epic_link": "Dark Mode Implementation",
            "source_requirements": [
                "Add dark mode theme with manual toggle and automatic system-level theme preference detection (TechCorp, DesignHub)"
            ],
            "technical_notes": "Requires CSS variable system for theme switching. Consider using prefers-color-scheme media query for system detection. Store preference in localStorage. May need to update component library if not theme-aware.",
        },
    },
    {
        "input_requirement": {
            "requirement": "Optimize export performance to handle 2,000+ issues in under 10 seconds for CSV and Excel formats without timeouts",
            "type": "bug_report",
            "priority_signal": "urgent",
            "impact": "Blocking monthly reporting workflow - executives can't get data for board meetings. Users resorting to manual data copying. Currently takes 3-4 minutes with timeouts for 2,000 issues.",
            "stakeholder": "James Lee (DataCore), Alex Martinez (TechCorp)",
        },
        "generated_story": {
            "title": "Export: Fix timeout and optimize for 2,000+ issues",
            "user_story": "As a product manager preparing monthly reports, I want to export 2,000+ issues to CSV/Excel in under 10 seconds without timeouts, so that I can generate executive reports reliably and on time",
            "description": """**Context**: Critical blocker for monthly reporting workflows. Multiple customers experiencing 3-4 minute export times with frequent timeouts for large backlogs.

**Current Pain**:
- DataCore: 2,000 issues take 3-4 minutes, frequent timeouts
- TechCorp: 500 issues take 90 seconds
- Executives cannot get data for board meetings
- Users manually copying data as workaround

**Business Impact**:
- Blocking monthly board meeting preparations
- Lost productivity from manual workarounds
- Poor product perception vs competitors

**Proposed Solution**:
Optimize export backend to achieve:
- Target: < 10 seconds for 2,000 issues
- Support both CSV and Excel formats
- No timeouts for datasets up to 5,000 issues
- Streaming response for large datasets

**Performance Requirement**: < 10 seconds for 2,000 issues (both formats)""",
            "acceptance_criteria": [
                "Given a backlog with 2,000 issues, When user exports to CSV, Then export completes in < 10 seconds",
                "Given a backlog with 2,000 issues, When user exports to Excel, Then export completes in < 10 seconds",
                "Given a backlog with 5,000 issues, When user exports, Then export completes without timeout (< 30 seconds)",
                "Given an export in progress, When it takes > 5 seconds, Then user sees a progress indicator",
                "Exported data includes all issue fields: ID, title, status, assignee, priority, labels, created date, updated date"
            ],
            "story_points": 8,
            "priority": "P1",
            "labels": ["backend", "bug-fix", "performance", "customer-requested", "urgent"],
            "epic_link": "Export Performance Optimization",
            "source_requirements": [
                "Optimize export performance to handle 2,000+ issues in under 10 seconds (DataCore, TechCorp)"
            ],
            "technical_notes": "Investigate: 1) Database query optimization (N+1 queries?), 2) Streaming response to avoid memory issues, 3) Background job with download link for very large exports, 4) Consider caching frequently exported views. May need database indexes on commonly exported fields. ADR-005: Consider async event for exports > 5,000 issues.",
        },
    },
]


def format_story_generation_prompt(requirements: list, context: dict = None) -> str:
    """
    Format the story generation prompt with requirements.

    Args:
        requirements: List of Requirement objects or dicts
        context: Optional context dict with project info, ADRs, etc.

    Returns:
        Complete prompt ready for Claude API
    """
    context = context or {}

    # Format requirements for prompt
    requirements_text = "\n\n".join(
        [
            f"**Requirement {i+1}:**\n"
            f"- Description: {req.get('requirement') if isinstance(req, dict) else req.requirement}\n"
            f"- Type: {req.get('type') if isinstance(req, dict) else req.type}\n"
            f"- Priority Signal: {req.get('priority_signal') if isinstance(req, dict) else req.priority_signal}\n"
            f"- Impact: {req.get('impact') if isinstance(req, dict) else req.impact}\n"
            f"- Stakeholder: {req.get('stakeholder') if isinstance(req, dict) else req.stakeholder}\n"
            f"- Context: {req.get('context') if isinstance(req, dict) else req.context}"
            for i, req in enumerate(requirements)
        ]
    )

    # Format examples
    examples_text = "\n\n".join(
        [
            f"**Example {i+1}:**\n\n"
            f"**Input Requirement:**\n```json\n{format_json(ex['input_requirement'])}\n```\n\n"
            f"**Generated Story:**\n```json\n{format_json(ex['generated_story'])}\n```"
            for i, ex in enumerate(FEW_SHOT_EXAMPLES)
        ]
    )

    # Add context if provided
    context_text = ""
    if context:
        if "adrs" in context:
            context_text += f"\n\n**Architecture Constraints (ADRs)**:\n{context['adrs']}"
        if "project_info" in context:
            context_text += f"\n\n**Project Context**:\n{context['project_info']}"

    return f"""{STORY_GENERATION_SYSTEM_PROMPT}

---

## Few-Shot Examples

{examples_text}

---

## Your Task

Convert the following customer requirements into well-structured JIRA user stories.

{context_text}

**Requirements to Convert:**

{requirements_text}

**Instructions:**
1. Create one story per requirement (unless tightly coupled)
2. Follow INVEST principles
3. Include 3-5 specific acceptance criteria per story
4. Size stories appropriately (split if > 8 points)
5. Map customer priority to JIRA priority (P1-P4)
6. Add relevant labels
7. Group into logical epics
8. Reference source requirements for traceability

Return ONLY the JSON array, no additional commentary.

IMPORTANT: Ensure all quotes within string values are properly escaped with backslashes (\\").
For example: "status updates (e.g., \\"In Review\\" -> \\"Done\\")"
"""


def format_json(obj):
    """Pretty-print JSON for prompt examples."""
    import json

    return json.dumps(obj, indent=2)
