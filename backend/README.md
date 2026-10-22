# MedEvidence backend

FastAPI + PostgreSQL/pgvector backend for MedEvidence. Documents are split into chunks,
embedded with `all-MiniLM-L6-v2` (384 dimensions) and stored in Neon Postgres. A question is
validated against the metadata stored with each record, and only the records that pass are sent
to the chat model, which answers with citations.

The UI lives in `../frontend` and is served by this same process, so there is one URL to open.

Everything below runs from the `backend` folder.

```powershell
cd C:\CodeFile\Medev\backend
```

## 1. Install the requirements

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

This is a large install (torch arrives with sentence-transformers). The first time the app
embeds anything it also loads the `all-MiniLM-L6-v2` model (about 90 MB on first download), so
the first search after a fresh install is slow.

Tested with Python 3.10+ (development machine: 3.14).

## 2. Fill in `.env`

Copy the example and edit it:

```powershell
Copy-Item .env.example .env
```

| Variable | Meaning |
| --- | --- |
| `DB_URL` | Full PostgreSQL connection string. For Neon include `?sslmode=require&channel_binding=require`. The database must allow the `vector` extension; the app runs `CREATE EXTENSION IF NOT EXISTS vector` on startup. |
| `LLM_BASE_URL` | Base URL of an OpenAI-compatible chat endpoint. `http://localhost:11434/v1` for Ollama. A value without a scheme (for example `//192.168.1.10:8080/api`) is accepted and sent over `http`. |
| `LLM_MODEL` | Model name served at that URL. |
| `LLM_API_KEY` | Sent as `Authorization: Bearer ...`. Can be left empty for a local server. |
| `SCORE_MIN` | Minimum similarity (0-1) for a record to count as evidence. Default `0.30`. |
| `TOP_K` | Maximum number of sources returned per question. Default `5`. |

`.env` is git-ignored. Never commit it.

## 3. Run the server

```powershell
python -m uvicorn app.main:app --reload --port 8000
```

- Frontend: <http://127.0.0.1:8000/> (served from `../frontend`)
- Interactive API docs: <http://127.0.0.1:8000/docs>
- Health check: <http://127.0.0.1:8000/api/health>

Tables are created and older ones migrated automatically on startup, so the first run works
against an empty database.

## 4. Load the demo records

```powershell
python -m scripts.make_fake_docs
python -m scripts.seed
```

| Script | What it does |
| --- | --- |
| `scripts.make_fake_docs` | Writes 11 synthetic `.txt` records into `data/docs/`. Each file starts with `Title:` and `Author:` lines, then a blank line, then the body. The set contains deliberate look-alikes: benign versus malignant breast lesions, adult versus pediatric asthma, type 1 versus type 2 diabetes, benign prostatic hyperplasia versus prostate adenocarcinoma. |
| `scripts.seed` | Reads every file in `data/docs/`, asks the model for the metadata (diagnosis, classification, patient group, study type, source, summary, findings, keywords), embeds the text and stores it. Documents whose title is already stored are skipped, so it is safe to run twice. Records created this way are marked as built-in synthetic. |
| `scripts.smoke_test` | Calls a running server end to end (`/api/health`, `/api/documents`, `/api/search` for three demo questions, `/api/history`) and prints the results. Start uvicorn first. Documents now need a token, so set `SMOKE_TOKEN` to a Firebase ID token to list them; without it the script reports the expected `401`. |

