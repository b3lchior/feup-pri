import json
import time
import urllib.parse
import urllib.request

import pandas as pd
from utils import read_columns

RAW = "../data/raw"
API = "https://www.wikidata.org/w/api.php"
USER_AGENT = "PRrevIews/0.1 (https://github.com/b3lchior/feup-pri)"
BATCH = 50
RETRIES = 4


def english_titles(items):
    query = urllib.parse.urlencode({"action": "wbgetentities", "ids": "|".join(items), "props": "sitelinks", "sitefilter": "enwiki", "format": "json"})
    request = urllib.request.Request(f"{API}?{query}", headers={"User-Agent": USER_AGENT})
    for attempt in range(RETRIES):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                entities = json.load(response)["entities"]
            break
        except OSError:
            if attempt == RETRIES - 1:
                raise
            time.sleep(2 ** attempt)
    return [entities.get(item, {}).get("sitelinks", {}).get("enwiki", {}).get("title", "") for item in items]


if __name__ == "__main__":
    movies = read_columns(f"{RAW}/imdb_spoiler/IMDB_movie_details.json", ["movie_id"])["movie_id"].str.rstrip("/")
    links = pd.read_csv(f"{RAW}/wikidata/links.csv", dtype=str, keep_default_na=False)
    items = sorted(set(links.loc[links["imdb_id"].isin(movies), "film"].str.removeprefix("http://www.wikidata.org/entity/")))
    titles = [title for start in range(0, len(items), BATCH) for title in english_titles(items[start:start + BATCH])]
    pd.DataFrame({"wikidata_id": items, "wikipedia_title": titles}).to_csv(f"{RAW}/wikidata/wikipedia_titles.csv", index=False)
