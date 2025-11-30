"""
Vector Memory Engine using ChromaDB.

This module provides semantic memory for requirements and user stories,
enabling gap detection, conflict detection, and deduplication.

Key capabilities:
- Store requirements/stories with embeddings
- Semantic search: "Find requirements similar to X"
- Gap detection: Compare new vs existing backlog
- Conflict detection: Find contradicting requirements
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions

logger = logging.getLogger(__name__)


class VectorMemoryEngine:
    """
    Vector memory engine for semantic search over requirements and stories.

    Uses ChromaDB with sentence transformers for embeddings.
    """

    def __init__(
        self,
        persist_directory: str = "data/chroma",
        collection_name: str = "backlog_memory",
        embedding_model: str = "all-MiniLM-L6-v2",
    ):
        """
        Initialize vector memory engine.

        Args:
            persist_directory: Directory for ChromaDB persistence
            collection_name: Name of the collection
            embedding_model: Sentence transformer model for embeddings
        """
        self.persist_directory = persist_directory
        self.collection_name = collection_name

        # Ensure persist directory exists
        Path(persist_directory).mkdir(parents=True, exist_ok=True)

        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True,
            )
        )

        # Initialize embedding function (sentence transformers)
        self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=embedding_model
        )

        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            embedding_function=self.embedding_function,
            metadata={"description": "Backlog requirements and user stories"}
        )

        logger.info(
            f"VectorMemoryEngine initialized: {persist_directory}/{collection_name} "
            f"(model={embedding_model})"
        )

    def add_requirements(
        self,
        requirements: List[Dict[str, Any]],
        source: str = "transcript",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        """
        Add requirements to vector memory.

        Args:
            requirements: List of requirement dicts
            source: Source of requirements (transcript, jira, etc.)
            metadata: Additional metadata to store

        Returns:
            List of document IDs
        """
        if not requirements:
            return []

        # Prepare documents for ChromaDB
        documents = []
        metadatas = []
        ids = []

        for i, req in enumerate(requirements):
            # Create rich text representation for embedding
            req_text = req.get("requirement", "")
            req_type = req.get("type", "unknown")
            priority = req.get("priority_signal", "medium")
            impact = req.get("impact", "")

            # Combine fields for better semantic search
            doc_text = f"{req_text}\nType: {req_type}\nPriority: {priority}\nImpact: {impact}"

            documents.append(doc_text)

            # Store metadata
            meta = {
                "type": "requirement",
                "source": source,
                "requirement_type": req_type,
                "priority": priority,
                "requirement_text": req_text[:500],  # Truncate for storage
            }

            # Add custom metadata if provided
            if metadata:
                meta.update(metadata)

            metadatas.append(meta)

            # Generate ID
            doc_id = f"req_{source}_{i}_{hash(req_text) % 100000}"
            ids.append(doc_id)

        # Add to collection
        self.collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )

        logger.info(f"Added {len(requirements)} requirements to vector memory (source={source})")
        return ids

    def add_stories(
        self,
        stories: List[Dict[str, Any]],
        source: str = "generated",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        """
        Add user stories to vector memory.

        Args:
            stories: List of user story dicts
            source: Source of stories (generated, jira, etc.)
            metadata: Additional metadata to store

        Returns:
            List of document IDs
        """
        if not stories:
            return []

        # Prepare documents for ChromaDB
        documents = []
        metadatas = []
        ids = []

        for i, story in enumerate(stories):
            # Create rich text representation for embedding
            title = story.get("title", "")
            description = story.get("description", "")
            epic = story.get("epic_link", "")
            points = story.get("story_points", 0)

            # Combine fields for better semantic search
            doc_text = f"{title}\n{description}\nEpic: {epic}\nPoints: {points}"

            documents.append(doc_text)

            # Store metadata
            meta = {
                "type": "story",
                "source": source,
                "title": title[:200],  # Truncate for storage
                "epic": epic,
                "story_points": points,
            }

            # Add custom metadata if provided
            if metadata:
                meta.update(metadata)

            metadatas.append(meta)

            # Generate ID
            doc_id = f"story_{source}_{i}_{hash(title) % 100000}"
            ids.append(doc_id)

        # Add to collection
        self.collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )

        logger.info(f"Added {len(stories)} stories to vector memory (source={source})")
        return ids

    def search_similar_requirements(
        self,
        query: str,
        n_results: int = 5,
        source_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search for requirements similar to query.

        Args:
            query: Search query text
            n_results: Number of results to return
            source_filter: Optional filter by source

        Returns:
            List of similar requirements with metadata and distances
        """
        # Build where filter
        if source_filter:
            where = {
                "$and": [
                    {"type": "requirement"},
                    {"source": source_filter}
                ]
            }
        else:
            where = {"type": "requirement"}

        # Query collection
        results = self.collection.query(
            query_texts=[query],
            n_results=n_results,
            where=where
        )

        # Parse results
        similar_reqs = []
        if results["ids"] and results["ids"][0]:
            for i, doc_id in enumerate(results["ids"][0]):
                similar_reqs.append({
                    "id": doc_id,
                    "document": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "distance": results["distances"][0][i] if results.get("distances") else None,
                })

        logger.debug(f"Found {len(similar_reqs)} similar requirements for query: {query[:50]}...")
        return similar_reqs

    def search_similar_stories(
        self,
        query: str,
        n_results: int = 5,
        source_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search for stories similar to query.

        Args:
            query: Search query text
            n_results: Number of results to return
            source_filter: Optional filter by source

        Returns:
            List of similar stories with metadata and distances
        """
        # Build where filter
        if source_filter:
            where = {
                "$and": [
                    {"type": "story"},
                    {"source": source_filter}
                ]
            }
        else:
            where = {"type": "story"}

        # Query collection
        results = self.collection.query(
            query_texts=[query],
            n_results=n_results,
            where=where
        )

        # Parse results
        similar_stories = []
        if results["ids"] and results["ids"][0]:
            for i, doc_id in enumerate(results["ids"][0]):
                similar_stories.append({
                    "id": doc_id,
                    "document": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "distance": results["distances"][0][i] if results.get("distances") else None,
                })

        logger.debug(f"Found {len(similar_stories)} similar stories for query: {query[:50]}...")
        return similar_stories

    def find_gaps(
        self,
        new_requirements: List[Dict[str, Any]],
        threshold: float = 0.7,
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Find gaps between new requirements and existing memory.

        Args:
            new_requirements: New requirements to check
            threshold: Similarity threshold (0-1, lower = more similar)

        Returns:
            Tuple of (novel_requirements, covered_requirements)
            - novel: Requirements not covered by existing memory
            - covered: Requirements already covered
        """
        novel_reqs = []
        covered_reqs = []

        for req in new_requirements:
            req_text = req.get("requirement", "")

            # Search for similar existing requirements
            similar = self.search_similar_requirements(
                query=req_text,
                n_results=1,
                source_filter="jira"  # Only compare against existing JIRA backlog
            )

            if similar and similar[0]["distance"] < threshold:
                # Requirement is covered
                covered_reqs.append({
                    "requirement": req,
                    "covered_by": similar[0],
                    "similarity_score": 1 - similar[0]["distance"]
                })
            else:
                # Requirement is novel (gap)
                novel_reqs.append(req)

        logger.info(
            f"Gap analysis: {len(novel_reqs)} novel requirements, "
            f"{len(covered_reqs)} covered requirements"
        )

        return novel_reqs, covered_reqs

    def find_conflicts(
        self,
        requirements: List[Dict[str, Any]],
        threshold: float = 0.8,
    ) -> List[Dict[str, Any]]:
        """
        Find potentially conflicting requirements.

        Args:
            requirements: Requirements to check for conflicts
            threshold: Similarity threshold for considering conflicts

        Returns:
            List of conflict pairs with metadata
        """
        conflicts = []

        # For each requirement, find similar ones
        for i, req in enumerate(requirements):
            req_text = req.get("requirement", "")

            # Search for similar requirements
            similar = self.search_similar_requirements(
                query=req_text,
                n_results=5
            )

            # Check for conflicts (high similarity but different types/priorities)
            for sim in similar:
                # Skip self-matches
                if sim["id"].endswith(str(i)):
                    continue

                # Check if similar but conflicting
                similarity_score = 1 - sim["distance"]
                if similarity_score > threshold:
                    req_type = req.get("type")
                    sim_type = sim["metadata"].get("requirement_type")

                    req_priority = req.get("priority_signal")
                    sim_priority = sim["metadata"].get("priority")

                    # Flag if types or priorities differ significantly
                    if req_type != sim_type or req_priority != sim_priority:
                        conflicts.append({
                            "requirement_1": req,
                            "requirement_2": {
                                "text": sim["metadata"]["requirement_text"],
                                "type": sim_type,
                                "priority": sim_priority,
                            },
                            "similarity_score": similarity_score,
                            "conflict_reason": f"Similar content but different {('type' if req_type != sim_type else 'priority')}"
                        })

        logger.info(f"Found {len(conflicts)} potential conflicts")
        return conflicts

    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about vector memory.

        Returns:
            Dictionary with counts and metadata
        """
        # Get all items
        all_items = self.collection.get()

        # Count by type
        req_count = sum(1 for m in all_items["metadatas"] if m.get("type") == "requirement")
        story_count = sum(1 for m in all_items["metadatas"] if m.get("type") == "story")

        # Count by source
        sources = {}
        for m in all_items["metadatas"]:
            source = m.get("source", "unknown")
            sources[source] = sources.get(source, 0) + 1

        return {
            "total_items": len(all_items["ids"]),
            "requirements": req_count,
            "stories": story_count,
            "sources": sources,
            "collection_name": self.collection_name,
        }

    def clear(self) -> None:
        """Clear all data from collection."""
        # Delete and recreate collection
        self.client.delete_collection(name=self.collection_name)
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            embedding_function=self.embedding_function,
            metadata={"description": "Backlog requirements and user stories"}
        )
        logger.info(f"Cleared collection: {self.collection_name}")
