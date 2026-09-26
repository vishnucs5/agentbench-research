from __future__ import annotations

import hashlib
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any
from uuid import UUID

import httpx
from packages.domain.config import get_settings
from packages.domain.models import Chunk, Paper
from packages.plagiarism.normalizer import TextNormalizer, create_normalizer
from packages.plagiarism.similarity import (
    SegmentSimilarityCalculator,
    SimilarityCalculator,
    SimilarityResult,
    create_similarity_calculator,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


@dataclass
class PlagiarismCheckResult:
    """Result of a plagiarism check."""

    overall_similarity: float
    originality_score: float
    total_matches: int
    matches: list[SimilarityResult]
    provider_used: str
    processing_time_ms: int
    error_message: str | None = None


class PlagiarismProvider(ABC):
    """Abstract base class for plagiarism detection providers."""

    @abstractmethod
    async def check(
        self,
        text: str,
        session: AsyncSession,
        user_id: UUID,
        project_id: UUID | None = None,
        threshold: float = 0.3,
    ) -> PlagiarismCheckResult:
        """Check text for plagiarism.

        Args:
            text: Text to check
            session: Database session
            user_id: ID of user requesting check
            project_id: Optional project ID to limit scope
            threshold: Minimum similarity threshold

        Returns:
            PlagiarismCheckResult with matches and scores
        """
        pass

    @abstractmethod
    def get_name(self) -> str:
        """Get provider name."""
        pass


class InternalProvider(PlagiarismProvider):
    """Internal plagiarism detection using local document comparison."""

    def __init__(
        self,
        normalizer: TextNormalizer | None = None,
        similarity_calculator: SimilarityCalculator | None = None,
        segment_calculator: SegmentSimilarityCalculator | None = None,
    ):
        self.normalizer = normalizer or create_normalizer()
        self.similarity_calculator = similarity_calculator or create_similarity_calculator(
            "tfidf_cosine"
        )
        self.segment_calculator = segment_calculator or SegmentSimilarityCalculator(
            create_similarity_calculator("jaccard", shingle_size=3)
        )

    def get_name(self) -> str:
        return "internal"

    async def check(
        self,
        text: str,
        session: AsyncSession,
        user_id: UUID,
        project_id: UUID | None = None,
        threshold: float = 0.3,
    ) -> PlagiarismCheckResult:
        start_time = time.perf_counter()

        if not text or not text.strip():
            return PlagiarismCheckResult(
                overall_similarity=0.0,
                originality_score=100.0,
                total_matches=0,
                matches=[],
                provider_used=self.get_name(),
                processing_time_ms=int((time.perf_counter() - start_time) * 1000),
            )

        # Normalize and segment the input text
        normalized_text = self.normalizer.normalize(text)
        segments = self.normalizer.split_into_segments(normalized_text)
        source_segments = [s.text for s in segments if len(s.text) >= 20]

        if not source_segments:
            return PlagiarismCheckResult(
                overall_similarity=0.0,
                originality_score=100.0,
                total_matches=0,
                matches=[],
                provider_used=self.get_name(),
                processing_time_ms=int((time.perf_counter() - start_time) * 1000),
            )

        # Fetch documents to compare against
        target_segments = await self._fetch_target_segments(session, project_id)

        if not target_segments:
            return PlagiarismCheckResult(
                overall_similarity=0.0,
                originality_score=100.0,
                total_matches=0,
                matches=[],
                provider_used=self.get_name(),
                processing_time_ms=int((time.perf_counter() - start_time) * 1000),
            )

        # Compare segments
        segment_matches = self.segment_calculator.calculate_segment_matches(
            source_segments, target_segments, threshold
        )

        # Deduplicate matches (same source text matched multiple times)
        unique_matches = self._deduplicate_matches(segment_matches)

        # Calculate overall similarity (max of segment matches)
        overall_similarity = max([m.similarity_score for m in unique_matches], default=0.0)
        originality_score = max(0.0, 100.0 - (overall_similarity * 100))

        processing_time = int((time.perf_counter() - start_time) * 1000)

        return PlagiarismCheckResult(
            overall_similarity=overall_similarity,
            originality_score=originality_score,
            total_matches=len(unique_matches),
            matches=unique_matches,
            provider_used=self.get_name(),
            processing_time_ms=processing_time,
        )

    async def _fetch_target_segments(
        self, session: AsyncSession, project_id: UUID | None = None
    ) -> list[str]:
        """Fetch text segments from stored documents for comparison."""
        # Query chunks from papers in the project (or all if no project)
        query = select(Chunk.text).join(Paper, Chunk.paper_id == Paper.id)

        if project_id:
            query = query.where(Paper.project_id == project_id)

        # Limit to avoid excessive memory usage
        query = query.limit(1000)

        result = await session.execute(query)
        chunks = result.scalars().all()

        # Normalize and segment each chunk
        all_segments = []
        for chunk_text in chunks:
            normalized = self.normalizer.normalize(chunk_text)
            segments = self.normalizer.split_into_segments(normalized)
            all_segments.extend([s.text for s in segments if len(s.text) >= 20])

        return all_segments

    def _deduplicate_matches(self, matches: list[SimilarityResult]) -> list[SimilarityResult]:
        """Remove duplicate matches based on source text."""
        seen_sources = set()
        unique = []

        for match in matches:
            # Create a hash of the source text for deduplication
            source_hash = hashlib.md5(match.source_text.encode()).hexdigest()[:16]
            if source_hash not in seen_sources:
                seen_sources.add(source_hash)
                unique.append(match)

        return unique


class ExternalAPIProvider(PlagiarismProvider):
    """External plagiarism detection API provider."""

    def __init__(
        self,
        api_key: str | None = None,
        api_url: str | None = None,
        timeout: float = 30.0,
    ):
        settings = get_settings()
        self.api_key = api_key or settings.plagiarism_api_key
        self.api_url = api_url or settings.plagiarism_api_url
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    def get_name(self) -> str:
        return "external_api"

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                headers={
                    "Authorization": f"Bearer {self.api_key}" if self.api_key else "",
                    "Content-Type": "application/json",
                },
            )
        return self._client

    async def check(
        self,
        text: str,
        session: AsyncSession,
        user_id: UUID,
        project_id: UUID | None = None,
        threshold: float = 0.3,
    ) -> PlagiarismCheckResult:
        start_time = time.perf_counter()

        if not self.api_key:
            return PlagiarismCheckResult(
                overall_similarity=0.0,
                originality_score=100.0,
                total_matches=0,
                matches=[],
                provider_used=self.get_name(),
                processing_time_ms=int((time.perf_counter() - start_time) * 1000),
                error_message="External API key not configured",
            )

        if not text or not text.strip():
            return PlagiarismCheckResult(
                overall_similarity=0.0,
                originality_score=100.0,
                total_matches=0,
                matches=[],
                provider_used=self.get_name(),
                processing_time_ms=int((time.perf_counter() - start_time) * 1000),
            )

        try:
            client = await self._get_client()
            response = await client.post(
                f"{self.api_url}/check",
                json={
                    "text": text,
                    "threshold": threshold,
                },
            )
            response.raise_for_status()
            data = response.json()

            # Parse response (format depends on external API)
            matches = []
            for match_data in data.get("matches", []):
                matches.append(
                    SimilarityResult(
                        similarity_score=match_data.get("similarity", 0.0),
                        confidence=match_data.get("confidence", 0.0),
                        matched_text=match_data.get("matched_text", ""),
                        source_text=match_data.get("source_text", ""),
                        match_start=match_data.get("match_start", 0),
                        match_end=match_data.get("match_end", 0),
                        source_start=match_data.get("source_start", 0),
                        source_end=match_data.get("source_end", 0),
                    )
                )

            overall_similarity = data.get("overall_similarity", 0.0)
            originality_score = data.get("originality_score", 100.0 - overall_similarity * 100)

            return PlagiarismCheckResult(
                overall_similarity=overall_similarity,
                originality_score=originality_score,
                total_matches=len(matches),
                matches=matches,
                provider_used=self.get_name(),
                processing_time_ms=int((time.perf_counter() - start_time) * 1000),
            )

        except httpx.HTTPStatusError as e:
            logger.error(f"External plagiarism API error: {e}")
            return PlagiarismCheckResult(
                overall_similarity=0.0,
                originality_score=100.0,
                total_matches=0,
                matches=[],
                provider_used=self.get_name(),
                processing_time_ms=int((time.perf_counter() - start_time) * 1000),
                error_message=f"API error: {e.response.status_code}",
            )
        except Exception as e:
            logger.error(f"External plagiarism API error: {e}")
            return PlagiarismCheckResult(
                overall_similarity=0.0,
                originality_score=100.0,
                total_matches=0,
                matches=[],
                provider_used=self.get_name(),
                processing_time_ms=int((time.perf_counter() - start_time) * 1000),
                error_message=str(e),
            )

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None


