SET search_path TO csci341_part1, pg_catalog;
INSERT INTO app_user (user_id, given_name, surname, email, affiliation, country, phone_number) VALUES
 (1, 'Arman', 'Armanov', 'arman.armanov@example.com', 'Steppe University', 'Kazakhstan', '+77010000001'),
 (2, 'Amina', 'Aminova', 'amina.aminova@example.com', 'Steppe University', 'Kazakhstan', '+77010000002'),
 (3, 'Dana', 'Sarsenova', 'dana.sarsenova@example.com', 'Alatau Institute', 'Kazakhstan', '+77010000003'),
 (4, 'Ilyas', 'Omarov', 'ilyas.omarov@example.com', 'Alatau Institute', 'Kazakhstan', '+77010000004'),
 (5, 'Leila', 'Asanova', 'leila.asanova@example.com', 'Steppe University', 'Kazakhstan', '+77010000005'),
 (6, 'Miras', 'Bekov', 'miras.bekov@example.com', 'Saryarka Institute', 'Kazakhstan', '+77010000006'),
 (7, 'Aliya', 'Nurgali', 'aliya.nurgali@example.com', 'Alatau Institute', 'Kazakhstan', '+77010000007'),
 (8, 'Nurlan', 'Sadykov', 'nurlan.sadykov@example.com', 'Saryarka Institute', 'Kazakhstan', '+77010000008'),
 (9, 'Timur', 'Karimov', 'timur.karimov@example.com', 'Steppe University', 'Kazakhstan', '+77010000009'),
 (10, 'Zhanna', 'Iskakova', 'zhanna.iskakova@example.com', 'Saryarka Institute', 'Kazakhstan', '+77010000010');
INSERT INTO author (author_id, orcid) VALUES
 (1, '0000-0002-1825-0097'), (2, NULL), (3, NULL), (4, NULL),
 (5, NULL), (6, NULL), (7, NULL), (8, NULL);
INSERT INTO author_research_area (author_id, area_label) VALUES
 (1, 'Databases'), (2, 'Databases'), (3, 'Machine Learning'), (4, 'Security'),
 (5, 'Distributed Systems'), (6, 'Networks'), (7, 'Machine Learning'), (8, 'Databases');
INSERT INTO reviewer (reviewer_id, years_experience) VALUES (2, 4), (9, 7), (10, 0);
INSERT INTO reviewer_expertise (reviewer_id, area_label) VALUES
 (2, 'Databases'), (9, 'Databases'), (10, 'Networks');
INSERT INTO conference (conference_id, name, acronym, description, city, country, start_date, end_date, submission_deadline, review_deadline) VALUES
 (1, 'Steppe Data Conference 2026', 'SDC26', 'Research on reliable data systems.', 'Astana', 'Kazakhstan', '2026-12-10', '2026-12-12', '2026-10-01', '2026-11-15'),
 (2, 'Alatau Computing Conference 2026', 'ACC26', 'Research on applied computing.', 'Almaty', 'Kazakhstan', '2026-12-15', '2026-12-16', '2026-10-01', '2026-11-17'),
 (3, 'Saryarka Networks Conference 2026', 'SNC26', 'A conference with no submitted papers yet.', 'Astana', 'Kazakhstan', '2026-12-20', '2026-12-21', '2026-10-01', '2026-11-19');
INSERT INTO conference_host (conference_id, host_name) VALUES
 (1, 'Steppe University'), (2, 'Alatau Institute'), (3, 'Saryarka Institute');
INSERT INTO conference_reviewer (conference_id, reviewer_id) VALUES (1, 9), (2, 2), (3, 10);
INSERT INTO track (track_id, conference_id, name, description, research_area, coordinator_id) VALUES
 (1, 1, 'Data Systems', 'Storage, learning, and reliable systems.', 'Databases', 9),
 (2, 2, 'Applied Computing', 'Applications of computing research.', 'Machine Learning', 2),
 (3, 3, 'Future Networks', 'An empty track for forthcoming submissions.', 'Networks', 10);
INSERT INTO conference_session (session_id, conference_id, title, session_date, start_time, end_time, room_label, chair_id) VALUES
 (1, 1, 'Data Systems Presentations', '2026-12-10', '09:00', '10:00', 'Room A', 9),
 (2, 1, 'Open Research Session', '2026-12-10', '11:00', '12:00', 'Room B', 9);
