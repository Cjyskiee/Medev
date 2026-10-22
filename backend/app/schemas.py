"""Request and response models for the API."""

from typing import Literal

from pydantic import BaseModel


# The five form fields kept for the legacy /api/submit reply.
class DocumentForm(BaseModel):
    condition: str
    condition_type: str
    patient_group: str
    study_type: str
    treatment: str


# Body of POST /api/submit.
class SubmitRequest(BaseModel):
    title: str
    author: str = ""
    text: str
    deidentified: bool = False


# Reply of POST /api/submit.
class SubmitResponse(BaseModel):
    document_id: int
    form: DocumentForm
    chunk_count: int


# The hard filters chosen for a question; None means "no filter".
class AskFilters(BaseModel):
    condition_type: str | None = None
    study_type: str | None = None


# One cited passage in the answer, numbered from 1.
class SourceItem(BaseModel):
    n: int
    document_id: int
    title: str
    author: str | None = None
    condition_type: str | None = None
    study_type: str | None = None
    snippet: str
    score: float


# One close document that was not used as a source.
class RelatedItem(BaseModel):
    document_id: int
    title: str
    author: str | None = None
    condition_type: str | None = None
    study_type: str | None = None
    snippet: str
    score: float


# Body of POST /api/ask.
class AskRequest(BaseModel):
    question: str
    mode: Literal["smart", "basic"] = "smart"


# Reply of POST /api/ask.
class AskResponse(BaseModel):
    found: bool
    answer: str | None = None
    filters: AskFilters
    sources: list[SourceItem]
    related: list[RelatedItem]


# Body of POST /api/search, used by the frontend.
class SearchRequest(BaseModel):
    query: str
