"""Test matching engine."""

from app.services.matching import (
    find_best_match,
    match_doi,
    match_name,
    match_title,
    normalize_doi,
    normalize_title,
)


class TestNormalization:
    def test_normalize_doi(self):
        assert normalize_doi("10.1234/test") == "10.1234/test"
        assert normalize_doi("https://doi.org/10.1234/TEST") == "10.1234/test"
        assert normalize_doi("http://dx.doi.org/10.1234/Test") == "10.1234/test"
        assert normalize_doi(None) is None
        assert normalize_doi("") is None

    def test_normalize_title(self):
        result = normalize_title("A Novel Approach to Quantum Computing!")
        assert result == "a novel approach to quantum computing"

        # Strip accents
        result = normalize_title("Résumé of Naïve Approaches")
        assert "resume" in result
        assert "naive" in result


class TestDOIMatching:
    def test_exact_doi_match(self):
        is_match, score = match_doi("10.1234/test", "10.1234/test")
        assert is_match is True
        assert score == 1.0

    def test_doi_case_insensitive(self):
        is_match, score = match_doi("10.1234/TEST", "10.1234/test")
        assert is_match is True

    def test_doi_no_match(self):
        is_match, score = match_doi("10.1234/test", "10.5678/other")
        assert is_match is False
        assert score == 0.0

    def test_doi_none(self):
        is_match, score = match_doi(None, "10.1234/test")
        assert is_match is False


class TestTitleMatching:
    def test_exact_title_match(self):
        is_match, score = match_title(
            "Deep Learning for NLP", "Deep Learning for NLP"
        )
        assert is_match is True
        assert score == 100.0

    def test_similar_title_match(self):
        is_match, score = match_title(
            "A Novel Approach to Quantum Computing",
            "Novel Approach to Quantum Computing: A Study",
        )
        assert score > 70  # Should have high similarity

    def test_different_titles(self):
        is_match, score = match_title(
            "Machine Learning Basics",
            "Quantum Physics Advanced Topics",
        )
        assert score < 50


class TestNameMatching:
    def test_exact_name_match(self):
        is_match, score = match_name("Smith, A.", "Smith, A.")
        assert is_match is True

    def test_similar_name_match(self):
        is_match, score = match_name("Smith, Alice", "Smith, A.")
        assert score > 60


class TestFindBestMatch:
    def test_doi_match_wins(self):

        class FakePub:
            def __init__(self, pub_id, doi, title, authors):
                self.id = pub_id
                self.doi = doi
                self.title = title
                self.authors = authors

        existing = [
            FakePub(1, "10.1234/test", "Some Title", "Smith, A."),
            FakePub(2, "10.5678/other", "Other Title", "Jones, B."),
        ]
        incoming = {"doi": "10.1234/test", "title": "Some Title", "authors": "Smith, A."}

        method, score, matched_id = find_best_match(incoming, existing)
        assert method == "doi"
        assert score == 1.0
        assert matched_id == 1
