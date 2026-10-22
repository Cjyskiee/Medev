"""All model calls go through this file: the chat model and the embedding model."""

import json

import httpx

from app.config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL

EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"

# Filled on the first embed_texts() call so the model is loaded only once.
_embedding_model = None


# Returns the model base URL with a scheme, using http:// when the value has none.
def _base_url():
    base = LLM_BASE_URL.strip().rstrip("/")
    if "://" not in base:
        base = "http://" + base.lstrip("/")
    return base


# Sends the messages to the model server and returns the reply text, or "" on failure.
def _call_llm_server(messages):
    url = _base_url() + "/chat/completions"
    headers = {"Authorization": f"Bearer {LLM_API_KEY}"}
    body = {"model": LLM_MODEL, "messages": messages}
    try:
        response = httpx.post(url, json=body, headers=headers, timeout=120.0)
        if response.status_code >= 400:
            print(f"LLM request failed ({response.status_code}) at {url}: {response.text[:300]}")
            return ""
        return response.json()["choices"][0]["message"]["content"] or ""
    except Exception as error:
        print(f"LLM request failed at {url}: {type(error).__name__}: {error}")
        return ""


# Asks the model one question and returns its reply as plain text.
def ask_llm(prompt, system=None):
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    return _call_llm_server(messages).strip()


# Returns the first {...} block in the text as a dict, or None if it is not valid JSON.
def parse_json(text):
    if not text:
        return None
    start = text.find("{")
    if start == -1:
        return None
    depth = 0
    for position in range(start, len(text)):
        if text[position] == "{":
            depth += 1
        elif text[position] == "}":
            depth -= 1
            if depth == 0:
                try:
                    data = json.loads(text[start:position + 1])
                except Exception:
                    return None
                return data if isinstance(data, dict) else None
    return None


# Turns each text into 384 numbers, loading the embedding model on the first call only.
def embed_texts(texts):
    global _embedding_model
    if not texts:
        return []
    if _embedding_model is None:
        # Imported here so the rest of the app still runs if the heavy model is unavailable.
        from sentence_transformers import SentenceTransformer
        _embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    vectors = _embedding_model.encode(texts)
    return [vector.tolist() for vector in vectors]
