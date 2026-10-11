import pandas as pd

RAW = "../data/raw"
PROCESSED = "../data/processed"


def log(step, data):
    print(f"  {step}: {len(data)} rows")


def write_jsonl(data, path):
    with open(path, "w", encoding="utf-8") as file:
        for start in range(0, len(data), 100_000):
            data.iloc[start:start + 100_000].to_json(file, orient="records", lines=True, force_ascii=False)


def clean_rt_reviews():
    reviews = pd.read_csv(f"{RAW}/rotten_tomatoes/rotten_tomatoes_movie_reviews.csv", dtype=str, keep_default_na=False)
    # print("rt_reviews")
    # log("raw", reviews)
    reviews["reviewText"] = reviews["reviewText"].str.strip()
    reviews = reviews.drop_duplicates()
    # log("without exact duplicates", reviews)
    reviews = reviews[reviews["reviewText"] != ""]
    # log("without empty reviews", reviews)
    write_jsonl(reviews, f"{PROCESSED}/rt_reviews.jsonl")


if __name__ == "__main__":
    clean_rt_reviews()
