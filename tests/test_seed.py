"""Fixture assertions, including future query readiness, without Part 2 SQL."""
from collections import Counter
from decimal import Decimal


def test_minimal_exact_counts(data):
    assert {name: len(rows) for name, rows in data.items()} == {
        "app_user": 10, "author": 8, "author_research_area": 8,
        "reviewer": 3, "reviewer_expertise": 3, "conference": 3,
        "conference_host": 3, "conference_reviewer": 3, "track": 3,
        "conference_session": 2, "paper": 10, "paper_keyword": 10,
        "paper_author": 11, "paper_version": 11, "review": 10,
    }


def test_roles_labels_and_required_children(data):
    users = {r["user_id"] for r in data["app_user"]}
    authors = {r["author_id"] for r in data["author"]}
    reviewers = {r["reviewer_id"] for r in data["reviewer"]}
    assert users == authors | reviewers
    assert authors - reviewers and reviewers - authors and authors & reviewers == {2}
    assert authors == {r["author_id"] for r in data["author_research_area"]}
    assert reviewers == {r["reviewer_id"] for r in data["reviewer_expertise"]}
    conferences = {r["conference_id"] for r in data["conference"]}
    for table in ("conference_host", "conference_reviewer", "track"):
        assert conferences == {r["conference_id"] for r in data[table]}
    papers = {r["paper_id"] for r in data["paper"]}
    for table in ("paper_author", "paper_keyword", "paper_version"):
        assert papers == {r["paper_id"] for r in data[table]}
    corresponding = Counter(r["paper_id"] for r in data["paper_author"] if r["is_corresponding"])
    assert corresponding == Counter({p: 1 for p in papers})
    assert 8 not in {r["author_id"] for r in data["paper_author"]}  # Author with zero papers.


def test_pool_membership_self_reviews_and_scheduling(data):
    pool = {(r["conference_id"], r["reviewer_id"]) for r in data["conference_reviewer"]}
    for track in data["track"]:
        assert (track["conference_id"], track["coordinator_id"]) in pool
    for session in data["conference_session"]:
        assert (session["conference_id"], session["chair_id"]) in pool
    authorship = {(r["paper_id"], r["author_id"]) for r in data["paper_author"]}
    for review in data["review"]:
        assert (review["paper_id"], review["reviewer_id"]) not in authorship
        assert review["review_submission_date"] is not None
        assert review["comments_for_authors"].strip()
        assert 1 <= review["overall_score"] <= 5
        assert review["recommendation"] in {"accept", "reject"}
    tracks = {r["track_id"]: r for r in data["track"]}
    sessions = {r["session_id"]: r for r in data["conference_session"]}
    for paper in data["paper"]:
        if paper["session_id"] is not None:
            assert paper["status"] == "accepted"
            assert tracks[paper["track_id"]]["conference_id"] == sessions[paper["session_id"]]["conference_id"]


def test_named_users_and_future_mutation_targets(data):
    users = {r["email"]: r for r in data["app_user"]}
    arman = users["arman.armanov@example.com"]
    amina = users["amina.aminova@example.com"]
    assert (arman["given_name"], arman["surname"]) == ("Arman", "Armanov")
    assert arman["phone_number"] != "+77773414141"
    assert (amina["given_name"], amina["surname"]) == ("Amina", "Aminova")
    assert amina["user_id"] in {r["author_id"] for r in data["author"]}
    amina_corresponding = {r["paper_id"] for r in data["paper_author"] if r["author_id"] == amina["user_id"] and r["is_corresponding"]}
    targets = {r["paper_id"] for r in data["paper"] if r["status"] == "withdrawn"} & amina_corresponding
    assert targets == {6, 7}
    for table in ("paper_author", "paper_keyword", "paper_version", "review"):
        assert targets <= {r["paper_id"] for r in data[table]}
    astana = {r["conference_id"] for r in data["conference"] if r["city"] == "Astana"}
    assert astana == {1, 3}
    assert {r["conference_id"] for r in data["conference"] if r["city"] != "Astana"} == {2}
    assigned = {r["session_id"] for r in data["paper"]}
    assert {s["session_id"] for s in data["conference_session"] if s["conference_id"] in astana and s["session_id"] not in assigned} == {2}
    assert 1 in assigned


def test_statuses_multiple_authors_versions_and_simple_query_inputs(data):
    assert {r["status"] for r in data["paper"]} == {"submitted", "under review", "accepted", "rejected", "withdrawn"}
    assert {r["paper_id"] for r in data["paper"] if r["status"] == "accepted"} == {1, 2, 8}
    assert {r["paper_id"] for r in data["paper"] if "machine learning" in r["abstract"].lower()} == {1, 8}
    assert [(r["author_id"], r["author_position"]) for r in data["paper_author"] if r["paper_id"] == 1] == [(1, 1), (3, 2)]
    versions = sorted((r["version_no"] for r in data["paper_version"] if r["paper_id"] == 1), reverse=True)
    assert versions == [3, 1]  # Highest version, not number of versions; gaps allowed.
    pool = {r["reviewer_id"] for r in data["conference_reviewer"] if r["conference_id"] == 1}
    experts = {r["reviewer_id"] for r in data["reviewer_expertise"] if r["area_label"] == "Databases"}
    experienced = {r["reviewer_id"] for r in data["reviewer"] if r["years_experience"] >= 3}
    assert pool & experts & experienced == {9}
    assert {r["paper_id"] for r in data["paper"] if r["session_id"] is not None} == {1}
    assert {r["paper_id"] for r in data["paper"] if r["status"] == "accepted" and r["session_id"] is None} == {2, 8}


def test_future_aggregate_populations(data):
    # Python fixture oracle only: no assignment query, UPDATE, DELETE, or view implementation.
    for track_id, expected_papers, expected_authors in [(1, 7, 6), (2, 3, 3), (3, 0, 0)]:
        papers = {r["paper_id"] for r in data["paper"] if r["track_id"] == track_id}
        authors = {r["author_id"] for r in data["paper_author"] if r["paper_id"] in papers}
        assert (len(papers), len(authors)) == (expected_papers, expected_authors)
    counts = {r["reviewer_id"]: 0 for r in data["reviewer"]}
    counts.update(Counter(r["reviewer_id"] for r in data["review"]))
    assert counts == {2: 4, 9: 6, 10: 0}
    mean = sum(counts.values()) / len(counts)
    assert mean == 10 / 3
    assert {rid for rid, count in counts.items() if count > mean} == {2, 9}
    assert Counter(r["paper_id"] for r in data["review"])[1] == 2
    expected = {1: (7, 2, 1, 7, 21, Decimal("66.67")), 2: (3, 1, 1, 3, 10, Decimal("50.00")), 3: (0, 0, 0, 0, 0, None)}
    for conference_id, result in expected.items():
        tracks = {r["track_id"] for r in data["track"] if r["conference_id"] == conference_id}
        papers = [r for r in data["paper"] if r["track_id"] in tracks]
        paper_ids = {r["paper_id"] for r in papers}
        accepted = sum(r["status"] == "accepted" for r in papers)
        rejected = sum(r["status"] == "rejected" for r in papers)
        reviews = [r for r in data["review"] if r["paper_id"] in paper_ids]
        rate = (Decimal(100) * accepted / (accepted + rejected)).quantize(Decimal("0.01")) if accepted + rejected else None
        assert (len(papers), accepted, rejected, len(reviews), sum(r["overall_score"] for r in reviews), rate) == result
