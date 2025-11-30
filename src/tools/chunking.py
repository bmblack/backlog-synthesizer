"""
Text chunking utilities for processing large documents.

This module provides intelligent chunking strategies for splitting large transcripts
and documents while preserving context and structure.
"""

import re
from dataclasses import dataclass
from typing import List, Optional

import tiktoken


@dataclass
class TextChunk:
    """A chunk of text with metadata."""

    text: str
    start_char: int
    end_char: int
    start_line: int
    end_line: int
    chunk_index: int
    total_chunks: int
    overlap_with_previous: int = 0
    overlap_with_next: int = 0


class TranscriptChunker:
    """
    Intelligent chunker for meeting transcripts and customer feedback.

    Preserves conversation structure by splitting at natural boundaries
    (speaker changes, timestamps, paragraphs) rather than arbitrary positions.
    """

    def __init__(
        self,
        chunk_size: int = 4000,
        chunk_overlap: int = 200,
        model: str = "gpt-4",
        preserve_structure: bool = True,
    ):
        """
        Initialize the chunker.

        Args:
            chunk_size: Target size in tokens per chunk
            chunk_overlap: Number of overlapping tokens between chunks
            model: Tokenizer model to use for counting tokens
            preserve_structure: If True, split at natural boundaries (timestamps, speakers)
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.preserve_structure = preserve_structure

        # Initialize tokenizer
        try:
            self.tokenizer = tiktoken.encoding_for_model(model)
        except KeyError:
            # Fallback to cl100k_base (used by GPT-4)
            self.tokenizer = tiktoken.get_encoding("cl100k_base")

    def count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        return len(self.tokenizer.encode(text))

    def chunk_text(self, text: str) -> List[TextChunk]:
        """
        Split text into overlapping chunks.

        Args:
            text: Text to chunk

        Returns:
            List of TextChunk objects with metadata
        """
        if not text or not text.strip():
            return []

        total_tokens = self.count_tokens(text)

        # If text fits in one chunk, return as-is
        if total_tokens <= self.chunk_size:
            return [
                TextChunk(
                    text=text,
                    start_char=0,
                    end_char=len(text),
                    start_line=1,
                    end_line=len(text.splitlines()),
                    chunk_index=0,
                    total_chunks=1,
                )
            ]

        # Split text based on structure
        if self.preserve_structure:
            segments = self._split_by_structure(text)
        else:
            segments = self._split_by_lines(text)

        # Group segments into chunks
        chunks = self._group_segments_into_chunks(segments, text)

        return chunks

    def _split_by_structure(self, text: str) -> List[str]:
        """
        Split text by structural boundaries (timestamps, speakers, paragraphs).

        Priority order:
        1. Timestamp patterns like [00:45], [02:15]
        2. Speaker patterns like "Alex Martinez (TechCorp):"
        3. Double newlines (paragraph breaks)
        4. Single newlines
        """
        # Pattern: [timestamp] Speaker (Company): or [timestamp] Speaker:
        pattern = r"(\[\d{1,2}:\d{2}\]\s+[A-Za-z\s]+(?:\([^)]+\))?\s*:)"

        # Split by pattern while keeping delimiters
        segments = re.split(pattern, text)

        # Recombine pattern with following text
        combined = []
        for i in range(0, len(segments), 2):
            if i + 1 < len(segments):
                combined.append(segments[i] + segments[i + 1])
            elif segments[i].strip():
                combined.append(segments[i])

        # If no structural splits found, fall back to paragraph splits
        if len(combined) <= 1:
            combined = text.split("\n\n")

        # Filter empty segments
        return [s.strip() for s in combined if s.strip()]

    def _split_by_lines(self, text: str) -> List[str]:
        """Simple line-based splitting."""
        return [line.strip() for line in text.splitlines() if line.strip()]

    def _group_segments_into_chunks(
        self, segments: List[str], original_text: str
    ) -> List[TextChunk]:
        """
        Group segments into chunks respecting token limits.

        Args:
            segments: List of text segments
            original_text: Original full text for character position tracking

        Returns:
            List of TextChunk objects
        """
        chunks = []
        current_chunk_segments = []
        current_tokens = 0

        for segment in segments:
            segment_tokens = self.count_tokens(segment)

            # If single segment exceeds chunk size, split it forcefully
            if segment_tokens > self.chunk_size:
                # Save current chunk if any
                if current_chunk_segments:
                    chunks.append(current_chunk_segments)
                    current_chunk_segments = []
                    current_tokens = 0

                # Split large segment into smaller pieces
                lines = segment.splitlines()
                for line in lines:
                    line_tokens = self.count_tokens(line)
                    if current_tokens + line_tokens > self.chunk_size:
                        if current_chunk_segments:
                            chunks.append(current_chunk_segments)
                            # Overlap: keep last segment
                            overlap_tokens = self.count_tokens(current_chunk_segments[-1])
                            if overlap_tokens < self.chunk_overlap:
                                current_chunk_segments = [current_chunk_segments[-1], line]
                                current_tokens = overlap_tokens + line_tokens
                            else:
                                current_chunk_segments = [line]
                                current_tokens = line_tokens
                        else:
                            current_chunk_segments = [line]
                            current_tokens = line_tokens
                    else:
                        current_chunk_segments.append(line)
                        current_tokens += line_tokens
                continue

            # Check if adding segment would exceed limit
            if current_tokens + segment_tokens > self.chunk_size and current_chunk_segments:
                # Save current chunk
                chunks.append(current_chunk_segments)

                # Start new chunk with overlap
                overlap_segments = []
                overlap_tokens = 0
                for seg in reversed(current_chunk_segments):
                    seg_tokens = self.count_tokens(seg)
                    if overlap_tokens + seg_tokens <= self.chunk_overlap:
                        overlap_segments.insert(0, seg)
                        overlap_tokens += seg_tokens
                    else:
                        break

                current_chunk_segments = overlap_segments + [segment]
                current_tokens = overlap_tokens + segment_tokens
            else:
                current_chunk_segments.append(segment)
                current_tokens += segment_tokens

        # Add final chunk
        if current_chunk_segments:
            chunks.append(current_chunk_segments)

        # Convert to TextChunk objects with metadata
        return self._create_text_chunks(chunks, original_text)

    def _create_text_chunks(
        self, chunk_segments: List[List[str]], original_text: str
    ) -> List[TextChunk]:
        """
        Create TextChunk objects with proper metadata.

        Args:
            chunk_segments: List of segment lists (each inner list is one chunk)
            original_text: Original full text

        Returns:
            List of TextChunk objects
        """
        text_chunks = []
        total_chunks = len(chunk_segments)

        for i, segments in enumerate(chunk_segments):
            chunk_text = "\n".join(segments)

            # Find character positions
            start_char = original_text.find(segments[0])
            if start_char == -1:
                start_char = 0
            end_char = start_char + len(chunk_text)

            # Calculate line numbers
            start_line = original_text[:start_char].count("\n") + 1
            end_line = original_text[:end_char].count("\n") + 1

            # Calculate overlaps
            overlap_prev = 0
            overlap_next = 0
            if i > 0:
                prev_segments = chunk_segments[i - 1]
                # Count overlapping segments
                for seg in segments:
                    if seg in prev_segments:
                        overlap_prev += len(seg)
                    else:
                        break

            if i < len(chunk_segments) - 1:
                next_segments = chunk_segments[i + 1]
                for seg in reversed(segments):
                    if seg in next_segments:
                        overlap_next += len(seg)
                    else:
                        break

            text_chunks.append(
                TextChunk(
                    text=chunk_text,
                    start_char=start_char,
                    end_char=end_char,
                    start_line=start_line,
                    end_line=end_line,
                    chunk_index=i,
                    total_chunks=total_chunks,
                    overlap_with_previous=overlap_prev,
                    overlap_with_next=overlap_next,
                )
            )

        return text_chunks


def estimate_chunk_count(text: str, chunk_size: int = 4000, model: str = "gpt-4") -> int:
    """
    Estimate how many chunks a text will be split into.

    Args:
        text: Text to estimate
        chunk_size: Target chunk size in tokens
        model: Model to use for tokenization

    Returns:
        Estimated number of chunks
    """
    try:
        tokenizer = tiktoken.encoding_for_model(model)
    except KeyError:
        tokenizer = tiktoken.get_encoding("cl100k_base")

    total_tokens = len(tokenizer.encode(text))
    return max(1, (total_tokens + chunk_size - 1) // chunk_size)
