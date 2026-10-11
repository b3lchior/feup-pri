#!/usr/bin/env python3
"""Extract as much information as possible about films from Wikipedia (one file, Wikipedia only).

Install:   pip install requests beautifulsoup4
Set a User-Agent with your email (Wikimedia asks for it):
           export FILM_USER_AGENT="FilmProject/1.0 (your.email@example.com)"

Usage
    python wikipedia_film.py "Ex Machina (film)" "Memento (film)"          # exact article titles
    python wikipedia_film.py --search "Ex Machina" "Memento"               # find the article first
    python wikipedia_film.py --category "Category:2000s black comedy films" --limit 50
    python wikipedia_film.py --titles-file titles.txt --out films.jsonl
    python wikipedia_film.py --search "Ex Machina" "Memento" --db films.db      # also fill SQL tables
    python wikipedia_film.py --category "Category:2000s black comedy films" --db films.db --no-jsonl

Per film you get (JSON):
    title, url, year, short_description, wikidata_id (the id only, no Wikidata calls)
    infobox       raw key/value pairs (Directed by, Starring, Running time, Budget, Box office...)
    facts         cleaned infobox: directors, writers, cast, runtime_minutes, countries, languages...
    text          lead, plot, cast, production, release, reception, themes (canonical sections)
    sections      every section of the article as clean text
    cast_list     [{"actor": ..., "character": ..., "note": ...}] parsed from the Cast section
    categories    e.g. "Films about amnesia", "2014 science fiction films"
    external      imdb_id, rotten_tomatoes_url, metacritic_url, ... (handy to join with Rotten Tomatoes)
    languages     titles of the article in other Wikipedia languages
Downloads are cached in ./wiki_cache so you can stop and re-run at any time.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

USER_AGENT = os.environ.get(
    "FILM_USER_AGENT", "FilmProject/1.0 (set the FILM_USER_AGENT env var with your email)")
CACHE_DIR = Path(os.environ.get("FILM_CACHE_DIR", "wiki_cache"))
API = "https://{lang}.wikipedia.org/w/api.php"

SKIP_SECTIONS = {
    "references", "external links", "see also", "notes", "further reading", "bibliography",
    "footnotes", "sources", "citations", "works cited", "explanatory notes", "general references",
}
CANONICAL = {  # canonical field -> lower-cased section titles that feed it
    "plot": ["plot", "synopsis", "plot summary", "plot synopsis", "premise", "summary", "story"],
    "cast": ["cast", "cast and characters", "voice cast", "characters", "cast and crew"],
    "production": ["production", "development", "filming", "casting", "pre-production",
                   "principal photography", "visual effects", "music", "soundtrack", "writing", "design"],
    "release": ["release", "marketing", "home media", "theatrical release", "distribution"],
    "reception": ["reception", "critical reception", "critical response", "reviews", "box office"],
    "themes": ["themes", "analysis", "interpretation", "style", "themes and analysis",
               "themes and interpretations"],
}
REMOVE_SELECTORS = [
    "sup.reference", "sup.noprint", "sup.Inline-Template", "style", "script", "div.navbox",
    "div.hatnote", "div.reflist", "div.refbegin", "div.mw-references-wrap", "div.thumb", "figure",
    "div.gallery", "div.side-box", "div.sistersitebox", "div.ambox", ".mw-editsection", ".noprint",
    ".mw-empty-elt", "span.mw-cite-backlink",
]
HEADING_TAGS = ["h2", "h3", "h4", "h5", "h6"]


# ============================================================================ HTTP + cache

class Client:
    def __init__(self, lang: str = "en", delay: float = 0.3):
        self.lang, self.delay, self._last = lang, delay, 0.0
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT, "Accept-Encoding": "gzip"})
        retry = Retry(total=6, backoff_factor=2, status_forcelist=(429, 500, 502, 503, 504),
                      allowed_methods=("GET",), respect_retry_after_header=True)
        self.session.mount("https://", HTTPAdapter(max_retries=retry))

    def get(self, **params) -> dict:
        wait = self.delay - (time.monotonic() - self._last)
        if wait > 0:
            time.sleep(wait)
        params.update(format="json", formatversion=2)
        r = self.session.get(API.format(lang=self.lang), params=params, timeout=90)
        self._last = time.monotonic()
        r.raise_for_status()
        return r.json()


def _cache_file(lang: str, title: str) -> Path:
    digest = hashlib.sha1(f"{lang}:{title}".encode()).hexdigest()[:8]
    slug = re.sub(r"[^A-Za-z0-9._-]+", "_", title)[:100]
    return CACHE_DIR / f"{lang}__{slug}__{digest}.json"


# ============================================================================ HTML parsing

def clean(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("\xa0", " ")).strip()


def tidy_punctuation(text: str) -> str:
    text = re.sub(r"\s+([,.;:!?%)\]])", r"\1", text)   # "Lisbon , Portugal ." -> "Lisbon, Portugal."
    return re.sub(r"([(\[])\s+", r"\1", text)


def cell_values(td):
    for br in td.find_all("br"):
        br.replace_with("\n")
    items = [clean(li.get_text(" ")) for li in td.find_all("li")]
    if not items:
        items = [clean(p) for p in td.get_text(" ").split("\n")]
    items = [tidy_punctuation(i) for i in items if i]
    if not items:
        return None
    return items[0] if len(items) == 1 else items


def parse_infobox(root) -> dict:
    infobox = {}
    box = root.select_one("table.infobox")
    if box is not None:
        for row in box.select("tr"):
            th, td = row.find("th"), row.find("td")
            if th is not None and td is not None:
                key, value = clean(th.get_text(" ")), cell_values(td)
                if key and value:
                    infobox[key] = value
    return infobox


def heading_of(el):
    if el.name in HEADING_TAGS:
        return el.name, clean(el.get_text(" "))
    if el.name == "div" and "mw-heading" in (el.get("class") or []):
        h = el.find(HEADING_TAGS)
        if h is not None:
            return h.name, clean(h.get_text(" "))
    return None


class Sections:
    def __init__(self):
        self.data = {"Lead": []}
        self.current = "Lead"

    def heading(self, tag, title):
        if tag == "h2":
            self.current = title
            self.data.setdefault(title, [])
        elif title:
            self.data[self.current].append(f"{title}:")      # sub-headings stay as inline labels

    def add(self, line):
        if line:
            self.data[self.current].append(line)


def emit_list(el, state: Sections):
    """One line per list item; nested lists become their own lines (not glued to the parent)."""
    for li in el.find_all("li", recursive=False):
        nested = [sub.extract() for sub in li.find_all(["ul", "ol"], recursive=False)]
        state.add("- " + clean(li.get_text(" ")))
        for sub in nested:
            emit_list(sub, state)


def walk(node, state: Sections):
    for el in node.find_all(recursive=False):
        h = heading_of(el)
        if h:
            state.heading(*h)
        elif el.name in ("div", "section"):
            walk(el, state)
        elif el.name == "p":
            state.add(clean(el.get_text(" ")))
        elif el.name in ("ul", "ol"):
            emit_list(el, state)
        elif el.name == "dl":
            for item in el.find_all(["dt", "dd"]):
                state.add(clean(item.get_text(" ")))
        elif el.name == "blockquote":
            state.add(clean(el.get_text(" ")))


def parse_html(html: str):
    soup = BeautifulSoup(html, "html.parser")
    root = soup.select_one("div.mw-parser-output") or soup
    for sel in REMOVE_SELECTORS:
        for tag in root.select(sel):
            tag.decompose()
    infobox = parse_infobox(root)                  # before tables are removed
    for tag in root.select("table"):
        tag.decompose()
    state = Sections()
    walk(root, state)
    sections = {t: tidy_punctuation("\n".join(lines)).strip() for t, lines in state.data.items()
                if t.lower() not in SKIP_SECTIONS and any(lines)}
    return infobox, sections


def canonical_text(sections: dict) -> dict:
    out = {"lead": sections.get("Lead", "")}
    for field, names in CANONICAL.items():
        out[field] = "\n\n".join(t for title, t in sections.items() if title.lower() in names)
    return out


# ============================================================================ derived facts

def as_list(v) -> list:
    return [] if v is None else (v if isinstance(v, list) else [v])


def find_key(infobox: dict, *needles) -> list:
    for key, value in infobox.items():
        if any(n in key.lower() for n in needles):
            return as_list(value)
    return []


def parse_cast(cast_text: str) -> list:
    """'- Alicia Vikander as Ava, an android' -> {'actor','character','note'} (best effort)."""
    result = []
    for line in cast_text.splitlines():
        if not line.startswith("- "):
            continue
        line = line[2:].strip()
        if " as " in line:
            actor, rest = line.split(" as ", 1)
            m = re.search(r",\s|\s[–—-]\s", rest)
            character, note = (rest[:m.start()], rest[m.end():]) if m else (rest, "")
            result.append({"actor": actor.strip(), "character": character.strip(), "note": note.strip()})
        else:
            result.append({"actor": line, "character": "", "note": ""})
    return result


def runtime_minutes(infobox: dict):
    for value in find_key(infobox, "running time", "runtime"):
        m = re.search(r"(\d+)\s*min", value)
        if m:
            return int(m.group(1))
        m = re.search(r"(\d+)\s*h\w*\s*(\d+)?", value)
        if m:
            return int(m.group(1)) * 60 + int(m.group(2) or 0)
    return None


def guess_year(title: str, categories: list, infobox: dict, lead: str):
    for c in categories:                                  # "2014 films" is the most reliable
        m = re.fullmatch(r"(\d{4}) films", c)
        if m:
            return int(m.group(1))
    m = re.search(r"\((\d{4}) \w*\s?film\)", title)
    if m:
        return int(m.group(1))
    for value in find_key(infobox, "release"):
        m = re.search(r"\b(1[89]\d\d|20\d\d)\b", value)
        if m:
            return int(m.group(1))
    m = re.search(r"\b(1[89]\d\d|20\d\d)\b", lead)
    return int(m.group(1)) if m else None


def external_ids(urls: list) -> dict:
    out = {}
    for u in urls:
        if m := re.search(r"imdb\.com/title/(tt\d+)", u):
            out.setdefault("imdb_id", m.group(1))
        elif "rottentomatoes.com/m/" in u:
            out.setdefault("rotten_tomatoes_url", u)
        elif "metacritic.com/movie/" in u:
            out.setdefault("metacritic_url", u)
        elif "boxofficemojo.com" in u:
            out.setdefault("box_office_mojo_url", u)
        elif "letterboxd.com/film/" in u:
            out.setdefault("letterboxd_url", u)
        elif "allmovie.com" in u:
            out.setdefault("allmovie_url", u)
    return out


def prop(props, name):
    if isinstance(props, dict):
        return props.get(name)
    for p in props or []:
        if p.get("name") == name:
            return p.get("*") or p.get("value")
    return None


def build_record(parse: dict, lang: str) -> dict:
    html = parse["text"]
    html = html.get("*", "") if isinstance(html, dict) else html
    infobox, sections = parse_html(html)
    text = canonical_text(sections)
    props = parse.get("properties")
    title = parse["title"]

    categories = []
    for c in parse.get("categories", []):
        hidden = bool(c.get("hidden")) or c.get("hidden") == ""
        name = c.get("category") or c.get("*")
        if name and not hidden:
            categories.append(name.replace("_", " "))
    languages = {l["lang"]: (l.get("title") or l.get("*")) for l in parse.get("langlinks", []) if l.get("lang")}
    ext_urls = parse.get("externallinks", [])

    facts = {
        "directors": find_key(infobox, "directed by"),
        "writers": find_key(infobox, "written by", "screenplay by", "story by"),
        "producers": find_key(infobox, "produced by"),
        "cast": find_key(infobox, "starring"),
        "music": find_key(infobox, "music by"),
        "cinematography": find_key(infobox, "cinematography"),
        "editors": find_key(infobox, "edited by"),
        "production_companies": find_key(infobox, "production compan"),
        "distributors": find_key(infobox, "distributed by"),
        "release_dates": find_key(infobox, "release date"),
        "runtime_minutes": runtime_minutes(infobox),
        "countries": find_key(infobox, "countr"),
        "languages": find_key(infobox, "language"),
        "budget": find_key(infobox, "budget"),
        "box_office": find_key(infobox, "box office"),
        "based_on": find_key(infobox, "based on"),
    }
    return {
        "title": title,
        "pageid": parse.get("pageid"),
        "revid": parse.get("revid"),
        "url": f"https://{lang}.wikipedia.org/wiki/{quote(title.replace(' ', '_'))}",
        "lang": lang,
        "year": guess_year(title, categories, infobox, text["lead"]),
        "short_description": prop(props, "wikibase-shortdesc"),
        "wikidata_id": prop(props, "wikibase_item"),
        "is_disambiguation": prop(props, "disambiguation") is not None,
        "infobox": infobox,
        "facts": facts,
        "text": text,
        "sections": sections,
        "cast_list": parse_cast(text["cast"]),
        "plot_word_count": len(text["plot"].split()),
        "categories": categories,
        "external": external_ids(ext_urls),
        "external_links": ext_urls,
        "languages": languages,
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


# ============================================================================ API calls

def fetch_film(client: Client, title: str, use_cache: bool = True):
    """Download + parse one article. Returns None if the page does not exist."""
    path = _cache_file(client.lang, title)
    if use_cache and path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    data = client.get(action="parse", page=title, redirects=1,
                      prop="text|categories|properties|langlinks|externallinks|revid",
                      disableeditsection=1, disabletoc=1, disablelimitreport=1)
    if "error" in data:
        return None
    record = build_record(data["parse"], client.lang)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
    return record


def search_title(client: Client, query: str):
    """Best matching article title for a free-text query, preferring pages about films."""
    data = client.get(action="query", list="search", srsearch=f"{query} film", srlimit=5, srnamespace=0)
    hits = [h["title"] for h in data.get("query", {}).get("search", [])]
    for h in hits:                       # prefer "X (film)" / "X (2014 film)"
        if "film)" in h and query.lower() in h.lower():
            return h
    return hits[0] if hits else None


def resolve_and_fetch_film(client: Client, query: str, use_cache: bool = True):
    """Fetch an exact page title first; use Wikipedia search only when it is missing."""
    record = fetch_film(client, query, use_cache=use_cache)
    if record is not None and not record["is_disambiguation"]:
        return record
    title = search_title(client, query)
    if not title or title == query:
        return record
    return fetch_film(client, title, use_cache=use_cache)


def category_members(client: Client, category: str, limit: int = 0) -> list:
    """Article titles inside a Wikipedia category (no sub-categories)."""
    if not category.lower().startswith("category:"):
        category = "Category:" + category
    titles, cont = [], {}
    while True:
        data = client.get(action="query", list="categorymembers", cmtitle=category,
                          cmtype="page", cmlimit=500, **cont)
        titles += [m["title"] for m in data.get("query", {}).get("categorymembers", [])]
        if limit and len(titles) >= limit:
            return titles[:limit]
        if "continue" not in data:
            return titles
        cont = data["continue"]


# ============================================================================ SQLite

SCHEMA = """
CREATE TABLE IF NOT EXISTS films (
    film_id          INTEGER PRIMARY KEY,   -- Wikipedia page id
    title            TEXT NOT NULL,
    year             INTEGER,
    url              TEXT,
    short_description TEXT,
    wikidata_id      TEXT,
    runtime_minutes  INTEGER,
    lead             TEXT,
    plot             TEXT,
    cast_text        TEXT,
    production_text  TEXT,
    release_text     TEXT,
    reception_text   TEXT,
    themes_text      TEXT,
    plot_word_count  INTEGER,
    revid            INTEGER,
    fetched_at       TEXT
);
CREATE TABLE IF NOT EXISTS film_facts (film_id INTEGER, field TEXT, value TEXT);      -- directors, writers, countries, budget...
CREATE TABLE IF NOT EXISTS cast_members (film_id INTEGER, position INTEGER, actor TEXT, character TEXT, note TEXT);
CREATE TABLE IF NOT EXISTS categories (film_id INTEGER, category TEXT);
CREATE TABLE IF NOT EXISTS sections (film_id INTEGER, position INTEGER, title TEXT, body TEXT);
CREATE TABLE IF NOT EXISTS infobox (film_id INTEGER, field TEXT, value TEXT);         -- raw infobox rows
CREATE TABLE IF NOT EXISTS external_ids (film_id INTEGER, source TEXT, value TEXT);   -- imdb_id, rotten_tomatoes_url...
CREATE TABLE IF NOT EXISTS languages (film_id INTEGER, lang TEXT, title TEXT);
CREATE INDEX IF NOT EXISTS idx_facts_film ON film_facts(film_id);
CREATE INDEX IF NOT EXISTS idx_facts_field ON film_facts(field, value);
CREATE INDEX IF NOT EXISTS idx_cast_film ON cast_members(film_id);
CREATE INDEX IF NOT EXISTS idx_cast_actor ON cast_members(actor);
CREATE INDEX IF NOT EXISTS idx_cat_film ON categories(film_id);
CREATE INDEX IF NOT EXISTS idx_cat_name ON categories(category);
CREATE INDEX IF NOT EXISTS idx_sec_film ON sections(film_id);
CREATE INDEX IF NOT EXISTS idx_info_film ON infobox(film_id);
CREATE INDEX IF NOT EXISTS idx_ext_film ON external_ids(film_id);
CREATE INDEX IF NOT EXISTS idx_lang_film ON languages(film_id);
"""
CHILD_TABLES = ["film_facts", "cast_members", "categories", "sections", "infobox",
                "external_ids", "languages"]


def open_db(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.executescript(SCHEMA)
    return conn


def save_to_db(conn: sqlite3.Connection, r: dict) -> None:
    """Insert (or replace) one film and all its related rows. Safe to re-run."""
    fid, t = r["pageid"], r["text"]
    for table in CHILD_TABLES:
        conn.execute(f"DELETE FROM {table} WHERE film_id = ?", (fid,))
    conn.execute(
        """INSERT OR REPLACE INTO films (film_id, title, year, url, short_description, wikidata_id,
               runtime_minutes, lead, plot, cast_text, production_text, release_text, reception_text,
               themes_text, plot_word_count, revid, fetched_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (fid, r["title"], r["year"], r["url"], r["short_description"], r["wikidata_id"],
         r["facts"]["runtime_minutes"], t["lead"], t["plot"], t["cast"], t["production"], t["release"],
         t["reception"], t["themes"], r["plot_word_count"], r["revid"], r["fetched_at"]))
    for field, values in r["facts"].items():
        if field != "runtime_minutes":
            conn.executemany("INSERT INTO film_facts VALUES (?,?,?)", [(fid, field, v) for v in as_list(values)])
    conn.executemany("INSERT INTO cast_members VALUES (?,?,?,?,?)",
                     [(fid, i, c["actor"], c["character"], c["note"]) for i, c in enumerate(r["cast_list"], 1)])
    conn.executemany("INSERT INTO categories VALUES (?,?)", [(fid, c) for c in r["categories"]])
    conn.executemany("INSERT INTO sections VALUES (?,?,?,?)",
                     [(fid, i, title, body) for i, (title, body) in enumerate(r["sections"].items(), 1)])
    conn.executemany("INSERT INTO infobox VALUES (?,?,?)",
                     [(fid, k, v) for k, vals in r["infobox"].items() for v in as_list(vals)])
    conn.executemany("INSERT INTO external_ids VALUES (?,?,?)", [(fid, k, v) for k, v in r["external"].items()])
    conn.executemany("INSERT INTO languages VALUES (?,?,?)", [(fid, k, v) for k, v in r["languages"].items()])


