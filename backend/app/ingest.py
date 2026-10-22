"""Turns one document into validated metadata, a documents row and its embedding chunks."""

from psycopg.types.json import Jsonb

from app.chunking import split_text
from app.db import get_connection
from app.llm import ask_llm, embed_texts, parse_json

CLASSIFICATIONS = {"benign", "malignant", "not_applicable", "unknown"}
PATIENT_GROUPS = {"adult", "pediatric", "older_adult", "mixed", "unknown"}
STUDY_TYPES = {"clinical_trial", "case_report", "review", "lab_study", "other"}
DOCUMENT_TYPES = {"case_report", "cohort", "trial", "review", "guideline", "other"}

DEFAULT_METADATA = {
    "diagnosis": "unknown",
    "condition_classification": "unknown",
    "patient_group": "unknown",
    "study_type": "other",
    "document_type": "other",
    "source_name": "unknown",
    "source_location": "unknown",
    "summary": "",
    "findings": [],
    "keywords": [],
}

CLASSIFICATION_ALIASES = {
    "non_cancerous": "benign",
    "noncancerous": "benign",
    "non_malignant": "benign",
    "nonmalignant": "benign",
    "cancer": "malignant",
    "carcinoma": "malignant",
    "normal": "not_applicable",
    "not_applicable_to_condition": "not_applicable",
}
PATIENT_GROUP_ALIASES = {
    "adults": "adult",
    "adult_patients": "adult",
    "children": "pediatric",
    "child": "pediatric",
    "paediatric": "pediatric",
    "pediatric_patients": "pediatric",
    "adolescents": "pediatric",
    "elderly": "older_adult",
    "older_adults": "older_adult",
    "geriatric": "older_adult",
}
STUDY_TYPE_ALIASES = {
    "trial": "clinical_trial",
    "rct": "clinical_trial",
    "randomized_controlled_trial": "clinical_trial",
    "randomised_controlled_trial": "clinical_trial",
    "case_report_series": "case_report",
    "case_series": "case_report",
    "systematic_review": "review",
    "meta_analysis": "review",
    "laboratory_study": "lab_study",
    "in_vitro": "lab_study",
    "cohort": "clinical_trial",
}
DOCUMENT_TYPE_ALIASES = {
    "research_record": "case_report",
    "original_research": "cohort",
    "randomized_controlled_trial": "trial",
    "randomised_controlled_trial": "trial",
    "systematic_review": "review",
    "meta_analysis": "review",
}

METADATA_SYSTEM_PROMPT = (
    "You are a medical document classifier. Read the document and return ONLY a JSON object "
    "with these keys: diagnosis (short name of the main condition studied), "
    "condition_classification (one of: benign, malignant, not_applicable, unknown), "
    "patient_group (one of: adult, pediatric, older_adult, mixed, unknown), "
    "study_type (one of: clinical_trial, case_report, review, lab_study, other), "
    "document_type (one of: case_report, cohort, trial, review, guideline, other), "
    "source_name (journal, registry or institution, or 'unknown'), "
    "source_location (country or city, or 'unknown'), "
    "summary (at most two sentences describing what the document reports), "
    "findings (array of 2 to 4 short factual statements from the document), "
    "keywords (array of 3 to 6 short terms). "
    "Use 'unknown' or 'other' when the document does not say. Never guess. Return no other text."
)


# Returns a trimmed string for a value, or "" when the value is missing or not text.
def _text(value):
    return value.strip() if isinstance(value, str) else ""


# Turns a raw value into one of the allowed words, following the alias table, or None.
def _normalize(value, allowed, aliases):
    text = _text(value).lower().replace("-", "_").replace(" ", "_")
    text = aliases.get(text, text)
    return text if text in allowed else None


