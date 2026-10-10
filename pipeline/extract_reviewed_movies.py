"""Extract one row per movie represented in the review datasets."""

import csv
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW = PROJECT_ROOT / "data" / "raw"
OUTPUT = PROJECT_ROOT / "data" / "processed"


def release_year(value: str) -> str:
    match = re.search(r"\b(18|19|20)\d{2}\b", value or "")
    return match.group(0) if match else ""


def title_key(title: str) -> str:
    normalized = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode()
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized.casefold())
    return normalized.strip()


def extract_imdb_movies() -> list[dict[str, str | int]]:
    reviews_path = RAW / "imdb_spoiler" / "IMDB_reviews.json"
    details_path = RAW / "imdb_spoiler" / "IMDB_movie_details.json"
    titles_path = RAW / "imdb_spoiler" / "title.basics.tsv"

    review_counts: Counter[str] = Counter()
    with reviews_path.open(encoding="utf-8") as reviews_file:
        for line in reviews_file:
            review = json.loads(line)
            review_counts[review["movie_id"]] += 1

    details = {}
    with details_path.open(encoding="utf-8") as details_file:
        for line in details_file:
            movie = json.loads(line)
            details[movie["movie_id"]] = movie

    titles = {}
    with titles_path.open(encoding="utf-8") as titles_file:
        reader = csv.DictReader(titles_file, delimiter="\t")
        for movie in reader:
            if movie["tconst"] in review_counts:
                titles[movie["tconst"]] = movie["primaryTitle"]

    return [
        {
            "source": "imdb",
            "movie_id": movie_id,
            "movie_title": titles.get(movie_id, ""),
            "review_count": count,
            "release_date": details.get(movie_id, {}).get("release_date", ""),
            "rating": details.get(movie_id, {}).get("rating", ""),
        }
        for movie_id, count in sorted(review_counts.items())
    ]


def extract_rotten_tomatoes_movies() -> list[dict[str, str | int]]:
    reviews_path = RAW / "rotten_tomatoes" / "rotten_tomatoes_critic_reviews.csv"
    movies_path = RAW / "rotten_tomatoes" / "rotten_tomatoes_movies.csv"

    review_counts: Counter[str] = Counter()
    with reviews_path.open(newline="", encoding="utf-8") as reviews_file:
        for review in csv.DictReader(reviews_file):
            movie_id = review["rotten_tomatoes_link"]
            if movie_id:
                review_counts[movie_id] += 1

    movies = {}
    with movies_path.open(newline="", encoding="utf-8") as movies_file:
        for movie in csv.DictReader(movies_file):
            movies[movie["rotten_tomatoes_link"]] = movie

    return [
        {
            "source": "rotten_tomatoes",
            "movie_id": movie_id,
            "movie_title": movies.get(movie_id, {}).get("movie_title", ""),
            "review_count": count,
            "release_date": movies.get(movie_id, {}).get("original_release_date", ""),
            "rating": movies.get(movie_id, {}).get("tomatometer_rating", ""),
        }
        for movie_id, count in sorted(review_counts.items())
    ]


def write_movies(movies: list[dict[str, str | int]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "source",
        "movie_id",
        "movie_title",
        "review_count",
        "release_date",
        "rating",
    ]
    if movies and "imdb_id" in movies[0]:
        fieldnames += ["imdb_id", "rotten_tomatoes_id"]
    with path.open("w", newline="", encoding="utf-8") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(movies)


def deduplicate_movies(
    imdb_movies: list[dict[str, str | int]],
    rotten_tomatoes_movies: list[dict[str, str | int]],
) -> list[dict[str, str | int]]:
    canonical = {}
    for movie in imdb_movies + rotten_tomatoes_movies:
        year = release_year(str(movie["release_date"]))
        key = (title_key(str(movie["movie_title"])), year)
        # Unnamed or yearless records cannot be safely matched across sources.
        if not key[0] or not key[1]:
            key = (f"{movie['source']}:{movie['movie_id']}", "")
        existing = canonical.get(key)
        if existing is None:
            canonical[key] = {
                "source": str(movie["source"]),
                "movie_id": str(movie["movie_id"]),
                "movie_title": str(movie["movie_title"]),
                "review_count": int(movie["review_count"]),
                "release_date": str(movie["release_date"]),
                "rating": str(movie["rating"]),
                "imdb_id": str(movie["movie_id"]) if movie["source"] == "imdb" else "",
                "rotten_tomatoes_id": (
                    str(movie["movie_id"])
                    if movie["source"] == "rotten_tomatoes"
                    else ""
                ),
            }
            continue
        existing["source"] = f"{existing['source']},{movie['source']}"
        existing["movie_id"] = f"{existing['movie_id']},{movie['movie_id']}"
        existing["review_count"] += int(movie["review_count"])
        if movie["source"] == "imdb":
            existing["imdb_id"] = str(movie["movie_id"])
        else:
            existing["rotten_tomatoes_id"] = str(movie["movie_id"])

    return sorted(canonical.values(), key=lambda movie: title_key(str(movie["movie_title"])))


def write_wikipedia_titles(movies: list[dict[str, str | int]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    titles = sorted(
        {str(movie["movie_title"]) for movie in movies if str(movie["movie_title"]).strip()}
    )
    path.write_text("\n".join(titles) + "\n", encoding="utf-8")


def main() -> None:
    imdb_movies = extract_imdb_movies()
    rotten_tomatoes_movies = extract_rotten_tomatoes_movies()
    all_movies = deduplicate_movies(imdb_movies, rotten_tomatoes_movies)

    write_movies(imdb_movies, OUTPUT / "imdb_reviewed_movies.csv")
    write_movies(
        rotten_tomatoes_movies,
        OUTPUT / "rotten_tomatoes_reviewed_movies.csv",
    )
    write_movies(all_movies, OUTPUT / "reviewed_movies.csv")
    write_wikipedia_titles(all_movies, OUTPUT / "wikipedia_titles.txt")

    print(f"IMDb movies: {len(imdb_movies)}")
    print(f"Rotten Tomatoes movies: {len(rotten_tomatoes_movies)}")
    print(f"Unique reviewed movies: {len(all_movies)}")


if __name__ == "__main__":
    main()
