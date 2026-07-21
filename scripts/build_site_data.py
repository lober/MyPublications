#!/usr/bin/env python3
"""
Build the structured publication dataset consumed by the web page.

Reads:
    data/publications.json           (NCBI MyBibliography)
    data/openalex_publications.json  (OpenAlex, has citation counts)

Writes:
    site/data.json

Usage:
    python3 scripts/build_site_data.py
"""
import json
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
NCBI_PATH = BASE_DIR / "data" / "publications.json"
OPENALEX_PATH = BASE_DIR / "data" / "openalex_publications.json"
OUT_PATH = BASE_DIR / "site" / "data.json"

TYPE_LABELS = {
    "article": "Journal Article",
    "preprint": "Preprint",
    "conference-paper": "Conference Paper",
    "conference-abstract": "Conference Abstract",
    "review": "Review",
    "book-chapter": "Book Chapter",
    "letter": "Letter",
    "dataset": "Dataset",
}


def normalize_title(title: str) -> str:
    if not title:
        return ""
    title = title.lower()
    title = re.sub(r"[^a-z0-9]+", " ", title)
    return title.strip()


def short_authors(authors_str: str) -> str:
    if not authors_str:
        return ""
    names = [a.strip() for a in authors_str.split(",") if a.strip()]
    if len(names) > 3:
        return f"{names[0]}, et al."
    return ", ".join(names)


def short_authors_list(authors: list) -> str:
    if not authors:
        return ""
    if len(authors) > 3:
        return f"{authors[0]}, et al."
    return ", ".join(authors)


def main():
    ncbi = json.loads(NCBI_PATH.read_text())
    openalex = json.loads(OPENALEX_PATH.read_text())

    oa_by_pmid = {p["pmid"]: p for p in openalex if p.get("pmid")}
    oa_by_doi = {p["doi"].lower(): p for p in openalex if p.get("doi")}
    oa_by_title = {normalize_title(p["title"]): p for p in openalex if p.get("title")}

    matched_oa_ids = set()
    records = []

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

        work_type = oa_match["type"] if oa_match else "article"
        records.append({
            "title": pub.get("title") or (oa_match["title"] if oa_match else ""),
            "authors": short_authors(pub.get("authors", "")),
            "venue": pub.get("journal") or (oa_match["venue"] if oa_match else ""),
            "year": pub.get("year") or (oa_match["year"] if oa_match else None),
            "type": work_type,
            "type_label": TYPE_LABELS.get(work_type, work_type.replace("-", " ").title() if work_type else "Other"),
            "link": (oa_match["link"] if oa_match else None) or pub.get("url") or "",
            "cited_by_count": oa_match["cited_by_count"] if oa_match else 0,
            "counts_by_year": oa_match["counts_by_year"] if oa_match else {},
        })

    for pub in openalex:
        if pub["id"] in matched_oa_ids:
            continue
        work_type = pub.get("type") or "article"
        records.append({
            "title": pub.get("title") or "",
            "authors": short_authors_list(pub.get("authors", [])),
            "venue": pub.get("venue") or "",
            "year": pub.get("year"),
            "type": work_type,
            "type_label": TYPE_LABELS.get(work_type, work_type.replace("-", " ").title() if work_type else "Other"),
            "link": pub.get("link") or "",
            "cited_by_count": pub.get("cited_by_count") or 0,
            "counts_by_year": pub.get("counts_by_year") or {},
        })

    # Drop records with no usable title.
    records = [r for r in records if r["title"]]
    records.sort(key=lambda r: (r["year"] or 0), reverse=True)

    # Aggregate citation counts per year across all publications.
    year_totals = {}
    for r in records:
        for year, count in r["counts_by_year"].items():
            year_totals[year] = year_totals.get(year, 0) + count

    years_sorted = sorted(year_totals.keys())
    cumulative = []
    running = 0
    for y in years_sorted:
        running += year_totals[y]
        cumulative.append({"year": y, "total": running})

    per_year = [{"year": y, "count": year_totals[y]} for y in years_sorted]

    total_citations = sum(r["cited_by_count"] for r in records)

    output = {
        "generated_publication_count": len(records),
        "total_citations": total_citations,
        "publications": records,
        "citations_per_year": per_year,
        "citations_cumulative": cumulative,
    }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(output, indent=2))
    print(f"Saved {len(records)} publications ({total_citations} total citations) to {OUT_PATH}")


if __name__ == "__main__":
    main()
