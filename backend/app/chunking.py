"""Splits a long document body into small, overlapping pieces for embedding."""

import re


# Splits text into pieces of at most max_chars: paragraphs first, then sentences, then hard cuts.
def _split_units(text, max_chars):
    units = []
    for paragraph in re.split(r"\n\s*\n", text):
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        if len(paragraph) <= max_chars:
            units.append(paragraph)
            continue
        for sentence in re.split(r"(?<=[.!?])\s+", paragraph):
            sentence = sentence.strip()
            if not sentence:
                continue
            if len(sentence) <= max_chars:
                units.append(sentence)
                continue
            for start in range(0, len(sentence), max_chars):
                piece = sentence[start:start + max_chars].strip()
                if piece:
                    units.append(piece)
    return units


# Joins the pieces into chunks of at most max_chars, each starting with the previous chunk's tail.
def split_text(text, max_chars=700, overlap=100):
    text = (text or "").replace("\r\n", "\n")
    overlap = max(0, min(overlap, max_chars // 2))
    room = max_chars - overlap - 1 if overlap else max_chars

    units = _split_units(text, room)

    bodies = []
    current = ""
    for unit in units:
        candidate = unit if not current else current + " " + unit
        if len(candidate) <= room:
            current = candidate
            continue
        if current:
            bodies.append(current)
        current = unit
    if current:
        bodies.append(current)

    chunks = []
    for index, body in enumerate(bodies):
        if index == 0 or overlap == 0:
            chunks.append(body)
        else:
            chunks.append((bodies[index - 1][-overlap:] + " " + body).strip())
    return chunks
