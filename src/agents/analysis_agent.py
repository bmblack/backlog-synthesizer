"""
AnalysisAgent: Extracts structured requirements from customer transcripts.

This agent uses Claude 3.5 Sonnet to analyze meeting transcripts, customer feedback,
and product discussions, extracting actionable requirements with priority signals,
business impact, and source citations.
"""

import json
import logging
from typing import Any, Dict, List, Optional

from anthropic import Anthropic
from pydantic import BaseModel, Field

from src.agents.prompts.extraction_prompt import format_extraction_prompt
from src.tools.chunking import TranscriptChunker, estimate_chunk_count

# Configure logging
logger = logging.getLogger(__name__)


class Requirement(BaseModel):
    """Structured representation of an extracted requirement."""

    requirement: str = Field(
        description="Clear, concise description of what is needed (1-2 sentences)"
    )
    type: str = Field(
        description="Category: feature_request, bug_report, enhancement, pain_point, question"
    )
    priority_signal: str = Field(
        description="Urgency indicator: urgent, blocker, critical, high, medium, low, nice-to-have"
    )
    impact: str = Field(description="Business impact or pain caused by lack of this requirement")
    source_citation: str = Field(description="Direct quote from transcript")
    paragraph_number: int = Field(description="Line/paragraph number where requirement appears")
    stakeholder: str = Field(description="Person who mentioned the requirement")
    context: str = Field(description="Additional relevant details or constraints")


class ExtractionResult(BaseModel):
    """Result of requirement extraction from a transcript."""

    requirements: List[Requirement] = Field(default_factory=list)
    total_count: int = Field(default=0)
    extraction_metadata: Dict[str, Any] = Field(default_factory=dict)


