import html
import json
import os
import re
from collections import Counter

import pandas as pd
from utils import append_jsonl, contains_quote, log, write_jsonl, write_stats

RAW = "../data/raw"
LINKED = "../data/linked"
PROCESSED = "../data/processed"
SCRAPED = "../data/scraped/full_reviews.jsonl"

PLACEHOLDER = r"(full review|click|see (the )?full|for (the )?full|read (the )?(full|complete|my|our|more)|review in|podcast review|parental content review|\(?no quote available)"
TRANSLATED = r"\s*\[full review in [^\]]*\]\s*$"
GRADES = ["F", "D-", "D", "D+", "C-", "C", "C+", "B-", "B", "B+", "A-", "A", "A+"]
MONEY = {"": 1, "K": 1_000, "M": 1_000_000, "B": 1_000_000_000}
LAYOUT = r"(?:\|[ \t-]*){2,}"
MIN_WORDS = 150


def decode_html(text):
    return text.fillna("").map(html.unescape).str.strip()


def tidy_text(text):
    return re.sub(r"[ \t]{2,}", " ", re.sub(LAYOUT, " ", text)).strip()


def normalize_score(score):
    score = score.strip().upper().replace(" MINUS", "-").replace(" PLUS", "+")
    if score in GRADES:
        return round(GRADES.index(score) / (len(GRADES) - 1), 3)
    match = re.fullmatch(r"(\d*\.?\d+)\s*(?:/|OF|OUT OF)\s*(\d*\.?\d+)", score)
    if match and 0 < float(match[2]) and float(match[1]) <= float(match[2]):
        return round(float(match[1]) / float(match[2]), 3)
    return None


def minutes(duration):
    match = re.fullmatch(r"(?:(\d+)h)?\s*(?:(\d+)min)?", duration.strip())
    return int(match[1] or 0) * 60 + int(match[2] or 0)


def split_list(text):
    return [part.strip() for part in text.split(",") if part.strip()]


def dollars(text):
    match = re.fullmatch(r"\$([\d.]+)([KMB]?)", text.strip())
    return round(float(match[1]) * MONEY[match[2]]) if match else None


def clean_rt_reviews():
    reviews = pd.read_json(f"{LINKED}/rt_reviews.jsonl", lines=True, dtype=False, convert_dates=False)
    log("rt_reviews", "linked", len(reviews))
    reviews["reviewText"] = decode_html(reviews["reviewText"])
    reviews = reviews.drop_duplicates()
    log("rt_reviews", "without exact duplicates", len(reviews))
    reviews = reviews[reviews["reviewText"] != ""]
    log("rt_reviews", "without empty reviews", len(reviews))
    placeholder = reviews["reviewText"].str.lower().str.match(PLACEHOLDER) | ~reviews["reviewText"].str.contains(r"[^\W\d_]")
    reviews = reviews[~placeholder]
    log("rt_reviews", "without placeholder texts", len(reviews))
    reviews["translated"] = reviews["reviewText"].str.contains(TRANSLATED, case=False)
    reviews["reviewText"] = reviews["reviewText"].str.replace(TRANSLATED, "", case=False, regex=True)
    fake_date = (reviews["creationDate"] == "2000-01-01") | (reviews["creationDate"] < "1900")
    reviews.loc[fake_date, "creationDate"] = ""
    log("rt_reviews", "fake dates set to unknown", int(fake_date.sum()))
    reviews["score"] = reviews["originalScore"].map(normalize_score)
    log("rt_reviews", "with a score on a 0-1 scale", int(reviews["score"].notna().sum()))
    reviews["isTopCritic"] = reviews["isTopCritic"] == "True"
    reviews = reviews.drop(columns="scoreSentiment")
    write_jsonl(reviews, f"{PROCESSED}/rt_reviews.jsonl")
    return dict(zip(reviews["reviewId"], reviews["reviewText"]))


