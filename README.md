# CSCI 341 Assignment 3 — Parts 1, 2, and local Part 3

PostgreSQL schema, deterministic sample data, SQLAlchemy setup, reusable integrity
checks, and database validation tests. Based on Alibi Boranbayev's submitted
Assignment 1 EER/UML diagrams, the Assignment 1 specification, and Assignment 3
Part 1 plus Appendix A. Part 2 adds all numbered SQL operations and the live
schedule view. The PDF submission, team-registration, video, and deployment
instructions are contextual requirements, not work performed here.

**Scope:** Parts 1 and 2 and the complete local Part 3 FastAPI application are
implemented. Free Render configuration and a checked GitHub source archive are
ready; GitHub upload and manual deployment remain. The original schema, seed,
queries, CRUD, and integrity behavior are preserved. Local credentials now come
from ignored `.env`, and production startup initializes a fresh database once.

## Deploy on free Render

Extract `build/github-ready.zip`, upload its contents to an empty GitHub
repository, then connect it through Render **New → Blueprint**. Review that
both resources are **Free** before deploying. Full minimal instructions and
public verification checks are in [deployment.md](docs/deployment.md). Use no
payment method to avoid usage-overage charges. No resources have been deployed.
The ZIP can be recreated with `python tools/prepare_github.py` after installing
the development dependencies.

## Run the FastAPI application locally

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
docker --config .docker-local compose -f compose.yaml up -d --wait
.\.venv\Scripts\python.exe -m part3.local
```

Swagger UI: **http://127.0.0.1:8010/docs**. The server starts when this command is
run and stops with Ctrl+C. It provides full CRUD for users, papers, reviews, and
sessions, including nested profiles, authorship, keywords, and versions. Existing
data is never reset at application startup. See [Part 3 endpoints and examples](docs/part3.md)
and the [prepared deployment configuration](docs/deployment.md).

## Run the complete numbered Part 2 demonstration

With the existing dedicated database running and the original seed loaded, use
this single command from the project directory:

```powershell
.\.venv\Scripts\python.exe -m part2.demo --output build/part2-demo.txt
```

The runner displays each task number, the actual SQL sent by SQLAlchemy, bound
parameters, and results. The UTF-8 transcript is also saved to
`build/part2-demo.txt`. Tasks 1–2 execute the existing creation/seed scripts inside
a transaction that rolls back, preserving the existing tables, sequences, and
view. Each independent mutation and retrieval gets its own transaction; mutations
show before/after rows and roll back. Task 8 commits only the live
`accepted_paper_schedule` view, leaving all 98 seed rows and sequence values
unchanged. Running the command again produces the same results.

The runner checks that the existing rows match the original seed. It refuses a
different dataset instead of silently replacing it. See [Part 2 details](docs/part2.md)
for the task mapping, parameters, aggregate design, and restoration instructions.

## Run locally (PowerShell)

Requires Python 3.13 and Docker Desktop with Linux containers. The tested stack is
Python 3.13.5, PostgreSQL 16.4, SQLAlchemy 2.0.58, psycopg 3.3.9, and pytest 9.2.0.
Part 3 uses FastAPI 0.165.0, Pydantic 2.14.4, Uvicorn 0.54.0, and HTTPX2 2.16.2
for HTTP tests. Production dependencies are listed separately in `requirements-web.txt`.
Install only the project dependencies; PDF tools used to inspect the supplied
documents are not needed to run this project.

For a **new local clone**, copy `.env.example` to `.env` and replace
`PART1_DB_PASSWORD=CHANGE_ME` with a new local password before starting Compose.
Keep `.env` private. The current workspace already has its original database
password in this ignored file; do not replace it when using the existing volume.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
docker --config .docker-local compose -f compose.yaml up -d --wait
.\.venv\Scripts\python.exe -m part1.setup
.\.venv\Scripts\python.exe -m part2.demo --output build/part2-demo.txt
.\.venv\Scripts\python.exe -m pytest -q --junitxml=build/test-results.xml
```

To restore the exact initial dataset, including identity sequences:

```powershell
.\.venv\Scripts\python.exe -m part1.setup --reset
.\.venv\Scripts\python.exe -m part2.view
```

Setup runs schema creation and seeding in one transaction. A failure preserves the
previous committed dataset. Running setup on an existing schema without `--reset`
reports that reset is required. Tests reset this project's schema before testing,
roll back individual mutation tests, and restore the original seed and view afterward.
Run tests serially; they share this one dedicated fixture database.

The dedicated target is:

| Setting | Value |
| --- | --- |
| Compose project | `dbs-csci341-a3-part1` |
| Container | `dbs-csci341-a3-part1-db` |
| Host / port | `127.0.0.1:55431` |
| Database | `csci341_a3_part1` |
| PostgreSQL role | `csci341_part1` |
| Local credentials | `PART1_DB_PASSWORD` in ignored `.env` or the environment; no password in source |
| Schema | `csci341_part1` |
| Persistent volume | `dbs-csci341-a3-part1_part1_data` |

