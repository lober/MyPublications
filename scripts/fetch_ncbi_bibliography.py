#!/usr/bin/env python3
"""
Fetch William Lober's public NCBI MyBibliography and save as data/publications.json.

Usage:
    python3 scripts/fetch_ncbi_bibliography.py
"""
import json
import re
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

BIB_URL = "https://www.ncbi.nlm.nih.gov/myncbi/william.lober.1/bibliography/public/"
HEADERS = {"User-Agent": "Mozilla/5.0"}
OUT_PATH = Path(__file__).resolve().parent.parent / "data" / "publications.json"


def fetch_page(page: int) -> BeautifulSoup:
    resp = requests.get(BIB_URL, params={"page": page}, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return BeautifulSoup(resp.text, "html.parser")


def get_last_page(soup: BeautifulSoup) -> int:
    last_link = soup.select_one('a[href*="page="][href*="last"], a.last-page')
    for a in soup.find_all("a", href=True):
        m = re.search(r"page=(\d+)", a["href"])
        if m and a.get_text(strip=True).lower() in ("last page", "last"):
            return int(m.group(1))
    # Fallback: scan all page links for the max page number found
    pages = [int(m.group(1)) for a in soup.find_all("a", href=True)
             if (m := re.search(r"page=(\d+)", a["href"]))]
    return max(pages) if pages else 1


def parse_citation(div) -> dict:
    docsum = div.select_one(".ncbi-docsum")
    authors = docsum.select_one(".authors")
    authors = authors.get_text(strip=True) if authors else ""

    title_link = docsum.select_one("a")
    title_span = docsum.select_one(".title")
    if title_link:
        title = title_link.get_text(strip=True)
        url = title_link.get("href", "")
    elif title_span:
        title = title_span.get_text(strip=True)
        url = ""
    else:
        title = ""
        url = ""

    journal = docsum.select_one(".source, .journalname")
    journal = journal.get_text(strip=True) if journal else ""

    pubdate = docsum.select_one(".pubdate, .displaydate")
    pubdate = pubdate.get_text(strip=True) if pubdate else ""

    year_match = re.search(r"\d{4}", pubdate)
    year = int(year_match.group(0)) if year_match else None

    doi_span = docsum.select_one(".doi")
    doi = ""
    if doi_span:
        doi_match = re.search(r"10\.\S+", doi_span.get_text())
        if doi_match:
            doi = doi_match.group(0).rstrip(".")

    checkbox = div.select_one("input.citation-check")
    pmid = checkbox.get("pmid") if checkbox else None

    return {
        "authors": authors,
        "title": title,
        "journal": journal,
        "pubdate": pubdate,
        "year": year,
        "doi": doi,
        "pmid": pmid,
        "url": url,
    }


def main():
    first_page = fetch_page(1)
    last_page = get_last_page(first_page)
    print(f"Found {last_page} page(s) of publications")

    publications = []
    for page in range(1, last_page + 1):
        soup = first_page if page == 1 else fetch_page(page)
        citations = soup.select("div.citation-wrap")
        print(f"  page {page}: {len(citations)} citations")
        for div in citations:
            publications.append(parse_citation(div))
        if page < last_page:
            time.sleep(1)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(publications, indent=2))
    print(f"Saved {len(publications)} publications to {OUT_PATH}")


if __name__ == "__main__":
    main()
