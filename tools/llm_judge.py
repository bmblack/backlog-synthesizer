#!/usr/bin/env python3
"""
LLM-as-Judge evaluation using Claude Sonnet.

Uses Claude to evaluate the quality of extracted requirements and generated stories
on multiple dimensions (clarity, completeness, actionability, etc.)
"""

import json
import os
from typing import Any, Dict, List, Optional

from anthropic import Anthropic


class LLMJudge:
    """LLM-as-judge evaluator using Claude Sonnet."""

    def __init__(self, model: str = "claude-sonnet-4-20250514", api_key: Optional[str] = None):
        """
        Initialize LLM judge.

        Args:
            model: Claude model to use for evaluation
            api_key: Anthropic API key (or use ANTHROPIC_API_KEY env var)
        """
        self.model = model
        self.client = Anthropic(api_key=api_key or os.getenv("ANTHROPIC_API_KEY"))

    def evaluate_requirement(
        self,
        requirement: Dict[str, Any],
        transcript: str,
        confluence_context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Evaluate a single requirement using LLM-as-judge.

        Args:
            requirement: Requirement dict to evaluate
            transcript: Original transcript text
            confluence_context: Optional Confluence context

        Returns:
            Dict with scores (0-10) for each criterion
        """
        req_text = requirement.get("requirement", "")
        req_type = requirement.get("type", "unknown")
        priority = requirement.get("priority_signal", "unknown")
        impact = requirement.get("impact", "")

        # Build context section separately to avoid f-string backslash issue
        context_section = ""
        if confluence_context:
            context_section = f"CONFLUENCE CONTEXT (ADRs, Specs):\n{confluence_context[:1000]}...\n\n"

        prompt = f"""You are an expert product manager and software architect evaluating the quality of
an AI-extracted requirement from a meeting transcript.

INPUT TRANSCRIPT:
{transcript[:2000]}...
[Transcript truncated for evaluation]

{context_section}EXTRACTED REQUIREMENT:
Text: {req_text}
Type: {req_type}
Priority: {priority}
Impact: {impact}

EVALUATION TASK:
Rate this requirement on the following criteria (0-10 scale):

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

5. CONTEXT_INTEGRATION: Does it incorporate relevant Confluence context?
   - 0-3: Ignores relevant context
   - 4-6: Minimal context integration
   - 7-8: Good use of context
   - 9-10: Excellent context integration
   - N/A: No relevant context available

OUTPUT FORMAT (JSON only, no other text):
{{
  "clarity": 9,
  "completeness": 8,
  "actionability": 9,
  "correctness": 10,
  "context_integration": 7,
  "overall_score": 8.6,
  "justification": "Brief explanation of scores",
  "suggestions": "Specific improvement suggestions"
}}"""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                temperature=0.2,
                messages=[{"role": "user", "content": prompt}]
            )

            # Extract JSON from response
            content = response.content[0].text

            # Try to parse JSON (handle cases where model adds text before/after JSON)
            json_start = content.find('{')
            json_end = content.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                json_str = content[json_start:json_end]
                result = json.loads(json_str)
                return result
            else:
                raise ValueError("No JSON found in response")

        except Exception as e:
            print(f"Warning: LLM judge evaluation failed: {e}")
            # Return neutral scores on failure
            return {
                "clarity": 5,
                "completeness": 5,
                "actionability": 5,
                "correctness": 5,
                "context_integration": 5,
                "overall_score": 5.0,
                "justification": f"Evaluation failed: {str(e)}",
                "suggestions": "Unable to provide suggestions due to evaluation error"
            }

    def evaluate_story(
        self,
        story: Dict[str, Any],
        requirements: List[Dict[str, Any]],
        confluence_context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Evaluate a single user story using LLM-as-judge.

        Args:
            story: Story dict to evaluate
            requirements: List of requirements this story addresses
            confluence_context: Optional Confluence context

        Returns:
            Dict with scores (0-10) for each criterion
        """
        title = story.get("title", "")
        user_story = story.get("user_story", "")
        acceptance_criteria = story.get("acceptance_criteria", [])
        story_points = story.get("story_points", 0)
        technical_notes = story.get("technical_notes", "")

        ac_text = "\n".join([f"  - {ac}" for ac in acceptance_criteria]) if isinstance(acceptance_criteria, list) else str(acceptance_criteria)
        reqs_text = "\n".join([f"  - {r.get('requirement', '')}" for r in requirements[:5]])

        # Build context section separately to avoid f-string backslash issue
        context_section = ""
        if confluence_context:
            context_section = f"CONFLUENCE CONTEXT (ADRs, Specs):\n{confluence_context[:1000]}...\n\n"

        prompt = f"""You are an expert product manager and agile coach evaluating the quality of
an AI-generated user story.

RELATED REQUIREMENTS:
{reqs_text}

{context_section}USER STORY TO EVALUATE:
Title: {title}

Story:
{user_story}

Acceptance Criteria:
{ac_text}

Story Points: {story_points}

Technical Notes: {technical_notes}

EVALUATION TASK:
Rate this user story on the following criteria (0-10 scale):

1. USER_CENTRIC: Is it written from the user's perspective?
   - 0-3: Not user-focused, too technical
   - 4-6: Somewhat user-focused
   - 7-8: Clearly user-focused
   - 9-10: Excellent user perspective with clear value

2. VALUE_CLARITY: Is the value proposition clear?
   - 0-3: No clear value stated
   - 4-6: Value implied but not explicit
   - 7-8: Value clearly stated
   - 9-10: Compelling value proposition

3. ACCEPTANCE_CRITERIA: Are the acceptance criteria complete and testable?
   - 0-3: Missing or vague ACs
   - 4-6: Some ACs but incomplete
   - 7-8: Good ACs, mostly testable
   - 9-10: Excellent, comprehensive testable ACs

4. TECHNICAL_FEASIBILITY: Is the scope reasonable and achievable?
   - 0-3: Scope too large or unclear
   - 4-6: Somewhat achievable but unclear
   - 7-8: Reasonable and achievable
   - 9-10: Well-scoped and clearly achievable

5. INVEST_COMPLIANCE: Does it meet INVEST criteria?
   - 0-3: Violates multiple INVEST criteria
   - 4-6: Meets some INVEST criteria
   - 7-8: Meets most INVEST criteria
   - 9-10: Excellent INVEST compliance

6. CONTEXT_ALIGNMENT: Aligned with Confluence context (ADRs, tech stack)?
   - 0-3: Contradicts or ignores context
   - 4-6: Minimal context integration
   - 7-8: Good context alignment
   - 9-10: Excellent context integration
   - N/A: No relevant context available

OUTPUT FORMAT (JSON only, no other text):
{{
  "user_centric": 9,
  "value_clarity": 8,
  "acceptance_criteria": 9,
  "technical_feasibility": 8,
  "invest_compliance": 9,
  "context_alignment": 7,
  "overall_score": 8.3,
  "justification": "Brief explanation of scores",
  "suggestions": "Specific improvement suggestions"
}}"""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                temperature=0.2,
                messages=[{"role": "user", "content": prompt}]
            )

            # Extract JSON from response
            content = response.content[0].text

            json_start = content.find('{')
            json_end = content.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                json_str = content[json_start:json_end]
                result = json.loads(json_str)
                return result
            else:
                raise ValueError("No JSON found in response")

        except Exception as e:
            print(f"Warning: LLM judge evaluation failed: {e}")
            return {
                "user_centric": 5,
                "value_clarity": 5,
                "acceptance_criteria": 5,
                "technical_feasibility": 5,
                "invest_compliance": 5,
                "context_alignment": 5,
                "overall_score": 5.0,
                "justification": f"Evaluation failed: {str(e)}",
                "suggestions": "Unable to provide suggestions due to evaluation error"
            }

    def evaluate_requirements_batch(
        self,
        requirements: List[Dict[str, Any]],
        transcript: str,
        confluence_context: Optional[str] = None,
        max_samples: int = 10
    ) -> Dict[str, Any]:
        """
        Evaluate a batch of requirements.

        Args:
            requirements: List of requirements to evaluate
            transcript: Original transcript
            confluence_context: Optional Confluence context
            max_samples: Maximum number of requirements to sample

        Returns:
            Dict with aggregate scores and individual evaluations
        """
        # Sample requirements if too many
        sample_reqs = requirements[:max_samples] if len(requirements) > max_samples else requirements

        evaluations = []
        for req in sample_reqs:
            eval_result = self.evaluate_requirement(req, transcript, confluence_context)
            evaluations.append(eval_result)

        # Calculate averages
        avg_scores = {
            "clarity": sum(e.get("clarity", 0) for e in evaluations) / len(evaluations) if evaluations else 0,
            "completeness": sum(e.get("completeness", 0) for e in evaluations) / len(evaluations) if evaluations else 0,
            "actionability": sum(e.get("actionability", 0) for e in evaluations) / len(evaluations) if evaluations else 0,
            "correctness": sum(e.get("correctness", 0) for e in evaluations) / len(evaluations) if evaluations else 0,
            "context_integration": sum(e.get("context_integration", 0) for e in evaluations) / len(evaluations) if evaluations else 0,
            "overall_score": sum(e.get("overall_score", 0) for e in evaluations) / len(evaluations) if evaluations else 0
        }

        return {
            "average_scores": avg_scores,
            "individual_evaluations": evaluations,
            "total_evaluated": len(evaluations),
            "total_requirements": len(requirements)
        }

    def evaluate_stories_batch(
        self,
        stories: List[Dict[str, Any]],
        requirements: List[Dict[str, Any]],
        confluence_context: Optional[str] = None,
        max_samples: int = 10
    ) -> Dict[str, Any]:
        """
        Evaluate a batch of user stories.

        Args:
            stories: List of stories to evaluate
            requirements: List of related requirements
            confluence_context: Optional Confluence context
            max_samples: Maximum number of stories to sample

        Returns:
            Dict with aggregate scores and individual evaluations
        """
        # Sample stories if too many
        sample_stories = stories[:max_samples] if len(stories) > max_samples else stories

        evaluations = []
        for story in sample_stories:
            eval_result = self.evaluate_story(story, requirements, confluence_context)
            evaluations.append(eval_result)

        # Calculate averages
        avg_scores = {
            "user_centric": sum(e.get("user_centric", 0) for e in evaluations) / len(evaluations) if evaluations else 0,
            "value_clarity": sum(e.get("value_clarity", 0) for e in evaluations) / len(evaluations) if evaluations else 0,
            "acceptance_criteria": sum(e.get("acceptance_criteria", 0) for e in evaluations) / len(evaluations) if evaluations else 0,
            "technical_feasibility": sum(e.get("technical_feasibility", 0) for e in evaluations) / len(evaluations) if evaluations else 0,
            "invest_compliance": sum(e.get("invest_compliance", 0) for e in evaluations) / len(evaluations) if evaluations else 0,
            "context_alignment": sum(e.get("context_alignment", 0) for e in evaluations) / len(evaluations) if evaluations else 0,
            "overall_score": sum(e.get("overall_score", 0) for e in evaluations) / len(evaluations) if evaluations else 0
        }

        return {
            "average_scores": avg_scores,
            "individual_evaluations": evaluations,
            "total_evaluated": len(evaluations),
            "total_stories": len(stories)
        }