Local Python code and Compose read the same `.env` password. The port binds only to loopback.
`--config .docker-local` isolates Docker CLI configuration from other projects.
Connection guards reject different hosts, ports, database names, roles, drivers,
and URL query overrides. `PART1_DATABASE_URL` may override the password while
retaining the permitted target. Reset additionally requires the schema ownership
comment. No command here operates on existing containers or other databases.

Stop only this project, retaining its data:

```powershell
docker --config .docker-local compose -f compose.yaml stop
```

## Files

| File | Purpose |
| --- | --- |
| `compose.yaml` | Dedicated, persistent local PostgreSQL service |
| `requirements.txt`, `pytest.ini`, `.gitignore` | Dependencies and development configuration |
| `sql/schema.sql` | All 15 tables, keys, references, checks, and optional constraints |
| `sql/seed.sql` | Deterministic 98-row fixture and identity-sequence initialization |
| `sql/part1-export.sql` | Retained original Part 1 export (without the view) |
| `sql/accepted_paper_schedule.sql` | Part 2 task 8 view definition |
| `sql/assignment3-export.sql` | Current combined export: original schema/seed plus the view |
| `part1/db.py` | Restricted connection configuration |
| `part1/setup.py` | Atomic creation/reset and per-table row counts |
| `part1/integrity.py` | Required application checks and transactional authorship replacement |
| `part2/operations.py` | Numbered, parameterized SQL for tasks 3.1–7 and the ordered view query |
| `part2/demo.py` | Complete tasks 1–8 runner with independent transaction rollback |
| `part2/reporting.py`, `part2/state.py`, `part2/view.py` | Actual SQL/result output, preservation checks, and view installation |
| `part3/` | FastAPI routes, schemas, transactional workflows, environment configuration, initialization, and servers |
| `Dockerfile`, `.dockerignore`, `render.yaml`, `.env.example` | Prepared deployment configuration without real hosting credentials |
| `tools/prepare_github.py` | Checked, allowlisted source ZIP and file manifest for manual GitHub upload |
| `tests/` | 84 Part 1 cases, 25 Part 2 cases, 48 Part 3 cases, and 6 deployment/packaging cases |
| `docs/schema.md` | Design mapping, keys, deletion actions, and enforcement matrix |
| `docs/seed-coverage.md` | Fixture counts, scenario mapping, and query inputs/results |
| `docs/part2.md` | Part 2 task mapping, operation semantics, and view restoration |
| `docs/part3.md`, `docs/deployment.md` | API operations, local startup, integrity rules, and pending hosting requirements |
| `docs/validation.md` | Recorded verification and limitations |
| `build/test-results.xml` | Generated JUnit test report (ignored by version control) |
| `build/part2-demo.txt` | Generated complete numbered SQL/parameter/result transcript |
| `build/github-ready.zip`, `build/github-manifest.json` | Prepared public-source package and hashes; generated locally |

## Plain SQL restoration

The canonical repeatable restoration is `python -m part1.setup --reset`, followed
by `python -m part2.view`. For a fresh dedicated database with no `csci341_part1`
schema, the combined export can also be
loaded using PostgreSQL's `psql`. It creates that schema, so it intentionally fails
if the schema already exists. The export contains no `DROP DATABASE`, no role
creation, or Part 3 objects. It includes the Part 2 view. Do not apply both the
export and the seed script.

Generated SQL exports are retained locally for submission and excluded from the
GitHub source ZIP. A new clone can recreate them using the commands below.

```powershell
docker --config .docker-local cp sql/assignment3-export.sql dbs-csci341-a3-part1-db:/tmp/assignment3-export.sql
docker --config .docker-local exec dbs-csci341-a3-part1-db psql -U csci341_part1 -d csci341_a3_part1 -v ON_ERROR_STOP=1 --single-transaction -f /tmp/assignment3-export.sql
```

To regenerate the combined export from the verified original seed, write inside the
container and copy it back. This avoids PowerShell output-encoding differences:

```powershell
.\.venv\Scripts\python.exe -m part2.demo --output build/part2-demo.txt
docker --config .docker-local exec dbs-csci341-a3-part1-db pg_dump -U csci341_part1 -d csci341_a3_part1 --schema=csci341_part1 --no-owner --no-privileges --file=/tmp/assignment3-export.sql
docker --config .docker-local cp dbs-csci341-a3-part1-db:/tmp/assignment3-export.sql sql/assignment3-export.sql
```

## Using the integrity helpers later

Call helpers in `part1/integrity.py` inside `with engine.begin() as connection:`.
`save_review`, `save_paper`, `save_session`, and `save_track` insert complete new
records or update an existing record by its primary key. Existing records accept
partial changes; validation uses their merged proposed state.
`replace_paper_authors` accepts the complete desired authorship list and uses a
savepoint so a failed replacement cannot erase the previous authors.

The helpers reject invalid changes; they do not silently unschedule papers.
Passing `session_id=None` explicitly can remove an assignment in the same paper
change. Direct SQL is still governed by database constraints but bypasses these
application checks. Use the helpers for future application writes. Advanced
concurrency handling and triggers are not required or implemented.
