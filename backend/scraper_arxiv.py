import json
import xml.etree.ElementTree as ET
from pathlib import Path

import httpx


ARXIV_API_URL = "https://export.arxiv.org/api/query"
SEARCH_QUERY = "all:battery+materials+ionic+conductivity"
MAX_RESULTS = 30
OUTPUT_PATH = Path(__file__).resolve().parent / "data" / "arxiv_papers.json"
ATOM_NAMESPACE = {"atom": "http://www.w3.org/2005/Atom"}


def fetch_arxiv_feed() -> str:
    params = {
        "search_query": SEARCH_QUERY,
        "start": 0,
        "max_results": MAX_RESULTS,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    }
    with httpx.Client(timeout=30.0, follow_redirects=True) as client:
        response = client.get(ARXIV_API_URL, params=params)
        response.raise_for_status()
        return response.text


def parse_feed(feed_xml: str) -> list[dict]:
    root = ET.fromstring(feed_xml)
    papers: list[dict] = []

    for entry in root.findall("atom:entry", ATOM_NAMESPACE):
        arxiv_url = entry.findtext("atom:id", default="", namespaces=ATOM_NAMESPACE).strip()
        arxiv_id = arxiv_url.rstrip("/").split("/")[-1]
        title = " ".join(
            entry.findtext("atom:title", default="", namespaces=ATOM_NAMESPACE).split()
        )
        abstract = " ".join(
            entry.findtext("atom:summary", default="", namespaces=ATOM_NAMESPACE).split()
        )
        published = entry.findtext("atom:published", default="", namespaces=ATOM_NAMESPACE).strip()
        authors = [
            author.findtext("atom:name", default="", namespaces=ATOM_NAMESPACE).strip()
            for author in entry.findall("atom:author", ATOM_NAMESPACE)
        ]
        year = int(published[:4]) if len(published) >= 4 and published[:4].isdigit() else None

        papers.append(
            {
                "id": f"arxiv_{arxiv_id.replace('/', '_')}",
                "title": title,
                "authors": authors,
                "arxiv_id": arxiv_id,
                "year": year,
                "url": arxiv_url,
                "abstract": abstract,
            }
        )

    return papers


def main() -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    feed_xml = fetch_arxiv_feed()
    papers = parse_feed(feed_xml)

    with OUTPUT_PATH.open("w", encoding="utf-8") as output_file:
        json.dump(papers, output_file, indent=2, ensure_ascii=False)

    print(f"Fetched {len(papers)} papers.")
    print(f"Saved JSON to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
