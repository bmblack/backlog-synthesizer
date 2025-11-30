#!/usr/bin/env python3
"""
Evaluation utilities for assessing Backlog Synthesizer output quality.

Provides metrics calculation and comparison functions for:
- Requirements extraction (precision, recall, F1)
- Story generation (INVEST compliance, story points)
- Gap detection (duplicate detection rate, false positives)
"""

import json
import re
from typing import Any, Dict, List, Tuple
from difflib import SequenceMatcher


def normalize_text(text: str) -> str:
    """Normalize text for comparison (lowercase, remove extra spaces)."""
    return re.sub(r'\s+', ' ', text.lower().strip())


def text_similarity(text1: str, text2: str) -> float:
    """Calculate similarity between two texts using sequence matcher."""
    norm1 = normalize_text(text1)
    norm2 = normalize_text(text2)
    return SequenceMatcher(None, norm1, norm2).ratio()


def find_best_match(
    query: Dict[str, Any],
    candidates: List[Dict[str, Any]],
    text_field: str = "requirement",
    threshold: float = 0.7
) -> Tuple[Dict[str, Any] | None, float]:
    """
    Find the best matching candidate for a query item.

    Args:
        query: Query item to match
        candidates: List of candidate items
        text_field: Field name containing text to compare
        threshold: Minimum similarity threshold (0.0-1.0)

    Returns:
        Tuple of (best_match, similarity_score) or (None, 0.0) if no match
    """
    query_text = query.get(text_field, "")
    if not query_text:
        return None, 0.0

    best_match = None
    best_score = 0.0

    for candidate in candidates:
        candidate_text = candidate.get(text_field, "")
        if not candidate_text:
            continue

        similarity = text_similarity(query_text, candidate_text)
        if similarity > best_score:
            best_score = similarity
            best_match = candidate

    if best_score >= threshold:
        return best_match, best_score

    return None, best_score


def calculate_requirement_metrics(
    extracted: List[Dict[str, Any]],
    expected: List[Dict[str, Any]],
    match_threshold: float = 0.7
) -> Dict[str, Any]:
    """
    Calculate precision, recall, and F1 for requirements extraction.

    Args:
        extracted: List of extracted requirements
        expected: List of expected (ground truth) requirements
        match_threshold: Similarity threshold for matching (default 0.7)

    Returns:
        Dict with precision, recall, f1, true_positives, false_positives, false_negatives
    """
    true_positives = 0
    matched_expected = set()
    matched_extracted = set()

    # Find matches: extracted -> expected
    for i, ext_req in enumerate(extracted):
        match, score = find_best_match(
            ext_req,
            expected,
            text_field="requirement",
            threshold=match_threshold
        )
        if match:
            true_positives += 1
            matched_extracted.add(i)
            # Find index of match in expected
            for j, exp_req in enumerate(expected):
                if (normalize_text(exp_req.get("requirement", "")) ==
                    normalize_text(match.get("requirement", ""))):
                    matched_expected.add(j)
                    break

    false_positives = len(extracted) - true_positives
    false_negatives = len(expected) - len(matched_expected)

    # Calculate metrics
    precision = true_positives / len(extracted) if extracted else 0.0
    recall = true_positives / len(expected) if expected else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

    return {
        "precision": precision,
        "recall": recall,
        "f1_score": f1,
        "true_positives": true_positives,
        "false_positives": false_positives,
        "false_negatives": false_negatives,
        "total_extracted": len(extracted),
        "total_expected": len(expected),
        "matched_extracted_indices": list(matched_extracted),
        "matched_expected_indices": list(matched_expected)
    }


def calculate_type_accuracy(
    extracted: List[Dict[str, Any]],
    expected: List[Dict[str, Any]],
    match_threshold: float = 0.7
) -> float:
    """
    Calculate accuracy of requirement type classification.

    Args:
        extracted: List of extracted requirements with 'type' field
        expected: List of expected requirements with 'type' field
        match_threshold: Similarity threshold for matching requirements

    Returns:
        Type accuracy (0.0-1.0)
    """
    correct_types = 0
    total_matched = 0

    for ext_req in extracted:
        match, score = find_best_match(
            ext_req,
            expected,
            text_field="requirement",
            threshold=match_threshold
        )
        if match:
            total_matched += 1
            ext_type = normalize_text(ext_req.get("type", ""))
            exp_type = normalize_text(match.get("type", ""))
            if ext_type == exp_type:
                correct_types += 1

    return correct_types / total_matched if total_matched > 0 else 0.0


