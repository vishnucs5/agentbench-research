from __future__ import annotations

from .normalizer import TextNormalizer, create_normalizer
from .parser import DocumentParser, create_parser
from .providers import ExternalAPIProvider, InternalProvider, PlagiarismProvider, create_provider
from .schemas import (
    PlagiarismCheckRequest,
    PlagiarismCheckResponse,
    PlagiarismCheckStatus,
    PlagiarismMatchResponse,
    PlagiarismReportResponse,
    PlagiarismSourceType,
)
from .service import PlagiarismService, get_plagiarism_service
from .similarity import SimilarityCalculator, create_similarity_calculator

__all__ = [
    "DocumentParser",
    "create_parser",
    "TextNormalizer",
    "create_normalizer",
    "SimilarityCalculator",
    "create_similarity_calculator",
    "PlagiarismProvider",
    "InternalProvider",
    "ExternalAPIProvider",
    "create_provider",
    "PlagiarismService",
    "get_plagiarism_service",
    "PlagiarismCheckRequest",
    "PlagiarismCheckResponse",
    "PlagiarismMatchResponse",
    "PlagiarismReportResponse",
    "PlagiarismCheckStatus",
    "PlagiarismSourceType",
]
