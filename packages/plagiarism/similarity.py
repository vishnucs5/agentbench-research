from __future__ import annotations

import random
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


@dataclass
class SimilarityResult:
    """Result of a similarity comparison."""

    similarity_score: float  # 0.0 to 1.0
    confidence: float  # 0.0 to 1.0
    matched_text: str
    source_text: str
    match_start: int
    match_end: int
    source_start: int
    source_end: int


class SimilarityCalculator(ABC):
    """Abstract base class for similarity calculators."""

    @abstractmethod
    def calculate(self, text1: str, text2: str, threshold: float = 0.3) -> list[SimilarityResult]:
        """Calculate similarity between two texts.

        Args:
            text1: Source text (submitted content)
            text2: Target text (existing content)
            threshold: Minimum similarity score to report

        Returns:
            List of SimilarityResult objects
        """
        pass

    @abstractmethod
    def get_name(self) -> str:
        """Get the name of this similarity algorithm."""
        pass


class TfidfCosineSimilarity(SimilarityCalculator):
    """TF-IDF with Cosine Similarity for document-level comparison."""

    def __init__(
        self,
        ngram_range: tuple[int, int] = (1, 2),
        min_df: int = 1,
        max_df: float = 1.0,
        max_features: int = 10000,
    ):
        self.ngram_range = ngram_range
        self.min_df = min_df
        self.max_df = max_df
        self.max_features = max_features
        self._vectorizer: TfidfVectorizer | None = None

    def get_name(self) -> str:
        return "tfidf_cosine"

    def calculate(self, text1: str, text2: str, threshold: float = 0.3) -> list[SimilarityResult]:
        if not text1 or not text2:
            return []

        # For document-level similarity, we vectorize both texts
        texts = [text1, text2]
        vectorizer = TfidfVectorizer(
            ngram_range=self.ngram_range,
            min_df=self.min_df,
            max_df=self.max_df,
            max_features=self.max_features,
            stop_words="english",
        )

        try:
            tfidf_matrix = vectorizer.fit_transform(texts)
            # Cosine similarity between the two documents
            sim_matrix = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])
            similarity = min(float(sim_matrix[0, 0]), 1.0)

            if similarity >= threshold:
                return [
                    SimilarityResult(
                        similarity_score=similarity,
                        confidence=min(similarity * 1.2, 1.0),  # Heuristic confidence
                        matched_text=text1[:500] + "..." if len(text1) > 500 else text1,
                        source_text=text2[:500] + "..." if len(text2) > 500 else text2,
                        match_start=0,
                        match_end=len(text1),
                        source_start=0,
                        source_end=len(text2),
                    )
                ]
        except ValueError:
            # Handle case where vocabulary is empty
            pass

        return []


class JaccardSimilarity(SimilarityCalculator):
    """Jaccard Similarity for set-based comparison (shingles/n-grams)."""

    def __init__(self, shingle_size: int = 3):
        self.shingle_size = shingle_size

    def get_name(self) -> str:
        return "jaccard"

    def _get_shingles(self, text: str) -> set[str]:
        """Generate character shingles from text."""
        text = text.lower().replace(" ", "")
        if len(text) < self.shingle_size:
            return {text}
        return {text[i : i + self.shingle_size] for i in range(len(text) - self.shingle_size + 1)}

    def _jaccard(self, set1: set[str], set2: set[str]) -> float:
        """Calculate Jaccard similarity between two sets."""
        if not set1 and not set2:
            return 1.0
        if not set1 or not set2:
            return 0.0
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        return intersection / union if union > 0 else 0.0

    def calculate(self, text1: str, text2: str, threshold: float = 0.3) -> list[SimilarityResult]:
        if not text1 or not text2:
            return []

        shingles1 = self._get_shingles(text1)
        shingles2 = self._get_shingles(text2)

        similarity = self._jaccard(shingles1, shingles2)

        if similarity >= threshold:
            return [
                SimilarityResult(
                    similarity_score=similarity,
                    confidence=similarity,
                    matched_text=text1[:500] + "..." if len(text1) > 500 else text1,
                    source_text=text2[:500] + "..." if len(text2) > 500 else text2,
                    match_start=0,
                    match_end=len(text1),
                    source_start=0,
                    source_end=len(text2),
                )
            ]

        return []


