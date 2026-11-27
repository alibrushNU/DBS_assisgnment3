"""Assignment tasks 3.1–7. All filtering and aggregation runs in PostgreSQL."""
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Operation:
    number: str
    title: str
    sql: str
    parameters: dict = field(default_factory=dict)
    before_after_sql: str | None = None

    @property
    def is_mutation(self):
        return self.before_after_sql is not None


OPERATIONS = (
    Operation("3.1", "Update Arman's phone by email", """
        UPDATE app_user SET phone_number = :phone_number
        WHERE email = :email
        RETURNING user_id, given_name, surname, email, phone_number
    """, {"email": "arman.armanov@example.com", "phone_number": "+77773414141"}, """
        SELECT user_id, given_name, surname, email, phone_number
        FROM app_user WHERE email = :email ORDER BY user_id
    """),
    Operation("3.2", "Extend review deadlines in one conditional UPDATE", """
        WITH updated AS (
            UPDATE conference
            SET review_deadline = review_deadline + CASE
                WHEN city = :city THEN CAST(:astana_days AS integer)
                ELSE CAST(:other_days AS integer)
            END
            RETURNING conference_id, acronym, city, review_deadline
        )
        SELECT * FROM updated ORDER BY conference_id
    """, {"city": "Astana", "astana_days": 7, "other_days": 3}, """
        SELECT conference_id, acronym, city, review_deadline
        FROM conference ORDER BY conference_id
    """),
    Operation("4.1", "Delete Amina's withdrawn corresponding-author papers", """
        WITH deleted AS (
            DELETE FROM paper p
            WHERE p.status = :status AND EXISTS (
                SELECT 1 FROM paper_author pa
                JOIN app_user u ON u.user_id = pa.author_id
                WHERE pa.paper_id = p.paper_id AND pa.is_corresponding
                  AND u.email = :email
            )
            RETURNING p.paper_id, p.title, p.status
        )
        SELECT * FROM deleted ORDER BY paper_id
    """, {"email": "amina.aminova@example.com", "status": "withdrawn"}, """
        SELECT p.paper_id, p.title, p.status,
               (SELECT count(*) FROM paper_author a WHERE a.paper_id = p.paper_id) AS authors,
               (SELECT count(*) FROM paper_keyword k WHERE k.paper_id = p.paper_id) AS keywords,
               (SELECT count(*) FROM paper_version v WHERE v.paper_id = p.paper_id) AS versions,
               (SELECT count(*) FROM review r WHERE r.paper_id = p.paper_id) AS reviews
        FROM paper p ORDER BY p.paper_id
    """),
    Operation("4.2", "Delete empty sessions in Astana", """
        WITH deleted AS (
            DELETE FROM conference_session s
            USING conference c
            WHERE s.conference_id = c.conference_id AND c.city = :city
              AND NOT EXISTS (SELECT 1 FROM paper p WHERE p.session_id = s.session_id)
            RETURNING s.session_id, s.conference_id, s.title
        )
        SELECT * FROM deleted ORDER BY session_id
    """, {"city": "Astana"}, """
        SELECT s.session_id, s.conference_id, c.city, s.title,
               (SELECT count(*) FROM paper p WHERE p.session_id = s.session_id) AS paper_count
        FROM conference_session s JOIN conference c ON c.conference_id = s.conference_id
        ORDER BY s.session_id
    """),
    Operation("5.1", "Accepted papers and corresponding authors", """
        SELECT p.paper_id, p.title,
               u.given_name || ' ' || u.surname AS corresponding_author_name,
               u.email AS corresponding_author_email, t.name AS track_name,
               c.conference_id, c.acronym
        FROM paper p
        JOIN paper_author pa ON pa.paper_id = p.paper_id AND pa.is_corresponding
        JOIN app_user u ON u.user_id = pa.author_id
        JOIN track t ON t.track_id = p.track_id
        JOIN conference c ON c.conference_id = t.conference_id
        WHERE p.status = :status ORDER BY p.paper_id
    """, {"status": "accepted"}),
    Operation("5.2", "Case-insensitive abstract phrase search", """
        SELECT paper_id, title FROM paper
        WHERE abstract ILIKE :pattern ORDER BY paper_id
    """, {"pattern": "%machine learning%"}),
    Operation("5.3", "Selected paper's versions, highest number first", """
        SELECT version_no, file_location, uploaded_at FROM paper_version
        WHERE paper_id = :paper_id ORDER BY version_no DESC
    """, {"paper_id": 1}),
    Operation("5.4", "Experienced database reviewers in a conference pool", """
        SELECT r.reviewer_id, u.given_name || ' ' || u.surname AS full_name, u.email
        FROM reviewer r JOIN app_user u ON u.user_id = r.reviewer_id
        JOIN conference_reviewer cr ON cr.reviewer_id = r.reviewer_id
        WHERE cr.conference_id = :conference_id AND r.years_experience >= :minimum_years
          AND EXISTS (
              SELECT 1 FROM reviewer_expertise e
              WHERE e.reviewer_id = r.reviewer_id AND e.area_label = :expertise
          )
        ORDER BY r.reviewer_id
    """, {"conference_id": 1, "minimum_years": 3, "expertise": "Databases"}),
    Operation("6.1", "Distinct papers and authors for every track", """
        SELECT t.track_id, t.name AS track_name, t.conference_id,
               count(DISTINCT p.paper_id) AS paper_count,
               count(DISTINCT pa.author_id) AS author_count
        FROM track t
        LEFT JOIN paper p ON p.track_id = t.track_id
        LEFT JOIN paper_author pa ON pa.paper_id = p.paper_id
        GROUP BY t.track_id, t.name, t.conference_id ORDER BY t.track_id
    """),
    Operation("6.2", "Completed-review counts and averages for every reviewer", """
        SELECT r.reviewer_id, u.given_name || ' ' || u.surname AS full_name,
               count(rv.review_id) AS review_count, avg(rv.overall_score) AS average_score
        FROM reviewer r JOIN app_user u ON u.user_id = r.reviewer_id
        LEFT JOIN review rv ON rv.reviewer_id = r.reviewer_id
        GROUP BY r.reviewer_id, u.given_name, u.surname ORDER BY r.reviewer_id
    """),
    Operation("6.3", "Paper totals and review-weighted conference averages", """
        WITH paper_counts AS (
            SELECT t.conference_id, count(*) AS paper_count,
                   count(*) FILTER (WHERE p.status = :accepted) AS accepted_count
            FROM paper p JOIN track t ON t.track_id = p.track_id GROUP BY t.conference_id
        ), review_averages AS (
            SELECT t.conference_id, avg(r.overall_score) AS average_score
            FROM review r JOIN paper p ON p.paper_id = r.paper_id
            JOIN track t ON t.track_id = p.track_id GROUP BY t.conference_id
        )
        SELECT c.conference_id, c.acronym, coalesce(pc.paper_count, 0) AS paper_count,
               coalesce(pc.accepted_count, 0) AS accepted_count, ra.average_score
        FROM conference c
        LEFT JOIN paper_counts pc ON pc.conference_id = c.conference_id
        LEFT JOIN review_averages ra ON ra.conference_id = c.conference_id
        ORDER BY c.conference_id
    """, {"accepted": "accepted"}),
    Operation("6.4", "Reviewers above the all-reviewer average count", """
        WITH review_counts AS (
            SELECT r.reviewer_id, count(rv.review_id) AS review_count
            FROM reviewer r LEFT JOIN review rv ON rv.reviewer_id = r.reviewer_id
            GROUP BY r.reviewer_id
        ), overall AS (
            SELECT avg(review_count) AS overall_average FROM review_counts
        )
        SELECT rc.reviewer_id, u.given_name || ' ' || u.surname AS full_name,
               rc.review_count, o.overall_average
        FROM review_counts rc JOIN app_user u ON u.user_id = rc.reviewer_id
        CROSS JOIN overall o
        WHERE rc.review_count > o.overall_average ORDER BY rc.reviewer_id
    """),
    Operation("7", "Acceptance percentages among decided papers", """
        WITH decisions AS (
            SELECT c.conference_id, c.acronym,
                   count(p.paper_id) FILTER (WHERE p.status = :accepted) AS accepted_count,
                   count(p.paper_id) FILTER (WHERE p.status = :rejected) AS rejected_count
            FROM conference c LEFT JOIN track t ON t.conference_id = c.conference_id
            LEFT JOIN paper p ON p.track_id = t.track_id
            GROUP BY c.conference_id, c.acronym
        )
        SELECT conference_id, acronym, accepted_count, rejected_count,
               round(100.0 * accepted_count / nullif(accepted_count + rejected_count, 0), 2)
                   AS acceptance_rate
        FROM decisions ORDER BY conference_id
    """, {"accepted": "accepted", "rejected": "rejected"}),
)

BY_NUMBER = {operation.number: operation for operation in OPERATIONS}

# Task 8: ordering belongs to the SELECT, not to the stored view definition.
SCHEDULE_QUERY = """
    SELECT * FROM csci341_part1.accepted_paper_schedule
    ORDER BY conference_id, session_date, start_time, session_id, paper_id
"""
