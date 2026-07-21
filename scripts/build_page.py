#!/usr/bin/env python3
"""
Build the final self-contained site/index.html by embedding site/data.json
into site/template.html.

Usage:
    python3 scripts/build_page.py
"""
import json
from datetime import date
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_PATH = BASE_DIR / "site" / "data.json"
TEMPLATE_PATH = BASE_DIR / "site" / "template.html"
OUT_PATH = BASE_DIR / "site" / "index.html"


def main():
    data = json.loads(DATA_PATH.read_text())
    template = TEMPLATE_PATH.read_text()

    html = template.replace("__PUBLICATION_DATA__", json.dumps(data))
    html = html.replace("__GENERATED_DATE__", date.today().isoformat())

    OUT_PATH.write_text(html)
    print(f"Wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
