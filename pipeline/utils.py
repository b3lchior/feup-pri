import html
import re

import pandas as pd

STATS = []


def read_chunks(path):
    return pd.read_json(path, lines=True, dtype=False, convert_dates=False, chunksize=10_000)


def read_columns(path, columns):
    chunks = [chunk[columns] for chunk in read_chunks(path)]
    return pd.concat(chunks) if chunks else pd.DataFrame(columns=columns)


def append_jsonl(data, file):
    for start in range(0, len(data), 10_000):
        data.iloc[start:start + 10_000].to_json(file, orient="records", lines=True, force_ascii=False)


def write_jsonl(data, path):
    with open(path, "w", encoding="utf-8") as file:
        append_jsonl(data, file)


def log(dataset, step, rows):
    STATS.append({"dataset": dataset, "step": step, "rows": rows})


def write_stats(path):
    pd.DataFrame(STATS).to_csv(path, index=False)


def words(text):
    return re.findall(r"\w+", html.unescape(text).lower())


def contains_quote(article, quote):
    quote_words = words(quote)
    article_text = " " + " ".join(words(article)) + " "
    size = min(6, len(quote_words))
    return size > 0 and any(" " + " ".join(quote_words[i:i + size]) + " " in article_text for i in range(len(quote_words) - size + 1))