class MockProvider(PlagiarismProvider):
    """Mock provider for testing."""

    def __init__(self, simulate_matches: bool = True):
        self.simulate_matches = simulate_matches

    def get_name(self) -> str:
        return "mock"

    async def check(
        self,
        text: str,
        session: AsyncSession,
        user_id: UUID,
        project_id: UUID | None = None,
        threshold: float = 0.3,
    ) -> PlagiarismCheckResult:
        start_time = time.perf_counter()

        if not self.simulate_matches or not text:
            return PlagiarismCheckResult(
                overall_similarity=0.0,
                originality_score=100.0,
                total_matches=0,
                matches=[],
                provider_used=self.get_name(),
                processing_time_ms=int((time.perf_counter() - start_time) * 1000),
            )

        # Return a deterministic mock result based on text hash
        text_hash = hashlib.md5(text.encode()).hexdigest()
        hash_int = int(text_hash[:8], 16)

        # Simulate 30% chance of match
        has_match = (hash_int % 100) < 30

        if has_match:
            similarity = 0.3 + (hash_int % 70) / 100.0  # 0.3 to 1.0
            return PlagiarismCheckResult(
                overall_similarity=similarity,
                originality_score=100.0 - similarity * 100,
                total_matches=1,
                matches=[
                    SimilarityResult(
                        similarity_score=similarity,
                        confidence=similarity * 0.9,
                        matched_text=text[:200] + "..." if len(text) > 200 else text,
                        source_text="Mock source document text...",
                        match_start=0,
                        match_end=min(200, len(text)),
                        source_start=0,
                        source_end=50,
                    )
                ],
                provider_used=self.get_name(),
                processing_time_ms=int((time.perf_counter() - start_time) * 1000),
            )

        return PlagiarismCheckResult(
            overall_similarity=0.0,
            originality_score=100.0,
            total_matches=0,
            matches=[],
            provider_used=self.get_name(),
            processing_time_ms=int((time.perf_counter() - start_time) * 1000),
        )


