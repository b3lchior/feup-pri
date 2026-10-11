import pandas as pd
from utils import write_jsonl

RAW = "../data/raw"
LINKED = "../data/linked"


def link_imdb_movies():
    movies = pd.read_json(f"{RAW}/imdb_spoiler/IMDB_movie_details.json", lines=True, dtype=False, convert_dates=False)
    movies["movie_id"] = movies["movie_id"].str.rstrip("/")
    write_jsonl(movies, f"{LINKED}/imdb_movies.jsonl")
    return movies


def link_films(movies, rt_movies):
    links = pd.read_csv(f"{RAW}/wikidata/links.csv", dtype=str, keep_default_na=False)
    links["wikidata_id"] = links["film"].str.removeprefix("http://www.wikidata.org/entity/")
    links["rt_id"] = links["rt_id"].str.removeprefix("m/")
    links = links[links["imdb_id"].isin(movies["movie_id"]) & links["rt_id"].isin(rt_movies["id"])]
    links = links[["imdb_id", "wikidata_id", "rt_id"]].drop_duplicates(subset=["imdb_id", "rt_id"])
    write_jsonl(links, f"{LINKED}/film_links.jsonl")
    return links


def link_rt_movies(rt_movies, links):
    linked = rt_movies.rename(columns={"id": "rt_id"}).merge(links[["imdb_id", "rt_id"]], on="rt_id")
    write_jsonl(linked, f"{LINKED}/rt_movies.jsonl")


def link_rt_reviews(links):
    chunks = pd.read_csv(f"{RAW}/rotten_tomatoes/rotten_tomatoes_movie_reviews.csv", dtype=str, keep_default_na=False, chunksize=100_000)
    linked = pd.concat(chunk.rename(columns={"id": "rt_id"}).merge(links[["imdb_id", "rt_id"]], on="rt_id") for chunk in chunks)
    write_jsonl(linked, f"{LINKED}/rt_reviews.jsonl")


if __name__ == "__main__":
    movies = link_imdb_movies()
    rt_movies = pd.read_csv(f"{RAW}/rotten_tomatoes/rotten_tomatoes_movies.csv", dtype=str, keep_default_na=False)
    links = link_films(movies, rt_movies)
    link_rt_movies(rt_movies, links)
    link_rt_reviews(links)
