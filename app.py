"""
Milestone 5 (part 2) — query interface.

Pipeline stage: Generation -> [ Interface ]

A Gradio app over the grounded-generation pipeline. The user types a question; the
app retrieves the top-k review chunks, asks the LLM to answer using only those
chunks (see generate.py), and shows:

  - the grounded answer,
  - the source documents the answer is attributed to (built programmatically from
    the retrieved chunks' metadata — never from the model's reply), and
  - the exact retrieved excerpts, so the user can verify the answer is traceable to
    real review text.

Run:

    python app.py

then open the printed local URL.
"""

import gradio as gr

from generate import answer_query, build_sources
from retrieval import DEFAULT_K

EXAMPLES = [
    "What do students say about exam difficulty for professors teaching CS 111?",
    "Which CS 344 professor do students recommend most?",
    "How helpful is the professor for CS 205 outside of lecture?",
    "What is the classroom atmosphere like for the CS 211 professors?",
    "According to Reddit, who are the best and worst CS professors at Rutgers?",
]


def _render_chunks(chunks: list[dict]) -> str:
    """Markdown rendering of the retrieved excerpts that grounded the answer."""
    if not chunks:
        return "_No relevant review excerpts were retrieved for this question._"
    parts = []
    for i, c in enumerate(chunks, 1):
        parts.append(
            f"**[{i}] {c['source']}**  (cosine distance: {c['distance']:.3f})\n\n"
            f"> {c['text'].strip()}"
        )
    return "\n\n---\n\n".join(parts)


def ask(query: str, k: int):
    """Gradio handler: question -> (answer, sources markdown, retrieved chunks)."""
    result = answer_query(query, k=int(k))

    answer = result["answer"]
    if result["sources"]:
        sources_md = "\n".join(f"- `{s}`" for s in result["sources"])
    else:
        sources_md = "_No sources — the system did not have enough information._"

    return answer, sources_md, _render_chunks(result["chunks"])


def build_ui() -> gr.Blocks:
    with gr.Blocks(title="The Unofficial Guide — Rutgers CS Professors") as demo:
        gr.Markdown(
            "# The Unofficial Guide — Rutgers CS Professors(Core curriculum only)\n"
            "Ask about teaching style, exam difficulty, or how helpful a CS professor "
            "is. Answers come **only** from student reviews (RateMyProfessors + "
            "Reddit) retrieved from the vector store — every source is listed, and "
            "if the reviews don't cover your question the system says so instead of "
            "guessing."
        )

        with gr.Row():
            query = gr.Textbox(
                label="Your question",
                placeholder="e.g. What do students say about exams in CS 111?",
                lines=2,
                scale=4,
            )
            k = gr.Slider(
                label="Chunks to retrieve (top-k)",
                minimum=1,
                maximum=10,
                value=DEFAULT_K,
                step=1,
                scale=1,
            )

        ask_btn = gr.Button("Ask", variant="primary")

        answer = gr.Textbox(label="Answer", lines=6)
        sources = gr.Markdown(label="Sources")
        with gr.Accordion("Retrieved review excerpts (the grounding)", open=False):
            chunks = gr.Markdown()

        gr.Examples(examples=EXAMPLES, inputs=query)

        ask_btn.click(ask, inputs=[query, k], outputs=[
                      answer, sources, chunks])
        query.submit(ask, inputs=[query, k], outputs=[answer, sources, chunks])

    return demo


if __name__ == "__main__":
    build_ui().launch()
