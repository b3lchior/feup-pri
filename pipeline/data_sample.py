import pandas as pd
from utils import append_jsonl, log, read_chunks, read_columns, write_stats

PROCESSED = "../data/processed"
SAMPLED = "../data/sampled"
CAP = 200


def cap_per_film(data, identifier, film, stratum, preferred=None):
    data = data.assign(hash=pd.util.hash_pandas_object(data[identifier], index=False)).sort_values("hash", kind="stable")
    if preferred:
        data = data.sort_values(preferred, ascending=False, kind="stable")
    groups = data.groupby([film, stratum])
    data["order"] = (groups.cumcount() + 0.5) / groups[film].transform("size")
    return data.sort_values("order", kind="stable").groupby(film).head(CAP)


def write_selected(source, rows, output, full_texts=None):
    with open(output, "w", encoding="utf-8") as file:
        for chunk in read_chunks(source):
            chunk = chunk[chunk.index.isin(rows)]
            if full_texts is not None:
                chunk = chunk.assign(full_text=chunk["reviewId"].map(full_texts).fillna(""))
            append_jsonl(chunk, file)


def sample_rt():
    reviews = read_columns(f"{PROCESSED}/rt_reviews.jsonl", ["reviewId", "imdb_id", "reviewState"])
    texts = read_columns(f"{PROCESSED}/rt_full_texts.jsonl", ["reviewId", "full_text"])
    log("rt_reviews", "cleaned", len(reviews))
    reviews["has_full_text"] = reviews["reviewId"].isin(texts["reviewId"])
    kept = cap_per_film(reviews, "reviewId", "imdb_id", "reviewState", "has_full_text")
    log("rt_reviews", f"max {CAP} per film", len(kept))
    log("rt_reviews", "of which with a full text", int(kept["has_full_text"].sum()))
    write_selected(f"{PROCESSED}/rt_reviews.jsonl", kept.index, f"{SAMPLED}/rt_reviews.jsonl", texts.set_index("reviewId")["full_text"])
    return set(kept["imdb_id"])


def sample_imdb(films):
    reviews = read_columns(f"{PROCESSED}/imdb_reviews.jsonl", ["movie_id", "user_id", "rating"])
    log("imdb_reviews", "cleaned", len(reviews))
    reviews = reviews[reviews["movie_id"].isin(films)]
    log("imdb_reviews", "films with critic reviews", len(reviews))
    reviews = reviews.assign(review_id=reviews["movie_id"] + "_" + reviews["user_id"])
    kept = cap_per_film(reviews, "review_id", "movie_id", "rating")
    log("imdb_reviews", f"max {CAP} per film", len(kept))
    write_selected(f"{PROCESSED}/imdb_reviews.jsonl", kept.index, f"{SAMPLED}/imdb_reviews.jsonl")


if __name__ == "__main__":
    films = sample_rt()
    log("films", "with both kinds of review", len(films))
    sample_imdb(films)
    write_stats(f"{SAMPLED}/sample_stats.csv")