class MinHashSimilarity(SimilarityCalculator):
    """MinHash for efficient approximate Jaccard similarity on large texts."""

    def __init__(
        self,
        num_permutations: int = 128,
        shingle_size: int = 3,
        seed: int = 42,
    ):
        self.num_permutations = num_permutations
        self.shingle_size = shingle_size
        self.seed = seed
        self._permutations: list[tuple[int, int]] | None = None
        self._init_permutations()

    def _init_permutations(self) -> None:
        """Initialize hash permutations for MinHash."""
        random.seed(self.seed)
        # Use large prime for modulo
        prime = 2**31 - 1
        self._permutations = [
            (random.randint(1, prime - 1), random.randint(0, prime - 1))
            for _ in range(self.num_permutations)
        ]

    def get_name(self) -> str:
        return "minhash"

    def _get_shingles(self, text: str) -> set[str]:
        """Generate character shingles from text."""
        text = text.lower().replace(" ", "")
        if len(text) < self.shingle_size:
            return {text}
        return {text[i : i + self.shingle_size] for i in range(len(text) - self.shingle_size + 1)}

    def _minhash_signature(self, shingles: set[str]) -> list[int]:
        """Compute MinHash signature for a set of shingles."""
        if not self._permutations:
            return []

        prime = 2**31 - 1
        # Hash each shingle to integer
        shingle_hashes = [hash(s) % prime for s in shingles]

        signature = []
        for a, b in self._permutations:
            min_hash = prime
            for h in shingle_hashes:
                # MinHash: min((a * h + b) % prime)
                val = (a * h + b) % prime
                if val < min_hash:
                    min_hash = val
            signature.append(min_hash)
        return signature

    def _estimate_jaccard(self, sig1: list[int], sig2: list[int]) -> float:
        """Estimate Jaccard similarity from MinHash signatures."""
        if not sig1 or not sig2 or len(sig1) != len(sig2):
            return 0.0
        matches = sum(1 for a, b in zip(sig1, sig2, strict=True) if a == b)
        return matches / len(sig1)

    def calculate(self, text1: str, text2: str, threshold: float = 0.3) -> list[SimilarityResult]:
        if not text1 or not text2:
            return []

        shingles1 = self._get_shingles(text1)
        shingles2 = self._get_shingles(text2)

        sig1 = self._minhash_signature(shingles1)
        sig2 = self._minhash_signature(shingles2)

        similarity = self._estimate_jaccard(sig1, sig2)

        if similarity >= threshold:
            return [
                SimilarityResult(
                    similarity_score=similarity,
                    confidence=similarity * 0.9,  # MinHash is approximate
                    matched_text=text1[:500] + "..." if len(text1) > 500 else text1,
                    source_text=text2[:500] + "..." if len(text2) > 500 else text2,
                    match_start=0,
                    match_end=len(text1),
                    source_start=0,
                    source_end=len(text2),
                )
            ]

        return []


class SegmentSimilarityCalculator:
    """Calculator that compares text segments (sentences) for detailed matching."""

    def __init__(
        self,
        segment_calculator: SimilarityCalculator,
        min_segment_length: int = 20,
    ):
        self.segment_calculator = segment_calculator
        self.min_segment_length = min_segment_length

    def calculate_segment_matches(
        self,
        source_segments: list[str],
        target_segments: list[str],
        threshold: float = 0.5,
    ) -> list[SimilarityResult]:
        """Compare each source segment against all target segments.

        Args:
            source_segments: List of text segments from submitted text
            target_segments: List of text segments from source documents
            threshold: Minimum similarity for a match

        Returns:
            List of SimilarityResult with segment-level matches
        """
        results = []

        for _i, src_seg in enumerate(source_segments):
            if len(src_seg) < self.min_segment_length:
                continue

            for _j, tgt_seg in enumerate(target_segments):
                if len(tgt_seg) < self.min_segment_length:
                    continue

                matches = self.segment_calculator.calculate(src_seg, tgt_seg, threshold)
                for match in matches:
                    # Update with segment info
                    match.matched_text = src_seg
                    match.source_text = tgt_seg
                    results.append(match)

        # Sort by similarity score descending
        results.sort(key=lambda x: x.similarity_score, reverse=True)
        return results


def create_similarity_calculator(
    algorithm: str = "tfidf_cosine",
    **kwargs: Any,
) -> SimilarityCalculator:
    """Factory function to create similarity calculators.

    Args:
        algorithm: One of "tfidf_cosine", "jaccard", "minhash"
        **kwargs: Additional arguments for the calculator

    Returns:
        SimilarityCalculator instance
    """
    if algorithm == "tfidf_cosine":
        return TfidfCosineSimilarity(**kwargs)
    elif algorithm == "jaccard":
        return JaccardSimilarity(**kwargs)
    elif algorithm == "minhash":
        return MinHashSimilarity(**kwargs)
    else:
        raise ValueError(f"Unknown similarity algorithm: {algorithm}")
