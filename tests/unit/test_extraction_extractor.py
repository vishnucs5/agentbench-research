from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from packages.extraction.extractor import (
    EXTRACTION_PROMPTS,
    ClaimType,
    create_extraction_prompt,
    extract_all_claims,
)
from packages.extraction.schemas import DatasetClaim, ResearchProblemClaim


class TestExtractionPrompts:
    def test_all_claim_types_have_prompts(self):
        for claim_type in ClaimType:
            assert claim_type in EXTRACTION_PROMPTS
            prompt = EXTRACTION_PROMPTS[claim_type]
            assert prompt.system_prompt is not None
            assert prompt.user_prompt_template is not None
            assert prompt.output_schema is not None
            assert "{paper_text}" in prompt.user_prompt_template

    def test_prompt_schemas(self):
        assert EXTRACTION_PROMPTS[ClaimType.RESEARCH_PROBLEM].output_schema == ResearchProblemClaim
        assert EXTRACTION_PROMPTS[ClaimType.DATASET].output_schema == DatasetClaim


class TestCreateExtractionPrompt:
    def test_create_prompt(self):
        system, user, schema = create_extraction_prompt(ClaimType.DATASET, "Sample paper text")
        assert system is not None
        assert "Sample paper text" in user
        assert schema == DatasetClaim

    def test_invalid_claim_type(self):
        with pytest.raises(ValueError):
            create_extraction_prompt("invalid_type", "text")


class TestExtractAllClaims:
    @pytest.mark.asyncio
    async def test_extract_all_claims(self):
        mock_provider = AsyncMock()
        mock_response = MagicMock()
        mock_response.content = '{"name": "TestDataset", "description": "A test"}'
        mock_response.finish_reason = "stop"
        mock_response.usage = {"prompt_tokens": 100, "completion_tokens": 50}
        mock_response.model = "test-model"
        mock_provider.complete.return_value = mock_response

        results = await extract_all_claims(
            provider=mock_provider,
            paper_text="Test paper content",
            claim_types=[ClaimType.DATASET, ClaimType.MODEL],
        )

        assert ClaimType.DATASET in results
        assert ClaimType.MODEL in results
        assert mock_provider.complete.call_count == 2

    @pytest.mark.asyncio
    async def test_extract_all_claims_error_handling(self):
        mock_provider = AsyncMock()
        mock_provider.complete.side_effect = Exception("API Error")

        results = await extract_all_claims(
            provider=mock_provider,
            paper_text="Test paper",
            claim_types=[ClaimType.DATASET],
        )

        assert ClaimType.DATASET in results
        assert results[ClaimType.DATASET].finish_reason == "error"
        assert "Extraction failed" in results[ClaimType.DATASET].content

    @pytest.mark.asyncio
    async def test_extract_single_claim(self):
        from packages.extraction.extractor import extract_claim

        mock_provider = AsyncMock()
        mock_response = MagicMock()
        mock_response.content = '{"problem_statement": "Test"}'
        mock_response.finish_reason = "stop"
        mock_response.usage = {"prompt_tokens": 50}
        mock_response.model = "test-model"
        mock_provider.complete.return_value = mock_response

        result = await extract_claim(
            provider=mock_provider,
            claim_type=ClaimType.RESEARCH_PROBLEM,
            paper_text="Test paper",
        )

        assert result.content == '{"problem_statement": "Test"}'
        mock_provider.complete.assert_awaited_once()
