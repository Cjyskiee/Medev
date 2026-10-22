"""Health payload for the frontend: version, model status, collection size and thresholds."""

import time

import httpx

from app.config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL, SCORE_MIN
from app.db import count_documents
from app.llm import _base_url

VERSION = "1.0.0"

# Holds the outcome of the last real model probe so /api/health stays instant by default.
_last_probe = {"status": "not_checked", "detail": ""}


# Calls the model once and records whether the credentials and endpoint really work.
def probe_model():
    if not LLM_BASE_URL.strip():
        _last_probe.update(status="not_configured", detail="LLM_BASE_URL is empty")
        return

    url = _base_url() + "/chat/completions"
    body = {"model": LLM_MODEL, "messages": [{"role": "user", "content": "Reply with OK."}]}
    headers = {"Authorization": f"Bearer {LLM_API_KEY}"}
    started = time.time()
    try:
        response = httpx.post(url, json=body, headers=headers, timeout=30.0)
    except httpx.TimeoutException:
        _last_probe.update(status="unreachable", detail="the request timed out")
        return
    except Exception as error:
        _last_probe.update(status="unreachable", detail=f"{type(error).__name__}: {error}")
        return

    elapsed = time.time() - started
    if response.status_code in (401, 403):
        _last_probe.update(status="auth_failed", detail=f"HTTP {response.status_code}")
    elif response.status_code == 429:
        _last_probe.update(status="rate_limited", detail="HTTP 429")
    elif response.status_code >= 400:
        _last_probe.update(
            status="error",
            detail=f"HTTP {response.status_code}: {response.text[:160]}",
        )
    else:
        _last_probe.update(status="verified", detail=f"replied in {elapsed:.1f}s")


# Returns the model block, probing only when the caller explicitly asks for a check.
def model_status(check=False):
    if not LLM_BASE_URL.strip():
        return {
            "status": "not_configured",
            "model_id": LLM_MODEL,
            "detail": "LLM_BASE_URL is empty",
        }
    if check:
        probe_model()
    return {"status": _last_probe["status"], "model_id": LLM_MODEL, "detail": _last_probe["detail"]}


# Builds the whole /api/health body, reporting database problems as warnings instead of failing.
def health_payload(check_model=False):
    counts = {"total": 0, "seed": 0, "uploaded": 0}
    warnings = []
    try:
        counts = count_documents()
    except Exception as error:
        warnings.append(f"database unavailable: {type(error).__name__}")

    return {
        "status": "ok",
        "version": VERSION,
        "model": model_status(check_model),
        "documents": {**counts, "warnings": warnings},
        "retrieval": {"min_relevance": SCORE_MIN},
    }
