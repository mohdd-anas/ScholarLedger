"""Integration tests for OpenAlex API client and UI/sync routes."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.auth.security import hash_password
from app.models.faculty import Faculty, FacultyRole
from app.models.publication import Publication
from app.services.ingestion.openalex import (
    fetch_work_by_doi,
    fetch_works_by_orcid,
    search_works,
)


class TestOpenAlexClientAndRoutes:
    @pytest.mark.anyio
    async def test_search_works_parses_openalex_response(self):
        mock_payload = {
            "results": [
                {
                    "id": "https://openalex.org/W12345",
                    "title": "OpenAlex Metadata Integration",
                    "doi": "https://doi.org/10.1145/openalex.2024",
                    "publication_year": 2024,
                    "type": "journal-article",
                    "primary_location": {"source": {"display_name": "Journal of Open Science"}},
                    "authorships": [
                        {"author": {"display_name": "Alice Smith"}},
                        {"author": {"display_name": "Bob Jones"}},
                    ],
                },
                {
                    "id": "https://openalex.org/W99999",
                    "title": "Null Primary Location Paper",
                    "doi": None,
                    "publication_year": 2023,
                    "type": "posted-content",
                    "primary_location": None,
                    "authorships": [],
                },
            ]
        }

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=mock_payload)

        transport = httpx.MockTransport(handler)
        orig_client = httpx.AsyncClient

        with patch(
            "app.services.ingestion.openalex.httpx.AsyncClient",
            side_effect=lambda **kw: orig_client(transport=transport, **kw),
        ):
            works = await search_works("OpenAlex")

        assert len(works) == 2
        assert works[0]["title"] == "OpenAlex Metadata Integration"
        assert works[0]["doi"] == "10.1145/openalex.2024"
        assert works[0]["venue"] == "Journal of Open Science"
        assert works[0]["authors"] == "Alice Smith; Bob Jones"
        assert works[0]["source"] == "openalex"
        assert works[1]["venue"] == ""
        assert works[1]["type"] == "preprint"

    @pytest.mark.anyio
    async def test_fetch_works_by_orcid_and_doi(self):
        def handler(request: httpx.Request) -> httpx.Response:
            if "/authors" in request.url.path:
                return httpx.Response(200, json={"results": [{"id": "https://openalex.org/A1"}]})
            if "/works/https://doi.org/" in request.url.path:
                return httpx.Response(
                    200,
                    json={
                        "id": "https://openalex.org/W2",
                        "title": "DOI Lookup Paper",
                        "doi": "https://doi.org/10.1000/xyz",
                        "publication_year": 2024,
                        "type": "journal-article",
                        "primary_location": None,
                        "authorships": [],
                    },
                )
            return httpx.Response(
                200,
                json={
                    "results": [
                        {
                            "id": "https://openalex.org/W1",
                            "title": "ORCID Paper",
                            "doi": "https://doi.org/10.1000/orcid1",
                            "publication_year": 2024,
                            "type": "journal-article",
                            "primary_location": None,
                            "authorships": [],
                        }
                    ]
                },
            )

        transport = httpx.MockTransport(handler)
        orig_client = httpx.AsyncClient

        with patch(
            "app.services.ingestion.openalex.httpx.AsyncClient",
            side_effect=lambda **kw: orig_client(transport=transport, **kw),
        ):
            by_orcid = await fetch_works_by_orcid("0000-0001-2345-6789")
            by_doi = await fetch_work_by_doi("10.1000/xyz")

        assert len(by_orcid) == 1
        assert by_orcid[0]["title"] == "ORCID Paper"
        assert by_doi is not None
        assert by_doi["title"] == "DOI Lookup Paper"

    def test_openalex_search_and_import_routes(self, client, db_session):
        fac = Faculty(
            name="OpenAlex Tester",
            email="oa.tester@university.edu",
            department="CS",
            orcid_id="0000-0001-7777-8888",
            role=FacultyRole.FACULTY,
            password_hash=hash_password("password123!"),
        )
        db_session.add(fac)
        db_session.flush()

        client.post(
            "/login",
            data={"email": "oa.tester@university.edu", "password": "password123!"},
            follow_redirects=False,
        )

        mock_works = [
            {
                "title": "OpenAlex Live Search Paper",
                "authors": "OpenAlex Tester",
                "venue": "ICSE",
                "year": 2024,
                "doi": "10.1145/icse.2024.99",
                "type": "conference-paper",
                "source": "openalex",
            }
        ]
        with patch(
            "app.routes.publications.search_works",
            new=AsyncMock(return_value=mock_works),
        ):
            res = client.get("/publications/openalex?q=OpenAlex")
            assert res.status_code == 200
            assert "OpenAlex Live Search Paper" in res.text

        imp = client.post(
            "/publications/openalex/import",
            data={
                "title": "OpenAlex Live Search Paper",
                "authors": "OpenAlex Tester",
                "venue": "ICSE",
                "year": "2024",
                "doi": "10.1145/icse.2024.99",
                "pub_type": "conference-paper",
            },
            follow_redirects=False,
        )
        assert imp.status_code == 302

        stored = (
            db_session.query(Publication)
            .filter(Publication.owner_faculty_id == fac.id)
            .first()
        )
        assert stored is not None
        assert stored.doi == "10.1145/icse.2024.99"
