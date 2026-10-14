import pandas as pd
from utils import append_jsonl, log, read_chunks, read_columns, write_jsonl, write_stats

RAW = "../data/raw"
LINKED = "../data/linked"
PROCESSED = "../data/processed"
SAMPLED = "../data/sampled"
DOCUMENTS = "../data/documents"

IMDB_FILM_COLUMNS = {"movie_id": "imdb_id", "release_date": "release_date", "genre": "genres", "plot_summary": "plot_summary", "duration": "duration_minutes", "rating": "imdb_rating"}
RT_FILM_COLUMNS = {"imdb_id": "imdb_id", "rt_id": "rt_id", "title": "title", "tomatoMeter": "tomatometer", "audienceScore": "audience_score", "rating": "content_rating", "originalLanguage": "original_language", "director": "directors", "writer": "writers", "boxOffice": "box_office", "distributor": "distributor"}
FILM_FIELDS = ["imdb_id", "wikidata_id", "title", "year", "genres", "plot_summary", "imdb_rating", "tomatometer", "audience_score"]


def read_table(path):
    return pd.read_json(path, lines=True, dtype=False, convert_dates=False)


def empty_to_null(values):
    return values.mask(values == "")


def build_films(sampled_films):
    imdb = read_table(f"{PROCESSED}/imdb_movies.jsonl")[list(IMDB_FILM_COLUMNS)].rename(columns=IMDB_FILM_COLUMNS)
    rt = read_table(f"{PROCESSED}/rt_movies.jsonl")
    reviews_per_page = read_columns(f"{SAMPLED}/rt_reviews.jsonl", ["rt_id"])["rt_id"].value_counts()
    rt = rt.assign(reviews=rt["rt_id"].map(reviews_per_page).fillna(0)).sort_values("reviews", ascending=False)
    rt = rt.drop_duplicates("imdb_id")[list(RT_FILM_COLUMNS)].rename(columns=RT_FILM_COLUMNS)
    links = read_table(f"{LINKED}/film_links.jsonl").drop_duplicates("imdb_id")[["imdb_id", "wikidata_id"]]
    films = imdb[imdb["imdb_id"].isin(sampled_films)].merge(links, on="imdb_id").merge(rt, on="imdb_id")
    wikipedia = read_table(f"{RAW}/wikipedia/film_articles.jsonl").drop_duplicates("imdb_id")
    films = films.merge(wikipedia[["imdb_id", "wikipedia_title", "wikipedia_url", "wikipedia_page_id", "wikipedia_revision_id", "wikipedia_extract"]], on="imdb_id", how="left")
    films["year"] = films["release_date"].str[:4].astype(int)
    for column in ["tomatometer", "audience_score", "box_office", "wikipedia_page_id", "wikipedia_revision_id"]:
        films[column] = films[column].astype("Int64")
    log("films", "documents", len(films))
    write_jsonl(films, f"{DOCUMENTS}/films.jsonl")
    return films[FILM_FIELDS].add_prefix("film_")


def critic_documents(chunk):
    has_full_text = chunk["full_text"] != ""
    return pd.DataFrame({
        "id": "rt_" + chunk["reviewId"],
        "perspective": "critic",
        "text": chunk["full_text"].where(has_full_text, chunk["reviewText"]),
        "text_kind": has_full_text.map({True: "full", False: "quote"}),
        "quote": chunk["reviewText"],
        "score": chunk["score"],
        "original_score": empty_to_null(chunk["originalScore"]),
        "verdict": chunk["reviewState"],
        "top_critic": chunk["isTopCritic"],
        "translated": chunk["translated"],
        "author": chunk["criticName"],
        "publication": chunk["publicatioName"],
        "date": empty_to_null(chunk["creationDate"]),
        "url": empty_to_null(chunk["reviewUrl"]),
        "film_imdb_id": chunk["imdb_id"],
    })


def audience_documents(chunk):
    return pd.DataFrame({
        "id": "imdb_" + chunk["movie_id"] + "_" + chunk["user_id"],
        "perspective": "audience",
        "text": chunk["review_text"],
        "text_kind": "full",
        "summary": chunk["review_summary"],
        "score": chunk["rating"] / 10,
        "original_score": chunk["rating"].astype(str) + "/10",
        "is_spoiler": chunk["is_spoiler"],
        "author": chunk["user_id"],
        "date": chunk["review_date"],
        "film_imdb_id": chunk["movie_id"],
    })


def write_reviews(films):
    counts = {"critic": 0, "audience": 0, "full": 0}
    sources = [(f"{SAMPLED}/rt_reviews.jsonl", critic_documents), (f"{SAMPLED}/imdb_reviews.jsonl", audience_documents)]
    with open(f"{DOCUMENTS}/reviews.jsonl", "w", encoding="utf-8") as file:
        for path, to_documents in sources:
            for chunk in read_chunks(path):
                documents = to_documents(chunk)
                documents["word_count"] = documents["text"].str.split().str.len()
                documents = documents.merge(films, on="film_imdb_id", how="left")
                counts[documents["perspective"].iloc[0]] += len(documents)
                counts["full"] += int((documents["text_kind"] == "full").sum())
                append_jsonl(documents, file)
    log("reviews", "critic documents", counts["critic"])
    log("reviews", "audience documents", counts["audience"])
    log("reviews", "documents with a full review text", counts["full"])


if __name__ == "__main__":
    films = build_films(set(read_columns(f"{SAMPLED}/rt_reviews.jsonl", ["imdb_id"])["imdb_id"]))
    write_reviews(films)
    write_stats(f"{DOCUMENTS}/merge_stats.csv")
