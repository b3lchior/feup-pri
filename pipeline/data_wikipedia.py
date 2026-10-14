"""Download English Wikipedia article extracts for linked films."""

import json
import time
import urllib.error
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pandas as pd

LINKED = "../data/linked/film_links.jsonl"
OUTPUT = "../data/raw/wikipedia/film_articles.jsonl"
API = "https://en.wikipedia.org/w/api.php"
USER_AGENT = "PRevIews/0.1 (https://github.com/b3lchior/feup-pri)"
BATCH_SIZE = 1
RETRIES = 4


def fetch_batch(titles):
    params = {
        "action": "query",
        "prop": "extracts|info",
        "exlimit": len(titles),
        "explaintext": 1,
        "inprop": "url",
        "redirects": 1,
        "titles": "|".join(titles),
        "format": "json",
        "formatversion": 2,
    }
    request = Request(
        f"{API}?{urlencode(params)}",
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
    )
    for attempt in range(RETRIES):
        try:
            with urlopen(request, timeout=60) as response:
                result = json.load(response)
            break
        except (urllib.error.HTTPError, urllib.error.URLError):
            if attempt == RETRIES - 1:
                raise
            time.sleep(2**attempt)

    pages = result.get("query", {}).get("pages", [])
    aliases = {}
    for section in ("normalized", "redirects"):
        for item in result.get("query", {}).get(section, []):
            aliases[item["from"]] = item["to"]
    by_title = {page["title"]: page for page in pages}
    records = {}
    for requested in titles:
        canonical = requested
        while canonical in aliases:
            canonical = aliases[canonical]
        page = by_title.get(canonical)
        if page and not page.get("missing"):
            records[requested] = {
                "wikipedia_title": page["title"],
                "wikipedia_url": page.get("fullurl", ""),
                "wikipedia_page_id": page.get("pageid"),
                "wikipedia_revision_id": page.get("lastrevid"),
                "wikipedia_extract": page.get("extract", ""),
            }
        else:
            records[requested] = {
                "wikipedia_title": requested,
                "wikipedia_url": "",
                "wikipedia_page_id": None,
                "wikipedia_revision_id": None,
                "wikipedia_extract": "",
            }
    return records


def main():
    films = pd.read_json(LINKED, lines=True, dtype=False, convert_dates=False)
    films = films.drop_duplicates("wikidata_id")
    titles = sorted(set(films["wikipedia_title"].dropna()) - {""})
    fetched = {}
    for start in range(0, len(titles), BATCH_SIZE):
        fetched.update(fetch_batch(titles[start:start + BATCH_SIZE]))
        print(f"Wikipedia: fetched {min(start + BATCH_SIZE, len(titles))}/{len(titles)} titles")
        time.sleep(0.1)

    with open(OUTPUT, "w", encoding="utf-8") as output:
        for row in films.itertuples(index=False):
            title = row.wikipedia_title if isinstance(row.wikipedia_title, str) else ""
            article = fetched.get(title, {
                "wikipedia_title": "",
                "wikipedia_url": "",
                "wikipedia_page_id": None,
                "wikipedia_revision_id": None,
                "wikipedia_extract": "",
            })
            record = {
                "imdb_id": row.imdb_id,
                "wikidata_id": row.wikidata_id,
                **article,
            }
            output.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(f"Wikipedia: saved {len(films)} film records to {OUTPUT}")


if __name__ == "__main__":
    main()
