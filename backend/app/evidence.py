"""Builds the /api/search payload: validated evidence, cited answer and excluded look-alikes."""

from app.config import SCORE_MIN, TOP_K
from app.filters import extract_filters
from app.llm import ask_llm, embed_texts, parse_json
from app.search import search_candidates

CANDIDATE_LIMIT = 40
MAX_EXCLUDED = 5
FILTER_LABELS = {
    "condition_classification": "classification",
    "patient_group": "patient group",
    "study_type": "study type",
}
BROAD_SUGGESTION = "Example: benign breast tumors in adult women."

ANSWER_SYSTEM_PROMPT = (
    "Answer the question using ONLY the numbered passages below. Return ONLY a JSON object with "
    "two keys: answer (under 120 words, each claim followed by the passage number like [1]) and "
    "key_findings (array of 2 to 4 objects, each with text and source_ids, an array of the passage "
    "numbers that support it). If the passages do not clearly answer the question, return "
    '{"answer": "I couldn\'t find this in the documents.", "key_findings": []}. '
    "Do not use outside knowledge. Do not give medical advice. Return no other text."
)


# Returns a short readable list such as "classification benign and patient group adult".
def _describe_filters(filters):
    active = [
        f"{FILTER_LABELS[name]} {filters[name]}"
        for name in ("condition_classification", "patient_group", "study_type")
        if filters.get(name)
    ]
    return " and ".join(active)


# Tells whether one candidate satisfies every filter, and which attributes disagreed.
def _mismatches(candidate, filters):
    reasons = []
    if filters.get("condition_classification") and (
        candidate["condition_classification"] != filters["condition_classification"]
    ):
        reasons.append(
            f"classification is {candidate['condition_classification']}, "
            f"not {filters['condition_classification']}"
        )
    if filters.get("patient_group") and candidate["patient_group"] != filters["patient_group"]:
        reasons.append(
            f"patient group is {candidate['patient_group']}, not {filters['patient_group']}"
        )
    if filters.get("study_type") and candidate["study_type"] != filters["study_type"]:
        reasons.append(
            f"study type is {candidate['study_type']}, not {filters['study_type']}"
        )
    return reasons


# Explains why a candidate was kept, so the UI can show the validation that happened.
def _match_reasons(candidate, filters):
    reasons = [f"semantic similarity {candidate['score']:.2f} (minimum {SCORE_MIN:.2f})"]
    active = _describe_filters(filters)
    if not active:
        reasons.append("no condition, patient group or study type filter was detected")
        return reasons
    if filters.get("condition_classification"):
        reasons.append(f"classification matches: {candidate['condition_classification']}")
    if filters.get("patient_group"):
        reasons.append(f"patient group matches: {candidate['patient_group']}")
    if filters.get("study_type"):
        reasons.append(f"study type matches: {candidate['study_type']}")
    return reasons


# Formats one accepted candidate as a source card for the frontend.
def _source_item(candidate, number, filters):
    return {
        "n": number,
        "document_id": candidate["document_id"],
        "title": candidate["title"],
        "diagnosis": candidate["diagnosis"],
        "condition_classification": candidate["condition_classification"],
        "patient_group": candidate["patient_group"],
        "study_type": candidate["study_type"],
        "source_name": candidate["source_name"],
        "location": candidate["source_location"],
        "excerpt": candidate["snippet"],
        "score": candidate["score"],
        "match_reasons": _match_reasons(candidate, filters),
    }


# Formats one filtered-out candidate for the "excluded records" panel.
def _excluded_item(candidate, reasons):
    return {
        "document_id": candidate["document_id"],
        "title": candidate["title"],
        "score": candidate["score"],
        "reasons": reasons,
    }


# Builds the error payload the frontend renders as a red notice.
def _error(message, detail, error_code="invalid_query"):
    return {
        "status": "error",
        "error_code": error_code,
        "message": message,
        "detail": detail,
        "key_findings": [],
        "limitations": [],
        "sources": [],
        "excluded": [],
    }


# Builds the "nothing usable" payload, keeping any look-alikes that were rejected.
def _no_context(message, detail, suggestion, excluded):
    return {
        "status": "no_context",
        "message": message,
        "detail": detail,
        "suggestion": suggestion,
        "key_findings": [],
        "limitations": [],
        "sources": [],
        "excluded": excluded,
    }


