# Project 1 Planning: The Unofficial Guide

> Write this document before you write any pipeline code.
> Your spec and architecture diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation — the more specific they are, the more useful the generated code will be.
> Update the Retrieval Approach and Chunking Strategy sections if you change your approach during implementation.
> Update this file before starting any stretch features.

---

## Domain

<!-- What domain did you choose? Why is this knowledge valuable and hard to find through official channels? -->
     I chose this domain because for a student having the best professors to learn makes learning funner and high grades easier to get. However, since there was too much information, I cut it down to just my core classes, which works since those are the classes all cs students have to take. This knowledge is also valuable beacuse student reviews reveal the atmosphere of a professor, their exam difficulty, and the amount they help students outside of lecture, all of which are valuable information for students that want to take certain professors.
---

## Documents

<!-- List your specific sources: URLs, subreddit names, forum threads, or file descriptions.
     Aim for at least 10 sources that together cover different subtopics or perspectives within your domain. -->

| # | Source | Description | URL or location |
|---|--------|-------------|-----------------|
| 1 | RMP| Reviews of a professor teaching cs 111 and cs 112, and some electives| https://www.ratemyprofessors.com/professor/600296|
| 2 | RMP| Reviews of a professor teaching cs 205, cs 344, and cs 211, and some electives| https://www.ratemyprofessors.com/professor/2066022|
| 3 | RMP| Reviews of a professor teaching cs 205, 206, and some electives| https://www.ratemyprofessors.com/professor/2519830|
| 4 | RMP| Reviews of a professor teaching cs 111 and cs 112| https://www.ratemyprofessors.com/professor/2875899|
| 5 | RMP| Reviews of professor teaching cs 344 and cs 513| https://www.ratemyprofessors.com/professor/2447976|
| 6 | RMP| Reviews of a professor teaching cs 344 and some electives| https://www.ratemyprofessors.com/professor/2366659|
| 7 | RMP| Reviews of a professor teaching cs 211 and some electives| https://www.ratemyprofessors.com/professor/1916642|
| 8 | RMP| Reviews of a professor teaching cs 211| https://www.ratemyprofessors.com/professor/2635012|
| 9 | RMP| Reviews of a professor teaching cs 344| https://www.ratemyprofessors.com/professor/3060894|
| 10 | RMP| Reviews of a professor teaching cs 205, 206, 11 and more| https://www.ratemyprofessors.com/professor/2297066|
| 11 | Reddit| General reddit post of some good an bad professors in cs department. 4 years old.| https://www.reddit.com/r/rutgers/comments/u2bock/best_cs_professors_and_worst_cs_professors/|
| 12 | Reddit| General reddit post of some good professors in cs department. 4 years old.|https://www.reddit.com/r/rutgers/comments/tejyvj/best_cs_professors/ |
---

## Chunking Strategy

<!-- How will you split documents into chunks?
     State your chunk size (in tokens or characters), overlap size, and explain why those
     numbers fit the structure of your documents.
     A review-heavy corpus warrants different chunking than a long FAQ. -->

**Chunk size:** 400 characters.

**Overlap:** 50 characters.

**Reasoning:** Since my data is made up of many short, self-contained student reviews(from RMP mainly), a small chunk size keeps each individual review's opinion intact without bleeding into unrelated ones, and a light overlap preserves context for the few reviews that run slightly longer than one chunk.

---

## Retrieval Approach

<!-- Which embedding model are you using (e.g., all-MiniLM-L6-v2 via sentence-transformers)?
     How many chunks will you retrieve per query (top-k)?
     If you were deploying this for real users and cost wasn't a constraint, what tradeoffs
     would you weigh in choosing a different embedding model — context length, multilingual
     support, accuracy on domain-specific text, latency? -->

**Embedding model:** all-MiniLM-L6-v2 via sentence-transformers since it is locally available 

**Top-k:** 5

**Production tradeoff reflection:** If cost wasn't an issue, I would use a stronger embedding model from OpenAI because it will most likely be more accurate on informal, and slang language of student reviews. Here I would accept the latency and context length in exchange for retriving the information that better matches the user's question.

---

## Evaluation Plan

