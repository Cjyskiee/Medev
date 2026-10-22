"""Vector search over chunks, with optional hard filters taken from the document form."""

from app.config import SCORE_MIN
from app.db import get_connection

SEARCH_SQL = """
WITH scored AS (
    SELECT d.id AS document_id,
           d.title,
           d.author,
           d.condition_type,
           d.study_type,
           c.content AS snippet,
           1 - (c.embedding <=> %s::vector) AS score,
           ROW_NUMBER() OVER (PARTITION BY d.id ORDER BY c.embedding <=> %s::vector) AS chunk_rank
    FROM chunks c
    JOIN documents d ON d.id = c.document_id
    {where}
)
SELECT document_id, title, author, condition_type, study_type, snippet, score
FROM scored
WHERE chunk_rank = 1
ORDER BY score DESC
LIMIT %s
"""


# Turns a list of numbers into the text form pgvector expects, like '[0.1,0.2]'.
def _vector_to_text(vector):
    return "[" + ",".join(str(value) for value in vector) + "]"


# Builds the WHERE clause from the filters that are not None; values stay in parameters.
def _build_where(filters, exclude_document_ids):
    clauses = []
    values = []

    if filters.get("condition_type") is not None:
        clauses.append("d.condition_type = %s")
        values.append(filters["condition_type"])

    if filters.get("study_type") is not None:
        clauses.append("d.study_type = %s")
        values.append(filters["study_type"])

    if exclude_document_ids:
        clauses.append("d.id <> ALL(%s::int[])")
        values.append(list(exclude_document_ids))

    where = "WHERE " + " AND ".join(clauses) if clauses else ""
    return where, values


# Runs the shared query, keeps the best chunk per document and drops scores below SCORE_MIN.
def _run_search(question_vector, filters, top_k, exclude_document_ids=None):
    where, filter_values = _build_where(filters, exclude_document_ids)
    sql = SEARCH_SQL.format(where=where)
    vector_text = _vector_to_text(question_vector)
    params = [vector_text, vector_text] + filter_values + [top_k]

    with get_connection() as conn:
        rows = conn.execute(sql, params).fetchall()

    results = []
    for row in rows:
        raw_score = float(row[6])
        if raw_score < SCORE_MIN:
            continue
        results.append(
            {
                "document_id": row[0],
                "title": row[1],
                "author": row[2],
                "condition_type": row[3],
                "study_type": row[4],
                "snippet": row[5],
                "score": round(raw_score, 2),
            }
        )
    return results


# Finds the best matching chunk of each document that passes the hard filters.
def search_chunks(question_vector, filters, top_k):
    return _run_search(question_vector, filters or {}, top_k)


# Finds close documents the caller has not seen yet, ignoring the filters.
def search_related(question_vector, exclude_document_ids, top_k=3):
    return _run_search(question_vector, {}, top_k, exclude_document_ids)


CANDIDATE_SQL = """
WITH scored AS (
    SELECT d.id AS document_id,
           d.title,
           d.body,
           d.diagnosis,
           d.condition_classification,
           d.patient_group,
           d.study_type,
           d.source_name,
           d.source_location,
           c.content AS snippet,
           1 - (c.embedding <=> %s::vector) AS score,
           ROW_NUMBER() OVER (PARTITION BY d.id ORDER BY c.embedding <=> %s::vector) AS chunk_rank
    FROM chunks c
    JOIN documents d ON d.id = c.document_id
)
SELECT document_id, title, body, diagnosis, condition_classification, patient_group,
       study_type, source_name, source_location, snippet, score
FROM scored
WHERE chunk_rank = 1
ORDER BY score DESC
LIMIT %s
"""


# Returns the best chunk of the closest documents with all metadata, without any hard filter.
def search_candidates(question_vector, limit=40):
    vector_text = _vector_to_text(question_vector)
    with get_connection() as conn:
        rows = conn.execute(CANDIDATE_SQL, [vector_text, vector_text, limit]).fetchall()

    return [
        {
            "document_id": row[0],
            "title": row[1],
            "body": row[2] or "",
            "diagnosis": row[3] or "unknown",
            "condition_classification": row[4] or "unknown",
            "patient_group": row[5] or "unknown",
            "study_type": row[6] or "other",
            "source_name": row[7] or "unknown",
            "source_location": row[8] or "unknown",
            "snippet": row[9],
            "score": round(float(row[10]), 2),
        }
        for row in rows
    ]
