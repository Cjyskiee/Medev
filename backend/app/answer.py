"""Builds the answer for a question from the best matching chunks."""

from app.config import SCORE_MIN, TOP_K
from app.filters import extract_filters
from app.llm import ask_llm, embed_texts
from app.search import search_chunks, search_related

NOT_FOUND_ANSWER = "I couldn't find this in the documents."
BROAD_ANSWER = (
    "I couldn't find this in the documents. Your question may be too broad: "
    "try adding a condition, patient group or study type."
)
NO_FILTERS = {"condition_type": None, "study_type": None}

ANSWER_SYSTEM_PROMPT = (
    "Answer the question using ONLY the numbered passages below. After each claim, cite the "
    "passage number like [1]. If the passages do not clearly answer the question, or you are not "
    "sure, reply exactly: I couldn't find this in the documents. Do not use outside knowledge. "
    "Do not give medical advice. Keep the answer under 120 words."
)


# Adds the citation number n = 1, 2, 3... that the answer must refer to.
def _number_sources(results):
    return [{"n": number, **item} for number, item in enumerate(results, start=1)]


# Builds the user prompt: the question, then each numbered passage with its title.
def _build_user_prompt(question, sources):
    lines = [f"Question: {question}", "", "Passages:"]
    for source in sources:
        lines.append(f"[{source['n']}] {source['title']}")
        lines.append(source["snippet"])
        lines.append("")
    return "\n".join(lines)


# Tells whether the model refused with the agreed sentence, accepting a curly apostrophe.
def _says_not_found(reply):
    text = reply.lower().replace("\u2019", "'")
    return ("couldn't find this in the documents" in text
            or "could not find this in the documents" in text)


# Returns the standard "nothing relevant" response, keeping the filters and related list.
def _not_found(filters, answer, related=None):
    return {
        "found": False,
        "answer": answer,
        "filters": filters,
        "sources": [],
        "related": related or [],
    }


# Searches without filters, returns the found sources and leaves the answer null.
def _basic_answer(question):
    vector = embed_texts([question])[0]
    sources = _number_sources(search_chunks(vector, dict(NO_FILTERS), TOP_K))
    return {
        "found": bool(sources),
        "answer": None,
        "filters": dict(NO_FILTERS),
        "sources": sources,
        "related": [],
    }


# Applies the broad-question rule first, then filters, search and finally the model.
def _smart_answer(question):
    if len(question.split()) < 3:
        return _not_found(dict(NO_FILTERS), BROAD_ANSWER)

    filters = extract_filters(question)
    vector = embed_texts([question])[0]
    sources = _number_sources(search_chunks(vector, filters, TOP_K))

    has_filter = filters["condition_type"] is not None or filters["study_type"] is not None
    related = []
    if has_filter:
        related = search_related(vector, [source["document_id"] for source in sources])

    if not sources:
        return _not_found(filters, NOT_FOUND_ANSWER, related)
    if not has_filter and sources[0]["score"] < SCORE_MIN + 0.10:
        return _not_found(filters, NOT_FOUND_ANSWER, related)

    reply = ask_llm(_build_user_prompt(question, sources), system=ANSWER_SYSTEM_PROMPT).strip()
    if not reply or _says_not_found(reply):
        return _not_found(filters, NOT_FOUND_ANSWER, related)

    return {
        "found": True,
        "answer": reply,
        "filters": filters,
        "sources": sources,
        "related": related,
    }


# Answers one question in "basic" mode (no filters, no answer) or "smart" mode.
def answer_question(question, mode):
    if mode == "basic":
        return _basic_answer(question)
    return _smart_answer(question)
