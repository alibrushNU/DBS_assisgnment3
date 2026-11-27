# Validation record

Latest validation date: November 26, 2026 (Asia/Qyzylorda).

The suite was run against the dedicated Docker container
`dbs-csci341-a3-part1-db`, PostgreSQL 16.4, using the loopback port 55431 and
database `csci341_a3_part1`.

```text
python -m pytest -q --junitxml=build/test-results.xml
163 passed in 15.39s
```

The original 84 Part 1 cases continue to pass and cover:

- All 15 table counts, required roles, labels, child rows, statuses, named users,
  zero-count cases, multiple authors/versions/reviews, and future query inputs.
- Required keys, foreign keys, nullability, integer types, value checks,
  uniqueness, optional pool-membership FKs, and corresponding-author uniqueness.
- Rejection of self-reviews on insert, reviewer changes, paper changes, and
  authorship changes; valid completed-review insertion and update.
- Rejection of invalid scheduling, status/track changes, and moves of sessions
  or tracks between conferences; successful assignment and unassignment.
- Cascading paper deletion, session unassignment on deletion, and retaining
  independent reviewers when an empty conference is removed.
- Repeatable setup, schema ownership checks, connection-target guards,
  preservation of another schema's test table, identity-sequence advancement,
  and full rollback after an intentionally failed reset/seed transaction.

The 25 additional Part 2 cases cover all tasks 1–8, including every subquestion:

- Actual creation and insertion using the existing scripts, with empty-table and
  seeded counts, while retaining original database object IDs after rollback.
- Exact before/after results for all four mutations, both deadline branches,
  correct cascading deletions, exclusion cases, and independent rollback.
- Bound email/phrase inputs and correct projection, filtering, and ordering for
  all four simple queries.
- Distinct track counts, zero-review reviewers, empty conferences, NULL averages,
  review-weighted averages, repeated equal review scores, strict above-average
  comparisons including zero counts, and rounded acceptance-rate denominators.
- The real live view, exact columns and seed result, dynamic source changes using
  existing integrity helpers, and ordering across papers/sessions/conferences.
- Full demonstration numbering and repeatability, retention of rows and identity
  states, refusal of a non-seed dataset, and rollback after an output failure.

Tests leave the original fixture and the Part 2 view restored.
`build/test-results.xml` contains the machine-readable result. The full numbered
demo ran successfully using `python -m part2.demo --output build/part2-demo.txt`.
That transcript includes actual SQL, bound parameters, before/after results,
rollbacks, and the final view query.

The new `sql/assignment3-export.sql` was restored atomically into the guarded,
owned schema in this same dedicated database. A before/after comparison matched
all 15 tables, 98 rows, column definitions, primary/foreign keys, checks, indexes,
identity sequence values/called flags, the view definition, its schedule row, and
every Part 2 retrieval result. The original `sql/part1-export.sql` remains intact.

At completion of Part 2, SHA-256 comparisons confirmed that all original Part 1 Python files,
`sql/schema.sql`, `sql/seed.sql`, `compose.yaml`, and the original Part 1 export
are byte-for-byte unchanged. The test fixture now restores the new view, and the
old no-view assertion now checks that the original 15-table count remains intact.
No unrelated containers, databases, or projects were changed.

The 48 Part 3 cases cover full HTTP CRUD for users, papers, reviews, and sessions;
nested role/label/authorship/keyword/version replacement and removal; cascades;
missing records; duplicates and foreign keys; required integer/range validation;
both mandatory business rules including relevant updates; atomic rollback after
late child-record errors; cross-connection visibility of committed requests;
safe database errors; and fresh/idempotent deployment initialization.

FastAPI 0.165.0, Pydantic 2.14.4, Uvicorn 0.54.0, and HTTPX2 2.16.2 were tested.
The final suite has no warnings, and `pip check` reports no broken requirements.
The production Docker image `dbs-csci341-a3-api:local` built successfully. Real
HTTP tests passed for the local runner and Linux production image: `/docs`,
`/openapi.json`, `/health`, users/papers/reviews/sessions, and the schedule. Image
inspection verified non-root execution and exclusion of the local configuration
and development credentials. Details are in `build/part3-smoke.json`.

The temporary local HTTP process and API smoke-test container were removed. The
dedicated PostgreSQL container remains available. No unrelated Docker resources
were modified. Before free-hosting preparation, SHA-256 checks matched the
original Parts 1–2 files. The subsequent configuration changes are limited to
local credential loading in `part1/db.py` and `compose.yaml`, plus production
startup in `part3/serve.py`. Schema/seed/query/CRUD/integrity files and SQL exports
remain unchanged. The existing combined SQL export remains current.

The 6 free-deployment/packaging regression cases verify free-only plan settings,
initialization before listening, aborting startup on initialization failure,
absence of an embedded local password fallback, exclusion of local/generated
artifacts from the source archive, and rejection of a known leaked credential.

The rebuilt production image was also tested against a newly created temporary
local database. Its first start created all schema/seed/view objects. Swagger,
health, CRUD, and both mandatory rejection checks passed. A saved user edit
survived a container restart and then replacement by a new container. Image
credential checks passed. The temporary database and containers were removed,
and the original assignment database snapshot was unchanged. Results are saved
in `build/free-startup-check.json`.

`build/github-ready.zip` contains only allowlisted source files; `.env`, virtual
environments, caches, PDFs, transcripts, and generated SQL exports are excluded.
The known local database credential and recognizable token/private-key patterns
were checked before packaging. File hashes are in `build/github-manifest.json`.
The local password is preserved in ignored `.env`, not in publishable source.

No unresolved local implementation or test failures were found. Optional
minimum-participation rules are documented and tested in the seed rather than
globally enforced. Application checks require callers to use the provided
helpers; direct SQL and concurrent-writer race protection are outside those
checks, as permitted by the assignment. The API enforces the additional minimum
role/label/paper-child rules documented in `docs/part3.md`. Public deployment and
verification of the hosted URL/persistence are incomplete pending your GitHub
upload, Render login/authorization, and manual free-plan deployment. No public
hosting resources were created or deployed, and no provider charges were incurred.
