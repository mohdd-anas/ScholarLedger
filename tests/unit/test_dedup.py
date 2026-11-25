"""Test deduplication logic."""

from app.services.dedup import deduplicate_works


class TestDeduplication:
    def test_no_duplicates(self):
        works = [
            {"title": "Paper A", "doi": "10.1234/a"},
            {"title": "Paper B", "doi": "10.1234/b"},
        ]
        result = deduplicate_works(works)
        assert len(result) == 2

    def test_doi_duplicate(self):
        works = [
            {"title": "Paper A", "doi": "10.1234/a", "year": 2024},
            {"title": "Paper A (variant)", "doi": "10.1234/A", "year": None},
        ]
        result = deduplicate_works(works)
        assert len(result) == 1
        assert result[0]["year"] == 2024  # Keeps non-empty field

    def test_title_duplicate(self):
        works = [
            {"title": "A Novel Approach to Machine Learning", "doi": None},
            {"title": "a novel approach to machine learning", "doi": "10.1234/x"},
        ]
        result = deduplicate_works(works)
        assert len(result) == 1
        assert result[0]["doi"] == "10.1234/x"  # Merged

    def test_mixed_sources(self):
        works = [
            {"title": "Paper X", "doi": "10.1/x", "source": "orcid", "authors": ""},
            {"title": "Paper Y", "doi": "10.1/y", "source": "openalex", "authors": "Smith"},
            {
                "title": "Paper X Duplicate",
                "doi": "10.1/x",
                "source": "crossref",
                "authors": "Jones",
            },
        ]
        result = deduplicate_works(works)
        assert len(result) == 2

    def test_empty_input(self):
        result = deduplicate_works([])
        assert len(result) == 0
