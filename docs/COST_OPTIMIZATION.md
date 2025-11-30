# Cost Optimization Guide

**Date**: 2024-11-26
**Project**: Backlog Synthesizer

---

## 💰 Model Selection Strategy

### Principle: **Use the cheapest model that can reliably complete the task**

Different tasks require different levels of reasoning capability. Using expensive models for simple tasks wastes money.

---

## 📊 Claude Model Comparison

| Model | Input Cost | Output Cost | Max Output Tokens | Speed | Best For |
|-------|-----------|-------------|-------------------|-------|----------|
| **Haiku** | $0.80/M | $4.00/M | 4,096 | Fastest | Structured tasks, templates, formatting |
| **Sonnet 4** | $3.00/M | $15.00/M | 16,384 | Fast | Balanced reasoning, most tasks |
| **Sonnet 4.5** | $3.00/M | $15.00/M | 16,384 | Fast | Latest features, complex reasoning |
| **Opus** | $15.00/M | $75.00/M | 16,384 | Slower | Most complex reasoning, research |

---

## 🎯 Task-to-Model Mapping

### ✅ Use **Sonnet 4.5** (Expensive)

**When**: Complex reasoning, nuanced understanding, ambiguous inputs

**Tasks**:
1. **Requirement Extraction** (AnalysisAgent)
   - Parse unstructured conversations
   - Infer implicit priorities
   - Consolidate mentions across speakers
   - Handle ambiguous language
   - **Why**: Needs strong reasoning to understand "not a dealbreaker but..." = medium-high priority

2. **ADR Constraint Validation** (Future - Story 2.2)
   - Semantic understanding of architecture rules
   - Identify violations in proposed solutions
   - **Why**: Requires deep technical reasoning

3. **Gap Analysis** (Future - Story 2.3)
   - Identify missing requirements
   - Find contradictions
   - **Why**: Complex analytical reasoning

4. **LLM-as-Judge Evaluation**
   - Score story quality
   - Assess completeness
   - **Why**: Needs sophisticated judgment

---

### ✅ Use **Haiku** (Cheap - 5x cheaper)

**When**: Template-driven, structured output, well-defined format

**Tasks**:
1. **Story Generation** (StoryGenerationAgent) ✅ **UPDATED**
   - Input: Structured requirements (already parsed)
   - Output: Templated user stories
   - Format: Well-defined JSON schema
   - **Why**: Template-filling, not complex reasoning
   - **Note**: Process in batches of 5 requirements due to Haiku's 4,096 output token limit

2. **Story Formatting for JIRA** (Future - Story 1.2)
   - Convert JSON to JIRA markdown
   - Apply formatting rules
   - **Why**: Pure formatting, no reasoning needed

3. **Summary Generation** (Future)
   - Summarize lists of stories
   - Count by priority/epic
   - **Why**: Aggregation, not analysis

4. **Simple Classification**
   - Label categorization
   - Epic assignment (with rules)
   - **Why**: Pattern matching

---

### ⚠️ Use **Sonnet 4** (Middle Ground)

**When**: Some reasoning needed but not complex

**Tasks**:
1. **Deduplication** (Future enhancement)
   - Semantic similarity comparison
   - Merge related requirements
   - **Why**: Needs understanding but not deep reasoning

2. **Story Splitting**
   - Break large stories into smaller ones
   - Maintain dependencies
   - **Why**: Logical decomposition

---

## 💵 Cost Analysis

### Current Architecture (Optimized)

For a typical 40-minute customer transcript (9,070 chars, 13 requirements → 13 stories):

| Stage | Model | Input Tokens | Output Tokens | Cost |
|-------|-------|--------------|---------------|------|
| **1. Extract Requirements** | Sonnet 4.5 | 4,519 | 3,202 | $0.062 |
| **2. Generate Stories** (3 batches) | Haiku | 10,648 | 7,501 | $0.039 |
| **Total per transcript** | | | | **$0.101** |

### Before Optimization

| Stage | Model | Cost |
|-------|-------|------|
| **1. Extract Requirements** | Sonnet 4.5 | $0.062 |
| **2. Generate Stories** | Sonnet 4.5 | $0.099 |
| **Total per transcript** | | **$0.161** |

**Savings: 37% ($0.060 per transcript)**

**Note**: Batching increases input tokens (prompt repeated for each batch) but still provides significant savings. Without batching, a single Haiku call would be $0.026, but we need batching due to the 4,096 output token limit.

### Scale Estimates

