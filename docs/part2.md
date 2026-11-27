# Part 2: SQL operations through Python and SQLAlchemy

Requirements were read from pages 3–4 of
`CSCI-341-Assignment-3-Fall-2026.pdf`. All numbered tasks are implemented using
Python 3, SQLAlchemy 2, and the existing PostgreSQL 16.4 database. The 15-table
Part 1 schema and 98-row seed are unchanged.

## One-command demonstration

From the project directory, with the dedicated Docker service running:

```powershell
.\.venv\Scripts\python.exe -m part2.demo --output build/part2-demo.txt
```

The output contains tasks 1, 2, 3.1, 3.2, 4.1, 4.2, 5.1–5.4, 6.1–6.4, 7, and 8
in that order. Every executed assignment statement is displayed, with the bound
parameters and resulting rows. SQLAlchemy's `before_cursor_execute` event supplies
the actual driver SQL and parameter values; this is not a separately written SQL
description. NULL is printed explicitly. The same output is saved as UTF-8.

The supplied schema/seed files execute as SQL batches, as permitted for tasks
1–2; their complete SQL and resulting per-table counts are printed. The seed's
fixed literal values come from the unchanged supplied script. Runtime inputs in
numbered operations use bound parameters through `text()`. The view has a fixed
definition and no runtime inputs.

## Task implementation

| Task | Implementation and expected result on the original seed |
| --- | --- |
| 1 | Execute existing `sql/schema.sql` through SQLAlchemy; show all 15 newly created tables with zero rows |
| 2 | Execute existing `sql/seed.sql`; print counts for every table, totaling 98 rows |
| 3.1 | Bound email `arman.armanov@example.com` identifies user 1; set phone to `+77773414141`; show before/RETURNING/after |
| 3.2 | One conditional UPDATE uses PostgreSQL `date + integer`: 7 days for Astana, 3 elsewhere; all 3 conferences change; CTE sorts RETURNING rows |
| 4.1 | DELETE with EXISTS matches withdrawn papers whose corresponding author's email is `amina.aminova@example.com`; papers 6 and 7 and their four kinds of children cascade away; parent records and 8 other papers remain |
| 4.2 | DELETE uses conference city `Astana` and NOT EXISTS for assigned papers; removes only session 2, preserving session 1 and all conferences |
| 5.1 | Join accepted papers to their one corresponding author, track, and conference; IDs 1, 2, 8 |
| 5.2 | Bound ILIKE pattern `%machine learning%` on the abstract; IDs 1 and 8 |
| 5.3 | Bound `paper_id=1`; version numbers 3, 1 with file paths and UTC upload timestamps |
| 5.4 | Bound conference 1, expertise `Databases`, minimum experience 3; reviewer 9 once; EXISTS avoids expertise-label multiplication |
| 6.1 | LEFT JOIN all tracks with COUNT(DISTINCT paper_id) and COUNT(DISTINCT author_id); counts (7,6), (3,3), (0,0) |
| 6.2 | LEFT JOIN every reviewer to completed reviews; counts 4,6,0 and averages 3.5,17/6,NULL |
| 6.3 | Separate paper-count and review-average CTEs; conference counts 7/2,3/1,0/0 and review-weighted averages 3,10/3,NULL |
| 6.4 | Reviewer-count CTE includes zero-review reviewers; overall average 10/3; only reviewer 2 (4 reviews) and reviewer 9 (6) exceed it |
| 7 | Filter counts to accepted/rejected; `round(100.0 * accepted / nullif(accepted + rejected, 0), 2)` gives 66.67,50.00,NULL |
| 8 | Create/replace and query the live `csci341_part1.accepted_paper_schedule` view; one seed row for paper 1/session 1 |

The complete parameter and expected-result contract remains in
[seed-coverage.md](seed-coverage.md).

## Preserving the original database

The runner verifies the existing Part 1 ownership marker and reuses the existing
connection-target guard. It operates only in the dedicated database/container.

Tasks 1 and 2 share a transaction: temporarily drop the owned schema, execute the
original creation script, then execute the original seed script. PostgreSQL's
transactional DDL restores the original objects when this transaction rolls back.
The original table and view object IDs, table contents, and sequence values are
preserved. This executes real CREATE and INSERT statements while avoiding a
permanent rebuild of Part 1. The runner compares the inserted rows to the current
rows and refuses a non-seed dataset rather than overwriting it.

Each independent numbered mutation and retrieval then gets its own connection
transaction. Mutations print before/after rows; deletions also show every table's
before/after count to expose cascades and preservation of parent records. A
`finally` block rolls back even if execution or output fails. Consequently, no
later query observes an earlier update or deletion. The final view transaction
commits only after verifying that all original table rows and sequence values
remain identical. The view is the only intended persistent addition.

Run the demonstration and test suite serially against this local assignment
database. The creation demonstration temporarily locks its schema objects; it is
not a migration workflow for a concurrently used application.

## Aggregation and view semantics

Track counts use DISTINCT for both papers and authors; author appearances across
multiple papers count once per track. Reviewer averages use each review once.
Conference counts are aggregated independently of review averages, preventing
multi-review papers from multiplying paper totals. Review averages use all
review scores, including repeated equal values; neither `AVG(DISTINCT score)` nor
averaging per-paper averages would be correct. Keywords and versions do not join
these aggregates. Empty groups retain zero counts and NULL averages.

The schedule is a PostgreSQL view (`relkind='v'`), not a copied table or a
materialized view. It joins only accepted, session-assigned papers to their track,
conference, session, chair, and corresponding author. Unscheduled accepted papers
are excluded. Its SELECT explicitly orders by conference ID, session date,
start time, session ID, and paper ID. Changes to source rows appear immediately.

The existing Part 1 integrity helpers are retained unchanged. Numbered Part 2
mutations affect phone numbers, deadlines, and deletions; they do not introduce
review/authorship/assignment edits needing new validation. Tests use the existing
helpers for valid authorship, review, paper, and session changes when checking
deletion exclusions, aggregate edge cases, and live view behavior.

## View installation and restoration

Task 8 reads `sql/accepted_paper_schedule.sql`. To install/reinstall just the view:

```powershell
.\.venv\Scripts\python.exe -m part2.view
```

A Part 1 reset intentionally remains a Part 1 operation and drops the view along
with its schema. To restore the full current state, run:

```powershell
.\.venv\Scripts\python.exe -m part1.setup --reset
.\.venv\Scripts\python.exe -m part2.view
```

Alternatively, restore `sql/assignment3-export.sql` into the fresh dedicated
database using the README's `psql --single-transaction` command. That combined
export contains all 15 original tables, constraints, identities, seed rows, and
the view definition. The old `sql/part1-export.sql` is retained unchanged as the
original Part 1 artifact and does not include the view.

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest -q --junitxml=build/test-results.xml
```

The suite restores the original seed and installs the view before and after the
session. It contains the 84 Part 1 cases and 25 new Part 2 cases. The one original
assertion that no view exists now verifies the original 15 table count, allowing
the required Part 2 view. No Part 1 application, schema, seed, or Docker file was
changed.

Tests exercise actual query output, both deadline branches, mutation rollback,
bound inputs, corresponding-author/status deletion restrictions, preservation of
non-Astana empty sessions, distinct counts, zero/NULL groups, repeated equal
review scores, strict above-average comparisons, acceptance-rate denominators,
live view updates/order, repeated full demonstrations, and failed-output rollback.
Results are recorded in [validation.md](validation.md). The local Part 3
application now reuses these operations; see [part3.md](part3.md).
