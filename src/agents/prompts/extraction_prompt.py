"""
Prompt templates for requirement extraction from customer transcripts.

This module contains the system prompt and few-shot examples for the AnalysisAgent
to extract structured requirements from meeting transcripts, customer feedback, and
product discussions.
"""

EXTRACTION_SYSTEM_PROMPT = """You are an expert product analyst specializing in extracting actionable requirements from customer conversations.

Your task is to analyze meeting transcripts and extract structured requirements with the following information:
- **requirement**: Clear, concise description of what is needed (1-2 sentences)
- **type**: Category of requirement (feature_request, bug_report, enhancement, question, pain_point)
- **priority_signal**: Urgency/importance indicators from the conversation (urgent, blocker, critical, high, medium, low, nice-to-have)
- **impact**: Business impact mentioned (e.g., "blocking monthly reports", "affecting 50+ users")
- **source_citation**: Direct quote from transcript
- **paragraph_number**: Line/paragraph number where requirement appears
- **stakeholder**: Person who mentioned the requirement
- **context**: Additional relevant context or constraints

**Extraction Guidelines:**

1. **Be Specific**: Extract concrete, actionable requirements, not vague wishes
   - ✅ Good: "Export 2,000 issues to CSV in under 10 seconds"
   - ❌ Bad: "Make exports faster"

2. **Capture Priority Signals**: Look for urgency indicators
   - Words: urgent, blocker, critical, must-have, dealbreaker, ASAP
   - Context: "blocking our workflow", "team is frustrated", "executives need this"
   - Timeframes: "need by next month", "before Q4"

3. **Include Quantifiable Metrics**: Extract specific numbers when mentioned
   - User counts, time durations, data volumes, percentages
   - Example: "2,000 issues", "3-4 minute timeout", "90 seconds", "50 stories"

4. **Distinguish Requirement Types**:
   - **feature_request**: New functionality that doesn't exist
   - **bug_report**: Something broken or not working as expected
   - **enhancement**: Improvement to existing functionality
   - **pain_point**: Current friction without specific solution proposed
   - **question**: Clarification or information request

5. **Preserve Context**: Include relevant business context
   - Why it matters: "executives review on mobile during commute"
   - Who's affected: "our night shift developers", "external contractors"
   - Current workaround: "manually copying data", "rebuilding searches daily"

6. **Consolidate Related Mentions**: If multiple people mention the same requirement, combine them
   - Note all stakeholders who mentioned it
   - Include strongest priority signal
   - Cite multiple sources if relevant

**Output Format:**

Return a JSON array of requirement objects:

```json
[
  {
    "requirement": "Clear description of the requirement",
    "type": "feature_request|bug_report|enhancement|pain_point|question",
    "priority_signal": "urgent|blocker|critical|high|medium|low|nice-to-have",
    "impact": "Business impact or pain caused",
    "source_citation": "Direct quote from transcript",
    "paragraph_number": 42,
    "stakeholder": "Name (Company)",
    "context": "Additional relevant details"
  }
]
```

**Important**: Only extract genuine requirements. Skip pleasantries, meeting logistics, and off-topic discussions.
"""

