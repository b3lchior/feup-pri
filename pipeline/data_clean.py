import pandas as pd
from utils import write_jsonl

LINKED = "../data/linked"
PROCESSED = "../data/processed"

STATS = []


def log(dataset, step, data):
    STATS.append({"dataset": dataset, "step": step, "rows": len(data)})


def clean_rt_reviews():
    reviews = pd.read_json(f"{LINKED}/rt_reviews.jsonl", lines=True, dtype=False, convert_dates=False)
    log("rt_reviews", "linked", reviews)
    reviews["reviewText"] = reviews["reviewText"].str.strip()
    reviews = reviews.drop_duplicates()
    log("rt_reviews", "without exact duplicates", reviews)
    reviews = reviews[reviews["reviewText"] != ""]
    log("rt_reviews", "without empty reviews", reviews)
    write_jsonl(reviews, f"{PROCESSED}/rt_reviews.jsonl")


def clean_imdb_movies():
    movies = pd.read_json(f"{LINKED}/imdb_movies.jsonl", lines=True, dtype=False, convert_dates=False)
    movies = movies.drop(columns="plot_synopsis")
    write_jsonl(movies, f"{PROCESSED}/imdb_movies.jsonl")


if __name__ == "__main__":
    clean_rt_reviews()
    clean_imdb_movies()
    pd.DataFrame(STATS).to_csv(f"{PROCESSED}/cleaning_stats.csv", index=False)
