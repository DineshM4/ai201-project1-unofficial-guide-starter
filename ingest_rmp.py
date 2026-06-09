"""
Milestone 3 ingestion — RateMyProfessors.

RMP is a React/Relay app: the reviews are NOT in the page HTML, they are loaded
from a GraphQL API. This script hits that API directly so we get every review
(not just the first page) plus structured metadata (class, ratings, date).

For each professor it writes one .txt file into documents/. Each review is
prefixed with the professor name + class + ratings so that attribution survives
chunking (chunks are ~400 chars, so the prof/class must live inside each review
block, not in a far-away header).
"""

import base64
import time
from pathlib import Path

import requests

# --- Config -----------------------------------------------------------------

# The numeric IDs are taken straight from the /professor/<id> URLs in planning.md.
PROFESSOR_IDS = [
    600296,   # CS 111, CS 112, electives
    2066022,  # CS 205, CS 344, CS 211, electives
    2519830,  # CS 205, CS 206, electives
    2875899,  # CS 111, CS 112
    2447976,  # CS 344, CS 513
    2366659,  # CS 344, electives
    1916642,  # CS 211, electives
    2635012,  # CS 211
    3060894,  # CS 344
    2297066,  # CS 205, CS 206, CS 11x, more
]

GRAPHQL_URL = "https://www.ratemyprofessors.com/graphql"
# Public hardcoded token the RMP front-end itself ships with (base64 of "test:test").
AUTH_HEADER = "Basic dGVzdDp0ZXN0"

DOCS_DIR = Path(__file__).parent / "documents"

# Pull everything in one shot; no professor here is anywhere near 1000 reviews.
QUERY = """
query TeacherRatings($id: ID!) {
  node(id: $id) {
    ... on Teacher {
      firstName
      lastName
      department
      avgRating
      avgDifficulty
      numRatings
      wouldTakeAgainPercent
      school { name }
      ratings(first: 1000) {
        edges {
          node {
            class
            comment
            date
            qualityRating
            difficultyRating
            grade
            wouldTakeAgain
            ratingTags
          }
        }
      }
    }
  }
}
"""


def encode_teacher_id(numeric_id: int) -> str:
    """RMP's GraphQL uses Relay node ids: base64 of 'Teacher-<numericId>'."""
    return base64.b64encode(f"Teacher-{numeric_id}".encode()).decode()


def fetch_professor(numeric_id: int) -> dict | None:
    resp = requests.post(
        GRAPHQL_URL,
        json={"query": QUERY, "variables": {"id": encode_teacher_id(numeric_id)}},
        headers={
            "Authorization": AUTH_HEADER,
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (educational RAG project ingestion)",
        },
        timeout=30,
    )
    resp.raise_for_status()
    payload = resp.json()
    return payload.get("data", {}).get("node")


def slugify(name: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in name).strip("_").lower()


def clean(text: str) -> str:
    if not text:
        return ""
    return " ".join(text.replace("\r", " ").replace("\n", " ").split())


def format_professor(prof: dict) -> str:
    full_name = f"{prof['firstName']} {prof['lastName']}".strip()
    dept = prof.get("department") or "Unknown department"
    school = (prof.get("school") or {}).get("name", "Unknown school")

    header = [
        f"Professor: {full_name}",
        f"Department: {dept} | School: {school}",
        f"Overall quality: {prof.get('avgRating')}/5 | "
        f"Difficulty: {prof.get('avgDifficulty')}/5 | "
        f"Would take again: {prof.get('wouldTakeAgainPercent')}% | "
        f"Total reviews: {prof.get('numRatings')}",
        "=" * 70,
        "",
    ]

    blocks = []
    edges = (prof.get("ratings") or {}).get("edges", [])
    for edge in edges:
        r = edge["node"]
        comment = clean(r.get("comment"))
        if not comment:
            continue
        course = clean(r.get("class")) or "Unknown course"
        tags = ", ".join(r.get("ratingTags", "").split("--")) if r.get("ratingTags") else ""
        date = (r.get("date") or "").split(" ")[0]

        # Prof name + course repeated in every block so each chunk stays attributable.
        meta = (
            f"[Professor {full_name} | Course: {course} | "
            f"Quality: {r.get('qualityRating')}/5 | "
            f"Difficulty: {r.get('difficultyRating')}/5"
        )
        if r.get("grade"):
            meta += f" | Grade: {clean(r['grade'])}"
        if r.get("wouldTakeAgain") is not None:
            meta += f" | Would take again: {'Yes' if r['wouldTakeAgain'] else 'No'}"
        meta += f" | {date}]"

        block = meta + "\n" + comment
        if tags:
            block += f"\nTags: {tags}"
        blocks.append(block)

    return "\n".join(header) + "\n\n".join(blocks) + "\n"


def main() -> None:
    DOCS_DIR.mkdir(exist_ok=True)
    total_reviews = 0

    for numeric_id in PROFESSOR_IDS:
        try:
            prof = fetch_professor(numeric_id)
        except requests.HTTPError as exc:
            print(f"  ! {numeric_id}: HTTP error {exc}")
            continue

        if not prof:
            print(f"  ! {numeric_id}: no teacher data returned")
            continue

        full_name = f"{prof['firstName']} {prof['lastName']}".strip()
        n_reviews = len((prof.get("ratings") or {}).get("edges", []))
        total_reviews += n_reviews

        out_path = DOCS_DIR / f"rmp_{numeric_id}_{slugify(full_name)}.txt"
        out_path.write_text(format_professor(prof), encoding="utf-8")
        print(f"  + {full_name:<28} {n_reviews:>3} reviews -> {out_path.name}")

        time.sleep(0.5)  # be polite to the API

    print(f"\nDone. {total_reviews} total reviews across {len(PROFESSOR_IDS)} professors.")


if __name__ == "__main__":
    main()
