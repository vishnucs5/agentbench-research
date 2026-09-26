from __future__ import annotations

from packages.plagiarism.similarity import (
    JaccardSimilarity,
    MinHashSimilarity,
    SegmentSimilarityCalculator,
    TfidfCosineSimilarity,
    create_similarity_calculator,
)


class TestTfidfCosineSimilarity:
    def test_identical_texts_high_similarity(self):
        calc = TfidfCosineSimilarity()
        text = "The quick brown fox jumps over the lazy dog"
        results = calc.calculate(text, text)
        assert len(results) == 1
        assert results[0].similarity_score > 0.9

    def test_different_texts_low_similarity(self):
        calc = TfidfCosineSimilarity()
        text1 = "The quick brown fox jumps over the lazy dog"
        text2 = "Machine learning algorithms process data efficiently"
        results = calc.calculate(text1, text2, threshold=0.1)
        # Different topics should have low similarity
        if results:
            assert results[0].similarity_score < 0.5

    def test_empty_texts(self):
        calc = TfidfCosineSimilarity()
        assert calc.calculate("", "some text") == []
        assert calc.calculate("some text", "") == []
        assert calc.calculate("", "") == []

    def test_threshold_filtering(self):
        calc = TfidfCosineSimilarity()
        text1 = "Hello world test"
        text2 = "Hello world test"
        # Very high threshold should still include identical
        results = calc.calculate(text1, text2, threshold=0.99)
        assert len(results) == 1
        # Identical should be above 0.99, but we test low threshold
        results_low = calc.calculate(text1, text2, threshold=0.3)
        assert len(results_low) == 1

    def test_get_name(self):
        calc = TfidfCosineSimilarity()
        assert calc.get_name() == "tfidf_cosine"

    def test_create_via_factory(self):
        calc = create_similarity_calculator("tfidf_cosine")
        assert isinstance(calc, TfidfCosineSimilarity)


class TestJaccardSimilarity:
    def test_identical_texts(self):
        calc = JaccardSimilarity(shingle_size=3)
        text = "hello world"
        results = calc.calculate(text, text)
        assert len(results) == 1
        assert results[0].similarity_score == 1.0

    def test_completely_different(self):
        calc = JaccardSimilarity(shingle_size=3)
        text1 = "abc def"
        text2 = "xyz uvw"
        results = calc.calculate(text1, text2, threshold=0.1)
        # May be empty or low similarity
        if results:
            assert results[0].similarity_score < 0.3

    def test_partial_overlap(self):
        calc = JaccardSimilarity(shingle_size=3)
        text1 = "hello world test"
        text2 = "hello world"
        results = calc.calculate(text1, text2, threshold=0.1)
        assert len(results) == 1
        assert 0 < results[0].similarity_score < 1.0

    def test_empty(self):
        calc = JaccardSimilarity()
        assert calc.calculate("", "text") == []

    def test_get_name(self):
        assert JaccardSimilarity().get_name() == "jaccard"


class TestMinHashSimilarity:
    def test_identical_texts(self):
        calc = MinHashSimilarity(num_permutations=64, shingle_size=3)
        text = "hello world this is a test"
        results = calc.calculate(text, text, threshold=0.5)
        assert len(results) == 1
        assert results[0].similarity_score > 0.5

    def test_different_texts(self):
        calc = MinHashSimilarity(num_permutations=64)
        text1 = "hello world this is a test"
        text2 = "completely different content here"
        results = calc.calculate(text1, text2, threshold=0.5)
        # Likely no matches above 0.5 for different content
        # Accept empty or low
        if results:
            assert results[0].similarity_score < 0.8

    def test_empty(self):
        calc = MinHashSimilarity()
        assert calc.calculate("", "") == []

    def test_get_name(self):
        assert MinHashSimilarity().get_name() == "minhash"


class TestSegmentSimilarity:
    def test_segment_matches(self):
        seg_calc = SegmentSimilarityCalculator(
            JaccardSimilarity(shingle_size=3), min_segment_length=10
        )
        source = ["hello world this is a test", "another sentence here"]
        target = ["hello world this is a test", "different content"]
        results = seg_calc.calculate_segment_matches(source, target, threshold=0.5)
        assert len(results) >= 1
        # Best match should be identical sentence
        assert results[0].similarity_score == 1.0

    def test_no_matches_below_threshold(self):
        seg_calc = SegmentSimilarityCalculator(
            JaccardSimilarity(shingle_size=3), min_segment_length=10
        )
        source = ["hello world"]
        target = ["xyz abc def"]
        results = seg_calc.calculate_segment_matches(source, target, threshold=0.9)
        assert len(results) == 0

    def test_sorted_by_similarity(self):
        seg_calc = SegmentSimilarityCalculator(
            JaccardSimilarity(shingle_size=3), min_segment_length=5
        )
        source = ["hello world test", "hello world"]
        target = ["hello world test", "hello world", "hello"]
        results = seg_calc.calculate_segment_matches(source, target, threshold=0.1)
        # Should be sorted descending
        scores = [r.similarity_score for r in results]
        assert scores == sorted(scores, reverse=True)


class TestMatchingPassageDetection:
    def test_high_similarity_passage(self):
        calc = JaccardSimilarity(shingle_size=3)
        text1 = "The network intrusion detection system monitors traffic patterns"
        text2 = "The network intrusion detection system monitors traffic patterns"
        results = calc.calculate(text1, text2, threshold=0.3)
        assert len(results) == 1
        assert results[0].similarity_score > 0.7

    def test_paraphrased_passage(self):
        calc = TfidfCosineSimilarity()
        text1 = "The system detects intrusions by analyzing network traffic"
        text2 = "Network traffic is analyzed to detect intrusions by the system"
        results = calc.calculate(text1, text2, threshold=0.1)
        # Paraphrased should have some similarity but not 1.0
        if results:
            assert 0.1 < results[0].similarity_score < 1.0

    def test_confidence_score_range(self):
        calc = JaccardSimilarity()
        results = calc.calculate("hello world test", "hello world test")
        assert all(0 <= r.confidence <= 1 for r in results)

    def test_similarity_score_range(self):
        calc = TfidfCosineSimilarity()
        results = calc.calculate("test content here", "test content here")
        assert all(0 <= r.similarity_score <= 1 for r in results)
