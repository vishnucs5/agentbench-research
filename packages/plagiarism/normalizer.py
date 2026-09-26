from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class TextSegment:
    """Represents a segment of text (sentence or paragraph)."""

    text: str
    start_offset: int
    end_offset: int
    segment_type: str  # "sentence" or "paragraph"
    paragraph_index: int


class TextNormalizer:
    """Normalizes text for plagiarism detection.

    Handles:
    - Whitespace normalization
    - Punctuation consistency
    - Paragraph structure preservation
    - Sentence splitting
    """

    # Common abbreviations that shouldn't end sentences
    ABBREVIATIONS = {
        "e.g.",
        "i.e.",
        "etc.",
        "vs.",
        "et al.",
        "fig.",
        "figs.",
        "eq.",
        "eqs.",
        "ref.",
        "refs.",
        "sec.",
        "secs.",
        "ch.",
        "chs.",
        "vol.",
        "vols.",
        "no.",
        "nos.",
        "pp.",
        "p.",
        "dr.",
        "prof.",
        "mr.",
        "mrs.",
        "ms.",
        "sr.",
        "jr.",
        "ph.d.",
        "m.d.",
        "b.s.",
        "m.s.",
        "b.a.",
        "m.a.",
        "u.s.",
        "u.k.",
        "e.u.",
        "a.m.",
        "p.m.",
        "jan.",
        "feb.",
        "mar.",
        "apr.",
        "jun.",
        "jul.",
        "aug.",
        "sep.",
        "oct.",
        "nov.",
        "dec.",
        "mon.",
        "tue.",
        "wed.",
        "thu.",
        "fri.",
        "sat.",
        "sun.",
        "mon",
        "tue",
        "wed",
        "thu",
        "fri",
        "sat",
        "sun",
    }

    def __init__(
        self,
        preserve_paragraphs: bool = True,
        min_segment_length: int = 10,
        max_segment_length: int = 5000,
    ):
        self.preserve_paragraphs = preserve_paragraphs
        self.min_segment_length = min_segment_length
        self.max_segment_length = max_segment_length

    def normalize(self, text: str) -> str:
        """Normalize text for comparison.

        Args:
            text: Raw text

        Returns:
            Normalized text
        """
        if not text:
            return ""

        # Remove null bytes
        text = text.replace("\x00", "")

        # Normalize line endings
        text = text.replace("\r\n", "\n").replace("\r", "\n")

        # Normalize whitespace (but preserve paragraph breaks)
        if self.preserve_paragraphs:
            # Split into paragraphs first
            paragraphs = text.split("\n\n")
            normalized_paragraphs = []
            for para in paragraphs:
                # Normalize whitespace within paragraph
                para = re.sub(r"[ \t]+", " ", para)
                para = para.strip()
                if para:
                    normalized_paragraphs.append(para)
            text = "\n\n".join(normalized_paragraphs)
        else:
            # Full whitespace normalization
            text = re.sub(r"\s+", " ", text)
            text = text.strip()

        # Normalize unicode quotes and dashes
        text = text.replace("\u201c", '"').replace("\u201d", '"')
        text = text.replace("\u2018", "'").replace("\u2019", "'")
        text = text.replace("\u2013", "-").replace("\u2014", "-")
        text = text.replace("\u2026", "...")

        # Normalize multiple spaces
        text = re.sub(r" {2,}", " ", text)

        return text

    def split_into_segments(self, text: str) -> list[TextSegment]:
        """Split normalized text into sentences/segments.

        Args:
            text: Normalized text

        Returns:
            List of TextSegment objects
        """
        if not text:
            return []

        normalized = self.normalize(text)
        segments = []

        if self.preserve_paragraphs:
            # Split by paragraphs first, then sentences within each paragraph
            paragraphs = normalized.split("\n\n")
            current_offset = 0

            for para_idx, paragraph in enumerate(paragraphs):
                para_start = normalized.find(paragraph, current_offset)
                if para_start == -1:
                    para_start = current_offset

                sentence_segments = self._split_sentences(paragraph)
                for sent in sentence_segments:
                    if len(sent.text) >= self.min_segment_length:
                        segments.append(
                            TextSegment(
                                text=sent.text,
                                start_offset=para_start + sent.start_offset,
                                end_offset=para_start + sent.end_offset,
                                segment_type="sentence",
                                paragraph_index=para_idx,
                            )
                        )

                current_offset = para_start + len(paragraph) + 2  # +2 for \n\n
        else:
            # Split entire text into sentences
            sentence_segments = self._split_sentences(normalized)
            for sent in sentence_segments:
                if len(sent.text) >= self.min_segment_length:
                    segments.append(
                        TextSegment(
                            text=sent.text,
                            start_offset=sent.start_offset,
                            end_offset=sent.end_offset,
                            segment_type="sentence",
                            paragraph_index=0,
                        )
                    )

        return segments

    def _split_sentences(self, text: str) -> list[TextSegment]:
        """Split text into sentences using regex with abbreviation handling."""
        # Pattern to match sentence endings, avoiding abbreviations
        # This is a simplified version; for production, consider using NLTK or spaCy
        segments = []

        # First, protect abbreviations by temporarily replacing periods
        protected_text = text
        abbr_map = {}
        for i, abbr in enumerate(self.ABBREVIATIONS):
            if abbr in protected_text.lower():
                placeholder = f"__ABBR_{i}__"
                abbr_map[placeholder] = abbr
                protected_text = re.sub(
                    re.escape(abbr),
                    placeholder,
                    protected_text,
                    flags=re.IGNORECASE,
                )

        # Split on sentence endings: . ! ? followed by space and capital letter
        # or end of string
        sentence_pattern = r"(?<=[.!?])\s+(?=[A-Z])|(?<=[.!?])$"
        raw_sentences = re.split(sentence_pattern, protected_text)

        current_pos = 0
        for raw_sent in raw_sentences:
            # Restore abbreviations
            sent = raw_sent
            for placeholder, abbr in abbr_map.items():
                sent = sent.replace(placeholder, abbr)

            sent = sent.strip()
            if sent and len(sent) >= self.min_segment_length:
                # Find position in original text
                start = text.find(sent, current_pos)
                if start == -1:
                    start = current_pos
                end = start + len(sent)
                segments.append(
                    TextSegment(
                        text=sent,
                        start_offset=start,
                        end_offset=end,
                        segment_type="sentence",
                        paragraph_index=0,
                    )
                )
                current_pos = end

        return segments

    def get_paragraphs(self, text: str) -> list[str]:
        """Extract paragraphs from text."""
        normalized = self.normalize(text)
        return [p.strip() for p in normalized.split("\n\n") if p.strip()]


def create_normalizer(
    preserve_paragraphs: bool = True,
    min_segment_length: int = 10,
    max_segment_length: int = 5000,
) -> TextNormalizer:
    """Create a text normalizer instance."""
    return TextNormalizer(
        preserve_paragraphs=preserve_paragraphs,
        min_segment_length=min_segment_length,
        max_segment_length=max_segment_length,
    )
