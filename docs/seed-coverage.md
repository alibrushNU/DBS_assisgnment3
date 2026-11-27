# Minimal fixture and query coverage

The fixture has **98 rows across 15 tables**. There are exactly 10 users, 10
papers, 11 versions, 10 completed reviews, and 3 conferences. Every remaining row
supports a required relationship, minimum participation, or scenario.

| Table | Rows | Reason |
| --- | ---: | --- |
| `app_user` | 10 | Requested total |
| `author` | 8 | Author-only users and the shared author/reviewer role |
| `author_research_area` | 8 | One label per author |
| `reviewer` | 3 | Two active reviewers and one with no reviews |
| `reviewer_expertise` | 3 | One label per reviewer |
| `conference` | 3 | Requested total; Astana and Almaty |
| `conference_host` | 3 | One required host per conference |
| `conference_reviewer` | 3 | One required pool member per conference |
| `track` | 3 | One required track per conference; track 3 is empty |
| `conference_session` | 2 | One populated and one empty Astana session |
| `paper` | 10 | Requested total and all five statuses |
| `paper_keyword` | 10 | One required keyword per paper |
| `paper_author` | 11 | One per paper plus a second author for paper 1 |
| `paper_version` | 11 | One per paper plus a second version for paper 1 |
| `review` | 10 | Requested total, including two reviews of paper 1 |

With ten users and at least one user in both roles, eleven role rows and eleven
profile-label rows are the minimum. Their allocation as eight authors and three
reviewers does not increase the total. Three conferences require three tracks,
hosts, and pool memberships. The empty-conference track also supplies the empty
track case, and both required session cases share conference 1. No separate
lookup objects or unnecessary relationship rows are added.

## Scenario map

| Requirement | Fixture |
| --- | --- |
| Author-only | Users 1 and 3–8 |
| Reviewer-only | Users 9 and 10 |
| Both roles | User 2, Amina Aminova |
| Arman | User 1, `arman.armanov@example.com`, initial phone `+77010000001` |
| Amina | User 2, `amina.aminova@example.com`, corresponding author of withdrawn papers 6 and 7 |
| Submitted | Paper 5 |
| Under review | Papers 4 and 10 |
| Accepted | Papers 1, 2, and 8 |
| Rejected | Papers 3 and 9 |
| Withdrawn | Papers 6 and 7; each has authorship, keyword, version, and review children |
| Multiple authors | Paper 1: Arman first/corresponding, Dana second |
| Multiple versions | Paper 1: versions 1 and 3; current version is 3 |
| Multiple reviews | Paper 1: reviewers 9 and 2, scores 5 and 4 |
| No reviews | Paper 5; reviewer 10 (Zhanna) |
| Author with no papers | User 8 (Nurlan) |
| Empty track / conference with no papers | Track 3 / conference 3 (`SNC26`) |
| Conference with no sessions | Conferences 2 and 3 |
| Accepted with a session | Paper 1 → session 1 → conference 1 |
| Accepted without a session | Papers 2 and 8 |
| Empty Astana session | Session 2 → conference 1 |
| Nonempty Astana session to preserve | Session 1, containing paper 1 |
| Geographic deadline branches | Conferences 1 and 3: Astana; conference 2: Almaty |

## Parameters and expected Part 2 results

The original fixture contract below is unchanged. Part 1 tests inspect the data;
Part 2 tests now execute the numbered SQL and view against PostgreSQL and verify
these expected results. Each operation runs independently against the original
seed. See [Part 2 implementation](part2.md).

| Item | Parameter / intended result |
| --- | --- |
| 3.1 | Email `arman.armanov@example.com`; user 1 is the sole target; requested new phone `+77773414141` differs from the seed |
| 3.2 | `Astana`; +7-day branch targets conferences 1 and 3, +3-day branch targets conference 2; resulting deadlines would be Nov 22, Nov 20, Nov 26, respectively |
| 4.1 | Email `amina.aminova@example.com`; paper IDs 6 and 7 qualify, with two rows removed from each dependent table; all eight other papers and parent entities survive |
| 4.2 | City `Astana`; only session 2 qualifies; session 1 and all three conferences survive |
| 5.1 | Accepted IDs 1, 2, 8, with exactly one corresponding author each |
| 5.2 | Phrase `machine learning`; IDs 1 and 8 match despite mixed/uppercase text |
| 5.3 | `paper_id=1`; versions returned in order 3, 1 |
| 5.4 | `conference_id=1`, expertise `Databases`, minimum experience 3; reviewer 9, Timur Karimov, qualifies (7 years) |
| 6.1 | Track 1: 7 papers, 6 distinct authors; track 2: 3 papers, 3 distinct authors; track 3: 0 and 0 |
| 6.2 | Reviewer 2: count 4, average 3.5; reviewer 9: count 6, average 17/6; reviewer 10: count 0, average NULL |
| 6.3 | Conference 1: 7 papers, 2 accepted, review average 21/7 = 3; conference 2: 3 papers, 1 accepted, review average 10/3; conference 3: 0 papers, 0 accepted, review average NULL |
| 6.4 | All-reviewer average is 10/3, including reviewer 10's zero; reviewers 2 and 9 exceed it |
| 7 | Conference 1: 2 accepted, 1 rejected, 66.67%; conference 2: 1 accepted, 1 rejected, 50.00%; conference 3: 0 accepted, 0 rejected, NULL |
| 8 | Schedule view has only paper 1/session 1/conference 1; chair Timur Karimov, corresponding author Arman Armanov; accepted unscheduled papers 2 and 8 excluded |

Paper 1 combines multiple authors, versions, and reviews so later join-based
aggregates must resist row multiplication. Dana appears on multiple papers in
track 1 so distinct-author counts differ from authorship counts. Under-review,
submitted, and withdrawn papers distinguish acceptance-rate denominators from
total-paper counts.
