#!/usr/bin/env python3
"""
Build a co-author network from the OpenAlex publication data.

Nodes are William Lober plus his most frequent collaborators (by shared paper
count); edges connect any two authors in that set who share at least one paper,
weighted by the number of shared papers. Restricting to frequent collaborators
keeps the diagram legible -- the full co-author graph has ~900 unique authors.

Reads:
    data/openalex_publications.json

Writes:
    site/coauthor_network.json

Usage:
    python3 scripts/build_coauthor_network.py [min_papers]

min_papers (default 10): minimum number of shared papers with Lober required
for a collaborator to be included as a node.
"""
import json
import re
import sys
from itertools import combinations
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
OPENALEX_PATH = BASE_DIR / "data" / "openalex_publications.json"
OUT_PATH = BASE_DIR / "site" / "coauthor_network.json"

DEFAULT_MIN_PAPERS = 10


def normalize_name(name: str) -> str:
    return re.sub(r"[^a-z]", "", (name or "").lower())


def entity_key(authorship: dict) -> str:
    return authorship.get("id") or ("name:" + normalize_name(authorship.get("name")))


def main():
    min_papers = int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_MIN_PAPERS

    works = json.loads(OPENALEX_PATH.read_text())

    paper_count = {}
    display_name = {}
    papers_by_entity = {}

    for work in works:
        seen = set()
        for a in work.get("authorships", []):
            key = entity_key(a)
            if key in seen:
                continue
            seen.add(key)
            paper_count[key] = paper_count.get(key, 0) + 1
            display_name[key] = a.get("name") or display_name.get(key, "Unknown")
            papers_by_entity.setdefault(key, []).append(work)

    # Identify the ego node (Lober himself) -- the author present on nearly every paper.
    ego_key = max(paper_count, key=lambda k: paper_count[k])
    if "lober" not in normalize_name(display_name[ego_key]):
        raise SystemExit(f"Expected ego author to be Lober, got {display_name[ego_key]!r}")

    node_keys = {ego_key} | {
        k for k, c in paper_count.items() if k != ego_key and c >= min_papers
    }

    nodes = [
        {
            "id": key,
            "name": display_name[key],
            "paper_count": paper_count[key],
            "is_ego": key == ego_key,
        }
        for key in node_keys
    ]
    nodes.sort(key=lambda n: -n["paper_count"])

    edge_weights = {}
    for work in works:
        present = set()
        for a in work.get("authorships", []):
            key = entity_key(a)
            if key in node_keys:
                present.add(key)
        for a, b in combinations(sorted(present), 2):
            edge_weights[(a, b)] = edge_weights.get((a, b), 0) + 1

    links = [
        {"source": a, "target": b, "weight": w}
        for (a, b), w in edge_weights.items()
    ]

    output = {
        "min_papers": min_papers,
        "total_unique_coauthors": len(paper_count) - 1,
        "nodes": nodes,
        "links": links,
    }

    OUT_PATH.write_text(json.dumps(output, indent=2))
    print(f"{len(nodes)} nodes, {len(links)} links (min_papers={min_papers})")
    print(f"Total unique co-authors in full dataset: {output['total_unique_coauthors']}")
    print(f"Saved to {OUT_PATH}")


if __name__ == "__main__":
    main()
