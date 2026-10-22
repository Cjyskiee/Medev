"""Database helpers: connections, table creation/migration and document queries."""

import psycopg

from app.config import DB_URL

# Columns added after the first schema, kept here so every startup migrates old databases.
DOCUMENT_COLUMNS = (
    ("diagnosis", "TEXT"),
    ("condition_classification", "TEXT"),
    ("source_name", "TEXT"),
    ("source_location", "TEXT"),
    ("summary", "TEXT"),
    ("findings", "JSONB DEFAULT '[]'::jsonb"),
    ("keywords", "JSONB DEFAULT '[]'::jsonb"),
    ("document_type", "TEXT"),
    ("synthetic", "BOOLEAN DEFAULT false"),
)


# Opens a new PostgreSQL connection using DB_URL.
def get_connection():
    return psycopg.connect(DB_URL)


# Returns the set of titles already stored, so seeding can skip duplicates.
def get_document_titles():
    with get_connection() as conn:
        rows = conn.execute("SELECT title FROM documents").fetchall()
    return {row[0] for row in rows}


# Returns every document in the shape the frontend list expects, newest first.
def list_documents():
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, title, diagnosis, condition_classification, patient_group,
                   study_type, source_name, source_location, created_at, synthetic
            FROM documents
            ORDER BY created_at DESC, id DESC
            """
        ).fetchall()
    return [
        {
            "document_id": row[0],
            "title": row[1],
            "diagnosis": row[2] or "unknown",
            "condition_classification": row[3] or "unknown",
            "patient_group": row[4] or "unknown",
            "study_type": row[5] or "other",
            "source_name": row[6] or "unknown",
            "source_location": row[7] or "unknown",
            "created_at": row[8].isoformat() if row[8] else None,
            "synthetic": bool(row[9]),
        }
        for row in rows
    ]


# Returns one document in the detailed shape, or None when the id does not exist.
def get_document(document_id):
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT id, title, body, diagnosis, condition_classification, patient_group,
                   study_type, source_name, source_location, summary, findings, keywords,
                   document_type, created_at, synthetic, author
            FROM documents
            WHERE id = %s
            """,
            (document_id,),
        ).fetchone()
    if row is None:
        return None
    return {
        "document_id": row[0],
        "title": row[1],
        "body": row[2],
        "diagnosis": row[3] or "unknown",
        "condition_classification": row[4] or "unknown",
        "patient_group": row[5] or "unknown",
        "study_type": row[6] or "other",
        "source_name": row[7] or "unknown",
        "source_location": row[8] or "unknown",
        "summary": row[9] or "",
        "findings": row[10] or [],
        "keywords": row[11] or [],
        "document_type": row[12] or "other",
        "created_at": row[13].isoformat() if row[13] else None,
        "synthetic": bool(row[14]),
        "author": row[15] or "",
    }


# Returns how many records exist, split into built-in synthetic and uploaded ones.
def count_documents():
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT count(*),
                   count(*) FILTER (WHERE synthetic),
                   count(*) FILTER (WHERE NOT synthetic)
            FROM documents
            """
        ).fetchone()
    return {"total": row[0], "seed": row[1], "uploaded": row[2]}


# Creates the extension and both tables, then adds any newer document columns in place.
def create_tables():
    with get_connection() as conn:
        conn.execute("CREATE EXTENSION IF NOT EXISTS vector")

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS documents (
                id SERIAL PRIMARY KEY,
                title TEXT NOT NULL,
                author TEXT,
                body TEXT NOT NULL,
                condition TEXT,
                condition_type TEXT,
                patient_group TEXT,
                study_type TEXT,
                treatment TEXT,
                created_at TIMESTAMPTZ DEFAULT now()
            )
            """
        )

        for name, definition in DOCUMENT_COLUMNS:
            conn.execute(f"ALTER TABLE documents ADD COLUMN IF NOT EXISTS {name} {definition}")

        # Old rows only have the legacy columns, so copy them across on the first upgraded start.
        conn.execute(
            """
            UPDATE documents
            SET condition_classification = condition_type
            WHERE condition_classification IS NULL AND condition_type IS NOT NULL
            """
        )
        conn.execute(
            """
            UPDATE documents
            SET diagnosis = condition
            WHERE diagnosis IS NULL AND condition IS NOT NULL
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS chunks (
                id SERIAL PRIMARY KEY,
                document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
                chunk_index INTEGER,
                content TEXT NOT NULL,
                embedding VECTOR(384) NOT NULL
            )
            """
        )