class AnalysisAgent:
    """
    Agent responsible for extracting requirements from customer transcripts.

    Uses Claude 3.5 Sonnet with structured output to identify feature requests,
    bug reports, enhancements, and pain points with priority signals and context.

    Attributes:
        client: Anthropic API client
        model: Claude model to use (default: claude-3-5-sonnet-20241022)
        max_tokens: Maximum tokens for Claude response
        temperature: Temperature for generation (0 for deterministic)
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-sonnet-4-5-20250929",
        max_tokens: int = 4096,
        temperature: float = 0.0,
        enable_chunking: bool = True,
        chunk_size: int = 4000,
        chunk_overlap: int = 200,
    ):
        """
        Initialize the AnalysisAgent.

        Args:
            api_key: Anthropic API key (if None, uses ANTHROPIC_API_KEY env var)
            model: Claude model to use
            max_tokens: Maximum tokens for response
            temperature: Generation temperature (0 = deterministic)
            enable_chunking: Whether to chunk large transcripts automatically
            chunk_size: Target size in tokens per chunk (if chunking enabled)
            chunk_overlap: Number of overlapping tokens between chunks
        """
        self.client = Anthropic(api_key=api_key) if api_key else Anthropic()
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.enable_chunking = enable_chunking
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

        # Initialize chunker if enabled
        if self.enable_chunking:
            self.chunker = TranscriptChunker(
                chunk_size=chunk_size, chunk_overlap=chunk_overlap, preserve_structure=True
            )
        else:
            self.chunker = None

        logger.info(
            f"AnalysisAgent initialized with model={model}, max_tokens={max_tokens}, "
            f"temperature={temperature}, chunking={'enabled' if enable_chunking else 'disabled'}"
        )

    def extract_requirements(
        self, transcript: str, metadata: Optional[Dict[str, Any]] = None
    ) -> ExtractionResult:
        """
        Extract structured requirements from a customer transcript.

        Automatically chunks large transcripts if chunking is enabled.

        Args:
            transcript: Meeting transcript or customer feedback text
            metadata: Optional metadata about the transcript (source, date, etc.)

        Returns:
            ExtractionResult containing list of extracted requirements

        Raises:
            ValueError: If transcript is empty or invalid
            Exception: If Claude API call fails
        """
        if not transcript or not transcript.strip():
            raise ValueError("Transcript cannot be empty")

        logger.info(f"Extracting requirements from transcript ({len(transcript)} chars)")

        # Check if chunking is needed
        if self.enable_chunking and self.chunker:
            estimated_chunks = estimate_chunk_count(transcript, self.chunk_size)
            if estimated_chunks > 1:
                logger.info(
                    f"Transcript is large, using chunking strategy "
                    f"(estimated {estimated_chunks} chunks)"
                )
                return self._extract_with_chunking(transcript, metadata)

        # Single-pass extraction for smaller transcripts
        return self._extract_single(transcript, metadata)

    def _extract_single(
        self, transcript: str, metadata: Optional[Dict[str, Any]] = None
    ) -> ExtractionResult:
        """
        Extract requirements from a single transcript without chunking.

        Args:
            transcript: Meeting transcript text
            metadata: Optional metadata

        Returns:
            ExtractionResult with extracted requirements
        """
        try:
            # Format the prompt with few-shot examples
            prompt = format_extraction_prompt(transcript)

            # Call Claude API
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                messages=[{"role": "user", "content": prompt}],
            )

            # Extract and parse response
            requirements_data = self._parse_response(response.content[0].text)

            # Validate and convert to Requirement objects
            requirements = [Requirement(**req) for req in requirements_data]

            logger.info(f"Successfully extracted {len(requirements)} requirements")

            # Build extraction metadata
            extraction_metadata = {
                "model": self.model,
                "tokens_used": {
                    "input": response.usage.input_tokens,
                    "output": response.usage.output_tokens,
                },
                "transcript_length": len(transcript),
                "chunked": False,
                "source_metadata": metadata or {},
            }

            return ExtractionResult(
                requirements=requirements,
                total_count=len(requirements),
                extraction_metadata=extraction_metadata,
            )

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response from Claude: {e}")
            raise Exception(f"Invalid JSON response from Claude: {e}")

        except Exception as e:
            logger.error(f"Requirement extraction failed: {e}")
            raise

    def _extract_with_chunking(
        self, transcript: str, metadata: Optional[Dict[str, Any]] = None
    ) -> ExtractionResult:
        """
        Extract requirements from a large transcript using chunking.

        Args:
            transcript: Meeting transcript text
            metadata: Optional metadata

        Returns:
            ExtractionResult with consolidated requirements from all chunks
        """
        # Split transcript into chunks
        chunks = self.chunker.chunk_text(transcript)
        logger.info(f"Split transcript into {len(chunks)} chunks")

        total_input_tokens = 0
        total_output_tokens = 0
        all_requirements = []

        # Process each chunk
        for chunk in chunks:
            logger.info(
                f"Processing chunk {chunk.chunk_index + 1}/{chunk.total_chunks} "
                f"(lines {chunk.start_line}-{chunk.end_line})"
            )

            try:
                # Extract from this chunk
                chunk_result = self._extract_single(chunk.text, metadata)

                # Accumulate requirements
                all_requirements.extend(chunk_result.requirements)

                # Track token usage
                tokens = chunk_result.extraction_metadata.get("tokens_used", {})
                total_input_tokens += tokens.get("input", 0)
                total_output_tokens += tokens.get("output", 0)

            except Exception as e:
                logger.warning(
                    f"Failed to extract from chunk {chunk.chunk_index + 1}: {e}. Continuing..."
                )
                continue

        # Deduplicate requirements (simple for now - exact matches)
        deduplicated = self._deduplicate_requirements(all_requirements)

        logger.info(
            f"Extracted {len(all_requirements)} total requirements, "
            f"{len(deduplicated)} after deduplication"
        )

        # Build consolidated metadata
        extraction_metadata = {
            "model": self.model,
            "tokens_used": {"input": total_input_tokens, "output": total_output_tokens},
            "transcript_length": len(transcript),
            "chunked": True,
            "num_chunks": len(chunks),
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
            "requirements_before_dedup": len(all_requirements),
            "requirements_after_dedup": len(deduplicated),
            "source_metadata": metadata or {},
        }

        return ExtractionResult(
            requirements=deduplicated,
            total_count=len(deduplicated),
            extraction_metadata=extraction_metadata,
        )

    def _parse_response(self, response_text: str) -> List[Dict]:
        """
        Parse Claude response, handling markdown code fences.

        Args:
            response_text: Raw response from Claude

        Returns:
            Parsed JSON data as list of dicts
        """
        # Strip markdown code fences if present
        response_text = response_text.strip()
        if response_text.startswith("```json"):
            response_text = response_text[7:]  # Remove ```json
        elif response_text.startswith("```"):
            response_text = response_text[3:]  # Remove ```
        if response_text.endswith("```"):
            response_text = response_text[:-3]  # Remove trailing ```
        response_text = response_text.strip()

        # Parse JSON
        return json.loads(response_text)

    def _deduplicate_requirements(self, requirements: List[Requirement]) -> List[Requirement]:
        """
        Remove duplicate requirements.

        Currently uses simple exact text matching. Future enhancement will use
        semantic similarity for better deduplication.

        Args:
            requirements: List of requirements to deduplicate

        Returns:
            Deduplicated list of requirements
        """
        seen = set()
        deduplicated = []

        for req in requirements:
            # Use requirement text as key (simple approach)
            key = req.requirement.strip().lower()

            if key not in seen:
                seen.add(key)
                deduplicated.append(req)
            else:
                logger.debug(f"Removed duplicate requirement: {req.requirement[:50]}...")

        return deduplicated

    def extract_requirements_batch(
        self, transcripts: List[Dict[str, Any]]
    ) -> List[ExtractionResult]:
        """
        Extract requirements from multiple transcripts in batch.

        Args:
            transcripts: List of dicts with 'text' and optional 'metadata' keys

        Returns:
            List of ExtractionResult objects, one per transcript

        Raises:
            ValueError: If transcripts list is empty or invalid
        """
        if not transcripts:
            raise ValueError("Transcripts list cannot be empty")

        logger.info(f"Extracting requirements from {len(transcripts)} transcripts")

        results = []
        for i, transcript_data in enumerate(transcripts):
            try:
                text = transcript_data.get("text")
                metadata = transcript_data.get("metadata", {})

                if not text:
                    logger.warning(f"Skipping transcript {i}: empty text")
                    continue

                result = self.extract_requirements(text, metadata)
                results.append(result)

            except Exception as e:
                logger.error(f"Failed to extract from transcript {i}: {e}")
                # Continue with remaining transcripts
                results.append(
                    ExtractionResult(
                        requirements=[],
                        total_count=0,
                        extraction_metadata={"error": str(e), "index": i},
                    )
                )

        logger.info(
            f"Batch extraction complete: {len(results)} results, "
            f"{sum(r.total_count for r in results)} total requirements"
        )

        return results

    def consolidate_requirements(self, results: List[ExtractionResult]) -> ExtractionResult:
        """
        Consolidate requirements from multiple extraction results.

        Combines requirements across multiple transcripts, removing duplicates
        and merging related requirements.

        Args:
            results: List of ExtractionResult objects to consolidate

        Returns:
            Single ExtractionResult with consolidated requirements

        Note:
            Current implementation is simple concatenation. Future enhancement
            will add deduplication and semantic merging.
        """
        logger.info(f"Consolidating {len(results)} extraction results")

        all_requirements = []
        total_tokens_input = 0
        total_tokens_output = 0

        for result in results:
            all_requirements.extend(result.requirements)

            # Aggregate token usage
            tokens = result.extraction_metadata.get("tokens_used", {})
            total_tokens_input += tokens.get("input", 0)
            total_tokens_output += tokens.get("output", 0)

        # Build consolidated metadata
        consolidated_metadata = {
            "model": self.model,
            "tokens_used": {"input": total_tokens_input, "output": total_tokens_output},
            "num_transcripts": len(results),
            "note": "Simple concatenation - deduplication not yet implemented",
        }

        logger.info(
            f"Consolidation complete: {len(all_requirements)} total requirements "
            f"from {len(results)} transcripts"
        )

        return ExtractionResult(
            requirements=all_requirements,
            total_count=len(all_requirements),
            extraction_metadata=consolidated_metadata,
        )
