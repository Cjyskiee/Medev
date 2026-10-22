"""Turns a question into the hard filters used before the vector search."""

from app.llm import ask_llm, parse_json

CONDITION_TYPES = {"benign", "malignant"}
PATIENT_GROUPS = {"adult", "pediatric", "older_adult"}
STUDY_TYPES = {"clinical_trial", "case_report", "review", "lab_study"}

FILTER_SYSTEM_PROMPT = (
    "Read the user's question and return ONLY a JSON object with three keys. "
    "condition_classification: 'benign' if the question asks for benign or non-cancerous "
    "conditions; 'malignant' if it asks for cancer, malignant tumors or carcinoma; otherwise null. "
    "patient_group: 'pediatric' for children, infants or adolescents; 'older_adult' for elderly or "
    "older patients; 'adult' for adults; otherwise null. "
    "study_type: one of clinical_trial, case_report, review, lab_study when the question clearly "
    "asks for that kind of study; otherwise null. The word 'tumor' on its own does NOT mean "
    "benign or malignant, so use null. When unsure, use null. Return no other text."
)


ALIASES = {
    "adults": "adult",
    "paediatric": "pediatric",
    "children": "pediatric",
    "child": "pediatric",
    "adolescents": "pediatric",
    "elderly": "older_adult",
    "older_adults": "older_adult",
    "geriatric": "older_adult",
    "cancer": "malignant",
    "carcinoma": "malignant",
    "non_cancerous": "benign",
    "noncancerous": "benign",
    "randomized_controlled_trial": "clinical_trial",
    "randomised_controlled_trial": "clinical_trial",
    "trial": "clinical_trial",
    "systematic_review": "review",
    "meta_analysis": "review",
    "case_series": "case_report",
}


# Returns a trimmed lowercase string for a value, or "" when it is missing or not text.
def _text(value):
    return value.strip().lower().replace("-", "_").replace(" ", "_") if isinstance(value, str) else ""


# Keeps a value only if it belongs to the allowed list, otherwise returns None.
def _clean(value, allowed):
    text = _text(value)
    text = ALIASES.get(text, text)
    return text if text in allowed else None


# Turns a question into the filter dict without ever raising.
def extract_filters(question):
    try:
        reply = ask_llm(question, system=FILTER_SYSTEM_PROMPT)
        data = parse_json(reply) or {}
    except Exception:
        data = {}

    classification = _clean(
        data.get("condition_classification", data.get("condition_type")), CONDITION_TYPES
    )
    return {
        "condition_classification": classification,
        "condition_type": classification,
        "patient_group": _clean(data.get("patient_group"), PATIENT_GROUPS),
        "study_type": _clean(data.get("study_type"), STUDY_TYPES),
    }
