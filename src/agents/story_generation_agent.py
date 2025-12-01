"""
StoryGenerationAgent: Converts requirements into JIRA-ready user stories.

This agent takes extracted requirements and generates well-structured user stories
following INVEST principles with acceptance criteria, story points, and priorities.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from anthropic import Anthropic
from pydantic import BaseModel, Field, field_validator

from src.agents.prompts.story_generation_prompt import format_story_generation_prompt

# Configure logging
logger = logging.getLogger(__name__)


class UserStory(BaseModel):
    """Structured representation of a JIRA user story."""

    title: str = Field(description="Brief, action-oriented summary (5-10 words)")
    user_story: str = Field(
        description="As a [persona], I want to [action], so that [benefit]"
    )
    description: str = Field(description="Detailed explanation with context and solution")
    acceptance_criteria: List[str] = Field(
        description="3-5 testable conditions", min_length=3, max_length=10
    )
    story_points: int = Field(description="Fibonacci scale (1,2,3,5,8,13)", ge=1, le=13)
    priority: str = Field(description="P0 (Blocker) to P4 (Low)")
    labels: List[str] = Field(description="Categorization tags")
    epic_link: Optional[str] = Field(default=None, description="Epic grouping")
    source_requirements: List[str] = Field(
        description="Original requirements this story addresses"
    )
    technical_notes: Optional[str] = Field(
        default=None, description="Architecture, dependencies, risks"
    )

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: str) -> str:
        """Validate priority is in correct format."""
        valid_priorities = ["P0", "P1", "P2", "P3", "P4"]
        if v not in valid_priorities:
            raise ValueError(f"Priority must be one of {valid_priorities}, got {v}")
        return v

    @field_validator("story_points")
    @classmethod
    def validate_story_points(cls, v: int) -> int:
        """Validate story points follow Fibonacci sequence."""
        valid_points = [1, 2, 3, 5, 8, 13]
        if v not in valid_points:
            raise ValueError(f"Story points must be one of {valid_points}, got {v}")
        return v

    def calculate_invest_score(self) -> Dict[str, Any]:
        """
        Calculate INVEST score for story quality.

        Returns dict with scores for each INVEST criterion.
        """
        score = {
            "independent": 0,  # Based on technical_notes mentioning dependencies
            "negotiable": 0,  # Based on description flexibility
            "valuable": 0,  # Based on user_story clarity
            "estimable": 0,  # Based on acceptance_criteria specificity
            "small": 0,  # Based on story_points
            "testable": 0,  # Based on acceptance_criteria
            "total": 0,
        }

        # Independent: No mention of dependencies
        if self.technical_notes and "depends" not in self.technical_notes.lower():
            score["independent"] = 2
        elif not self.technical_notes:
            score["independent"] = 2

        # Negotiable: Has description with context
        if len(self.description) > 100:
            score["negotiable"] = 2

        # Valuable: Has clear user_story with benefit
        if "so that" in self.user_story.lower():
            score["valuable"] = 2

        # Estimable: Has clear acceptance criteria
        if len(self.acceptance_criteria) >= 3:
            score["estimable"] = 2

        # Small: Story points <= 8
        if self.story_points <= 8:
            score["small"] = 2
        elif self.story_points <= 13:
            score["small"] = 1

        # Testable: Has measurable acceptance criteria
        measurable_keywords = ["<", ">", "seconds", "exactly", "contains", "displays"]
        if any(
            any(keyword in ac.lower() for keyword in measurable_keywords)
            for ac in self.acceptance_criteria
        ):
            score["testable"] = 2

        score["total"] = sum(v for k, v in score.items() if k != "total")
        return score


class StoryGenerationResult(BaseModel):
    """Result of story generation from requirements."""

    stories: List[UserStory] = Field(default_factory=list)
    total_count: int = Field(default=0)
    generation_metadata: Dict[str, Any] = Field(default_factory=dict)


class StoryGenerationAgent:
    """
    Agent responsible for generating user stories from requirements.

    Uses Claude Sonnet 4.5 to convert extracted requirements into well-structured
    JIRA user stories following INVEST principles.

    Attributes:
        client: Anthropic API client
        model: Claude model to use
        max_tokens: Maximum tokens for response
        temperature: Temperature for generation
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-3-haiku-20240307",  # Haiku is sufficient for structured story generation
        max_tokens: int = 4096,  # Haiku max output tokens (Sonnet/Opus support up to 16384)
        temperature: float = 0.3,
    ):
        """
        Initialize the StoryGenerationAgent.

        Args:
            api_key: Anthropic API key (if None, uses ANTHROPIC_API_KEY env var)
            model: Claude model to use
            max_tokens: Maximum tokens for response
            temperature: Generation temperature (0.3 for creative but consistent)
        """
        self.client = Anthropic(api_key=api_key) if api_key else Anthropic()
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature

        logger.info(
            f"StoryGenerationAgent initialized with model={model}, "
            f"max_tokens={max_tokens}, temperature={temperature}"
        )

    def generate_stories(
        self,
        requirements: List[Any],
        context: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> StoryGenerationResult:
        """
        Generate user stories from requirements.

        Args:
            requirements: List of Requirement objects or dicts
            context: Optional context (ADRs, project info, etc.)
            metadata: Optional metadata about the generation

        Returns:
            StoryGenerationResult containing generated stories

        Raises:
            ValueError: If requirements list is empty
            Exception: If Claude API call fails
        """
        if not requirements:
            raise ValueError("Requirements list cannot be empty")

        logger.info(f"Generating user stories from {len(requirements)} requirements")

        try:
            # Format the prompt
            prompt = format_story_generation_prompt(requirements, context)

            # Call Claude API
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                messages=[{"role": "user", "content": prompt}],
            )

            # Extract and parse response
            stories_data = self._parse_response(response.content[0].text)

            # Validate and convert to UserStory objects
            stories = [UserStory(**story) for story in stories_data]

            logger.info(f"Successfully generated {len(stories)} user stories")

            # Calculate INVEST scores
            for story in stories:
                invest_score = story.calculate_invest_score()
                logger.debug(
                    f"Story '{story.title[:50]}...' INVEST score: {invest_score['total']}/12"
                )

            # Build generation metadata
            generation_metadata = {
                "model": self.model,
                "tokens_used": {
                    "input": response.usage.input_tokens,
                    "output": response.usage.output_tokens,
                },
                "num_requirements": len(requirements),
                "num_stories_generated": len(stories),
                "source_metadata": metadata or {},
            }

            return StoryGenerationResult(
                stories=stories,
                total_count=len(stories),
                generation_metadata=generation_metadata,
            )

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response from Claude: {e}")
            raise Exception(f"Invalid JSON response from Claude: {e}")

        except Exception as e:
            logger.error(f"Story generation failed: {e}")
            raise

    def generate_stories_batch(
        self, requirement_batches: List[Dict[str, Any]]
    ) -> List[StoryGenerationResult]:
        """
        Generate stories from multiple requirement batches.

        Args:
            requirement_batches: List of dicts with 'requirements' and optional 'context'

        Returns:
            List of StoryGenerationResult objects

        Raises:
            ValueError: If batches list is empty
        """
        if not requirement_batches:
            raise ValueError("Requirement batches list cannot be empty")

        logger.info(f"Generating stories from {len(requirement_batches)} batches")

        results = []
        for i, batch in enumerate(requirement_batches):
            try:
                requirements = batch.get("requirements", [])
                context = batch.get("context")
                metadata = batch.get("metadata", {})

                if not requirements:
                    logger.warning(f"Skipping batch {i}: empty requirements")
                    continue

                result = self.generate_stories(requirements, context, metadata)
                results.append(result)

            except Exception as e:
                logger.error(f"Failed to generate from batch {i}: {e}")
                # Continue with remaining batches
                results.append(
                    StoryGenerationResult(
                        stories=[],
                        total_count=0,
                        generation_metadata={"error": str(e), "batch_index": i},
                    )
                )

        logger.info(
            f"Batch generation complete: {len(results)} results, "
            f"{sum(r.total_count for r in results)} total stories"
        )

        return results

    def validate_story_quality(self, story: UserStory, min_invest_score: int = 8) -> bool:
        """
        Validate story meets quality thresholds.

        Args:
            story: UserStory to validate
            min_invest_score: Minimum INVEST score (out of 12)

        Returns:
            True if story meets quality threshold
        """
        invest_score = story.calculate_invest_score()
        total_score = invest_score["total"]

        if total_score < min_invest_score:
            logger.warning(
                f"Story '{story.title[:50]}...' below quality threshold: "
                f"{total_score}/{min_invest_score}"
            )
            return False

        return True

    def _parse_response(self, response_text: str) -> List[Dict]:
        """
        Parse Claude response, handling markdown code fences and truncation.

        Args:
            response_text: Raw response from Claude

        Returns:
            Parsed JSON data as list of dicts

        Raises:
            Exception: If JSON is invalid or truncated
        """
        # Strip markdown code fences if present
        response_text = response_text.strip()

        # Handle text before code fence (e.g., "Here is the JSON array:")
        if "```json" in response_text:
            response_text = response_text.split("```json", 1)[1]
        elif "```" in response_text:
            response_text = response_text.split("```", 1)[1]

        # Remove closing fence
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        response_text = response_text.strip()

        # Handle leading text before JSON array (e.g., "Here is the JSON...")
        # Find the first '[' character which starts the JSON array
        if response_text and not response_text.startswith('['):
            bracket_pos = response_text.find('[')
            if bracket_pos > 0:
                logger.debug(f"Stripping {bracket_pos} chars of leading text before JSON array")
                response_text = response_text[bracket_pos:]

        # Check if response looks truncated (doesn't end with ] or })
        if not response_text.endswith("]") and not response_text.endswith("}"):
            logger.warning("Response appears truncated, attempting to fix...")

            # Strategy: Remove incomplete trailing object and close the array
            # Find the last complete object by looking for the last "},\n  {" pattern
            # Then truncate after the last complete "}" and close the array with "]"

            # Look for the last successfully closed object
            last_complete_obj = response_text.rfind("  }")
            if last_complete_obj > 0:
                # Check if there's a trailing comma after this
                after_obj = response_text[last_complete_obj + 3:].strip()
                if after_obj.startswith(","):
                    # Remove the trailing comma and everything after it
                    response_text = response_text[:last_complete_obj + 3]
                else:
                    # Keep up to the closing brace
                    response_text = response_text[:last_complete_obj + 3]

                # Close the array
                response_text += "\n]"
                logger.warning(f"Truncated incomplete trailing object, closed array properly")
            else:
                # Fallback: Try the old method of closing brackets
                if response_text.rstrip().endswith(","):
                    response_text = response_text.rstrip().rstrip(",")

                open_brackets = response_text.count("[") - response_text.count("]")
                open_braces = response_text.count("{") - response_text.count("}")

                response_text += "}" * open_braces
                response_text += "]" * open_brackets
                logger.warning(f"Fixed response: added {open_braces} braces, {open_brackets} brackets")

        # Fix common JSON formatting issues from LLM responses
        # Normalize curly quotes to straight quotes (Claude sometimes uses typographic quotes)
        response_text = response_text.replace('"', '"').replace('"', '"').replace("'", "'").replace("'", "'")

        # Parse JSON
        try:
            return json.loads(response_text)
        except json.JSONDecodeError as e:
            # Save the problematic response for debugging
            debug_path = Path("tests/output/debug_response.txt")
            debug_path.parent.mkdir(exist_ok=True)
            with open(debug_path, "w") as f:
                f.write(response_text)
            logger.error(f"Saved problematic response to {debug_path}")
            raise
