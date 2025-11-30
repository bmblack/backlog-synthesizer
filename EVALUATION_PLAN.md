# Evaluation Plan: Backlog Synthesizer

## Overview

This document defines the comprehensive evaluation strategy for the Backlog Synthesizer system, including golden datasets, evaluation metrics, and LLM-as-judge quality assessment.

## 1. Golden Dataset

### 1.1 Dataset Structure

Our golden dataset consists of 5 carefully curated scenarios representing real-world product development conversations:

```
golden_dataset/
├── scenario_01_authentication/
│   ├── input_transcript.txt
│   ├── expected_requirements.json
│   ├── expected_stories.json
│   └── metadata.json
├── scenario_02_api_integration/
│   ├── input_transcript.txt
│   ├── expected_requirements.json
│   ├── expected_stories.json
│   └── metadata.json
├── scenario_03_ui_redesign/
├── scenario_04_data_migration/
└── scenario_05_mobile_app/
```

### 1.2 Scenario Descriptions

#### Scenario 1: Authentication System
- **Domain**: User authentication and security
- **Complexity**: Medium
- **Requirements**: 12 requirements (8 functional, 4 non-functional)
- **Stories**: 8 user stories across 2 epics
- **Key Challenges**: Security requirements, technical constraints

#### Scenario 2: API Integration
- **Domain**: Third-party integrations
- **Complexity**: High
- **Requirements**: 15 requirements (10 functional, 5 non-functional)
- **Stories**: 10 user stories across 3 epics
- **Key Challenges**: External dependencies, error handling

#### Scenario 3: UI Redesign
- **Domain**: Frontend/UX improvements
- **Complexity**: Low
- **Requirements**: 8 requirements (6 functional, 2 non-functional)
- **Stories**: 6 user stories across 1 epic
- **Key Challenges**: Subjective quality, user experience

#### Scenario 4: Data Migration
- **Domain**: Backend/infrastructure
- **Complexity**: High
- **Requirements**: 18 requirements (12 functional, 6 non-functional)
- **Stories**: 12 user stories across 3 epics
- **Key Challenges**: Data integrity, performance

#### Scenario 5: Mobile App
- **Domain**: Mobile development
- **Complexity**: Medium
- **Requirements**: 14 requirements (10 functional, 4 non-functional)
- **Stories**: 9 user stories across 2 epics
- **Key Challenges**: Platform differences, offline support

## 2. Evaluation Metrics

### 2.1 Requirements Extraction Metrics

#### Precision
```
Precision = True Positives / (True Positives + False Positives)
```
- Measures: How many extracted requirements are correct?
- Target: ≥ 90%

#### Recall
```
Recall = True Positives / (True Positives + False Negatives)
```
- Measures: How many actual requirements were extracted?
- Target: ≥ 85%

#### F1 Score
```
F1 = 2 * (Precision * Recall) / (Precision + Recall)
```
- Measures: Harmonic mean of precision and recall
- Target: ≥ 87%

#### Requirement Type Accuracy
```
Type Accuracy = Correctly Classified Types / Total Requirements
```
- Measures: Accuracy of requirement type classification (functional, non-functional, etc.)
- Target: ≥ 80%

#### Priority Accuracy
```
Priority Accuracy = Correctly Assigned Priorities / Total Requirements
```
- Measures: Accuracy of priority signal detection
- Target: ≥ 75%

### 2.2 Story Generation Metrics

#### INVEST Compliance Score
Evaluate each story against INVEST criteria (0-5 scale):
- **I**ndependent: Can be developed independently?
- **N**egotiable: Flexible scope?
- **V**aluable: Delivers user value?
- **E**stimable: Can be estimated?
- **S**mall: Completable in one sprint?
- **T**estable: Has clear acceptance criteria?

```
INVEST Score = (I + N + V + E + S + T) / 6
```
- Target: ≥ 4.0/5.0

#### Story Point Accuracy
```
Story Point Error = |Estimated Points - Actual Points| / Actual Points
```
- Measures: Deviation from expert-assigned story points
- Target: ≤ 25% mean absolute error

#### Acceptance Criteria Quality
```
AC Quality = (# of testable ACs / # of total ACs) * completeness_score
```
- Measures: Quality and completeness of acceptance criteria
- Target: ≥ 85%

### 2.3 Gap Detection Metrics

#### Duplicate Detection Rate
```
DDR = True Duplicates Detected / Total Duplicates
```
- Measures: Ability to identify duplicate requirements
- Target: ≥ 90%

