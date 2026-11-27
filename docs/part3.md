# Part 3: FastAPI application with Swagger UI

Implemented and tested locally on November 26, 2026. The complete Part 3
requirements were read from page 5 of the Assignment 3 PDF, alongside the
mandatory integrity rules on page 2. Public deployment remains pending your
GitHub upload and manual deployment on the selected Free Render plans. No provider
resources have been created.

## Start locally

From the project directory, install the current dependencies and run:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
docker --config .docker-local compose -f compose.yaml up -d --wait
.\.venv\Scripts\python.exe -m part3.local
```

Open **http://127.0.0.1:8010/docs**. The root URL redirects to Swagger UI, and
`/openapi.json` provides the API definition. The local runner binds only to
loopback and reuses the existing Part 1 connection configuration. Stop it with
Ctrl+C. The database must already contain the original schema and Part 2 view;
the local application checks these at startup and never reseeds. The production
entry point now initializes a fresh database before starting, preserving all
existing data on subsequent starts.

The temporary HTTP verification servers used during implementation were stopped.
Run the command above to keep the local app available while using Swagger.

## Endpoints

| Method / path | Behavior |
| --- | --- |
| `GET /users` | List users with author/reviewer profiles and labels |
| `POST /users` | Create a user and its nested profiles/labels |
| `GET /users/{user_id}` | Read a complete user |
| `PUT /users/{user_id}` | Replace user fields and author/reviewer profiles |
| `DELETE /users/{user_id}` | Delete an unreferenced user and dependent profiles/labels |
| `GET /papers` | List papers with authors, keywords, versions, and current version number |
| `POST /papers` | Create a paper with all required related records |
| `GET /papers/{paper_id}` | Read a complete paper |
| `PUT /papers/{paper_id}` | Replace paper fields, authorship, keywords, and versions |
| `DELETE /papers/{paper_id}` | Delete a paper, cascading authorships, keywords, versions, and reviews |
| `GET /reviews`, `POST /reviews` | List or create completed reviews |
| `GET /reviews/{review_id}`, `PUT /reviews/{review_id}`, `DELETE /reviews/{review_id}` | Read, replace, or delete a completed review |
| `GET /sessions`, `POST /sessions` | List or create conference sessions |
| `GET /sessions/{session_id}`, `PUT /sessions/{session_id}`, `DELETE /sessions/{session_id}` | Read, replace, or delete a session; deletion unassigns its papers |
| `GET /reference/{relation}` | Read conferences, tracks, reviewer pools, hosts, research areas, or expertise areas |
| `GET /schedule` | Read the existing Part 2 schedule view in the required order |
| `GET /health` | Check database connectivity and return `{"status":"ok"}` |

List endpoints support `limit` (1–100, default 50) and `offset` (default 0), and
order by primary key. Reference relation names are `conferences`, `tracks`,
`reviewer-pools`, `hosts`, `research-areas`, and `expertise-areas`.

Swagger exposes request schemas and valid POST examples using the existing seed
IDs. There are no authentication, React, file-upload, or supporting-table write
endpoints. Paper file locations are strings; files are not uploaded.

## Request semantics and related records

PUT is full replacement, not a partial PATCH. A missing resource returns 404;
PUT never silently creates it. User bodies contain scalar user fields plus
`author` and `reviewer`. Each profile is either its nested object or NULL; NULL
removes that role if no foreign-key references prevent removal. At least one
profile must remain. Author research areas and reviewer expertise are nonempty
lists managed within these profiles.

Paper bodies contain scalar paper fields plus nonempty `authors`, `keywords`,
and `versions` lists. PUT replaces these lists; omitted entries are removed.
Authors include `author_id`, `author_position`, and `is_corresponding`. Versions
include their positive `version_no`, `file_location`, timezone-aware
`uploaded_at`, and optional `change_note`. Version gaps are valid; GET returns
`current_version_no` as the maximum number. Keep at least one version.

When using a GET result as a PUT body, omit its own primary key and, for papers,
`current_version_no`; they are read-only. Keep foreign keys such as `track_id`,
`paper_id` on reviews, and `session_id` on papers. Unknown body fields are
rejected to avoid accidental edits.

## Transactions, checks, and errors

Each HTTP request uses a SQLAlchemy transaction. The connection dependency uses
function scope, so it commits before a successful response is sent; failures
roll back parent and related-record changes together. This follows FastAPI's
[dependency lifecycle documentation](https://fastapi.tiangolo.com/tutorial/dependencies/dependencies-with-yield/).

Existing database constraints remain in force. `part1/integrity.py` is unchanged:

- Review creation and changes call `save_review`, rejecting reviewers who authored
  the proposed paper.
- Paper author replacement calls `replace_paper_authors`, rejecting additions
  that would turn an existing review into a self-review.
- Paper creation and changes call `save_paper`, validating acceptance and matching
  conference for every session assignment, including status and track edits.
- Session creation and changes call `save_session`, rejecting conference moves
  that would invalidate already-assigned papers.
- Optional pool-membership constraints remain database foreign keys, so chairs
  must belong to the relevant conference's reviewer pool.

The API additionally requires at least one role per user, nonempty profile labels,
at least one paper author/keyword/version, exactly one corresponding author,
nonblank required text, and valid local session times. Scores, experience,
positions, and version numbers are integers; fractional numbers and booleans
are rejected where integers are required. These checks apply to the API; raw SQL
has the original documented database enforcement limits.

| Status | Meaning |
| --- | --- |
| 201 | Created a resource and related records |
| 200 | Read or updated successfully |
| 204 | Deleted successfully |
| 404 | Requested resource does not exist |
| 409 | Duplicate value, missing referenced ID, or deletion/role removal blocked by dependents |
| 422 | Invalid request shape/value or business-rule violation |
| 503 | Database unavailable |

Errors contain clear `detail` text; database-constraint failures also identify
the constraint where available. Responses do not include raw SQL, connection
URLs, PostgreSQL error details, or passwords. Referenced-user deletion is rejected
instead of silently deleting unrelated papers or reviews.

## Demonstrate CRUD and rejected changes in Swagger

1. Use a POST example to create a user. GET the returned ID, PUT a complete body
   adding/changing its reviewer profile and labels, and DELETE it while unreferenced.
2. POST a paper using the example (author 1, track 1), then PUT its full body to
   change authors, keywords, and version numbers. GET shows the related records.
3. POST a review for that new paper by reviewer 9, GET it, PUT a new score/comment,
   and DELETE it. For rejection, attempt reviewer 2 on paper 6: HTTP 422 explains
   the self-review. Adding author 2 to paper 1 also returns 422 because reviewer 2
   already reviewed it.
4. POST a session using conference 1/chair 9. PUT its title/time, GET it, then
   DELETE it. To exercise assignments, PUT the newly created paper with status
   `accepted` and this session's ID; session deletion then unassigns the paper.
5. Attempt to assign submitted paper 5 to session 1: HTTP 422. Assigning accepted
   paper 8 (conference 2) to session 1 (conference 1) is also rejected. Changing
   session 1 to conference 2/chair 2 is rejected while paper 1 remains assigned.

Remove demonstration records afterward or deliberately restore the original seed
with the existing Part 1 reset and Part 2 view commands. Automated tests perform
these workflows without retaining test records.

## Tests and deployment status

```powershell
.\.venv\Scripts\python.exe -m pytest -q --junitxml=build/test-results.xml
```

There are 163 cases: 109 Parts 1–2 cases, 48 Part 3 cases, and 6 free-deployment
and source-packaging cases. The API
cases use FastAPI's HTTP TestClient with the real Docker PostgreSQL database.
They cover all CRUD endpoints, nested replacements/removals, cascades, mandatory
checks in both update directions, invalid inputs, rollback after late failures,
safe errors, actual cross-connection commits, and deployment initialization.

The Linux Docker image was built successfully. Real HTTP checks passed for both
the local runner and production image, including Swagger, OpenAPI, health, all
resource lists, and the schedule. Image inspection confirmed non-root execution,
absence of the local connection module/Compose file, and absence of development
credentials in application files. The temporary verification servers were removed.

See [deployment.md](deployment.md) for the prepared hosting configuration. Public
deployment and public-URL verification are the remaining Part 3 requirements.
