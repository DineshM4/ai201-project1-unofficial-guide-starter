"""
Milestone 4 (part 1) — embedding + vector store.

Pipeline stage: Chunking -> [ Embedding + Vector Store ] -> Retrieval

Loads the chunks produced by the ingestion pipeline (chunks.json, written by
chunk.py), embeds each chunk's text with all-MiniLM-L6-v2 (sentence-transformers,
runs locally, no API key), and stores the vectors in a persistent ChromaDB
collection together with per-chunk metadata (source document name + the chunk's
position in that document). The source metadata is what we use later for
attribution in the generation step.

Run this once to build/refresh the index:

    python embed.py
"""

import json
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

HERE = Path(__file__).parent
CHUNKS_IN = HERE / "chunks.json"
CHROMA_DIR = HERE / "chroma_db"          # persisted on disk; gitignored
COLLECTION_NAME = "CS professor_reviews"
MODEL_NAME = "all-MiniLM-L6-v2"          # planning.md Retrieval Approach


def load_chunks(path: Path = CHUNKS_IN) -> list[dict]:
    """Read the ingestion artifact. Each item is
    {id, source, chunk_index, text} (see chunk.py)."""
    if not path.exists():
        raise FileNotFoundError(
            f"{path.name} not found — run `python chunk.py` first to produce it."
        )
    return json.loads(path.read_text(encoding="utf-8"))


def get_model(model_name: str = MODEL_NAME) -> SentenceTransformer:
    """Load the local embedding model once and reuse it."""
    return SentenceTransformer(model_name)


def get_collection(client: chromadb.ClientAPI):
    """Get (or create) the cosine-similarity collection.

    metadata={"hnsw:space": "cosine"} tells Chroma to score with cosine
    distance instead of its default squared-L2. We chose cosine in planning.md
    because sentence-transformer embeddings encode meaning in direction, not
    magnitude, so the angle between vectors is the right notion of similarity.
    Cosine distance returned by Chroma is `1 - cosine_similarity`: 0.0 means
    identical, ~1.0 means unrelated.
    """
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def build_index(rebuild: bool = True) -> int:
    """Embed every chunk and (re)load it into ChromaDB. Returns the chunk count.

    `rebuild=True` drops any existing collection first so re-running this script
    never leaves stale or duplicated vectors behind.
    """
    chunks = load_chunks()
    model = get_model()

    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    if rebuild:
        try:
            client.delete_collection(COLLECTION_NAME)
        except Exception:
            pass  # collection didn't exist yet — nothing to drop
    collection = get_collection(client)

    # Embed all chunk texts in one batched call. normalize_embeddings keeps the
    # vectors unit-length, which pairs cleanly with cosine distance.
    texts = [c["text"] for c in chunks]
    embeddings = model.encode(
        texts,
        batch_size=64,
        show_progress_bar=True,
        normalize_embeddings=True,
    ).tolist()

    # Parallel lists, one entry per chunk. metadatas carries the attribution
    # fields we need downstream: which document and where in it.
    ids = [c["id"] for c in chunks]
    metadatas = [
        {"source": c["source"], "chunk_index": c["chunk_index"]}
        for c in chunks
    ]

    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=texts,
        metadatas=metadatas,
    )
    return collection.count()


def main() -> None:
    count = build_index(rebuild=True)
    print(f"\nEmbedded and stored {count} chunks in ChromaDB collection "
          f"'{COLLECTION_NAME}' at {CHROMA_DIR.name}/ (model: {MODEL_NAME}).")


if __name__ == "__main__":
    main()
