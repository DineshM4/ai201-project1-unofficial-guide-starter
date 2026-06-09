"""
Milestone 4 (part 2) — retrieval.

Pipeline stage: Embedding + Vector Store -> [ Retrieval ] -> Generation

retrieve(query, k=5) embeds the query with the SAME model used at index time
(all-MiniLM-L6-v2 — this matters: a query embedded by a different model would
live in a different vector space and the distances would be meaningless), then
asks ChromaDB for the top-k nearest chunks by cosine distance. Each result
carries its source document and chunk position so the generation step can cite
where an answer came from.

Run directly to sanity-check retrieval against the planning.md evaluation queries:

    python retrieval.py
"""

from functools import lru_cache

import chromadb

from embed import CHROMA_DIR, COLLECTION_NAME, MODEL_NAME, get_model

DEFAULT_K = 5  # planning.md Retrieval Approach


@lru_cache(maxsize=1)
def _model():
    """Load the embedding model once per process (cached)."""
    return get_model(MODEL_NAME)


@lru_cache(maxsize=1)
def _collection():
    """Open the persisted collection once per process (cached)."""
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return client.get_collection(COLLECTION_NAME)


def retrieve(query: str, k: int = DEFAULT_K) -> list[dict]:
    """Return the top-k most relevant chunks for `query`.

    Each result dict has:
      text        — the chunk text
      source      — source document filename (for attribution)
      chunk_index — position of the chunk within that document
      distance    — cosine distance (0 = identical, ~1 = unrelated)
    Lower distance = more relevant; results come back sorted nearest-first.
    """
    query_embedding = _model().encode(
        [query], normalize_embeddings=True
    ).tolist()

    result = _collection().query(
        query_embeddings=query_embedding,
        n_results=k,
        include=["documents", "metadatas", "distances"],
    )

    # Chroma returns column-style lists nested one level per query; we sent a
    # single query, so everything we want is in the [0] slot.
    documents = result["documents"][0]
    metadatas = result["metadatas"][0]
    distances = result["distances"][0]

    return [
        {
            "text": doc,
            "source": meta["source"],
            "chunk_index": meta["chunk_index"],
            "distance": dist,
        }
        for doc, meta, dist in zip(documents, metadatas, distances)
    ]


# planning.md Evaluation Plan — testing 5/5 of the planned queries here.
EVAL_QUERIES = [
    "What do students say about exam difficulty for professors teaching CS 111?",
    "Which CS 344 professor do students recommend most?",
    "How helpful is the professor for CS 205 outside of lecture?",
    "What is the classroom atmosphere like for the CS 211 professors?",
    "According to Reddit, who are the best and worst CS professors at Rutgers?",
]


def main() -> None:
    for i, query in enumerate(EVAL_QUERIES, 1):
        print("=" * 80)
        print(f"Q{i}: {query}")
        print("=" * 80)
        for rank, hit in enumerate(retrieve(query), 1):
            preview = hit["text"].replace("\n", " ")
            if len(preview) > 240:
                preview = preview[:240] + "…"
            print(f"\n[{rank}] distance={hit['distance']:.4f}  "
                  f"source={hit['source']}  chunk={hit['chunk_index']}")
            print(f"    {preview}")
        print()


if __name__ == "__main__":
    main()
