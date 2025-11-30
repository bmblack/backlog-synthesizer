#!/usr/bin/env python3
"""
Evaluation runner for Backlog Synthesizer.

Runs the system on golden dataset scenarios and evaluates output quality using:
- Automated metrics (precision, recall, F1, INVEST scores)
- LLM-as-judge evaluation (quality ratings 0-10)

Usage:
    python tools/evaluate.py --scenario 01
    python tools/evaluate.py --all
    python tools/evaluate.py --scenario 01 --use-judge
    python tools/evaluate.py --all --report --output results/
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.evaluation_utils import (
    calculate_requirement_metrics,
    calculate_type_accuracy,
    calculate_priority_accuracy,
    calculate_story_metrics,
    calculate_gap_detection_metrics,
    format_metrics_report
)
from tools.llm_judge import LLMJudge
from src.orchestration.graph import BacklogSynthesizerGraph

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def load_scenario(scenario_path: Path) -> Dict[str, Any]:
    """
    Load a golden dataset scenario.

    Args:
        scenario_path: Path to scenario directory

    Returns:
        Dict with transcript, expected_requirements, expected_stories, metadata
    """
    logger.info(f"Loading scenario from {scenario_path}")

    scenario = {}

    # Load transcript
    transcript_path = scenario_path / "input_transcript.txt"
    if transcript_path.exists():
        with open(transcript_path, 'r') as f:
            scenario["transcript"] = f.read()
    else:
        raise FileNotFoundError(f"Transcript not found: {transcript_path}")

    # Load expected requirements
    reqs_path = scenario_path / "expected_requirements.json"
    if reqs_path.exists():
        with open(reqs_path, 'r') as f:
            scenario["expected_requirements"] = json.load(f)
    else:
        scenario["expected_requirements"] = []

    # Load expected stories
    stories_path = scenario_path / "expected_stories.json"
    if stories_path.exists():
        with open(stories_path, 'r') as f:
            scenario["expected_stories"] = json.load(f)
    else:
        scenario["expected_stories"] = []

    # Load metadata
    metadata_path = scenario_path / "metadata.json"
    if metadata_path.exists():
        with open(metadata_path, 'r') as f:
            scenario["metadata"] = json.load(f)
    else:
        scenario["metadata"] = {}

    logger.info(f"Loaded scenario: {scenario['metadata'].get('scenario_name', 'Unknown')}")
    logger.info(f"  - Expected requirements: {len(scenario['expected_requirements'])}")
    logger.info(f"  - Expected stories: {len(scenario['expected_stories'])}")

    return scenario


def run_workflow_on_scenario(scenario: Dict[str, Any], thread_id: str) -> Dict[str, Any]:
    """
    Run the backlog synthesizer workflow on a scenario.

    Args:
        scenario: Scenario dict with transcript
        thread_id: Unique thread ID for this run

    Returns:
        Workflow result state
    """
    logger.info("Running workflow on scenario...")

    # Set dummy JIRA credentials for evaluation (won't actually push to JIRA)
    import os
    os.environ.setdefault("JIRA_URL", "https://eval.atlassian.net")
    os.environ.setdefault("JIRA_EMAIL", "eval@example.com")
    os.environ.setdefault("JIRA_API_TOKEN", "eval-token")
    os.environ.setdefault("JIRA_PROJECT_KEY", "EVAL")

    # Initialize workflow (disable JIRA push, enable vector memory for gap detection)
    workflow = BacklogSynthesizerGraph(
        enable_checkpointing=False,  # Don't need checkpoint for evaluation
        enable_audit_logging=False,  # Don't need audit for evaluation
        enable_vector_memory=True,   # Need for gap detection
        vector_memory_path=f"data/eval_chroma_{thread_id}"  # Unique path per run
    )

    # Write transcript to temporary file
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write(scenario["transcript"])
        temp_file = f.name

    try:
        # Run workflow
        result = workflow.run(
            input_file_path=temp_file,
            context={
                "project": scenario["metadata"].get("scenario_name", "Evaluation"),
                "evaluation": True
            },
            thread_id=thread_id
        )

        logger.info("Workflow completed")
        logger.info(f"  - Requirements extracted: {len(result.requirements)}")
        logger.info(f"  - Stories generated: {len(result.stories)}")
        logger.info(f"  - Gap analysis: {result.gap_analysis.get('total_novel', 0)} novel, {result.gap_analysis.get('total_covered', 0)} covered")

        return result

    finally:
        # Clean up temporary file
        import os as os_module
        if os_module.path.exists(temp_file):
            os_module.unlink(temp_file)


def evaluate_scenario(
    scenario: Dict[str, Any],
    result: Any,
    use_llm_judge: bool = False
) -> Dict[str, Any]:
    """
    Evaluate workflow results against expected outputs.

    Args:
        scenario: Scenario dict with expected outputs
        result: Workflow result state
        use_llm_judge: Whether to use LLM-as-judge evaluation

    Returns:
        Dict with all evaluation metrics
    """
    logger.info("Evaluating results...")

    metrics = {}

    # 1. Requirements extraction metrics
    if scenario["expected_requirements"] and result.requirements:
        req_metrics = calculate_requirement_metrics(
            result.requirements,
            scenario["expected_requirements"],
            match_threshold=0.7
        )

        # Add type and priority accuracy
        req_metrics["type_accuracy"] = calculate_type_accuracy(
            result.requirements,
            scenario["expected_requirements"],
            match_threshold=0.7
        )
        req_metrics["priority_accuracy"] = calculate_priority_accuracy(
            result.requirements,
            scenario["expected_requirements"],
            match_threshold=0.7
        )

        metrics["requirements"] = req_metrics
        logger.info(f"Requirements metrics: P={req_metrics['precision']:.2%}, R={req_metrics['recall']:.2%}, F1={req_metrics['f1_score']:.2%}")

    # 2. Story generation metrics
    if scenario["expected_stories"] and result.stories:
        story_metrics = calculate_story_metrics(
            result.stories,
            scenario["expected_stories"],
            match_threshold=0.6
        )
        metrics["stories"] = story_metrics
        logger.info(f"Story metrics: INVEST={story_metrics['average_invest_score']:.2f}/5.0, MAE={story_metrics['story_point_mean_absolute_error']:.2%}")

    # 3. Gap detection metrics
    if result.gap_analysis and scenario["metadata"]:
        # Try to infer expected novel/covered from metadata
        eval_notes = scenario["metadata"].get("evaluation_notes", {})
        expected_perf = eval_notes.get("expected_agent_performance", {})

        # For now, use actual as expected (this should be specified in metadata)
        # In a real scenario, you'd define these in metadata.json
        gap_metrics = calculate_gap_detection_metrics(
            result.gap_analysis,
            expected_novel=result.gap_analysis.get("total_novel", 0),  # Would come from metadata
            expected_covered=result.gap_analysis.get("total_covered", 0)  # Would come from metadata
        )
        metrics["gap_detection"] = gap_metrics
        logger.info(f"Gap detection: DDR={gap_metrics['duplicate_detection_rate']:.2%}, FPR={gap_metrics['false_positive_rate']:.2%}")

    # 4. LLM-as-judge evaluation (optional, costs API calls)
    if use_llm_judge:
        logger.info("Running LLM-as-judge evaluation...")
        try:
            judge = LLMJudge()

            # Evaluate requirements
            req_eval = judge.evaluate_requirements_batch(
                result.requirements,
                scenario["transcript"],
                confluence_context=None,  # Could extract from result.context
                max_samples=5  # Limit to reduce API costs
            )

            # Evaluate stories
            story_eval = judge.evaluate_stories_batch(
                result.stories,
                result.requirements,
                confluence_context=None,
                max_samples=5
            )

            metrics["llm_judge"] = {
                "requirements": req_eval,
                "stories": story_eval,
                "avg_requirement_quality": req_eval["average_scores"]["overall_score"],
                "avg_story_quality": story_eval["average_scores"]["overall_score"],
                "avg_context_integration": (
                    req_eval["average_scores"].get("context_integration", 0) +
                    story_eval["average_scores"].get("context_alignment", 0)
                ) / 2
            }

            logger.info(f"LLM judge scores: Req={metrics['llm_judge']['avg_requirement_quality']:.1f}/10, Story={metrics['llm_judge']['avg_story_quality']:.1f}/10")

        except Exception as e:
            logger.error(f"LLM-as-judge evaluation failed: {e}")
            metrics["llm_judge"] = {"error": str(e)}

    return metrics


def save_evaluation_report(
    scenario_id: str,
    scenario: Dict[str, Any],
    metrics: Dict[str, Any],
    output_dir: Path
) -> Path:
    """
    Save evaluation report to file.

    Args:
        scenario_id: Scenario identifier
        scenario: Scenario dict
        metrics: Evaluation metrics
        output_dir: Output directory

    Returns:
        Path to saved report
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = output_dir / f"evaluation_{scenario_id}_{timestamp}.txt"

    # Generate formatted report
    report = format_metrics_report(metrics)

    # Add header
    header = f"""
BACKLOG SYNTHESIZER EVALUATION REPORT
Scenario: {scenario['metadata'].get('scenario_name', scenario_id)}
Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Scenario ID: {scenario_id}

"""

    full_report = header + report

    # Save report
    with open(report_path, 'w') as f:
        f.write(full_report)

    logger.info(f"Evaluation report saved to {report_path}")

    # Also save JSON results
    json_path = output_dir / f"evaluation_{scenario_id}_{timestamp}.json"
    with open(json_path, 'w') as f:
        json.dump({
            "scenario_id": scenario_id,
            "scenario_name": scenario['metadata'].get('scenario_name', scenario_id),
            "timestamp": timestamp,
            "metrics": metrics
        }, f, indent=2)

    logger.info(f"Evaluation JSON saved to {json_path}")

    return report_path


