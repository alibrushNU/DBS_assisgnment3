-- Part 2, task 8. A live database view; no duplicated result table.
CREATE OR REPLACE VIEW csci341_part1.accepted_paper_schedule AS
SELECT p.paper_id, p.title AS paper_title,
       c.conference_id, c.acronym, t.name AS track_name,
       s.session_id, s.title AS session_title, s.session_date,
       s.start_time, s.end_time, s.room_label,
       chair.given_name || ' ' || chair.surname AS chair_full_name,
       correspondent.given_name || ' ' || correspondent.surname AS corresponding_author_name,
       correspondent.email AS corresponding_author_email
FROM csci341_part1.paper p
JOIN csci341_part1.track t ON t.track_id = p.track_id
JOIN csci341_part1.conference c ON c.conference_id = t.conference_id
JOIN csci341_part1.conference_session s
  ON s.session_id = p.session_id AND s.conference_id = c.conference_id
JOIN csci341_part1.app_user chair ON chair.user_id = s.chair_id
JOIN csci341_part1.paper_author pa ON pa.paper_id = p.paper_id AND pa.is_corresponding
JOIN csci341_part1.app_user correspondent ON correspondent.user_id = pa.author_id
WHERE p.status = 'accepted';