def calculate_priority_accuracy(
    extracted: List[Dict[str, Any]],
    expected: List[Dict[str, Any]],
    match_threshold: float = 0.7
) -> float:
    """
    Calculate accuracy of priority signal detection.

    Args:
        extracted: List of extracted requirements with 'priority_signal' field
        expected: List of expected requirements with 'priority_signal' field
        match_threshold: Similarity threshold for matching requirements

    Returns:
        Priority accuracy (0.0-1.0)
    """
    correct_priorities = 0
    total_matched = 0

    for ext_req in extracted:
        match, score = find_best_match(
            ext_req,
            expected,
            text_field="requirement",
            threshold=match_threshold
        )
        if match:
            total_matched += 1
            ext_priority = normalize_text(ext_req.get("priority_signal", ""))
            exp_priority = normalize_text(match.get("priority_signal", ""))
            if ext_priority == exp_priority:
                correct_priorities += 1

    return correct_priorities / total_matched if total_matched > 0 else 0.0


def calculate_invest_score(story: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate INVEST compliance score for a user story.

    INVEST criteria:
    - Independent: Can be developed independently
    - Negotiable: Flexible scope
    - Valuable: Delivers user value
    - Estimable: Can be estimated
    - Small: Completable in one sprint
    - Testable: Has clear acceptance criteria

    Args:
        story: User story dict with title, user_story, acceptance_criteria, story_points

    Returns:
        Dict with individual scores and overall INVEST score (0-5)
    """
    scores = {
        "independent": 0,
        "negotiable": 0,
        "valuable": 0,
        "estimable": 0,
        "small": 0,
        "testable": 0
    }

    user_story = story.get("user_story", "")
    acceptance_criteria = story.get("acceptance_criteria", [])
    story_points = story.get("story_points", 0)

    # Independent: Has clear scope and not too many dependencies
    # Check if story has clear "As a... I want... so that..." structure
    if re.search(r'as a .+i want.+so that', user_story, re.IGNORECASE):
        scores["independent"] = 4
    elif "as a" in user_story.lower() or "i want" in user_story.lower():
        scores["independent"] = 3
    else:
        scores["independent"] = 2

    # Negotiable: Story describes what, not how (some flexibility)
    # Check if story avoids implementation details
    impl_keywords = ["implement", "code", "program", "database", "table", "function"]
    impl_count = sum(1 for kw in impl_keywords if kw in user_story.lower())
    if impl_count == 0:
        scores["negotiable"] = 5
    elif impl_count <= 2:
        scores["negotiable"] = 3
    else:
        scores["negotiable"] = 2

    # Valuable: Clear value proposition in "so that" clause
    if "so that" in user_story.lower():
        scores["valuable"] = 5
    elif "value" in user_story.lower() or "benefit" in user_story.lower():
        scores["valuable"] = 3
    else:
        scores["valuable"] = 2

    # Estimable: Has story points assigned
    if story_points > 0:
        if story_points in [1, 2, 3, 5, 8, 13]:  # Fibonacci
            scores["estimable"] = 5
        else:
            scores["estimable"] = 3
    else:
        scores["estimable"] = 1

    # Small: Story points indicate reasonable size
    if 1 <= story_points <= 5:
        scores["small"] = 5
    elif story_points <= 8:
        scores["small"] = 4
    elif story_points <= 13:
        scores["small"] = 3
    else:
        scores["small"] = 2

    # Testable: Has clear acceptance criteria
    ac_count = len(acceptance_criteria) if isinstance(acceptance_criteria, list) else 0
    if ac_count >= 5:
        scores["testable"] = 5
    elif ac_count >= 3:
        scores["testable"] = 4
    elif ac_count >= 1:
        scores["testable"] = 3
    else:
        scores["testable"] = 1

    # Calculate overall score
    overall_score = sum(scores.values()) / len(scores)

    return {
        **scores,
        "overall_invest_score": overall_score,
        "max_score": 5.0
    }


def calculate_story_metrics(
    generated: List[Dict[str, Any]],
    expected: List[Dict[str, Any]],
    match_threshold: float = 0.6
) -> Dict[str, Any]:
    """
    Calculate metrics for generated user stories.

    Args:
        generated: List of generated stories
        expected: List of expected stories
        match_threshold: Similarity threshold for matching stories

    Returns:
        Dict with story metrics including INVEST scores, story point accuracy
    """
    invest_scores = []
    story_point_errors = []
    ac_quality_scores = []

    matched_count = 0

    for gen_story in generated:
        # Calculate INVEST score
        invest_result = calculate_invest_score(gen_story)
        invest_scores.append(invest_result["overall_invest_score"])

        # Find matching expected story
        match, score = find_best_match(
            gen_story,
            expected,
            text_field="title",
            threshold=match_threshold
        )

        if match:
            matched_count += 1

            # Story point accuracy
            gen_points = gen_story.get("story_points", 0)
            exp_points = match.get("story_points", 0)
            if exp_points > 0:
                error = abs(gen_points - exp_points) / exp_points
                story_point_errors.append(error)

            # Acceptance criteria quality
            gen_ac = gen_story.get("acceptance_criteria", [])
            exp_ac = match.get("acceptance_criteria", [])
            if isinstance(gen_ac, list) and isinstance(exp_ac, list):
                ac_coverage = min(len(gen_ac), len(exp_ac)) / max(len(exp_ac), 1)
                ac_quality_scores.append(ac_coverage)

    # Calculate aggregate metrics
    avg_invest = sum(invest_scores) / len(invest_scores) if invest_scores else 0.0
    avg_sp_error = sum(story_point_errors) / len(story_point_errors) if story_point_errors else 0.0
    avg_ac_quality = sum(ac_quality_scores) / len(ac_quality_scores) if ac_quality_scores else 0.0

    return {
        "average_invest_score": avg_invest,
        "invest_scores": invest_scores,
        "story_point_mean_absolute_error": avg_sp_error,
        "acceptance_criteria_quality": avg_ac_quality,
        "matched_stories": matched_count,
        "total_generated": len(generated),
        "total_expected": len(expected)
    }


def calculate_gap_detection_metrics(
    gap_analysis: Dict[str, Any],
    expected_novel: int,
    expected_covered: int
) -> Dict[str, Any]:
    """
    Calculate gap detection accuracy metrics.

    Args:
        gap_analysis: Gap analysis results from workflow
        expected_novel: Expected number of novel requirements
        expected_covered: Expected number of covered requirements

    Returns:
        Dict with gap detection metrics
    """
    actual_novel = gap_analysis.get("total_novel", 0)
    actual_covered = gap_analysis.get("total_covered", 0)

    # Calculate accuracy
    total_expected = expected_novel + expected_covered
    total_actual = actual_novel + actual_covered

    # True positives for duplicate detection = correctly identified covered
    # True negatives = correctly identified novel
    correct_novel = min(actual_novel, expected_novel)
    correct_covered = min(actual_covered, expected_covered)

    duplicate_detection_rate = correct_covered / expected_covered if expected_covered > 0 else 0.0
    false_positive_rate = abs(actual_novel - expected_novel) / expected_novel if expected_novel > 0 else 0.0

    overall_accuracy = (correct_novel + correct_covered) / total_expected if total_expected > 0 else 0.0

    return {
        "duplicate_detection_rate": duplicate_detection_rate,
        "false_positive_rate": false_positive_rate,
        "overall_gap_accuracy": overall_accuracy,
        "expected_novel": expected_novel,
        "expected_covered": expected_covered,
        "actual_novel": actual_novel,
        "actual_covered": actual_covered,
        "correct_novel": correct_novel,
        "correct_covered": correct_covered
    }


def format_metrics_report(metrics: Dict[str, Any]) -> str:
    """
    Format evaluation metrics as a readable report.

    Args:
        metrics: Dict containing all evaluation metrics

    Returns:
        Formatted string report
    """
    report_lines = []

    report_lines.append("=" * 80)
    report_lines.append("EVALUATION METRICS REPORT")
    report_lines.append("=" * 80)
    report_lines.append("")

    # Requirements Extraction
    if "requirements" in metrics:
        req_metrics = metrics["requirements"]
        report_lines.append("REQUIREMENTS EXTRACTION")
        report_lines.append("-" * 80)
        report_lines.append(f"  Precision:          {req_metrics.get('precision', 0):.2%}")
        report_lines.append(f"  Recall:             {req_metrics.get('recall', 0):.2%}")
        report_lines.append(f"  F1 Score:           {req_metrics.get('f1_score', 0):.2%}")
        report_lines.append(f"  Type Accuracy:      {req_metrics.get('type_accuracy', 0):.2%}")
        report_lines.append(f"  Priority Accuracy:  {req_metrics.get('priority_accuracy', 0):.2%}")
        report_lines.append(f"  True Positives:     {req_metrics.get('true_positives', 0)}")
        report_lines.append(f"  False Positives:    {req_metrics.get('false_positives', 0)}")
        report_lines.append(f"  False Negatives:    {req_metrics.get('false_negatives', 0)}")
        report_lines.append("")

    # Story Generation
    if "stories" in metrics:
        story_metrics = metrics["stories"]
        report_lines.append("STORY GENERATION")
        report_lines.append("-" * 80)
        report_lines.append(f"  Average INVEST Score:       {story_metrics.get('average_invest_score', 0):.2f}/5.0")
        report_lines.append(f"  Story Point MAE:            {story_metrics.get('story_point_mean_absolute_error', 0):.2%}")
        report_lines.append(f"  Acceptance Criteria Quality: {story_metrics.get('acceptance_criteria_quality', 0):.2%}")
        report_lines.append(f"  Matched Stories:            {story_metrics.get('matched_stories', 0)}/{story_metrics.get('total_expected', 0)}")
        report_lines.append("")

    # Gap Detection
    if "gap_detection" in metrics:
        gap_metrics = metrics["gap_detection"]
        report_lines.append("GAP DETECTION")
        report_lines.append("-" * 80)
        report_lines.append(f"  Duplicate Detection Rate:   {gap_metrics.get('duplicate_detection_rate', 0):.2%}")
        report_lines.append(f"  False Positive Rate:        {gap_metrics.get('false_positive_rate', 0):.2%}")
        report_lines.append(f"  Overall Gap Accuracy:       {gap_metrics.get('overall_gap_accuracy', 0):.2%}")
        report_lines.append(f"  Novel (Expected/Actual):    {gap_metrics.get('expected_novel', 0)}/{gap_metrics.get('actual_novel', 0)}")
        report_lines.append(f"  Covered (Expected/Actual):  {gap_metrics.get('expected_covered', 0)}/{gap_metrics.get('actual_covered', 0)}")
        report_lines.append("")

    # LLM Judge Scores
    if "llm_judge" in metrics:
        judge_metrics = metrics["llm_judge"]
        report_lines.append("LLM-AS-JUDGE QUALITY SCORES")
        report_lines.append("-" * 80)
        report_lines.append(f"  Average Requirement Quality: {judge_metrics.get('avg_requirement_quality', 0):.1f}/10.0")
        report_lines.append(f"  Average Story Quality:       {judge_metrics.get('avg_story_quality', 0):.1f}/10.0")
        report_lines.append(f"  Context Integration:         {judge_metrics.get('avg_context_integration', 0):.1f}/10.0")
        report_lines.append("")

    # Overall Summary
    report_lines.append("=" * 80)
    report_lines.append("SUMMARY")
    report_lines.append("=" * 80)

    # Check against targets
    targets_met = []
    targets_missed = []

    if "requirements" in metrics:
        req_m = metrics["requirements"]
        if req_m.get("precision", 0) >= 0.90:
            targets_met.append("✓ Requirement Precision ≥ 90%")
        else:
            targets_missed.append("✗ Requirement Precision < 90%")

        if req_m.get("recall", 0) >= 0.85:
            targets_met.append("✓ Requirement Recall ≥ 85%")
        else:
            targets_missed.append("✗ Requirement Recall < 85%")

    if "stories" in metrics:
        story_m = metrics["stories"]
        if story_m.get("average_invest_score", 0) >= 4.0:
            targets_met.append("✓ INVEST Score ≥ 4.0")
        else:
            targets_missed.append("✗ INVEST Score < 4.0")

    if "gap_detection" in metrics:
        gap_m = metrics["gap_detection"]
        if gap_m.get("duplicate_detection_rate", 0) >= 0.90:
            targets_met.append("✓ Duplicate Detection ≥ 90%")
        else:
            targets_missed.append("✗ Duplicate Detection < 90%")

    if targets_met:
        report_lines.append("\nTargets Met:")
        for target in targets_met:
            report_lines.append(f"  {target}")

    if targets_missed:
        report_lines.append("\nTargets Missed:")
        for target in targets_missed:
            report_lines.append(f"  {target}")

    report_lines.append("")
    report_lines.append("=" * 80)

    return "\n".join(report_lines)