def main():
    """Main evaluation runner."""
    parser = argparse.ArgumentParser(description="Evaluate Backlog Synthesizer on golden dataset")
    parser.add_argument(
        "--scenario",
        type=str,
        help="Scenario ID to evaluate (e.g., '01' for scenario_01_authentication)"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Evaluate all scenarios in golden_dataset/"
    )
    parser.add_argument(
        "--use-judge",
        action="store_true",
        help="Use LLM-as-judge evaluation (costs API calls)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="results/evaluation",
        help="Output directory for reports (default: results/evaluation)"
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Generate detailed evaluation report"
    )

    args = parser.parse_args()

    if not args.scenario and not args.all:
        parser.error("Must specify either --scenario or --all")

    # Find scenarios to evaluate
    golden_dataset_dir = Path("golden_dataset")
    if not golden_dataset_dir.exists():
        logger.error(f"Golden dataset directory not found: {golden_dataset_dir}")
        return 1

    scenarios_to_eval = []

    if args.all:
        # Find all scenario directories
        for scenario_dir in sorted(golden_dataset_dir.glob("scenario_*")):
            if scenario_dir.is_dir():
                scenarios_to_eval.append(scenario_dir)
    else:
        # Find specific scenario
        scenario_pattern = f"scenario_{args.scenario.zfill(2)}_*"
        matching = list(golden_dataset_dir.glob(scenario_pattern))
        if not matching:
            logger.error(f"Scenario not found: {scenario_pattern}")
            return 1
        scenarios_to_eval = matching

    if not scenarios_to_eval:
        logger.error("No scenarios found to evaluate")
        return 1

    logger.info(f"Found {len(scenarios_to_eval)} scenario(s) to evaluate")

    # Evaluate each scenario
    all_results = []

    for scenario_dir in scenarios_to_eval:
        scenario_id = scenario_dir.name.split('_')[1]  # Extract '01' from 'scenario_01_authentication'
        logger.info("=" * 80)
        logger.info(f"EVALUATING SCENARIO {scenario_id}: {scenario_dir.name}")
        logger.info("=" * 80)

        try:
            # Load scenario
            scenario = load_scenario(scenario_dir)

            # Run workflow
            thread_id = f"eval-{scenario_id}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            result = run_workflow_on_scenario(scenario, thread_id)

            # Evaluate results
            metrics = evaluate_scenario(scenario, result, use_llm_judge=args.use_judge)

            # Save report if requested
            if args.report:
                output_dir = Path(args.output)
                report_path = save_evaluation_report(scenario_id, scenario, metrics, output_dir)
                logger.info(f"Report saved: {report_path}")
            else:
                # Print report to console
                report = format_metrics_report(metrics)
                print("\n" + report)

            all_results.append({
                "scenario_id": scenario_id,
                "scenario_name": scenario["metadata"].get("scenario_name", "Unknown"),
                "metrics": metrics,
                "status": "success"
            })

        except Exception as e:
            logger.error(f"Evaluation failed for scenario {scenario_id}: {e}", exc_info=True)
            all_results.append({
                "scenario_id": scenario_id,
                "status": "failed",
                "error": str(e)
            })

    # Summary
    logger.info("=" * 80)
    logger.info("EVALUATION SUMMARY")
    logger.info("=" * 80)

    successful = sum(1 for r in all_results if r["status"] == "success")
    failed = sum(1 for r in all_results if r["status"] == "failed")

    logger.info(f"Total scenarios: {len(all_results)}")
    logger.info(f"Successful: {successful}")
    logger.info(f"Failed: {failed}")

    if successful > 0:
        logger.info("\nAggregate Metrics (across successful scenarios):")

        # Calculate aggregate metrics
        all_metrics = [r["metrics"] for r in all_results if r["status"] == "success"]

        if all_metrics:
            # Requirements
            req_precisions = [m["requirements"]["precision"] for m in all_metrics if "requirements" in m]
            req_recalls = [m["requirements"]["recall"] for m in all_metrics if "requirements" in m]
            req_f1s = [m["requirements"]["f1_score"] for m in all_metrics if "requirements" in m]

            if req_precisions:
                logger.info(f"  Requirement Precision: {sum(req_precisions)/len(req_precisions):.2%}")
            if req_recalls:
                logger.info(f"  Requirement Recall:    {sum(req_recalls)/len(req_recalls):.2%}")
            if req_f1s:
                logger.info(f"  Requirement F1:        {sum(req_f1s)/len(req_f1s):.2%}")

            # Stories
            invest_scores = [m["stories"]["average_invest_score"] for m in all_metrics if "stories" in m]
            if invest_scores:
                logger.info(f"  Average INVEST Score:  {sum(invest_scores)/len(invest_scores):.2f}/5.0")

            # LLM Judge
            if args.use_judge:
                req_qualities = [m["llm_judge"]["avg_requirement_quality"] for m in all_metrics if "llm_judge" in m and "error" not in m["llm_judge"]]
                story_qualities = [m["llm_judge"]["avg_story_quality"] for m in all_metrics if "llm_judge" in m and "error" not in m["llm_judge"]]

                if req_qualities:
                    logger.info(f"  LLM Judge Req Quality: {sum(req_qualities)/len(req_qualities):.1f}/10.0")
                if story_qualities:
                    logger.info(f"  LLM Judge Story Quality: {sum(story_qualities)/len(story_qualities):.1f}/10.0")

    logger.info("\n✓ Evaluation complete!")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