## 5. API

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/health` | Version, model status, record counts and the relevance threshold. Add `?check_model=true` to make a real call to the model and report `verified`, `unreachable`, `auth_failed`, `rate_limited` or `error`. |
| POST | `/api/search` | `{"query": "..."}`. Returns validated evidence, a cited answer, key findings, limitations, the records that were excluded and why. |
| GET | `/api/history` | The last 100 searches, newest first, each with the full result so it can be replayed. |
| DELETE | `/api/history` | Clears the stored searches. |
| GET | `/api/documents` | Every record, newest first, in the shape the Documents view renders. Requires a signed-in account. |
| POST | `/api/documents` | Uploads one or more records: `{"documents": [...]}` or a single record. Requires a signed-in account. Titles must be unique; records already carrying metadata skip the model call. The UI turns a `.txt` or `.md` file into one record (`Title:`/`Author:` lines or a `# Heading`, then the body) and still accepts `.json`/`.jsonl`. |
| GET | `/api/documents/{id}` | One record with its metadata, summary, findings, keywords and full body. Requires a signed-in account. |
| POST | `/api/ask` | Legacy question endpoint: `smart` (filters and a cited answer) or `basic` (raw vector search). Kept for scripts. |
| POST | `/api/submit` | Legacy single-document endpoint. Requires `"deidentified": true`. |
| GET | `/api/auth/status` | Whether the backend can verify Firebase ID tokens, plus the project id or the init error. |
| GET | `/api/auth/me` | The signed-in user decoded from `Authorization: Bearer <firebase-id-token>`. `401` without a valid token. |

### What `/api/search` returns

- `status`: `ok`, `no_context` or `error`.
- `answer`: a summary that cites sources as `[1]`, `[2]`.
- `key_findings`: `[{text, source_ids}]` where the ids are the citation numbers.
- `limitations`: short statements about what the summary is and is not.
- `sources`: `document_id`, `title`, `diagnosis`, `condition_classification`, `patient_group`,
  `study_type`, `source_name`, `location`, `excerpt`, `score`, `match_reasons`.
- `excluded`: look-alike records that were close in meaning but failed validation, each with
  `reasons` such as `classification is malignant, not benign`.

Questions under three words are rejected as too broad without searching, and nothing is
accepted without evidence: if no record passes, `status` is `no_context` and the excluded list
still shows what was rejected and why.

### Example

```powershell
$body = @{ query = "Benign breast tumors in adult women" } | ConvertTo-Json
Invoke-RestMethod http://127.0.0.1:8000/api/search -Method Post -ContentType "application/json" -Body $body
```

## 6. Authentication

The frontend signs users in with Firebase (email and password, then a verification link). The
browser keeps the session; this backend verifies the ID token that the page sends as
`Authorization: Bearer <token>` on every API call.

- `FIREBASE_PROJECT_ID` (default `medev-f910b`) is the project the token audience is checked
  against. This is enough to verify tokens; no service account is needed for that.
- `FIREBASE_CREDENTIALS` is optional. Point it at a service account JSON (absolute, or relative to
  `backend/`) when the backend itself must call Admin APIs such as `create_user`.
- `REQUIRE_AUTH` (default `false`) gates search, history and the legacy endpoints behind a
  **verified** email. The document routes (list, detail, upload) require any signed-in account,
  verified or not, so a fresh sign-up can use the app immediately; guests still see the prompt.

`GET /api/auth/status` reports whether verification is ready, and `GET /api/auth/me` returns
`uid`, `email`, `email_verified`, `name`, `picture` and `sign_in_provider` for a valid token.
The backend never reads verification from the request body: `email_verified` comes from the
signed token.

### If sign-in says `auth/invalid-credential`

This project has email enumeration protection on (checked against the Identity Toolkit API: an
unknown address also returns `INVALID_LOGIN_CREDENTIALS`), so Firebase deliberately uses the same
error for "no account with this email" and "wrong password".

- Sign in with the full email address, not a username, and type the password by hand; autofill can
  keep an older password.
- Press **Forgot password?** on the sign-in screen to set a new one.
- To tell the two cases apart, try **Create account** with the same email. If it succeeds, no
  account existed in this project (an older verification link can belong to another project); if
  it says the email already has an account, the password was the problem.

## 7. Notes

- Search history is stored in `data/history.json` and is not committed.
- Uploaded records are stored with `synthetic` false; the seeded demo records are `true`, so the
  Settings view can show the two counts separately.
- The model API key stays on the backend; the browser never receives it.
