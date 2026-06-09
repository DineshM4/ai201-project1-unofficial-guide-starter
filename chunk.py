"""
Milestone 3 — ingestion loader + chunking.

Loads every .txt in documents/ and splits each into overlapping chunks.

Each document begins with a small header (professor summary stats, or the Reddit
thread title/URL); that header becomes its own chunk.
"""

import json
import re
from pathlib import Path

DOCS_DIR = Path(__file__).parent / "documents"
CHUNKS_OUT = Path(__file__).parent / "chunks.json"

# 600-char cap: measured review-length median is 446 and max ~550, so a 600 cap
# keeps essentially every review as one intact, attributed chunk. A review longer
# than this is the only thing that gets character-split (with OVERLAP).
CHUNK_SIZE = 600
OVERLAP = 50


def split_into_blocks(text: str) -> list[str]:
    """Split a document into its natural units: the leading header, then each
    review block. Every review/comment block begins on its own line with a '['
    marker ('[Professor ...]', '[Reddit comment ...]', '[Original post]'), so we
    cut the text right before each such line.
    """
    text = text.strip()
    parts = re.split(r"\n(?=\[)", text)
    return [p.strip() for p in parts if p.strip()]


def _char_split(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Fallback sliding-window splitter for a single review longer than the cap.

    The window advances by `chunk_size - overlap`; each cut snaps back to the last
    space so words aren't sliced in half. Only used for over-long reviews.
    """
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        if end < len(text):
            boundary = text.rfind(" ", start, end)
            if boundary > start:
                end = boundary
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
    return chunks


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = OVERLAP) -> list[str]:
    """Review-aware chunking: one chunk per review (or header) block.

    Each natural block becomes a single chunk so reviews never bleed into one
    another. A block that exceeds `chunk_size` is the only thing that gets
    character-split, using `overlap` to preserve context across the cut.
    """
    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")

    chunks: list[str] = []
    for block in split_into_blocks(text):
        if len(block) <= chunk_size:
            chunks.append(block)
        else:
            chunks.extend(_char_split(block, chunk_size, overlap))
    return chunks


def load_documents(docs_dir: Path = DOCS_DIR) -> list[dict]:
    """Read every .txt file in docs_dir into {'source': filename, 'text': ...}."""
    docs = []
    for path in sorted(docs_dir.glob("*.txt")):
        text = path.read_text(encoding="utf-8").strip()
        if text:
            docs.append({"source": path.name, "text": text})
    return docs


def chunk_documents(docs: list[dict]) -> list[dict]:
    """Chunk each document, carrying the source filename onto every chunk so
    attribution survives into retrieval/generation."""
    all_chunks = []
    for doc in docs:
        for i, piece in enumerate(chunk_text(doc["text"])):
            all_chunks.append(
                {
                    "id": f"{doc['source']}::chunk-{i}",
                    "source": doc["source"],
                    "chunk_index": i,
                    "text": piece,
                }
            )
    return all_chunks


def main() -> None:
    docs = load_documents()
    chunks = chunk_documents(docs)

    CHUNKS_OUT.write_text(json.dumps(
        chunks, indent=2, ensure_ascii=False), encoding="utf-8")

    # --- Report so the chunking can be verified ---------------------------
    lengths = [len(c["text"]) for c in chunks]
    print(f"Loaded {len(docs)} documents -> {len(chunks)} chunks")
    print(f"Chunk length: min={min(lengths)}  max={max(lengths)}  "
          f"avg={sum(lengths) // len(lengths)} chars")
    print(f"Wrote {CHUNKS_OUT.name}\n")

    print("Chunks per document:")
    for doc in docs:
        n = sum(1 for c in chunks if c["source"] == doc["source"])
        print(f"  {n:>4}  {doc['source']}")

    print("\nSample chunks (verify a review stays intact):")
    for c in chunks[:2]:
        print(f"\n--- {c['id']} ({len(c['text'])} chars) ---")
        print(c["text"])


if __name__ == "__main__":
    main()
