# PRrevIews

Search films by what their reviews say. This repository holds the data pipeline (Milestone 1, PRI, M.EIC, FEUP 2026/27): it downloads IMDb audience reviews and Rotten Tomatoes critic reviews, links the two through Wikidata, cleans them, and builds the document collection.

## Requirements

- Linux or macOS (on Windows, use WSL)
- Python 3.11 or newer, `make`, `curl` and `unzip`
- About 5 GB of free disk space and 2 GB of free memory

The pipeline installs its own Python packages in a virtual environment (`.venv/`), so nothing is installed system-wide.

## Quick start

**1. Clone the repository**

```sh
git clone git@github.com:b3lchior/feup-pri.git
cd feup-pri
```

**2. Download the scraped critic reviews**

The full texts of the Rotten Tomatoes critic reviews were collected once from the critics' own websites (about 10 hours of crawling). The pipeline does not scrape again; it uses this file instead.

- **Google Drive link:** `https://drive.google.com/file/d/1aLzWqiFQRipg5uev5MwcX-1aIMxr904T/view?usp=sharing`
- Place the file exactly here (create the folders if needed):

```
feup-pri/data/scraped/full_reviews.jsonl
```

```sh
mkdir -p data/scraped
mv ~/Downloads/full_reviews.jsonl data/scraped/
```

If the Drive file is compressed, extract it first: the pipeline expects the `.jsonl` file itself.

Without this file the pipeline still runs, but critic reviews keep only their short Rotten Tomatoes quotes, and `make` prints a warning.

**3. Run the pipeline**

```sh
cd pipeline
make
```

The first run downloads about 500 MB from Kaggle and Wikidata. After that, a full run takes about 2–3 minutes. Running `make` again re-runs the processing but never downloads twice.

**4. Use the results** in `data/documents/`:

| File | Contents |
|---|---|
| `reviews.jsonl` | 439,946 review documents, one per line: 179,779 critic and 260,167 audience reviews about 1,498 films |
| `films.jsonl` | one document per film, including its English Wikipedia article extract when available |
| `merge_stats.csv` | document counts |

Each review document has its text (`text`, plus `text_kind`: `full` or `quote`), its perspective (`critic` or `audience`), its score on a 0–1 scale, author, date and other details, and a copy of its film's details (`film_title`, `film_year`, `film_genres`, `film_plot_summary`, `film_tomatometer`…).

## Pipeline stages

All commands run from the `pipeline/` folder.

| Command | What it does | Output |
|---|---|---|
| `make` | Runs every stage below, in order | |
| `make requirements` | Creates `.venv/` and installs `requirements.txt` | `.venv/` |
| `make collect` | Downloads IMDb Spoiler (Kaggle, version 1), Rotten Tomatoes/Clapper (Kaggle, version 4) and IMDb ↔ Rotten Tomatoes links plus English Wikipedia titles from Wikidata | `data/raw/` |
| `make link` | Matches IMDb and Rotten Tomatoes films through Wikidata and keeps only our films | `data/linked/` |
| `make wikipedia` | Fetches English Wikipedia plain-text extracts for linked films through the MediaWiki API | `data/raw/wikipedia/film_articles.jsonl` |
| `make cleaning` | Removes duplicates and placeholders, fixes dates, scores and formats, attaches the scraped full texts | `data/processed/`, with `cleaning_stats.csv` |
| `make sample` | Keeps the films with both critic and audience reviews, at most 200 reviews per film from each source | `data/sampled/`, with `sample_stats.csv` |
| `make merge` | Builds the final documents | `data/documents/` |
| `make inspect` | Optional: data-quality report for each raw file (needs about 4.5 GB of memory) | `data/inspection/` |
| `make clean` | Deletes everything the pipeline generated, except `data/scraped/` | |

To rebuild everything from scratch: `make clean all`.

## Repository layout

```
feup-pri/
├── README.md
├── requirements.txt          Python packages, with pinned versions
└── pipeline/
    ├── makefile              the pipeline stages
    ├── wikidata_links.rq     Wikidata query for IMDb, Rotten Tomatoes and English Wikipedia links
    ├── data_wikipedia.py     fetches linked Wikipedia article extracts
    ├── data_inspect.py       make inspect
    ├── data_link.py          make link
    ├── data_clean.py         make cleaning
    ├── data_sample.py        make sample
    ├── data_merge.py         make merge
    ├── data_scrape.py        the scraper that produced full_reviews.jsonl (not run by make)
    └── utils.py              shared helpers
```

The `data/` folder is created by the pipeline and is not part of the repository.

## Data sources

| Source | Version | License |
|---|---|---|
| [IMDb Spoiler Dataset](https://www.kaggle.com/datasets/rmisra/imdb-spoiler-dataset) (Rishabh Misra) | Kaggle version 1 | CC BY 4.0 |
| [Massive Rotten Tomatoes Movies & Reviews](https://www.kaggle.com/datasets/andrezaza/clapper-massive-rotten-tomatoes-movies-and-reviews) (andrezaza) | Kaggle version 4 | CC0 |
| [Wikidata](https://query.wikidata.org), IMDb ID (P345) and Rotten Tomatoes ID (P1258) | queried live at download time | CC0 |
| [English Wikipedia](https://en.wikipedia.org), article extracts matched through Wikidata sitelinks | fetched live through the MediaWiki API | CC BY-SA; retain the article URL and revision ID for attribution |

Wikipedia text is stored once per film in `films.jsonl` as `wikipedia_extract`, alongside `wikipedia_url` and `wikipedia_revision_id` for attribution. It is not copied into every review document. The pipeline requests English Wikipedia only; films without an English article have empty Wikipedia fields. Wikipedia text is available under CC BY-SA, so preserve attribution if the data or extracts are redistributed.
| Full critic reviews, scraped from the critics' websites | collected 2026-10-11/12 | copyrighted by their authors |

Wikidata changes over time, so a fresh download can link a slightly different set of films than ours. Our copy was downloaded on 2026-10-13.

## About the scraped reviews

`data_scrape.py` fetched each critic review's link (`reviewUrl`). It obeyed each site's `robots.txt` and `Crawl-delay`, waited at least 2 seconds between requests to the same site, and never got around paywalls. A page was kept only if it contained the Rotten Tomatoes quote. 56,946 full critic reviews were recovered.

These texts are copyrighted articles, used only for research inside this project. **Do not commit them to git or share the Drive file publicly.**

The scraper is kept for documentation and is not part of `make`. Running it again sends about 170,000 requests to about 2,800 websites and takes about 10 hours.
