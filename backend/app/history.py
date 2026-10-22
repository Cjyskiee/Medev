"""Small JSON file that keeps the last searches so the Chat History view can replay them."""

import json
import os
import tempfile
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

HISTORY_PATH = Path(__file__).resolve().parents[1] / "data" / "history.json"
MAX_ITEMS = 100
_lock = threading.Lock()


# Reads the stored items, returning an empty list when the file is missing or unreadable.
def _read_all():
    try:
        data = json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []
    items = data.get("items") if isinstance(data, dict) else None
    return items if isinstance(items, list) else []


# Writes the whole history atomically so a crash never leaves a half-written file.
def _write_all(items):
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=HISTORY_PATH.parent, delete=False, suffix=".tmp"
    )
    try:
        json.dump({"items": items}, handle, ensure_ascii=False)
        handle.flush()
        os.fsync(handle.fileno())
    finally:
        handle.close()
    os.replace(handle.name, HISTORY_PATH)


# Returns every stored search, newest first.
def list_history():
    with _lock:
        return _read_all()


# Adds one search result to the front of the history and drops the oldest entries.
def append_history(query, result):
    item = {
        "id": uuid.uuid4().hex,
        "query": query,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": result.get("status", "error"),
        "source_ids": [source.get("document_id") for source in result.get("sources", [])],
        "result": result,
    }
    with _lock:
        items = [item] + _read_all()
        _write_all(items[:MAX_ITEMS])
    return item


# Removes every stored search.
def clear_history():
    with _lock:
        _write_all([])
