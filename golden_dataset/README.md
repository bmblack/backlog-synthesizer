# Golden Dataset for Backlog Synthesizer Evaluation

## Overview

This directory contains carefully curated golden datasets for evaluating the Backlog Synthesizer system. Each scenario represents a real-world requirements gathering session with expected outputs for automated testing and quality assessment.

## Dataset Structure

Each scenario follows this structure:

```
scenario_XX_name/
├── input_transcript.txt          # Meeting transcript (input)
├── expected_requirements.json    # Expected extracted requirements (ground truth)
├── expected_stories.json         # Expected generated user stories (ground truth)
└── metadata.json                 # Scenario metadata and test assertions
```

## Current Scenarios

### Scenario 01: Authentication System ✅
- **Domain**: User Authentication and Security
- **Complexity**: High
- **Requirements**: 21 (10 functional, 7 non-functional, 4 technical)
- **Stories**: 12 user stories across 3 epics
- **Key Challenges**: Security-critical requirements, OAuth integration, 2FA, accessibility
- **Status**: Complete

### Scenario 02: API Integration (Planned)
- **Domain**: Third-party integrations
- **Complexity**: High
- **Requirements**: ~15 requirements
- **Stories**: ~10 user stories

### Scenario 03: UI Redesign (Planned)
- **Domain**: Frontend/UX improvements
- **Complexity**: Low
- **Requirements**: ~8 requirements
- **Stories**: ~6 user stories

### Scenario 04: Data Migration (Planned)
- **Domain**: Backend/infrastructure
- **Complexity**: High
- **Requirements**: ~18 requirements
- **Stories**: ~12 user stories

### Scenario 05: Mobile App (Planned)
- **Domain**: Mobile development
- **Complexity**: Medium
- **Requirements**: ~14 requirements
- **Stories**: ~9 user stories

## Usage

### Running Evaluation

```bash
# Evaluate all scenarios
python tools/evaluate.py --all

# Evaluate specific scenario
python tools/evaluate.py --scenario 01

# Run with LLM-as-judge
python tools/evaluate.py --scenario 01 --use-judge

# Generate evaluation report
python tools/evaluate.py --all --report
```

### Expected Output

The evaluation script will:
1. Run the workflow on each scenario's input transcript
2. Compare output against expected requirements and stories
3. Calculate metrics (precision, recall, F1, INVEST score, etc.)
4. Run LLM-as-judge evaluation (if enabled)
5. Generate a comprehensive evaluation report

### Evaluation Metrics

**Requirement Extraction:**
- Precision: True Positives / (True Positives + False Positives)
- Recall: True Positives / (True Positives + False Negatives)
- F1 Score: Harmonic mean of precision and recall
- Type Accuracy: Correctly classified types / Total requirements

**Story Generation:**
- INVEST Compliance Score: 0-5 scale for each INVEST criterion
- Story Point Accuracy: Mean absolute error vs expected points
- Acceptance Criteria Quality: Testability and completeness

**Gap Detection:**
- Duplicate Detection Rate: True duplicates detected / Total duplicates
- False Positive Rate: False duplicates / Total novel requirements

**LLM-as-Judge:**
- Requirement Quality: 0-10 scale (clarity, completeness, actionability, correctness)
- Story Quality: 0-10 scale (user-centric, value clarity, AC quality, feasibility, INVEST)
- Context Integration: 0-10 scale (relevance, consistency, terminology)

## Creating New Scenarios

To add a new scenario:

1. **Create directory**: `scenario_XX_name/`
2. **Write transcript**: `input_transcript.txt`
   - Real or realistic meeting dialogue
   - 20-45 minute duration
   - 2-4 speakers
   - Clear requirements discussion
   - Include context references (ADRs, specs)

3. **Define expected requirements**: `expected_requirements.json`
   - Extract ground truth requirements
   - Classify types (functional, non-functional, technical)
   - Assign priority signals
   - Note source locations in transcript

4. **Define expected stories**: `expected_stories.json`
   - Write high-quality user stories
   - Include comprehensive acceptance criteria
   - Assign story points (1, 2, 3, 5, 8, 13)
   - Link to epics
   - Add technical notes

5. **Create metadata**: `metadata.json`
   - Scenario description
   - Statistics (length, duration, counts)
   - Key challenges
   - Context references
   - Test assertions

6. **Validate scenario**:
   ```bash
   python tools/validate_scenario.py --scenario XX
   ```

## Quality Guidelines

### Transcript Quality
- ✅ Natural conversation flow
- ✅ Realistic discussion patterns
- ✅ Clear speaker attribution
- ✅ Timestamps or duration markers
- ✅ Mix of explicit and implicit requirements
- ✅ Context references (ADRs, specs)
- ❌ No overly formal or robotic language
- ❌ No unrealistic perfection (include tangents, clarifications)

### Expected Requirements Quality
- ✅ Complete coverage of discussed requirements
- ✅ Accurate type classification
- ✅ Realistic priority signals
- ✅ Impact analysis included
- ✅ Source locations referenced
- ❌ No hallucinated requirements
- ❌ No requirements not in transcript

### Expected Stories Quality
- ✅ INVEST criteria compliance
- ✅ Clear user story format ("As a... I want... so that...")
- ✅ Comprehensive acceptance criteria (5-8 per story)
- ✅ Realistic story points
- ✅ Technical notes with architectural context
- ✅ Proper epic linkage
- ❌ No vague or generic stories
- ❌ No missing acceptance criteria

## Test Assertion Types

### Must Extract
Requirements that MUST be extracted from the transcript. Failure to extract these indicates a recall problem.

Example:
```json
"must_extract": [
  "Email/password authentication",
  "OAuth 2.0 (Google and GitHub)",
  "Two-factor authentication (TOTP)"
]
```

### Must Not Hallucinate
Technologies, features, or requirements that are NOT in the transcript. Extracting these indicates a precision problem.

Example:
```json
"must_not_hallucinate": [
  "MongoDB",
  "Angular framework",
  "Blockchain integration"
]
```

### Context Integration Checks
Verify that Confluence context (ADRs, specs) is properly incorporated into stories.

Example:
```json
"context_integration_checks": [
  "Stories should reference FastAPI (from ADR-002)",
  "Stories should reference PostgreSQL (from ADR-002)"
]
```

## Benchmark Targets

| Metric | Target | Minimum Acceptable |
|--------|--------|-------------------|
| Requirement Precision | 90% | 85% |
| Requirement Recall | 85% | 80% |
| Requirement F1 | 87% | 82% |
| Story INVEST Score | 4.0/5 | 3.5/5 |
| Duplicate Detection | 90% | 85% |
| LLM Judge Score | 8.0/10 | 7.0/10 |

## Version History

- **v1.0** (2024-11-29): Initial dataset with Scenario 01 (Authentication System)
- **v1.1** (TBD): Add Scenarios 02-05
- **v2.0** (TBD): Expand to 10 scenarios across diverse domains

## Contributing

To contribute new scenarios:

1. Follow the structure and quality guidelines above
2. Validate scenario with `validate_scenario.py`
3. Run evaluation to ensure reasonable baseline
4. Submit PR with scenario files and justification
5. Include metadata on domain, complexity, and key challenges

## License

This dataset is part of the Backlog Synthesizer project and is available under the same license as the main project.

---

**Dataset Version**: 1.0
**Last Updated**: 2024-11-29
**Maintainer**: Capstone Project Team