#### False Positive Rate
```
FPR = False Duplicates / Total Novel Requirements
```
- Measures: Incorrectly flagged novel requirements
- Target: ≤ 10%

#### Semantic Similarity Accuracy
```
SSA = Correct Similarity Classifications / Total Comparisons
```
- Measures: Accuracy of semantic similarity judgments
- Target: ≥ 85%

### 2.4 System Performance Metrics

#### Latency
- **Requirements Extraction**: Target < 10 seconds
- **Story Generation**: Target < 15 seconds
- **Gap Detection**: Target < 5 seconds
- **End-to-End**: Target < 60 seconds

#### Throughput
- **Concurrent Workflows**: Target ≥ 5 simultaneous
- **Daily Capacity**: Target ≥ 500 transcripts/day

#### Resource Utilization
- **Memory**: Target < 2GB per workflow
- **Storage**: Target < 10MB per workflow run

### 2.5 Audit & Observability Metrics

#### Audit Trail Completeness
```
ATC = Logged Events / Total Events
```
- Target: 100%

#### Checkpoint Success Rate
```
CSR = Successful Resumes / Total Resume Attempts
```
- Target: ≥ 95%

## 3. LLM-as-Judge Evaluation

### 3.1 Judge Configuration

We use **Claude Sonnet 4.5** as the judge with specialized evaluation prompts.

### 3.2 Judging Criteria

#### Requirements Quality (0-10 scale)
```
Evaluate the extracted requirement:
1. Clarity (0-10): Is the requirement clearly stated?
2. Completeness (0-10): Does it capture all necessary details?
3. Actionability (0-10): Can engineers act on this?
4. Correctness (0-10): Does it match the transcript intent?

Overall Requirement Score = (Clarity + Completeness + Actionability + Correctness) / 4
```
- Target: ≥ 8.0/10

#### Story Quality (0-10 scale)
```
Evaluate the user story:
1. User-Centric (0-10): Written from user perspective?
2. Value Clarity (0-10): Is the value proposition clear?
3. Acceptance Criteria (0-10): Are ACs complete and testable?
4. Technical Feasibility (0-10): Is the scope reasonable?
5. INVEST Compliance (0-10): Meets INVEST criteria?

Overall Story Score = (User-Centric + Value Clarity + AC + Feasibility + INVEST) / 5
```
- Target: ≥ 8.0/10

#### Context Integration (0-10 scale)
```
Evaluate how well Confluence context was incorporated:
1. Relevance (0-10): Was relevant context used?
2. Technical Consistency (0-10): Aligned with ADRs?
3. Terminology (0-10): Uses project-specific terms?

Context Integration Score = (Relevance + Consistency + Terminology) / 3
```
- Target: ≥ 7.0/10

### 3.3 Judge Prompt Template

```
You are an expert product manager and software architect evaluating the quality of
AI-generated requirements and user stories.

INPUT TRANSCRIPT:
{transcript}

CONFLUENCE CONTEXT (ADRs, Specs):
{confluence_context}

EXTRACTED REQUIREMENT:
{requirement}

EVALUATION TASK:
Rate the requirement on the following criteria (0-10 scale):

1. CLARITY: Is the requirement clearly and unambiguously stated?
   - 0-3: Vague or confusing
   - 4-6: Somewhat clear but needs improvement
   - 7-8: Clear with minor ambiguities
   - 9-10: Crystal clear and unambiguous

2. COMPLETENESS: Does it capture all necessary details from the transcript?
   - 0-3: Missing critical information
   - 4-6: Captures basic idea but lacks details
   - 7-8: Most details captured
   - 9-10: Comprehensive and complete

3. ACTIONABILITY: Can engineers act on this requirement?
   - 0-3: Too vague to implement
   - 4-6: General direction but needs clarification
   - 7-8: Mostly actionable
   - 9-10: Immediately actionable

4. CORRECTNESS: Does it accurately reflect the transcript intent?
   - 0-3: Misinterprets or contradicts transcript
   - 4-6: Partially correct
   - 7-8: Mostly correct with minor deviations
   - 9-10: Perfectly captures intent

5. CONTEXT INTEGRATION: Does it incorporate relevant Confluence context?
   - 0-3: Ignores relevant context
   - 4-6: Minimal context integration
   - 7-8: Good use of context
   - 9-10: Excellent context integration

OUTPUT FORMAT:
{
  "clarity": 9,
  "completeness": 8,
  "actionability": 9,
  "correctness": 10,
  "context_integration": 7,
  "overall_score": 8.6,
  "justification": "Brief explanation of scores",
  "suggestions": "Specific improvement suggestions"
}
```

