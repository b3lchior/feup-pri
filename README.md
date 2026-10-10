# feup-pri

requirements
py -m pip install requests beautifulsoup4
$env:FILM_USER_AGENT = "FilmProject/1.0 (email@gmail.com)"

## Extract movies with reviews

From the `pipeline` directory, run:

```sh
make extract_movies
```

This writes the following files under `data/processed/`:

- `reviewed_movies.csv`: one deduplicated row per film represented in either review source
- `imdb_reviewed_movies.csv`: one row per IMDb movie with at least one review
- `rotten_tomatoes_reviewed_movies.csv`: one row per Rotten Tomatoes movie with at least one critic review
- `wikipedia_titles.txt`: unique titles ready for Wikipedia extraction

Each row contains the source, source-specific movie identifier, movie title,
review count, release date, and rating. IMDb titles are resolved using IMDb's
public `title.basics.tsv` dataset. IMDb and Rotten Tomatoes identifiers are
kept in their own columns. Cross-source duplicates are merged by normalized
movie title and release year; records without a safe title/year match remain
separate.

To extract the Wikipedia articles, from the repository root run:

```sh
python3 wikipedia_film.py --search \
  --titles-file feup-pri/data/processed/wikipedia_titles.txt \
  --out feup-pri/data/processed/reviewed_films.jsonl
```

Or run the equivalent explicit pipeline target:

```sh
cd feup-pri/pipeline
make wikipedia
```

The Wikipedia script caches downloaded pages in `wiki_cache/`, so interrupted
runs can be resumed safely.