INSERT INTO paper (paper_id, track_id, title, abstract, submission_date, status, session_id) VALUES
 (1, 1, 'Learning Query Plans', 'Machine Learning improves query plan selection.', '2026-09-01', 'accepted', 1),
 (2, 1, 'Reliable Indexes', 'An evaluation of fault-tolerant database indexes.', '2026-09-02', 'accepted', NULL),
 (3, 1, 'Private Data Sharing', 'Privacy controls for shared research datasets.', '2026-09-03', 'rejected', NULL),
 (4, 1, 'Distributed Checkpoints', 'Checkpoint placement for distributed storage.', '2026-09-04', 'under review', NULL),
 (5, 1, 'Network Telemetry', 'Low-cost telemetry for data center networks.', '2026-09-05', 'submitted', NULL),
 (6, 1, 'Withdrawn Replication Study', 'An early replication study withdrawn by its authors.', '2026-09-06', 'withdrawn', NULL),
 (7, 1, 'Withdrawn Cache Study', 'An early cache study withdrawn after initial review.', '2026-09-07', 'withdrawn', NULL),
 (8, 2, 'Learning for Agriculture', 'Field trials using MACHINE LEARNING for crop forecasting.', '2026-09-08', 'accepted', NULL),
 (9, 2, 'Sensor Compression', 'Compression methods for agricultural sensors.', '2026-09-09', 'rejected', NULL),
 (10, 2, 'Edge Inference', 'Measuring inference latency on edge devices.', '2026-09-10', 'under review', NULL);
INSERT INTO paper_keyword (paper_id, keyword) VALUES
 (1, 'query optimization'), (2, 'indexing'), (3, 'privacy'), (4, 'checkpoints'),
 (5, 'telemetry'), (6, 'replication'), (7, 'caching'), (8, 'agriculture'),
 (9, 'compression'), (10, 'edge computing');
INSERT INTO paper_author (paper_id, author_id, author_position, is_corresponding) VALUES
 (1, 1, 1, true), (1, 3, 2, false), (2, 3, 1, true), (3, 4, 1, true),
 (4, 5, 1, true), (5, 6, 1, true), (6, 2, 1, true), (7, 2, 1, true),
 (8, 7, 1, true), (9, 1, 1, true), (10, 3, 1, true);
INSERT INTO paper_version (paper_id, version_no, file_location, uploaded_at, change_note) VALUES
 (1, 1, 'papers/1/v1.pdf', '2026-09-01 09:00:00+00', NULL),
 (1, 3, 'papers/1/v3.pdf', '2026-09-15 09:00:00+00', 'Revised experiments; version gaps are permitted.'),
 (2, 1, 'papers/2/v1.pdf', '2026-09-02 09:00:00+00', NULL),
 (3, 1, 'papers/3/v1.pdf', '2026-09-03 09:00:00+00', NULL),
 (4, 1, 'papers/4/v1.pdf', '2026-09-04 09:00:00+00', NULL),
 (5, 1, 'papers/5/v1.pdf', '2026-09-05 09:00:00+00', NULL),
 (6, 1, 'papers/6/v1.pdf', '2026-09-06 09:00:00+00', NULL),
 (7, 1, 'papers/7/v1.pdf', '2026-09-07 09:00:00+00', NULL),
 (8, 1, 'papers/8/v1.pdf', '2026-09-08 09:00:00+00', NULL),
 (9, 1, 'papers/9/v1.pdf', '2026-09-09 09:00:00+00', NULL),
 (10, 1, 'papers/10/v1.pdf', '2026-09-10 09:00:00+00', NULL);
INSERT INTO review (review_id, paper_id, reviewer_id, overall_score, recommendation, comments_for_authors, confidential_comments, review_submission_date) VALUES
 (1, 1, 9, 5, 'accept', 'Clear evaluation and strong results.', NULL, '2026-10-05'),
 (2, 1, 2, 4, 'accept', 'Useful approach; clarify the cost model.', 'Suitable for the main session.', '2026-10-06'),
 (3, 2, 9, 4, 'accept', 'The recovery experiments are convincing.', NULL, '2026-10-07'),
 (4, 3, 9, 2, 'reject', 'The privacy analysis needs more evidence.', NULL, '2026-10-08'),
 (5, 4, 9, 3, 'accept', 'Promising results with limited scale.', NULL, '2026-10-09'),
 (6, 6, 9, 1, 'reject', 'The replication baseline is incomplete.', NULL, '2026-10-10'),
 (7, 7, 9, 2, 'reject', 'Include additional cache workloads.', NULL, '2026-10-11'),
 (8, 8, 2, 5, 'accept', 'Strong field validation.', NULL, '2026-10-12'),
 (9, 9, 2, 2, 'reject', 'Compression comparisons need improvement.', NULL, '2026-10-13'),
 (10, 10, 2, 3, 'accept', 'Useful measurements; expand the discussion.', NULL, '2026-10-14');

-- Explicit IDs make the fixture stable; advance each identity for future inserts.
SELECT setval(pg_get_serial_sequence('app_user', 'user_id'), 10, true);
SELECT setval(pg_get_serial_sequence('conference', 'conference_id'), 3, true);
SELECT setval(pg_get_serial_sequence('track', 'track_id'), 3, true);
SELECT setval(pg_get_serial_sequence('conference_session', 'session_id'), 2, true);
SELECT setval(pg_get_serial_sequence('paper', 'paper_id'), 10, true);
SELECT setval(pg_get_serial_sequence('review', 'review_id'), 10, true);