class CombinedProvider(PlagiarismProvider):
    """Provider that combines internal and external checks (requirement 5)."""

    def __init__(
        self,
        internal: PlagiarismProvider | None = None,
        external: PlagiarismProvider | None = None,
    ):
        self.internal = internal or InternalProvider()
        self.external = external

    def get_name(self) -> str:
        return "combined"

    async def check(
        self,
        text: str,
        session: AsyncSession,
        user_id: UUID,
        project_id: UUID | None = None,
        threshold: float = 0.3,
    ) -> PlagiarismCheckResult:
        start = time.perf_counter()
        internal_result = await self.internal.check(text, session, user_id, project_id, threshold)

        if self.external is None:
            return internal_result

        try:
            external_result = await self.external.check(
                text, session, user_id, project_id, threshold
            )
        except Exception as e:
            logger.warning("External provider failed, using internal only: %s", e)
            return internal_result

        # If external had error, prefer internal
        if external_result.error_message:
            # Merge but mark external error, keep internal matches
            combined_matches = list(internal_result.matches)
            # Still include external matches if any despite error message? Prefer internal only.
            overall = max(internal_result.overall_similarity, external_result.overall_similarity)
            return PlagiarismCheckResult(
                overall_similarity=overall,
                originality_score=max(0.0, 100.0 - overall * 100),
                total_matches=len(combined_matches),
                matches=combined_matches,
                provider_used="combined",
                processing_time_ms=int((time.perf_counter() - start) * 1000),
                error_message=None,
            )

        # Merge matches, dedup by source text
        seen = set()
        merged: list[SimilarityResult] = []
        for m in list(internal_result.matches) + list(external_result.matches):
            key = hashlib.md5(m.source_text.encode()).hexdigest()
            if key not in seen:
                seen.add(key)
                merged.append(m)
        merged.sort(key=lambda x: x.similarity_score, reverse=True)
        overall = max(
            [m.similarity_score for m in merged]
            + [internal_result.overall_similarity, external_result.overall_similarity],
            default=0.0,
        )
        return PlagiarismCheckResult(
            overall_similarity=overall,
            originality_score=max(0.0, 100.0 - overall * 100),
            total_matches=len(merged),
            matches=merged,
            provider_used="combined",
            processing_time_ms=int((time.perf_counter() - start) * 1000),
        )


def create_provider(
    provider_type: str = "internal",
    **kwargs: Any,
) -> PlagiarismProvider:
    """Factory function to create plagiarism providers.

    Args:
        provider_type: One of "internal", "external_api", "mock", "combined"
        **kwargs: Additional arguments for the provider

    Returns:
        PlagiarismProvider instance
    """
    if provider_type == "internal":
        return InternalProvider(**kwargs)
    elif provider_type == "external_api":
        return ExternalAPIProvider(**kwargs)
    elif provider_type == "mock":
        return MockProvider(**kwargs)
    elif provider_type == "combined":
        return CombinedProvider(**kwargs)
    else:
        raise ValueError(f"Unknown provider type: {provider_type}")