# ============================================================================ CLI

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("titles", nargs="*", help="article titles (or search words with --search)")
    ap.add_argument("--search", action="store_true", help="treat the arguments as search queries")
    ap.add_argument("--category", help='e.g. "Category:2000s black comedy films"')
    ap.add_argument("--titles-file", help="text file with one title per line")
    ap.add_argument("--lang", default="en")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--delay", type=float, default=0.3, help="seconds between requests")
    ap.add_argument("--refresh", action="store_true", help="ignore cache")
    ap.add_argument("--out", default="films.jsonl", help="JSONL output file")
    ap.add_argument("--progress", help="checkpoint file (defaults to <out>.progress.jsonl)")
    ap.add_argument("--overwrite", action="store_true",
                     help="start a fresh output and checkpoint instead of resuming")
    ap.add_argument("--db", help="also save everything into this SQLite database, e.g. films.db")
    ap.add_argument("--no-jsonl", action="store_true", help="do not write the JSONL file")
    args = ap.parse_args()

    client = Client(args.lang, args.delay)
    titles = list(args.titles)
    if args.titles_file:
        titles += [l.strip() for l in Path(args.titles_file).read_text(encoding="utf-8").splitlines() if l.strip()]
    if args.category:
        titles += category_members(client, args.category, args.limit)
    if args.limit:
        titles = titles[: args.limit]
    if not titles:
        sys.exit("Nothing to do. Pass titles, --titles-file or --category (see --help).")

    output_path = Path(args.out)
    progress_path = Path(args.progress) if args.progress else Path(args.out + ".progress.jsonl")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    progress_path.parent.mkdir(parents=True, exist_ok=True)
    if args.overwrite:
        output_path.write_text("", encoding="utf-8")
        progress_path.write_text("", encoding="utf-8")

    # A progress row records the input query and its outcome. Successful and
    # permanent misses are skipped on resume; transient request errors are not.
    completed_queries = set()
    if progress_path.exists():
        with progress_path.open(encoding="utf-8") as progress_file:
            for line in progress_file:
                try:
                    row = json.loads(line)
                    if row.get("status") in {"saved", "not_found", "disambiguation"}:
                        completed_queries.add(row["query"])
                except (json.JSONDecodeError, KeyError):
                    continue

    existing_records = {}
    if not args.no_jsonl and output_path.exists():
        with output_path.open(encoding="utf-8") as existing_file:
            for line in existing_file:
                try:
                    record = json.loads(line)
                    if record.get("pageid") is not None:
                        existing_records[record["pageid"]] = record
                        # Supports resuming outputs created before checkpoints
                        # existed, where the original query was not recorded.
                        completed_queries.add(record.get("title", ""))
                except json.JSONDecodeError:
                    continue

    done, failed = 0, []
    out = None if args.no_jsonl else output_path.open("a", encoding="utf-8")
    progress = progress_path.open("a", encoding="utf-8")
    conn = open_db(args.db) if args.db else None
    try:
        for i, t in enumerate(titles, 1):
            if t in completed_queries:
                continue
            try:
                if args.search:
                    record = resolve_and_fetch_film(client, t, use_cache=not args.refresh)
                else:
                    record = fetch_film(client, t, use_cache=not args.refresh)
            except requests.RequestException as exc:
                failed.append((t, repr(exc)))
                progress.write(json.dumps({"query": t, "status": "request_error",
                                           "error": repr(exc)}, ensure_ascii=False) + "\n")
                progress.flush()
                continue
            if record is None:
                failed.append((t, "not found"))
                progress.write(json.dumps({"query": t, "status": "not_found"}, ensure_ascii=False) + "\n")
                progress.flush()
                continue
            if record["is_disambiguation"]:
                failed.append((t, "disambiguation page"))
                progress.write(json.dumps({"query": t, "status": "disambiguation",
                                           "title": record["title"]}, ensure_ascii=False) + "\n")
                progress.flush()
                continue
            if out and record["pageid"] not in existing_records:
                out.write(json.dumps(record, ensure_ascii=False) + "\n")
                out.flush()
            existing_records[record["pageid"]] = record
            if conn:
                save_to_db(conn, record)
                conn.commit()
            progress.write(json.dumps({"query": t, "status": "saved",
                                       "title": record["title"], "pageid": record["pageid"]},
                                      ensure_ascii=False) + "\n")
            progress.flush()
            completed_queries.add(t)
            done += 1
            print(f"[{i}/{len(titles)}] {record['title']} ({record['year']}) - "
                  f"plot {record['plot_word_count']} words, {len(record['categories'])} categories")
    finally:
        if out:
            out.close()
        progress.close()
        if conn:
            conn.close()
    where = ", ".join(x for x in ([None if args.no_jsonl else str(output_path)] + [args.db]) if x)
    print(f"\nSaved {done} films to {where}")
    for t, why in failed:
        print(f"  skipped: {t} ({why})")


if __name__ == "__main__":
    main()