<!-- List your 5 test questions with their expected correct answers.
     Questions should be specific enough that you can judge whether the system's response
     is right or wrong. "What are good dining halls?" is too vague.
     "What do students say about wait times at [dining hall name] during lunch?" is testable. -->

| # | Question | Expected answer |
|---|----------|-----------------|
| 1 | What do students say about exam difficulty for professors teaching CS 111? | Reviews should describe how hard the exams are for the CS 111 professors. |
| 2 | Which CS 344 professor do students recommend most? | Reviews should point to the CS 344 professor students rate most positively. |
| 3 | How helpful is the professor for CS 205 outside of lecture? | Reviews should describe the out-of-lecture availability and helpfulness of a CS 205 professor. |
| 4 | What is the classroom atmosphere like for the CS 211 professors? | Reviews should summarize the teaching style and class atmosphere of CS 211 professors. |
| 5 | According to Reddit, who are considered the best and worst CS professors at Rutgers? | The two Reddit threads should name specific professors students consider good or bad in the CS department. |

---

## Anticipated Challenges

<!-- What could go wrong? Name at least two specific risks with reasoning.
     Consider: noisy or inconsistent documents, missing source attribution, off-topic
     retrieval, chunks that split key information across boundaries. -->

1. Student reviews are noisy and contradictory, so two reviews of the same professor may give opposite opinions and the system could surface a misleading consensus if retrieval pulls only one side.
2. The Reddit threads are four years old and reference professors who may no longer teach the listed courses, so retrieval could return outdated attributions that no longer match current course offerings.

---

## Architecture

<!-- Draw a diagram of your pipeline showing the five stages:
     Document Ingestion → Chunking → Embedding + Vector Store → Retrieval → Generation
     Label each stage with the tool or library you're using.
     You can use ASCII art, a Mermaid diagram, or embed a sketch as an image.
     You'll use this diagram as context when prompting AI tools to implement each stage. -->

Had AI generate this for me based on the information I gave it from all sections before
```
┌─────────────────────┐   ┌────────────┐   ┌──────────────────────────┐   ┌───────────────┐   ┌──────────────────┐
│ Document Ingestion  │ → │  Chunking  │ → │  Embedding + Vector Store │ → │   Retrieval   │ → │    Generation    │
│ (scrape RMP/Reddit, │   │ (400 char, │   │ (all-MiniLM-L6-v2 via     │   │ (top-k = 5,   │   │ (Claude via the  │
│  save to documents/)│   │ 50 overlap)│   │  sentence-transformers,   │   │  cosine sim)  │   │  Anthropic API)  │
│                     │   │            │   │  stored in a vector DB)   │   │               │   │                  │
└─────────────────────┘   └────────────┘   └──────────────────────────┘   └───────────────┘   └──────────────────┘
```

---

## AI Tool Plan

<!-- For each part of the pipeline below, describe:
     - Which AI tool you plan to use (Claude, Copilot, ChatGPT, etc.)
     - What you'll give it as input (which sections of this planning.md, which requirements)
     - What you expect it to produce
     - How you'll verify the output matches your spec

     "I'll use AI to help me code" is not a plan.
     "I'll give Claude my Chunking Strategy section and ask it to implement chunk_text()
     with my specified chunk size and overlap" is a plan. -->

**Milestone 3 — Ingestion and chunking:** I'll give Claude my Domain, Documents, and Chunking Strategy sections and ask it to implement an ingestion loader plus a `chunk_text()` function using my 400-character size and 50-character overlap, then verify it by checking that the saved chunks keep individual reviews intact.

**Milestone 4 — Embedding and retrieval:** I'll give Claude my Retrieval Approach section and ask it to embed the chunks with all-MiniLM-L6-v2 and implement a retrieval function returning the top-5 chunks by cosine similarity, verifying it by confirming relevant reviews come back for my five test questions.

**Milestone 5 — Generation and interface:** I'll give Claude my Architecture and Evaluation Plan sections and ask it to build a query interface that feeds retrieved chunks to the Anthropic API (Claude) for grounded answers, verifying it by running my five test questions and comparing the responses against my expected answers.
