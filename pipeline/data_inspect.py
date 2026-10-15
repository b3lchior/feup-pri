import json
import pandas as pd

RAW = "../data/raw"
INSPECTION = "../data/inspection"

FILES = {
    "imdb_reviews": "imdb_spoiler/IMDB_reviews.json",
    "imdb_movies": "imdb_spoiler/IMDB_movie_details.json",
    "rt_reviews": "rotten_tomatoes/rotten_tomatoes_movie_reviews.csv",
    "rt_movies": "rotten_tomatoes/rotten_tomatoes_movies.csv",
}


def load(path):
    if path.endswith(".json"):
        return pd.read_json(path, lines=True, dtype=False, convert_dates=False)
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def inspect_column(column):
    text = column.astype(str).str.strip()
    missing = column.isna() | (text == "")
    present = text[~missing]
    return {
        "missing": int(missing.sum()),
        "unique": int(present.nunique()),
        "top_values": {value[:80]: int(count) for value, count in present.value_counts().head(5).items()},
    }


def inspect_file(name, path):
    data = load(f"{RAW}/{path}")
    report = {
        "rows": len(data),
        "duplicate_rows": int(data.astype(str).duplicated().sum()),
        "columns": {column: inspect_column(data[column]) for column in data.columns},
    }
    with open(f"{INSPECTION}/{name}.json", "w", encoding="utf-8") as file:
        json.dump(report, file, indent=2, ensure_ascii=False)
    print(f"{name}: {report['rows']} rows, {report['duplicate_rows']} duplicate rows")


if __name__ == "__main__":
    for name, path in FILES.items():
        inspect_file(name, path)
