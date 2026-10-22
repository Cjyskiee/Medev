"""FastAPI app: health, search, documents, history, legacy endpoints and the frontend."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Body, Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.answer import answer_question
from app.config import REQUIRE_AUTH
from app.db import create_tables, get_document, get_document_titles, list_documents
from app.evidence import search_evidence
from app.firebase_auth import (
    firebase_status,
    get_current_user,
    init_firebase,
    public_user_view,
    require_verified_user,
)
from app.health import health_payload
from app.history import append_history, clear_history, list_history
from app.ingest import ingest_document
from app.schemas import (
    AskRequest,
    AskResponse,
    SearchRequest,
    SubmitRequest,
    SubmitResponse,
)

FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"
MAX_UPLOAD_DOCUMENTS = 100


# Creates the database tables and prepares token verification before serving requests.
@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables()
    init_firebase()
    yield


app = FastAPI(title="MedEvidence", lifespan=lifespan)

# Lets the page call the API from any origin or port (hackathon only).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# Tells the frontend that the backend is up, the model state and how many records exist.
@app.get("/api/health")
def health(check_model: bool = False):
    return health_payload(check_model)


# Returns a verified user only when REQUIRE_AUTH is on; the document routes need any signed-in user.
def owner_guard(authorization: str | None = Header(default=None)):
    if not REQUIRE_AUTH:
        return None
    return require_verified_user(authorization)


# Tells whether the backend can verify Firebase tokens.
@app.get("/api/auth/status")
def auth_status():
    return firebase_status()


# Returns the signed-in user decoded from the Firebase ID token.
@app.get("/api/auth/me")
def auth_me(claims: dict = Depends(get_current_user)):
    return public_user_view(claims)


# Runs one validated evidence search and stores it in the chat history.
@app.post("/api/search", dependencies=[Depends(owner_guard)])
def search(request: SearchRequest):
    query = request.query.strip()
    result = search_evidence(query)
    if result["status"] != "error":
        try:
            append_history(query, result)
        except Exception as error:
            print(f"History write failed: {type(error).__name__}: {error}")
    return result


# Returns every stored search, newest first.
@app.get("/api/history", dependencies=[Depends(owner_guard)])
def get_history():
    return {"items": list_history()}


# Removes every stored search.
@app.delete("/api/history", dependencies=[Depends(owner_guard)])
def delete_history():
    clear_history()
    return {"cleared": True}


# Returns the whole collection in the shape the Documents view renders.
@app.get("/api/documents", dependencies=[Depends(get_current_user)])
def documents():
    return {"documents": list_documents()}


# Reads one body value from an uploaded record, accepting the common field names.
def _upload_body(record):
    for field in ("body", "text", "excerpt", "content", "summary"):
        value = record.get(field)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


# Validates an upload payload and ingests every record, reporting bad rows together.
@app.post("/api/documents", dependencies=[Depends(get_current_user)])
def upload_documents(payload: dict = Body(...)):
    raw = payload.get("documents")
    records = raw if isinstance(raw, list) else [payload]
    if not records:
        return JSONResponse(status_code=422, content={"errors": ["No documents found in the request."]})
    if len(records) > MAX_UPLOAD_DOCUMENTS:
        return JSONResponse(
            status_code=422,
            content={"errors": [f"Upload at most {MAX_UPLOAD_DOCUMENTS} documents at once."]},
        )

    seen = {title.strip().lower() for title in get_document_titles()}
    errors = []
    valid = []
    for index, record in enumerate(records, 1):
        if not isinstance(record, dict):
            errors.append(f"document {index}: not a JSON object")
            continue
        title = record.get("title")
        if not isinstance(title, str) or not title.strip():
            errors.append(f"document {index}: missing title")
            continue
        title = title.strip()[:300]
        body = _upload_body(record)
        if not body:
            errors.append(f"document {index} ({title}): missing body text")
            continue
        if title.lower() in seen:
            errors.append(f"document {index} ({title}): a document with this title already exists")
            continue
        seen.add(title.lower())
        valid.append((title, body, record))

    if errors:
        return JSONResponse(status_code=422, content={"errors": errors})

    added = []
    failures = []
    for title, body, record in valid:
        author = record.get("author") if isinstance(record.get("author"), str) else ""
        try:
            result = ingest_document(
                title,
                author.strip(),
                body,
                metadata=record,
                synthetic=bool(record.get("synthetic", False)),
            )
            added.append(result["document_id"])
        except Exception as error:
            failures.append(f"{title}: {type(error).__name__}: {error}")
    if failures:
        return JSONResponse(status_code=422, content={"errors": failures, "added": added})
    return {"count": len(added), "added": added}


# Returns one document with its metadata, summary, findings and keywords.
@app.get("/api/documents/{document_id}", dependencies=[Depends(get_current_user)])
def document_detail(document_id: int):
    document = get_document(document_id)
    if document is None:
        raise HTTPException(status_code=404, detail=f"Document {document_id} was not found.")
    return document


# Stores one submitted document and returns its id, form and chunk count.
@app.post("/api/submit", response_model=SubmitResponse, dependencies=[Depends(owner_guard)])
def submit(request: SubmitRequest):
    if not request.deidentified:
        raise HTTPException(
            status_code=422,
            detail="Document must be de-identified before submitting: set deidentified to true.",
        )

    title = request.title.strip()
    text = request.text.strip()
    if not title or not text:
        raise HTTPException(
            status_code=422,
            detail="Title and text are required and cannot be empty.",
        )

    return ingest_document(title, request.author.strip(), text)


# Legacy question endpoint kept for scripts: smart or basic mode over the same chunks.
@app.post("/api/ask", response_model=AskResponse, dependencies=[Depends(owner_guard)])
def ask(request: AskRequest):
    return answer_question(request.question, request.mode)


# Serves the standalone frontend folder; mounted last so it never hides the /api routes.
if FRONTEND_DIR.is_dir():
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
else:
    print(f"Frontend folder not found at {FRONTEND_DIR}; only the API will be served.")
