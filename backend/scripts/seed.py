"""Seeds the database with the fake documents in data/docs/."""

from pathlib import Path

from app.db import get_document_titles
from app.ingest import ingest_document

DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "docs"


# Reads one file in the "Title: ...", "Author: ...", blank line, body format.
def read_document_file(path):
    lines = path.read_text(encoding="utf-8").splitlines()
    title = lines[0].removeprefix("Title:").strip() if lines else ""
    author = lines[1].removeprefix("Author:").strip() if len(lines) > 1 else ""
    body_start = 3 if len(lines) > 2 and not lines[2].strip() else 2
    body = "\n".join(lines[body_start:]).strip()
    if not title or not body:
        raise ValueError("file must start with Title:, then Author:, a blank line and a body")
    return title, author, body


# Ingests every .txt file in data/docs/, skipping titles that are already stored.
def main():
    file_paths = sorted(DATA_DIR.glob("*.txt"))
    if not file_paths:
        print(f"No .txt files found in {DATA_DIR}")
        return

    existing_titles = get_document_titles()
    for path in file_paths:
        try:
            title, author, body = read_document_file(path)
        except Exception as error:
            print(f"{path.name}: ERROR {error}")
            continue

        if title in existing_titles:
            print(f"{path.name}: skipped, already in the database: {title}")
            continue

        try:
            result = ingest_document(title, author, body, synthetic=True)
        except Exception as error:
            print(f"{path.name}: ERROR {error}")
            continue

        existing_titles.add(title)
        print(f"{path.name}: document {result['document_id']} | {title} | {result['form']}")


# Runs the seeder when called with "python -m scripts.seed".
if __name__ == "__main__":
    main()