# Builds the prompt: the question followed by each numbered passage and its metadata.
def _answer_prompt(query, sources):
    lines = [f"Question: {query}", "", "Passages:"]
    for source in sources:
        lines.append(
            f"[{source['n']}] {source['title']} | diagnosis: {source['diagnosis']} | "
            f"classification: {source['condition_classification']} | "
            f"patient group: {source['patient_group']} | study type: {source['study_type']}"
        )
        lines.append(source["excerpt"])
        lines.append("")
    return "\n".join(lines)


# Keeps the passage numbers a finding cites inside the range of the real sources.
def _clean_findings(raw, source_count):
    findings = []
    if not isinstance(raw, list):
        return findings
    for item in raw:
        if not isinstance(item, dict):
            continue
        text = item.get("text")
        if not isinstance(text, str) or not text.strip():
            continue
        ids = item.get("source_ids")
        if not isinstance(ids, list):
            ids = []
        numbers = sorted({value for value in ids if isinstance(value, int) and 1 <= value <= source_count})
        findings.append({"text": text.strip()[:400], "source_ids": numbers})
    return findings[:4]


# Asks the model to answer from the sources and returns the reply, the answer and its findings.
def _compose_answer(query, sources):
    reply = ask_llm(_answer_prompt(query, sources), system=ANSWER_SYSTEM_PROMPT)
    data = parse_json(reply) or {}
    answer = data.get("answer") if isinstance(data.get("answer"), str) else ""
    if not answer:
        answer = reply.strip()
    return reply, answer.strip(), _clean_findings(data.get("key_findings"), len(sources))


# Searches, validates every candidate against the filters and answers from what passed.
def search_evidence(query):
    query = (query or "").strip()
    if len(query) < 3 or len(query) > 500:
        return _error("Check your question", "Enter a question between 3 and 500 characters.")
    if len(query.split()) < 3:
        return _no_context(
            "Question too broad",
            "Add a condition, patient group or study type so the search can validate the evidence.",
            BROAD_SUGGESTION,
            [],
        )

    filters = extract_filters(query)
    vector = embed_texts([query])[0]
    candidates = search_candidates(vector, CANDIDATE_LIMIT)

    accepted = []
    excluded = []
    for candidate in candidates:
        if candidate["score"] < SCORE_MIN:
            continue
        reasons = _mismatches(candidate, filters)
        if reasons:
            excluded.append(_excluded_item(candidate, reasons))
        else:
            accepted.append(candidate)

    excluded = excluded[:MAX_EXCLUDED]
    sources = [_source_item(candidate, number, filters) for number, candidate in enumerate(accepted[:TOP_K], 1)]

    if not sources:
        active = _describe_filters(filters)
        detail = (
            f"Nothing in the collection passed {active} at the minimum relevance of {SCORE_MIN:.2f}."
            if active
            else f"Nothing in the collection reached the minimum relevance of {SCORE_MIN:.2f}."
        )
        return _no_context("No matching evidence", detail, BROAD_SUGGESTION, excluded)

    reply, answer, findings = _compose_answer(query, sources)
    if not reply:
        return _error(
            "The answer could not be generated",
            "The model did not return a response. Check the model connection in Settings.",
            "model_unavailable",
        )
    if not answer or "couldn't find this in the documents" in answer.lower():
        return _no_context(
            "No matching evidence",
            "The retrieved passages did not support an answer to this question.",
            BROAD_SUGGESTION,
            excluded,
        )

    active = _describe_filters(filters)
    limitations = [
        f"The summary uses only the {len(sources)} record(s) shown below.",
        "Synthetic records only; this is not a diagnosis or a treatment recommendation.",
    ]
    if active:
        limitations.append(f"Results were restricted to {active}.")
    else:
        limitations.append("No condition filter was detected, so unrelated records may appear.")

    return {
        "status": "ok",
        "query": query,
        "answer": answer,
        "key_findings": findings,
        "limitations": limitations,
        "filters": filters,
        "sources": sources,
        "excluded": excluded,
    }