FEW_SHOT_EXAMPLES = [
    {
        "transcript": """
[00:45] Alex Martinez (TechCorp): Thanks Sarah. First off, we love the product, but there's one thing that's driving our team crazy - the lack of dark mode. Our engineers work late hours and the bright white interface is really harsh on the eyes. We've had multiple developers mention this. It's not a dealbreaker, but it would significantly improve their experience.

[02:15] Sarah Chen: That's great feedback Alex. Dark mode has come up before. How critical would you rate this?

[02:30] Alex Martinez: I'd say medium-high priority. It's affecting productivity for our night shift team. We estimate it's costing us about 15-30 minutes per developer per day in eye strain and context switching to darker apps.
""",
        "extracted_requirements": [
            {
                "requirement": "Add dark mode theme to reduce eye strain for developers working late hours",
                "type": "feature_request",
                "priority_signal": "medium-high",
                "impact": "Affecting productivity - 15-30 min/developer/day lost to eye strain and context switching",
                "source_citation": "the lack of dark mode. Our engineers work late hours and the bright white interface is really harsh on the eyes... It's affecting productivity for our night shift team.",
                "paragraph_number": 10,
                "stakeholder": "Alex Martinez (TechCorp)",
                "context": "Multiple developers have mentioned this issue. Not a dealbreaker but significant UX improvement for night shift team."
            }
        ]
    },
    {
        "transcript": """
[05:00] James Lee (DataCore): While we're on UI topics, I have to mention the export functionality. It's painfully slow. When we try to export our backlog - and we have about 2,000 issues - it takes 3-4 minutes and sometimes times out completely. This is a blocker for our monthly reporting process.

[06:15] Sarah Chen: Ouch, that's definitely a problem. What format are you exporting to?

[06:30] James Lee: CSV mostly, sometimes Excel. The timeout happens with both. We need this data for executive reports and right now we're manually copying data because export is unreliable. It's urgent - we have a board meeting next month and need reliable exports.

[07:45] Alex Martinez: We have the same export issue! We only have 500 stories but it still takes 90 seconds. That's way too long.

[09:00] James Lee: For 2,000 issues? I'd expect under 10 seconds. Most tools do it instantly.
""",
        "extracted_requirements": [
            {
                "requirement": "Optimize export performance to handle 2,000+ issues in under 10 seconds for CSV and Excel formats without timeouts",
                "type": "bug_report",
                "priority_signal": "urgent",
                "impact": "Blocking monthly reporting workflow - executives can't get data for board meetings. Users resorting to manual data copying.",
                "source_citation": "It's painfully slow... takes 3-4 minutes and sometimes times out completely. This is a blocker for our monthly reporting process... It's urgent - we have a board meeting next month",
                "paragraph_number": 22,
                "stakeholder": "James Lee (DataCore), Alex Martinez (TechCorp)",
                "context": "Problem confirmed by multiple customers. DataCore has 2,000 issues (3-4 min with timeouts), TechCorp has 500 issues (90 sec). Export currently unreliable for both CSV and Excel. Acceptable performance: <10 seconds for 2,000 issues."
            }
        ]
    },
    {
        "transcript": """
[09:30] Maya Patel: I want to bring up search. The search functionality is really basic. We can't filter by multiple criteria at once. For example, I want to find all high-priority bugs assigned to the frontend team created in the last sprint. Right now I have to do three separate searches and manually cross-reference. It's tedious.

[11:00] Sarah Chen: Can you give me a specific example of a search you do frequently?

[11:20] Maya Patel: Sure. "Show me all stories tagged 'frontend' AND 'authentication' with status 'In Progress' created after October 1st." I need AND logic, not just individual filters.

[12:30] Alex Martinez: Yes! Advanced search would be huge. We also need saved search filters. I do the same searches every day - having to rebuild them is wasteful.
""",
        "extracted_requirements": [
            {
                "requirement": "Implement advanced search with multi-criteria filtering using AND logic (tags, status, assignee, date ranges)",
                "type": "feature_request",
                "priority_signal": "high",
                "impact": "Users performing 3+ separate searches and manually cross-referencing results. Daily time waste rebuilding same searches.",
                "source_citation": "We can't filter by multiple criteria at once... I have to do three separate searches and manually cross-reference. It's tedious... I need AND logic",
                "paragraph_number": 34,
                "stakeholder": "Maya Patel (DesignHub)",
                "context": "Example query: 'frontend' AND 'authentication' AND status='In Progress' AND created after Oct 1st. Current workaround is manual cross-referencing."
            },
            {
                "requirement": "Add saved search filters feature to preserve frequently-used search queries",
                "type": "feature_request",
                "priority_signal": "medium",
                "impact": "Users rebuild same searches daily - wasteful and frustrating",
                "source_citation": "We also need saved search filters. I do the same searches every day - having to rebuild them is wasteful",
                "paragraph_number": 40,
                "stakeholder": "Alex Martinez (TechCorp)",
                "context": "Related to advanced search feature. Users have recurring search patterns that should be saveable."
            }
        ]
    }
]

def format_extraction_prompt(transcript: str) -> str:
    """
    Format the extraction prompt with the transcript content.

    Args:
        transcript: Meeting transcript or customer feedback text

    Returns:
        Complete prompt ready for Claude API
    """
    examples_text = "\n\n".join([
        f"**Example {i+1}:**\n\n**Input Transcript:**\n{ex['transcript']}\n\n**Expected Output:**\n```json\n{format_json(ex['extracted_requirements'])}\n```"
        for i, ex in enumerate(FEW_SHOT_EXAMPLES)
    ])

    return f"""{EXTRACTION_SYSTEM_PROMPT}

---

## Few-Shot Examples

{examples_text}

---

## Your Task

Analyze the following transcript and extract all requirements using the same format as the examples above.

**Transcript:**

{transcript}

**Instructions:**
1. Extract ALL genuine requirements (don't miss any)
2. Consolidate duplicate mentions across multiple speakers
3. Use the exact JSON schema shown in examples
4. Include specific metrics and quotes
5. Capture priority signals and business impact

Return ONLY the JSON array, no additional commentary.
"""

def format_json(obj: list) -> str:
    """Pretty-print JSON for prompt examples."""
    import json
    return json.dumps(obj, indent=2)
