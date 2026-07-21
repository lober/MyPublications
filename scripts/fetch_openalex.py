#!/usr/bin/env python3
"""
Fetch publications for an ORCID from OpenAlex, including venue, year, work type,
a link to each paper, and per-year citation counts.

Usage:
    python3 scripts/fetch_openalex.py [orcid]

Defaults to William Lober's ORCID (0000-0002-1053-7501).
"""
import json
import sys
import time
from pathlib import Path

import requests

API_URL = "https://api.openalex.org/works"
HEADERS = {"User-Agent": "mailto:lober@uw.edu"}
OUT_PATH = Path(__file__).resolve().parent.parent / "data" / "openalex_publications.json"
PER_PAGE = 200


def fetch_all(orcid: str) -> list[dict]:
    works = []
    cursor = "*"
    while cursor:
        params = {
            "filter": f"author.orcid:{orcid}",
            "per-page": PER_PAGE,
            "cursor": cursor,
        }
        resp = requests.get(API_URL, params=params, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        works.extend(data["results"])
        cursor = data["meta"].get("next_cursor")
        print(f"  fetched {len(works)} / {data['meta']['count']}")
        if not data["results"]:
            break
        time.sleep(0.2)
    return works


def simplify(work: dict) -> dict:
    primary_location = work.get("primary_location") or {}
    source = primary_location.get("source") or {}

    link = (
        work.get("doi")
        or primary_location.get("landing_page_url")
        or work.get("id")
    )

    counts_by_year = {
        str(c["year"]): c["cited_by_count"] for c in work.get("counts_by_year", [])
    }

    return {
        "id": work.get("id"),
        "title": work.get("display_name"),
        "venue": source.get("display_name"),
        "year": work.get("publication_year"),
        "type": work.get("type"),
        "link": link,
        "cited_by_count": work.get("cited_by_count"),
        "counts_by_year": counts_by_year,
    }


def main():
    orcid = sys.argv[1] if len(sys.argv) > 1 else "0000-0002-1053-7501"
    print(f"Fetching works from OpenAlex for ORCID {orcid}")
    works = fetch_all(orcid)

    publications = [simplify(w) for w in works]
    publications.sort(key=lambda p: (p["year"] or 0), reverse=True)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(publications, indent=2))
    print(f"Saved {len(publications)} publications to {OUT_PATH}")


if __name__ == "__main__":
    main()