def latest_lines():
    latest = {}
    with open(SCRAPED, encoding="utf-8") as file:
        for number, line in enumerate(file):
            try:
                latest[json.loads(line)["reviewId"]] = number
            except json.JSONDecodeError:
                continue
    return set(latest.values())


def clean_full_texts(quotes):
    found = Counter()
    keep = latest_lines() if os.path.exists(SCRAPED) else set()
    with open(f"{PROCESSED}/rt_full_texts.jsonl", "w", encoding="utf-8") as output:
        if keep:
            with open(SCRAPED, encoding="utf-8") as file:
                for number, line in enumerate(file):
                    if number not in keep:
                        continue
                    item = json.loads(line)
                    quote = quotes.get(item["reviewId"])
                    if quote is None or item["status"] not in ("full", "no_quote"):
                        continue
                    if item["status"] == "full" or contains_quote(item["text"], quote):
                        text = tidy_text(item["text"])
                        if len(text.split()) < MIN_WORDS:
                            found["too short"] += 1
                            continue
                        found[item["status"]] += 1
                        output.write(json.dumps({"reviewId": item["reviewId"], "full_text": text}, ensure_ascii=False) + "\n")
    log("rt_full_texts", "quote found while scraping", found["full"])
    log("rt_full_texts", "quote found after decoding HTML codes", found["no_quote"])
    log("rt_full_texts", "dropped: under 150 words once layout borders are removed", found["too short"])


def clean_imdb_reviews():
    seen, total, kept = set(), 0, 0
    chunks = pd.read_json(f"{RAW}/imdb_spoiler/IMDB_reviews.json", lines=True, dtype=False, convert_dates=False, chunksize=100_000)
    with open(f"{PROCESSED}/imdb_reviews.jsonl", "w", encoding="utf-8") as file:
        for chunk in chunks:
            total += len(chunk)
            chunk["review_text"] = decode_html(chunk["review_text"])
            chunk["review_summary"] = decode_html(chunk["review_summary"])
            keys = pd.util.hash_pandas_object(chunk[["movie_id", "review_text"]], index=False)
            new = ~keys.duplicated() & ~keys.isin(seen)
            seen.update(keys[new])
            chunk = chunk[new]
            chunk["review_date"] = pd.to_datetime(chunk["review_date"], format="%d %B %Y").dt.strftime("%Y-%m-%d")
            chunk["rating"] = chunk["rating"].astype(int)
            kept += len(chunk)
            append_jsonl(chunk, file)
    log("imdb_reviews", "raw", total)
    log("imdb_reviews", "without repeated texts in the same film", kept)


def clean_imdb_movies():
    movies = pd.read_json(f"{LINKED}/imdb_movies.jsonl", lines=True, dtype=False, convert_dates=False)
    movies = movies.drop(columns="plot_synopsis")
    movies["plot_summary"] = decode_html(movies["plot_summary"])
    movies["duration"] = movies["duration"].map(minutes)
    movies["rating"] = movies["rating"].astype(float)
    write_jsonl(movies, f"{PROCESSED}/imdb_movies.jsonl")


def clean_rt_movies():
    movies = pd.read_json(f"{LINKED}/rt_movies.jsonl", lines=True, dtype=False, convert_dates=False)
    log("rt_movies", "linked", len(movies))
    movies = movies.drop_duplicates()
    log("rt_movies", "without exact duplicates", len(movies))
    movies["title"] = decode_html(movies["title"])
    for column in ["genre", "director", "writer"]:
        movies[column] = movies[column].map(split_list)
    for column in ["audienceScore", "tomatoMeter", "runtimeMinutes"]:
        movies[column] = pd.to_numeric(movies[column], errors="coerce").astype("Int64")
    movies["boxOffice"] = movies["boxOffice"].map(dollars)
    write_jsonl(movies, f"{PROCESSED}/rt_movies.jsonl")


if __name__ == "__main__":
    clean_full_texts(clean_rt_reviews())
    clean_imdb_reviews()
    clean_imdb_movies()
    clean_rt_movies()
    write_stats(f"{PROCESSED}/cleaning_stats.csv")