### 3.4 Judging Process

1. **Automated Evaluation**: Run judge on all golden dataset items
2. **Scoring**: Calculate mean scores per scenario
3. **Analysis**: Identify patterns in failures
4. **Iteration**: Refine prompts based on judge feedback
5. **Human Validation**: Sample 20% of judge evaluations for human review

## 4. Evaluation Workflow

### 4.1 Automated Evaluation Script

```python
# evaluate.py
def evaluate_system():
    results = {
        "scenarios": {},
        "aggregate_metrics": {}
    }

    for scenario in golden_dataset:
        # Run system on scenario
        output = run_workflow(scenario.transcript)

        # Calculate metrics
        req_metrics = evaluate_requirements(
            output.requirements,
            scenario.expected_requirements
        )
        story_metrics = evaluate_stories(
            output.stories,
            scenario.expected_stories
        )

        # LLM-as-judge evaluation
        judge_scores = llm_judge_evaluate(
            transcript=scenario.transcript,
            context=output.context,
            requirements=output.requirements,
            stories=output.stories
        )

        results["scenarios"][scenario.name] = {
            "requirement_metrics": req_metrics,
            "story_metrics": story_metrics,
            "judge_scores": judge_scores,
            "performance": measure_performance(output)
        }

    # Aggregate results
    results["aggregate_metrics"] = aggregate_results(
        results["scenarios"]
    )

    return results
```

### 4.2 Evaluation Schedule

- **Development**: Run on every major code change
- **Pre-Commit**: Quick smoke test (Scenario 1 only)
- **Nightly**: Full evaluation on all scenarios
- **Release**: Comprehensive evaluation + human review

## 5. Success Criteria

### 5.1 Minimum Viable Performance

| Metric | Target | Minimum Acceptable |
|--------|--------|-------------------|
| Requirement Precision | 90% | 85% |
| Requirement Recall | 85% | 80% |
| Story INVEST Score | 4.0/5 | 3.5/5 |
| Gap Detection DDR | 90% | 85% |
| LLM Judge Score | 8.0/10 | 7.0/10 |
| End-to-End Latency | 60s | 90s |

### 5.2 Production Readiness Checklist

- [ ] All metrics meet minimum acceptable thresholds
- [ ] LLM-as-judge scores validated by human experts
- [ ] Performance stable across all 5 scenarios
- [ ] Audit trail 100% complete
- [ ] Error handling tested for all failure modes
- [ ] Documentation complete
- [ ] Security review passed

## 6. Continuous Improvement

### 6.1 Feedback Loop

```
User Feedback → Analyze Failures → Update Golden Dataset →
Refine Prompts → Re-evaluate → Deploy
```

### 6.2 Model Versioning

Track evaluation results across model versions:
- Claude Sonnet 3.5
- Claude Sonnet 4.0
- Claude Sonnet 4.5
- Future models

### 6.3 Prompt Engineering Iterations

Document prompt changes and their impact on metrics:
- Version 1.0: Baseline prompts
- Version 1.1: Added context integration
- Version 1.2: Improved INVEST criteria
- Version 2.0: Multi-shot examples

## 7. Reporting

### 7.1 Evaluation Report Template

```markdown
# Evaluation Report: [Date]

## Summary
- Overall System Score: X.X/10
- All Scenarios Passed: Yes/No
- Recommendation: Production Ready / Needs Improvement

## Detailed Results
### Scenario 1: Authentication
- Requirement Metrics: P=X%, R=X%, F1=X%
- Story Metrics: INVEST=X.X, AC Quality=X%
- Judge Scores: Overall=X.X/10

[Repeat for all scenarios]

## Key Findings
1. Strengths: [What works well]
2. Weaknesses: [What needs improvement]
3. Edge Cases: [Unexpected failures]

## Recommendations
1. [Specific improvement actions]
2. [Prompt refinements needed]
3. [System enhancements]
```

### 7.2 Dashboard Metrics

Real-time dashboard showing:
- Latest evaluation scores
- Trend over time (last 30 days)
- Per-scenario breakdown
- Performance metrics
- Error rate tracking

---

**Version**: 1.0
**Last Updated**: 2024-11-29
**Status**: Implementation Pending
**Owner**: Capstone Project Team