| Volume | Monthly Cost (Optimized) | Monthly Cost (Before) | Savings |
|--------|-------------------------|----------------------|---------|
| 10 transcripts | $1.01 | $1.61 | $0.60 |
| 100 transcripts | $10.10 | $16.10 | $6.00 |
| 1,000 transcripts | $101.00 | $161.00 | $60.00 |

---

## 🧪 Testing Model Performance

### Before Switching Models

Always validate that cheaper models maintain quality:

```python
# Test with both models
results_sonnet = story_agent.generate_stories(requirements, model="claude-sonnet-4-5-20250929")
results_haiku = story_agent.generate_stories(requirements, model="claude-3-haiku-20240307")

# Compare INVEST scores
for i, (s_story, h_story) in enumerate(zip(results_sonnet.stories, results_haiku.stories)):
    s_score = s_story.calculate_invest_score()
    h_score = h_story.calculate_invest_score()

    print(f"Story {i+1}:")
    print(f"  Sonnet 4.5: {s_score['total']}/12")
    print(f"  Haiku: {h_score['total']}/12")
    print(f"  Delta: {h_score['total'] - s_score['total']}")
```

**Acceptance Criteria**: Haiku INVEST scores within 1 point of Sonnet

---

## 🔄 Future Optimizations

### 1. **Prompt Caching** (Anthropic Feature)
- Cache system prompts and few-shot examples
- Reduce repeated input costs by 90%
- **Estimated additional savings: 30-40%**

### 2. **Batch Processing**
- Process multiple transcripts in one API call
- Reduce overhead
- **Estimated savings: 10-15%**

### 3. **Smart Routing**
- Automatically route to cheapest model that can handle task
- Use heuristics: complexity, input size, required reasoning
- **Estimated savings: 20-25%**

### 4. **Output Compression**
- Request more concise descriptions
- Reduce acceptance criteria verbosity
- **Estimated savings: 15-20%**

---

## 📋 Model Selection Checklist

Before choosing a model for a new task, ask:

- [ ] **Is the input already structured?** → Consider Haiku
- [ ] **Is the output format well-defined?** → Consider Haiku
- [ ] **Does it require nuanced understanding?** → Use Sonnet
- [ ] **Is there ambiguity to resolve?** → Use Sonnet
- [ ] **Is it template-filling or formatting?** → Use Haiku
- [ ] **Will it be called frequently?** → Optimize aggressively
- [ ] **Is quality more important than cost?** → Use Sonnet/Opus

---

## 🎛️ Configuration

### Environment Variables

```bash
# .env file
REASONING_MODEL=claude-sonnet-4-5-20250929  # Complex reasoning
STORY_GENERATION_MODEL=claude-3-haiku-20240307  # Structured output
JUDGE_LLM_MODEL=claude-sonnet-4-5-20250929  # Evaluation
```

### Agent Initialization

```python
# Requirement extraction (needs reasoning)
analysis_agent = AnalysisAgent(model="claude-sonnet-4-5-20250929")

# Story generation (structured output)
story_agent = StoryGenerationAgent(model="claude-3-haiku-20240307")
```

---

## 📈 Monitoring Costs

### Track Token Usage

All agents return token usage in metadata:

```python
result = agent.extract_requirements(transcript)
tokens = result.extraction_metadata["tokens_used"]
cost = (tokens["input"] / 1_000_000 * 3.00) + (tokens["output"] / 1_000_000 * 15.00)
print(f"Cost: ${cost:.4f}")
```

### Log to Monitoring System

```python
import logging

logger.info(
    "Requirement extraction completed",
    extra={
        "model": agent.model,
        "input_tokens": tokens["input"],
        "output_tokens": tokens["output"],
        "cost_usd": cost,
    }
)
```

---

## 🚨 Red Flags

**When costs are too high:**
- Using Sonnet for simple formatting → Switch to Haiku
- Long prompts sent repeatedly → Implement prompt caching
- Generating too many tokens → Reduce output verbosity
- Not batching requests → Batch when possible

**When quality is too low:**
- Haiku missing nuance → Switch to Sonnet
- Inconsistent output format → Add more examples
- Hallucinations → Use more specific prompts

---

## 📚 Resources

- **Anthropic Pricing**: https://www.anthropic.com/pricing
- **Prompt Caching**: https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching
- **Token Counting**: Use `tiktoken` library

---

**Last Updated**: 2024-11-27
**Status**: ✅ StoryGenerationAgent optimized to use Haiku with batching (37% cost reduction, validated with full pipeline test)
