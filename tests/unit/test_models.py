"""Test SQLAlchemy models."""

from app.models import (
    Faculty,
    FacultyRole,
    MatchDecision,
    MatchMethod,
    MatchVerdict,
    Publication,
    PublicationSource,
    PublicationStatus,
    PublicationType,
    SyncRun,
    SyncStatus,
)


class TestFacultyModel:
    def test_create_faculty(self, db_session):
        faculty = Faculty(
            name="Dr. Alice Smith",
            email="alice@university.edu",
            department="Computer Science",
            orcid_id="0000-0001-2345-6789",
            role=FacultyRole.FACULTY,
            password_hash="$argon2id$v=19$m=65536,t=3,p=4$hash",
        )
        db_session.add(faculty)
        db_session.flush()

        assert faculty.id is not None
        assert faculty.name == "Dr. Alice Smith"
        assert faculty.role == FacultyRole.FACULTY
        assert faculty.orcid_id == "0000-0001-2345-6789"

    def test_faculty_unique_email(self, db_session):
        f1 = Faculty(name="A", email="same@u.edu", department="CS", password_hash="h")
        db_session.add(f1)
        db_session.flush()

        f2 = Faculty(name="B", email="same@u.edu", department="CS", password_hash="h")
        db_session.add(f2)
        try:
            db_session.flush()
            raise AssertionError("Should have raised IntegrityError")
        except Exception:
            db_session.rollback()

    def test_faculty_repr(self, db_session):
        faculty = Faculty(
            name="Dr. Bob",
            email="bob@university.edu",
            department="Physics",
            password_hash="hash",
        )
        db_session.add(faculty)
        db_session.flush()
        assert "Dr. Bob" in repr(faculty)


class TestPublicationModel:
    def test_create_publication(self, db_session):
        faculty = Faculty(
            name="Dr. Carol",
            email="carol@university.edu",
            department="Mathematics",
            password_hash="hash",
        )
        db_session.add(faculty)
        db_session.flush()

        pub = Publication(
            title="A Novel Approach to Quantum Computing",
            authors="Carol, D.; Eve, F.",
            venue="Nature Computing",
            year=2024,
            doi="10.1234/nc.2024.001",
            pub_type=PublicationType.JOURNAL_ARTICLE,
            department="Mathematics",
            status=PublicationStatus.DRAFT,
            source=PublicationSource.ORCID,
            owner_faculty_id=faculty.id,
            match_confidence=0.95,
        )
        db_session.add(pub)
        db_session.flush()

        assert pub.id is not None
        assert pub.owner_faculty_id == faculty.id
        assert pub.status == PublicationStatus.DRAFT
        assert pub.source == PublicationSource.ORCID

    def test_publication_coauthors(self, db_session):
        owner = Faculty(
            name="Dr. Owner",
            email="owner.co@university.edu",
            department="CS",
            password_hash="hash",
        )
        coauthor = Faculty(
            name="Dr. Coauthor",
            email="coauthor.co@university.edu",
            department="ECE",
            password_hash="hash",
        )
        db_session.add_all([owner, coauthor])
        db_session.flush()

        pub = Publication(
            title="Shared Paper",
            authors="Owner, D.; Coauthor, D.",
            owner_faculty_id=owner.id,
            source=PublicationSource.MANUAL,
        )
        pub.coauthors.append(coauthor)
        db_session.add(pub)
        db_session.flush()

        assert pub.coauthor_ids == [coauthor.id]
        assert pub.is_attributed_to(owner.id) is True
        assert pub.is_attributed_to(coauthor.id) is True
        assert pub in coauthor.coauthored_publications

    def test_publication_status_values(self):
        assert PublicationStatus.DRAFT.value == "draft"
        assert PublicationStatus.SUBMITTED.value == "submitted"
        assert PublicationStatus.VERIFIED.value == "verified"
        assert PublicationStatus.REJECTED.value == "rejected"

    def test_publication_source_values(self):
        assert PublicationSource.ORCID.value == "orcid"
        assert PublicationSource.OPENALEX.value == "openalex"
        assert PublicationSource.CROSSREF.value == "crossref"
        assert PublicationSource.SCHOLAR_EXPORT.value == "scholar_export"
        assert PublicationSource.MANUAL.value == "manual"


class TestMatchDecisionModel:
    def test_create_match_decision(self, db_session):
        faculty = Faculty(
            name="Dr. Dave",
            email="dave@university.edu",
            department="Chemistry",
            password_hash="hash",
        )
        db_session.add(faculty)
        db_session.flush()

        pub = Publication(
            title="Test Publication",
            authors="Dave, D.",
            owner_faculty_id=faculty.id,
            source=PublicationSource.MANUAL,
        )
        db_session.add(pub)
        db_session.flush()

        decision = MatchDecision(
            publication_id=pub.id,
            matched_by=MatchMethod.DOI,
            score=1.0,
            decision=MatchVerdict.ACCEPTED,
        )
        db_session.add(decision)
        db_session.flush()

        assert decision.id is not None
        assert decision.matched_by == MatchMethod.DOI
        assert decision.score == 1.0

    def test_match_method_values(self):
        assert MatchMethod.DOI.value == "doi"
        assert MatchMethod.TITLE.value == "title"
        assert MatchMethod.NAME.value == "name"


class TestSyncRunModel:
    def test_create_sync_run(self, db_session):
        run = SyncRun(
            source="orcid",
            records_fetched=50,
            records_merged=45,
            records_queued=5,
            status=SyncStatus.SUCCESS,
        )
        db_session.add(run)
        db_session.flush()

        assert run.id is not None
        assert run.records_fetched == 50
        assert run.status == SyncStatus.SUCCESS

    def test_sync_status_values(self):
        assert SyncStatus.RUNNING.value == "running"
        assert SyncStatus.SUCCESS.value == "success"
        assert SyncStatus.FAILED.value == "failed"
        assert SyncStatus.PARTIAL.value == "partial"

