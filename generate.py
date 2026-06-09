"""
Milestone 5 (part 1) — grounded generation.

Pipeline stage: Retrieval -> [ Generation ] -> Interface

Takes a user question, pulls the top-k chunks from the vector store (retrieval.py),
and asks an LLM to answer USING ONLY those chunks. The model is Groq's
llama-3.3-70b-versatile (free tier, OpenAI-compatible), called via the official
`groq` client with GROQ_API_KEY loaded from .env.

Grounding is enforced by FOUR mechanisms, not a polite suggestion:

  1. A strict system prompt with absolute rules — answer only from CONTEXT, never
     from prior knowledge, and reply with a fixed refusal sentence when the context
     is insufficient.
  2. temperature=0 — deterministic, so the model leans on the supplied text instead
     of sampling plausible-sounding training-data filler.
  3. A relevance backstop — if retrieval finds nothing close enough (every chunk is
     above RELEVANCE_CUTOFF cosine distance), we return the refusal WITHOUT calling
     the LLM at all. An off-domain question can't reach the model.
  4. Programmatic source attribution — the source list is built from the metadata of
     the chunks we actually fed the model. It is NOT parsed out of the model's reply,
     so a citation can never be hallucinated or omitted.

Run directly to test grounded generation against the planning.md eval queries plus
one deliberately off-domain question:

    python generate.py
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq

from retrieval import DEFAULT_K, retrieve

load_dotenv(Path(__file__).parent / ".env")

MODEL = "llama-3.3-70b-versatile"  # Groq free tier, OpenAI-compatible

# Cosine distance above which a chunk is treated as "not really about this query".
# Relevant review hits measure ~0.30–0.45 in practice (see retrieval.py); 0.85 only
# drops near-orthogonal noise. If EVERY retrieved chunk is above this, the query is
# off-domain and we refuse without calling the LLM.
RELEVANCE_CUTOFF = 0.85

REFUSAL = "I don't have enough information on that."

SYSTEM_PROMPT = (
    "You are a retrieval-grounded assistant that answers questions about student "
    "reviews of Rutgers CS professors. You answer STRICTLY from a CONTEXT block of "
    "retrieved review excerpts that is provided with every question.\n\n"
    "These rules are absolute and override any other instinct:\n"
    "1. Use ONLY the information inside the CONTEXT block. The context is your only "
    "source of truth.\n"
    "2. Do NOT use outside knowledge, prior training, assumptions, or general facts "
    "about professors, courses, or universities — even if you are certain they are "
    "true. If it is not in the CONTEXT, you do not know it.\n"
    "3. Never invent professor names, course numbers, ratings, opinions, or details "
    "that are not present in the CONTEXT.\n"
    "4. Every claim in your answer must be directly supported by a sentence in the "
    "CONTEXT.\n"
    f"5. If the CONTEXT does not contain enough information to answer the question, "
    f'reply with exactly this sentence and nothing else: "{REFUSAL}"\n\n'
    "Answer concisely, reflecting what the reviews actually say (including "
    "disagreement between reviewers when it exists)."
)


def _format_context(chunks: list[dict]) -> str:
    """Render retrieved chunks into a numbered, source-labeled CONTEXT block.

    Each excerpt is tagged with its source filename so the model can ground its
    wording in specific reviews — but attribution shown to the user is built
    separately from metadata (see build_sources), never from this text.
    """
    blocks = []
    for i, c in enumerate(chunks, 1):
        blocks.append(f"[{i}] (source: {c['source']})\n{c['text']}")
    return "\n\n".join(blocks)


def build_sources(chunks: list[dict]) -> list[str]:
    """Unique source filenames of the chunks fed to the model, in first-seen order.

    This is the programmatic attribution: the answer's sources are whatever
    documents the retrieved context came from, independent of the LLM's reply.
    """
    seen: list[str] = []
    for c in chunks:
        if c["source"] not in seen:
            seen.append(c["source"])
    return seen


def _client() -> Groq:
    key = os.getenv("GROQ_API_KEY")
    if not key:
        raise RuntimeError(
            "GROQ_API_KEY is not set. Copy .env.example to .env and add your key "
            "from https://console.groq.com"
        )
    return Groq(api_key=key)


def answer_query(query: str, k: int = DEFAULT_K) -> dict:
    """Answer `query` using only retrieved review context.

    Returns a dict:
      answer  — the grounded answer text, or the fixed REFUSAL sentence
      sources — list of source filenames the answer is grounded in (programmatic)
      chunks  — the retrieved chunks actually used (for transparency / display)
      grounded — True if the model was given relevant context; False if we refused
                 up front because retrieval found nothing relevant
    """
    query = (query or "").strip()
    if not query:
        return {"answer": REFUSAL, "sources": [], "chunks": [], "grounded": False}

    hits = retrieve(query, k=k)
    relevant = [h for h in hits if h["distance"] <= RELEVANCE_CUTOFF]

    # Backstop: nothing relevant retrieved -> refuse without involving the LLM,
    # so an off-domain question can never be answered from training data.
    if not relevant:
        return {"answer": REFUSAL, "sources": [], "chunks": [], "grounded": False}

    context = _format_context(relevant)
    user_message = (
        f"CONTEXT:\n{context}\n\n"
        f"QUESTION: {query}\n\n"
        f'Answer using only the CONTEXT above. If it is insufficient, reply exactly: "{REFUSAL}"'
    )

    completion = _client().chat.completions.create(
        model=MODEL,
        temperature=0,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
    )
    answer = completion.choices[0].message.content.strip()

    # If the model itself refused, don't attribute sources to a non-answer.
    # Normalize for the comparison so trailing punctuation/quotes/case don't slip
    # a refusal past us and get sources stapled onto it.
    refused = answer.strip().strip('"').rstrip(".").lower() == REFUSAL.rstrip(".").lower()
    sources = [] if refused else build_sources(relevant)

    return {
        "answer": answer,
        "sources": sources,
        "chunks": relevant,
        "grounded": True,
    }


def format_response(result: dict) -> str:
    """Render an answer_query result as 'answer + source list' text."""
    out = result["answer"]
    if result["sources"]:
        out += "\n\n**Sources:**\n" + "\n".join(f"- {s}" for s in result["sources"])
    return out


# planning.md eval queries (5) + one deliberately off-domain query (6) to prove the
# system refuses instead of inventing an answer from general knowledge.
TEST_QUERIES = [
    "What do students say about exam difficulty for professors teaching CS 111?",
    "Which CS 344 professor do students recommend most?",
    "How helpful is the professor for CS 205 outside of lecture?",
    "What is the classroom atmosphere like for the CS 211 professors?",
    "According to Reddit, who are the best and worst CS professors at Rutgers?",
    "What is the best pizza place near campus?",  # off-domain — must refuse
]


def main() -> None:
    for i, q in enumerate(TEST_QUERIES, 1):
        print("=" * 80)
        print(f"Q{i}: {q}")
        print("=" * 80)
        result = answer_query(q)
        print(format_response(result))
        print()


if __name__ == "__main__":
    main()
