from __future__ import annotations

from packages.plagiarism.normalizer import TextNormalizer, create_normalizer


class TestTextNormalization:
    def test_normalize_removes_extra_whitespace(self):
        n = TextNormalizer()
        text = "Hello    world\t\ttab  test"
        result = n.normalize(text)
        assert result == "Hello world tab test"

    def test_normalize_preserves_paragraphs(self):
        n = TextNormalizer(preserve_paragraphs=True)
        text = "Paragraph one.\n\nParagraph two.\n\nParagraph three."
        result = n.normalize(text)
        assert result == "Paragraph one.\n\nParagraph two.\n\nParagraph three."

    def test_normalize_handles_unicode_quotes(self):
        n = TextNormalizer()
        text = "\u201cHello\u201d and \u2018world\u2019"
        result = n.normalize(text)
        assert result == "\"Hello\" and 'world'"

    def test_normalize_handles_dashes(self):
        n = TextNormalizer()
        text = "Hello\u2013world\u2014test"
        result = n.normalize(text)
        assert "Hello-world-test" in result

    def test_normalize_removes_null_bytes(self):
        n = TextNormalizer()
        text = "Hello\x00world"
        result = n.normalize(text)
        assert "\x00" not in result
        assert result == "Helloworld"

    def test_normalize_empty(self):
        n = TextNormalizer()
        assert n.normalize("") == ""
        assert n.normalize("   ") == ""

    def test_normalize_line_endings(self):
        n = TextNormalizer()
        text = "Line1\r\nLine2\rLine3\nLine4"
        result = n.normalize(text)
        assert "\r" not in result

    def test_create_normalizer_factory(self):
        n = create_normalizer()
        assert isinstance(n, TextNormalizer)

    def test_normalize_collapses_multiple_newlines(self):
        n = TextNormalizer()
        text = "Para1\n\n\n\nPara2"
        result = n.normalize(text)
        # Should preserve paragraphs as \n\n not \n\n\n
        assert "\n\n\n" not in result


class TestSentenceSplitting:
    def test_split_simple_sentences(self):
        n = TextNormalizer()
        text = "This is sentence one. This is sentence two. This is sentence three."
        segments = n.split_into_segments(text)
        assert len(segments) >= 3
        assert all(s.segment_type == "sentence" for s in segments)

    def test_split_preserves_paragraph_structure(self):
        n = TextNormalizer(preserve_paragraphs=True, min_segment_length=5)
        text = "First paragraph sentence one. Sentence two.\n\nSecond paragraph. Another sentence."
        segments = n.split_into_segments(text)
        assert len(segments) >= 4
        # Check paragraph indexes
        para_indexes = {s.paragraph_index for s in segments}
        assert len(para_indexes) >= 2

    def test_split_handles_abbreviations(self):
        n = TextNormalizer(min_segment_length=5)
        text = "Dr. Smith went to the U.S. today. He met Mr. Jones."
        segments = n.split_into_segments(text)
        # Should not split on abbreviations like Dr.
        assert len(segments) >= 2

    def test_split_respects_min_length(self):
        n = TextNormalizer(min_segment_length=50)
        text = "Short. This is a very long sentence that exceeds fifty characters easily and should be kept."
        segments = n.split_into_segments(text)
        # Short sentence should be filtered
        assert all(len(s.text) >= 50 for s in segments)

    def test_split_empty(self):
        n = TextNormalizer()
        assert n.split_into_segments("") == []
        assert n.split_into_segments("   ") == []

    def test_get_paragraphs(self):
        n = TextNormalizer()
        text = "Para one content.\n\nPara two content.\n\nPara three."
        paras = n.get_paragraphs(text)
        assert len(paras) == 3
        assert paras[0] == "Para one content."
        assert paras[1] == "Para two content."

    def test_split_with_question_and_exclamation(self):
        n = TextNormalizer(min_segment_length=5)
        text = "Is this a question? Yes! This is an answer."
        segments = n.split_into_segments(text)
        # "Yes!" is 4 chars <5 so filtered; expect 2
        assert len(segments) == 2
        # With lower threshold, all 3 appear
        n2 = TextNormalizer(min_segment_length=3)
        segments2 = n2.split_into_segments(text)
        assert len(segments2) >= 3

    def test_split_offsets_correct(self):
        n = TextNormalizer(min_segment_length=5)
        text = "First sentence. Second sentence."
        segments = n.split_into_segments(text)
        assert len(segments) >= 2
        # Offsets should be non-negative and increasing
        for seg in segments:
            assert seg.start_offset >= 0
            assert seg.end_offset > seg.start_offset