# Keeps only allowed values and fills every missing or invalid field with a safe default.
def _clean_metadata(data):
    data = data if isinstance(data, dict) else {}
    metadata = dict(DEFAULT_METADATA)

    classification = _normalize(
        data.get("condition_classification", data.get("condition_type", data.get("classification"))),
        CLASSIFICATIONS,
        CLASSIFICATION_ALIASES,
    )
    if classification:
        metadata["condition_classification"] = classification

    patient_group = _normalize(data.get("patient_group"), PATIENT_GROUPS, PATIENT_GROUP_ALIASES)
    if patient_group:
        metadata["patient_group"] = patient_group

    study_type = _normalize(data.get("study_type"), STUDY_TYPES, STUDY_TYPE_ALIASES)
    if study_type:
        metadata["study_type"] = study_type

    document_type = _normalize(data.get("document_type"), DOCUMENT_TYPES, DOCUMENT_TYPE_ALIASES)
    if document_type:
        metadata["document_type"] = document_type

    source_location = _text(data.get("source_location") or data.get("location"))
    if source_location:
        metadata["source_location"] = source_location

    for field in ("diagnosis", "source_name", "summary"):
        value = _text(data.get(field))
        if value:
            metadata[field] = value

    for field, limit in (("findings", 6), ("keywords", 8)):
        raw = data.get(field)
        if isinstance(raw, str):
            raw = [raw]
        if isinstance(raw, list):
            cleaned = []
            for item in raw:
                value = _text(item)
                if value and value not in cleaned:
                    cleaned.append(value[:300])
            metadata[field] = cleaned[:limit]

    return metadata


# Asks the model about the document and returns the metadata, falling back to defaults.
def extract_metadata(text):
    reply = ask_llm(text[:6000], system=METADATA_SYSTEM_PROMPT)
    return _clean_metadata(parse_json(reply) or {})


# Turns the metadata into the legacy five-field form still used by POST /api/submit.
def _legacy_form(metadata):
    return {
        "condition": metadata["diagnosis"],
        "condition_type": metadata["condition_classification"],
        "patient_group": metadata["patient_group"],
        "study_type": metadata["study_type"],
        "treatment": "none",
    }


# Inserts the document row with its metadata and returns the new document id.
def _insert_document(conn, title, author, text, metadata, synthetic):
    form = _legacy_form(metadata)
    row = conn.execute(
        """
        INSERT INTO documents
            (title, author, body, condition, condition_type, patient_group, study_type, treatment,
             diagnosis, condition_classification, source_name, source_location, summary,
             findings, keywords, document_type, synthetic)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
        """,
        (
            title,
            author,
            text,
            form["condition"],
            form["condition_type"],
            form["patient_group"],
            form["study_type"],
            form["treatment"],
            metadata["diagnosis"],
            metadata["condition_classification"],
            metadata["source_name"],
            metadata["source_location"],
            metadata["summary"],
            Jsonb(metadata["findings"]),
            Jsonb(metadata["keywords"]),
            metadata["document_type"],
            bool(synthetic),
        ),
    ).fetchone()
    return row[0]


# Turns a list of numbers into the text form pgvector expects, like '[0.1,0.2]'.
def _vector_to_text(vector):
    return "[" + ",".join(str(value) for value in vector) + "]"


# Inserts one chunks row per piece, with its embedding cast to a vector.
def _insert_chunks(conn, document_id, chunks, vectors):
    for index, (content, vector) in enumerate(zip(chunks, vectors)):
        conn.execute(
            """
            INSERT INTO chunks (document_id, chunk_index, content, embedding)
            VALUES (%s, %s, %s, %s::vector)
            """,
            (document_id, index, content, _vector_to_text(vector)),
        )


# Saves one document and its chunks in a single transaction and returns the API-style result.
def ingest_document(title, author, text, metadata=None, synthetic=False):
    if metadata is None:
        metadata = extract_metadata(text)
    else:
        metadata = _clean_metadata(metadata)

    chunks = split_text(text)
    vectors = embed_texts(chunks)

    with get_connection() as conn:
        document_id = _insert_document(conn, title, author, text, metadata, synthetic)
        _insert_chunks(conn, document_id, chunks, vectors)

    return {"document_id": document_id, "form": _legacy_form(metadata), "chunk_count": len(chunks)}
