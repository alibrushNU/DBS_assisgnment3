# Free Render deployment — ready for your manual upload and deployment

Both resources in `render.yaml` explicitly use `plan: free`: one Docker web
service and one PostgreSQL 16 database in Frankfurt. There is no paid pre-deploy
hook, attached disk, worker, job, or paid plan. No GitHub or Render resources have
been created by the assistant.

## Steps you perform

1. Extract `build/github-ready.zip` into a new empty folder. Use its **contents**
   for GitHub, including `.gitignore` and `.dockerignore`; do not upload the ZIP,
   your workspace's `.env`, or the entire DBS directory.
2. Sign in to [GitHub](https://github.com/new). Create an empty repository named
   `csci341-assignment3` (Public is supported). Do not generate a README,
   `.gitignore`, or license. Choose **uploading an existing file** (or **Add file
   → Upload files**), drag in the extracted files/folders, and commit to `main`.
   Verify that `Dockerfile` and `render.yaml` are at the repository root.
   [GitHub upload instructions](https://docs.github.com/en/repositories/working-with-files/managing-files/adding-a-file-to-a-repository)
3. Sign in to [Render](https://dashboard.render.com/) using a free workspace with
   **no payment method**. Choose **New → Blueprint**, authorize GitHub access to
   the repository, connect `csci341-assignment3`, and select branch `main` and
   Blueprint path `render.yaml`.
4. Review the two proposed new resources. The web service and PostgreSQL database must
   **both say Free**, with no other resources or paid options. Then click
   **Deploy Blueprint**. Render supplies `DATABASE_URL` from the database
   automatically; you do not need to copy a password.
   [Render Blueprint instructions](https://render.com/docs/infrastructure-as-code)
5. Wait for both resources to be ready. Open the web service's assigned
   `https://…onrender.com` URL, then `/health` (expect `{"status":"ok"}`) and
   `/docs` (Swagger UI). Initialization happens before the server starts; the
   first deployment creates the original schema, seed, and view automatically.
6. In Swagger, run the checks below. For future code updates, commit the updated
   files to GitHub and use the web service's **Manual Deploy → Deploy latest
   commit**. Normal code auto-deploys are disabled. Do not reset the database.

GitHub/Render login and the GitHub authorization screen are your next manual
authentication steps. Do not send passwords, access tokens, or database URLs in
chat. If Render asks for a payment method, presents a nonzero resource charge,
or cannot provide the Free database, stop instead of choosing a paid option.

To stay within the requested no-charge setup, leave the payment method unset:
Render can bill bandwidth/build overages when a payment method is present; without
one it suspends services or builds at the free limits. Free PostgreSQL lasts 30
days and is limited to one active instance per workspace. Do not delete an
unrelated database or upgrade resources to get around that limit.
[Render free-tier limits](https://render.com/docs/free)

## Check the public deployment

- **CRUD and persistence:** POST `/users` with its Swagger example, record the
  returned `user_id`, GET it, and PUT a changed phone number using a complete
  request body without `user_id`. Manually redeploy the web service and GET the
  same ID: the edit must remain. DELETE that test user afterward.
- **Self-review rejection:** POST `/reviews` with its example, changing
  `paper_id` to `6` and `reviewer_id` to `2`. Expect HTTP 422.
- **Invalid assignment rejection:** POST `/papers` with its example, setting
  `session_id` to `1` while leaving `status` as `submitted`. Expect HTTP 422.
- **Schedule:** GET `/schedule` returns the seed's scheduled paper. All existing
  users/papers/reviews/sessions CRUD routes remain available through `/docs`.

Cold starts are expected. Data is held in the separate PostgreSQL service, so
restarting or replacing the web container does not lose it. This persistence
lasts until the free database expires or is deleted, not indefinitely.

## Configuration and source safety

`Dockerfile` starts `python -m part3.serve`. That entry point runs the existing
transactional initializer before Uvicorn. The initializer seeds only when the
schema is absent, preserves existing records on later starts, and rejects an
unexpected ownership marker. This replaces the paid-only pre-deploy hook without
changing any CRUD or integrity behavior. A failed initialization prevents the
server from starting. [Render hook availability](https://render.com/docs/blueprint-spec)

Production reads `DATABASE_URL` from the process environment and the HTTP port
from Render's `PORT`. Placeholder values are documented in `.env.example`.
The production image has no local credentials or environment files.

The existing local password was moved to ignored `.env` under
`PART1_DB_PASSWORD`. Local Python code and Compose read it; the password is no
longer embedded in publishable source. Local connection-target guards remain.
New local clones need their own `.env` password before starting Compose.

The checked source archive includes application code, original schema/seed/view
scripts, tests, documentation, and configuration. It excludes `.env`, virtual
environments, caches, Git metadata, generated transcripts, PDFs, ZIP files, and
generated SQL exports. The original exports remain in the local workspace for
assignment submission and can be regenerated from the SQL sources.

To rebuild the archive after source changes:

```powershell
.\.venv\Scripts\python.exe tools/prepare_github.py
```

Its file hashes are recorded in `build/github-manifest.json`. The packaging check
rejects known environment/local credentials, recognizable token/private-key
patterns, and paths outside the project. No files are published by this command.

## Verification and remaining work

All 163 tests pass. A fresh temporary local database was initialized by the
production Docker entry point; Swagger, health, CRUD, and both mandatory
rejections passed over real HTTP. A saved user edit survived both a container
restart and replacement with a new container. The image was checked for embedded
local credentials, and all temporary test resources were removed.

Only your GitHub upload, Render authentication/manual deployment, and public URL
verification remain. No public deployment or provider-side billing/account state
has been verified from this workspace.
