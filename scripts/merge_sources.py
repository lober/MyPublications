#!/usr/bin/env python3
"""
Merge the NCBI MyBibliography and OpenAlex publication lists into one table,
marking which source(s) each publication was found in.

Reads:
    data/publications.json           (from fetch_ncbi_bibliography.py)
    data/openalex_publications.json  (from fetch_openalex.py)

Writes:
    data/merged_publications.json

Usage:
    python3 scripts/merge_sources.py
"""
import json
import re
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
NCBI_PATH = DATA_DIR / "publications.json"
OPENALEX_PATH = DATA_DIR / "openalex_publications.json"
OUT_PATH = DATA_DIR / "merged_publications.json"


def normalize_title(title: str) -> str:
    if not title:
        return ""
    title = title.lower()
    title = re.sub(r"[^a-z0-9]+", " ", title)
    return title.strip()


def ncbi_citation(pub: dict) -> str:
    parts = [p for p in [pub.get("authors"), pub.get("title"), pub.get("journal"), pub.get("pubdate")] if p]
    return " ".join(parts).strip()


def openalex_citation(pub: dict) -> str:
    parts = [p for p in [pub.get("title"), pub.get("venue"), str(pub.get("year") or "")] if p]
    return ". ".join(parts).strip()


def main():
    ncbi = json.loads(NCBI_PATH.read_text())
    openalex = json.loads(OPENALEX_PATH.read_text())

    # Index OpenAlex records by pmid, doi, and normalized title for matching.
    oa_by_pmid = {p["pmid"]: p for p in openalex if p.get("pmid")}
    oa_by_doi = {p["doi"].lower(): p for p in openalex if p.get("doi")}
    oa_by_title = {normalize_title(p["title"]): p for p in openalex if p.get("title")}

    matched_oa_ids = set()
    merged = []

    for pub in ncbi:
        oa_match = None
        if pub.get("pmid") and pub["pmid"] in oa_by_pmid:
            oa_match = oa_by_pmid[pub["pmid"]]
        elif pub.get("doi") and pub["doi"].lower() in oa_by_doi:
            oa_match = oa_by_doi[pub["doi"].lower()]
        elif normalize_title(pub.get("title")) in oa_by_title:
            oa_match = oa_by_title[normalize_title(pub.get("title"))]

        if oa_match:
            matched_oa_ids.add(oa_match["id"])

        merged.append({
            "citation": ncbi_citation(pub),
            "year": pub.get("year") or (oa_match["year"] if oa_match else None),
            "in_ncbi": "Y",
            "in_openalex": "Y" if oa_match else "",
            "cited_by_count": oa_match["cited_by_count"] if oa_match else None,
            "counts_by_year": oa_match["counts_by_year"] if oa_match else {},
            "link": oa_match["link"] if oa_match else pub.get("url"),
            "in_summary": "",
        })

    # Any OpenAlex records not matched to an NCBI record.
    for pub in openalex:
        if pub["id"] in matched_oa_ids:
            continue
        merged.append({
            "citation": openalex_citation(pub),
            "year": pub.get("year"),
            "in_ncbi": "",
            "in_openalex": "Y",
            "cited_by_count": pub.get("cited_by_count"),
            "counts_by_year": pub.get("counts_by_year") or {},
            "link": pub.get("link"),
            "in_summary": "",
        })

    merged.sort(key=lambda p: (p["year"] or 0), reverse=True)

    OUT_PATH.write_text(json.dumps(merged, indent=2))

    both = sum(1 for p in merged if p["in_ncbi"] == "Y" and p["in_openalex"] == "Y")
    ncbi_only = sum(1 for p in merged if p["in_ncbi"] == "Y" and p["in_openalex"] != "Y")
    oa_only = sum(1 for p in merged if p["in_ncbi"] != "Y" and p["in_openalex"] == "Y")
    print(f"Total merged: {len(merged)}")
    print(f"  In both sources: {both}")
    print(f"  NCBI only: {ncbi_only}")
    print(f"  OpenAlex only: {oa_only}")
    print(f"Saved to {OUT_PATH}")


if __name__ == "__main__":
    main()
