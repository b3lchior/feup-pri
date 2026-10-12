import json
import os
import queue
import random
import re
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
from collections import Counter

import pandas as pd
import trafilatura

PROCESSED = "../data/processed"
OUTPUT = "../data/scraped/full_reviews.jsonl"
USER_AGENT = "PRrevIews-research-crawler/0.1 (FEUP university student project; respects robots.txt)"
WORKERS = 32
DELAY = 2
MAX_DELAY = 60
TIMEOUT = 15
PAGE_SECONDS = 30
MAX_BYTES = 3_000_000
MIN_WORDS = 150
URL_SAFE = ":/?#[]@!$&'()*+,;=%~"

extract_lock = threading.Lock()
sites_to_crawl = queue.Queue()
results = queue.Queue()
progress = Counter()


def get(url):
    try:
        request = urllib.request.Request(urllib.parse.quote(url, safe=URL_SAFE), headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            body, deadline = b"", time.time() + PAGE_SECONDS
            while len(body) < MAX_BYTES and time.time() < deadline:
                chunk = response.read(65_536)
                if not chunk:
                    break
                body += chunk
            return response.status, response.headers.get_content_type(), body
    except urllib.error.HTTPError as error:
        return error.code, "", b""
    except Exception:
        return None, "", b""


def read_robots(scheme, host):
    code, _, body = get(f"{scheme}://{host}/robots.txt")
    if code is None or code >= 500:
        return None
    parser = urllib.robotparser.RobotFileParser()
    if code == 200:
        parser.parse(body.decode("utf-8", "ignore").splitlines())
    elif code in (401, 403):
        parser.disallow_all = True
    else:
        parser.parse([])
    return parser


def words(text):
    return re.findall(r"\w+", text.lower())


def contains_quote(article, quote):
    quote_words = words(quote)
    article_text = " " + " ".join(words(article)) + " "
    size = min(6, len(quote_words))
    return size > 0 and any(" " + " ".join(quote_words[i:i + size]) + " " in article_text for i in range(len(quote_words) - size + 1))


def extract(body, url):
    with extract_lock:
        try:
            return trafilatura.extract(body, url=url) or ""
        except Exception:
            return ""


def page_status(code, text, quote):
    if code is None:
        return "unreachable"
    if code in (404, 410):
        return "gone"
    if not 200 <= code < 300:
        return f"http_{code}"
    if len(text.split()) < MIN_WORDS:
        return "no_text"
    if contains_quote(text, quote):
        return "full"
    return "no_quote"


def record(review_id, url, status, text):
    return {"reviewId": review_id, "url": url, "status": status, "words": len(text.split()), "text": text if status in ("full", "no_quote") else ""}


def crawl_site(host, pages):
    parser = read_robots(urllib.parse.urlsplit(pages[0][0]).scheme, host)
    delay = max(DELAY, parser.crawl_delay(USER_AGENT) or 0) if parser else DELAY
    for url, reviews in pages:
        code, text, status = None, "", None
        if parser is None:
            status = "unreachable"
        elif delay > MAX_DELAY:
            status = "too_slow"
        elif not parser.can_fetch(USER_AGENT, url):
            status = "robots_disallowed"
        else:
            time.sleep(delay)
            code, content_type, body = get(url)
            if code == 429:
                delay = min(delay * 2, MAX_DELAY)
            if code is not None and 200 <= code < 300 and "html" in content_type:
                text = extract(body, url)
        results.put([record(review_id, url, status or page_status(code, text, quote), text) for review_id, quote in reviews])


def worker():
    while True:
        try:
            host, pages = sites_to_crawl.get_nowait()
        except queue.Empty:
            return
        try:
            crawl_site(host, pages)
        except Exception as error:
            print(f"{host}: {error!r}", flush=True)
        finally:
            results.put(None)


def temporary(status):
    return status == "unreachable" or status.startswith("http_5")


def finished_reviews():
    last_status = {}
    if os.path.exists(OUTPUT):
        with open(OUTPUT, encoding="utf-8") as file:
            for line in file:
                try:
                    item = json.loads(line)
                except json.JSONDecodeError:
                    continue
                last_status[item["reviewId"]] = item["status"]
    return {review_id for review_id, status in last_status.items() if not temporary(status)}


def report(done, total, sites_done, sites_total, start):
    rate = done / (time.time() - start)
    hours_left = (total - done) / rate / 3600
    print(f"{done}/{total} pages | {sites_done}/{sites_total} sites | {rate:.1f} pages/s | about {hours_left:.1f} h left | {dict(progress)}", flush=True)


if __name__ == "__main__":
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None
    reviews = pd.read_json(f"{PROCESSED}/rt_reviews.jsonl", lines=True, dtype=False, convert_dates=False)
    reviews = reviews[reviews["reviewUrl"].str.startswith("http")]
    reviews = reviews[~reviews["reviewId"].isin(finished_reviews())]
    pages = [(url, list(zip(group["reviewId"], group["reviewText"]))) for url, group in reviews.groupby("reviewUrl")]
    random.Random(42).shuffle(pages)
    pages = pages[:limit]
    sites = {}
    for url, page_reviews in pages:
        sites.setdefault(urllib.parse.urlsplit(url).netloc.lower(), []).append((url, page_reviews))
    for host in sorted(sites, key=lambda host: len(sites[host]), reverse=True):
        sites_to_crawl.put((host, sites[host]))
    print(f"{len(pages)} pages to fetch on {len(sites)} sites", flush=True)
    for _ in range(WORKERS):
        threading.Thread(target=worker, daemon=True).start()
    start, done, sites_done = time.time(), 0, 0
    with open(OUTPUT, "a", encoding="utf-8") as output:
        while sites_done < len(sites):
            records = results.get()
            if records is None:
                sites_done += 1
                continue
            for item in records:
                output.write(json.dumps(item, ensure_ascii=False) + "\n")
                progress[item["status"]] += 1
            output.flush()
            done += 1
            if done % 500 == 0 or done == len(pages):
                report(done, len(pages), sites_done, len(sites), start)
