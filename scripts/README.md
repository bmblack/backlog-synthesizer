# Scripts Directory

Utility scripts for testing, development, and operations.

---

## 🧪 Test Scripts

### `test_extraction.py`

**Purpose**: Manually test requirement extraction on sample transcript

**Usage**:
```bash
# Activate virtual environment
source .venv/bin/activate

# Run the test
python scripts/test_extraction.py
```

**Requirements**:
- `.env` file with `ANTHROPIC_API_KEY` set
- Virtual environment activated
- Sample transcript at `tests/fixtures/sample_transcript_001.txt`

**Output**:
- Console output with formatted requirements
- JSON file at `tests/output/extracted_requirements.json`

**What it does**:
1. Loads sample transcript from fixtures
2. Initializes AnalysisAgent with Claude 3.5 Sonnet
3. Extracts structured requirements
4. Displays results grouped by type and priority
5. Saves JSON output for further analysis

**Example Output**:
```
================================================================================
🤖 Backlog Synthesizer - Requirement Extraction Test
================================================================================

📄 Loaded transcript: sample_transcript_001.txt
   Length: 12456 characters
   Lines: 125 lines

🔧 Initializing AnalysisAgent...
   Model: claude-3-5-sonnet-20241022
   Max tokens: 4096
   Temperature: 0.0

🔍 Extracting requirements from transcript...
   (This may take 10-30 seconds...)

✅ Extraction complete!

================================================================================
📊 EXTRACTION SUMMARY
================================================================================
Total requirements found: 11
Model used: claude-3-5-sonnet-20241022
Tokens used: 8234 input, 1456 output

================================================================================
📋 EXTRACTED REQUIREMENTS
================================================================================

────────────────────────────────────────────────────────────────────────────────
Requirement #1
────────────────────────────────────────────────────────────────────────────────
📝 Description: Add dark mode theme to reduce eye strain for developers...
🏷️  Type: feature_request
⚡ Priority: medium-high
💥 Impact: Affecting productivity - 15-30 min/developer/day lost...
👤 Stakeholder: Alex Martinez (TechCorp)
📍 Location: Paragraph 10
💬 Quote: "the lack of dark mode. Our engineers work late hours..."
ℹ️  Context: Multiple developers have mentioned this issue...
```

---

## 🔮 Future Scripts

The following scripts will be added as the project progresses:

### Document Processing
- `process_pdf.py` - Extract text from PDF documents
- `chunk_document.py` - Split documents into chunks
- `validate_chunks.py` - Verify chunk quality

### JIRA Integration
- `test_jira_connection.py` - Verify JIRA API access
- `create_sample_story.py` - Create test user story
- `sync_to_jira.py` - Bulk sync stories to JIRA

### Workflow Testing
- `test_full_pipeline.py` - End-to-end workflow test
- `test_human_loop.py` - Human-in-the-loop interaction
- `benchmark_performance.py` - Measure processing speed

### Evaluation
- `run_golden_dataset.py` - Evaluate against golden dataset
- `calculate_metrics.py` - Compute precision/recall/F1
- `generate_report.py` - Create evaluation report

### Operations
- `start_services.py` - Launch Redis, ChromaDB, API server
- `stop_services.py` - Gracefully shutdown services
- `health_check.py` - Verify all components running

---

## 📝 Script Development Guidelines

When adding new scripts to this directory:

1. **Add shebang**: Start with `#!/usr/bin/env python3`

2. **Make executable**: `chmod +x scripts/your_script.py`

3. **Add docstring**: Describe purpose, usage, requirements

4. **Handle errors gracefully**: Check for missing env vars, files, etc.

5. **Use rich output**: Color, formatting, progress indicators

6. **Log to file**: Save detailed logs for debugging

7. **Parse arguments**: Use `argparse` or `typer` for CLI options

8. **Update this README**: Add entry describing the new script

---

## 🛠️ Development Workflow

### Running Scripts

Always activate the virtual environment first:

```bash
cd /Users/bmblack/dev/backlog-synthesizer
source .venv/bin/activate
python scripts/your_script.py
```

### Adding Dependencies

If your script needs new packages:

```bash
# Add to pyproject.toml dependencies
# Then reinstall
pip install -e ".[dev]"
```

### Testing Scripts

Create corresponding test files in `tests/scripts/`:

```bash
tests/scripts/test_extraction_script.py
tests/scripts/test_jira_connection_script.py
```

---

## 📚 Resources

- **Main README**: `/README.md`
- **Implementation Plan**: `/docs/IMPLEMENTATION_PLAN.md`
- **Progress Tracker**: `/PROGRESS.md`

---

**Last Updated**: 2024-11-26
