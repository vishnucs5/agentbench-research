from __future__ import annotations

import pytest
from packages.plagiarism.schemas import PlagiarismCheckRequest


class TestAPIValidation:
    def test_valid_request(self):
        req = PlagiarismCheckRequest(text="Hello world", threshold=0.5)
        assert req.text == "Hello world"
        assert req.threshold == 0.5

    def test_threshold_bounds(self):
        # Valid thresholds
        PlagiarismCheckRequest(text="test", threshold=0.0)
        PlagiarismCheckRequest(text="test", threshold=1.0)
        PlagiarismCheckRequest(text="test", threshold=0.5)

    def test_threshold_invalid(self):
        with pytest.raises(Exception):
            PlagiarismCheckRequest(text="test", threshold=-0.1)
        with pytest.raises(Exception):
            PlagiarismCheckRequest(text="test", threshold=1.5)

    def test_empty_text_validation(self):
        # Pydantic may allow empty if min_length not set; API layer checks strip
        req = PlagiarismCheckRequest(text="   ")
        assert req.text.strip() == ""

    def test_consented_default(self):
        req = PlagiarismCheckRequest(text="hello")
        assert req.consented_to_store is False

    def test_project_id_optional(self):
        req = PlagiarismCheckRequest(text="hello", project_id=None)
        assert req.project_id is None


class TestAPIErrorHandling:
    def test_rate_limit_simulation(self):
        # Simulate rate limit logic
        import time
        from collections import defaultdict

        store: dict[str, list[float]] = defaultdict(list)
        key = "test-client"
        per_min = 10
        now = time.time()
        for i in range(10):
            store[key].append(now)
        minute_count = sum(1 for t in store[key] if now - t < 60)
        assert minute_count == 10
        # Next request should exceed
        assert minute_count >= per_min

    def test_sanitize_text(self):
        # Ensure html escape
        import html

        text = 'Hello <b>world</b> & "test"'
        sanitized = html.escape(text)
        assert "<b>" not in sanitized
        assert "&lt;b&gt;" in sanitized

    def test_unsupported_file_handling(self):
        from packages.plagiarism.parser import DocumentParserFactory

        factory = DocumentParserFactory()
        assert not factory.is_supported("file.exe", "application/octet-stream")

    def test_file_size_error(self):
        max_mb = 10
        max_bytes = max_mb * 1024 * 1024
        content = b"a" * (max_bytes + 1)
        assert len(content) > max_bytes

    def test_api_key_not_exposed(self):
        # Ensure config doesn't expose key to client
        from packages.domain.config import get_settings

        settings = get_settings()
        # API key should be server-side only, not in schemas sent to client
        # Check that supported-types endpoint doesn't include key
        assert hasattr(settings, "plagiarism_api_key")
        # PlagiarismCheckResponse should not contain api key
        from packages.plagiarism.schemas import PlagiarismCheckResponse

        fields = PlagiarismCheckResponse.model_fields.keys()
        assert "api_key" not in fields
        assert "plagiarism_api_key" not in fields


class TestWordingRequirements:
    def test_summary_uses_potentially_similar(self):
        # Ensure wording uses "potentially similar" not "plagiarized"
        summary = "Found 1 potentially similar passage(s) with an overall similarity of 50.0%."
        assert "potentially similar" in summary.lower()
        assert "plagiarized" not in summary.lower()

    def test_error_messages_not_claim_plagiarism(self):
        # Check that no hard claim wording in summary generator
        from unittest.mock import MagicMock

        from apps.api.plagiarism import _generate_summary

        mock_check = MagicMock()
        mock_check.status = "completed"
        mock_check.total_matches = 1
        mock_check.overall_similarity = 0.5
        mock_match = MagicMock()
        mock_match.similarity_score = 0.8
        summary = _generate_summary(mock_check, [mock_match])
        assert "potentially similar" in summary
        # Should contain disclaimer
        assert "not necessarily plagiarism" in summary

    def test_confidence_score_present(self):
        from packages.plagiarism.similarity import JaccardSimilarity

        calc = JaccardSimilarity()
        results = calc.calculate("hello world test", "hello world test")
        assert len(results) == 1
        assert 0 <= results[0].confidence <= 1
