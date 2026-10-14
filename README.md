# PRrevIews

Search films by what their reviews say. This repository holds the data pipeline (Milestone 1, PRI, M.EIC, FEUP 2026/27): it downloads IMDb audience reviews and Rotten Tomatoes critic reviews, links the two through Wikidata, adds each film's English Wikipedia article, cleans the data, and builds the document collection.

## Requirements

- Linux or macOS (on Windows, use WSL)
- Python 3.12 or newer, `make`, `curl` and `unzip`
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

The first run downloads about 500 MB from Kaggle, the links from Wikidata, and the English Wikipedia article of every film (about 1,500 requests, roughly 12 minutes). After that, `make` takes about 2 minutes and never downloads twice: a download is only repeated if its file is deleted or the query or script that produces it changes.

**4. Use the results** in `data/documents/`:

| File | Contents |
|---|---|
| `reviews.jsonl` | 438,157 review documents, one per line: 179,018 critic and 259,139 audience reviews about 1,492 films |
| `films.jsonl` | 1,492 film documents, each with its full English Wikipedia article when one exists (all films but one) |
| `merge_stats.csv` | document counts |

Each review document has its text (`text`, plus `text_kind`: `full` or `quote`), its perspective (`critic` or `audience`), its score on a 0–1 scale, author, date and other details, and a copy of its film's details (`film_title`, `film_year`, `film_genres`, `film_plot_summary`, `film_tomatometer`…). The Wikipedia fields are only in `films.jsonl`.

## Pipeline stages

All commands run from the `pipeline/` folder.

| Command | What it does | Output |
|---|---|---|
| `make` | Runs every stage below, in order | |
| `make requirements` | Creates `.venv/` and installs `requirements.txt` | `.venv/` |
| `make collect` | Downloads IMDb Spoiler (Kaggle, version 1), Rotten Tomatoes/Clapper (Kaggle, version 4), the IMDb ↔ Rotten Tomatoes links from Wikidata, and the English Wikipedia title of each of our films from the Wikidata API | `data/raw/` |
| `make link` | Matches IMDb and Rotten Tomatoes films through Wikidata and keeps only our films | `data/linked/` |
| `make wikipedia` | Downloads the full plain-text English Wikipedia article of each linked film through the MediaWiki API (only once) | `data/raw/wikipedia/film_articles.jsonl` |
| `make cleaning` | Removes duplicates and placeholders, fixes dates, scores and formats, attaches the scraped full texts | `data/processed/`, with `cleaning_stats.csv` |
| `make sample` | Keeps the films with both critic and audience reviews, at most 200 reviews per film from each source | `data/sampled/`, with `sample_stats.csv` |
| `make merge` | Builds the final documents | `data/documents/` |
| `make inspect` | Optional: data-quality report for each raw Kaggle file (needs about 4.5 GB of memory) | `data/inspection/` |
| `make clean` | Deletes everything the pipeline generated, except `data/scraped/` | |

To rebuild everything from scratch: `make clean all`.

## Repository layout

```
feup-pri/
├── README.md
├── requirements.txt               Python packages, all with pinned versions
└── pipeline/
    ├── makefile                   the pipeline stages
    ├── wikidata_links.rq          Wikidata query for the IMDb ↔ Rotten Tomatoes links
    ├── data_wikipedia_titles.py   English Wikipedia titles from the Wikidata API (make collect)
    ├── data_inspect.py            make inspect
    ├── data_link.py               make link
    ├── data_wikipedia.py          make wikipedia
    ├── data_clean.py              make cleaning
    ├── data_sample.py             make sample
    ├── data_merge.py              make merge
    ├── data_scrape.py             the scraper that produced full_reviews.jsonl (not run by make)
    └── utils.py                   shared helpers
```

The `data/` folder is created by the pipeline and is not part of the repository.

## Data sources

| Source | Version | License |
|---|---|---|
| [IMDb Spoiler Dataset](https://www.kaggle.com/datasets/rmisra/imdb-spoiler-dataset) (Rishabh Misra) | Kaggle version 1 | CC BY 4.0 |
| [Massive Rotten Tomatoes Movies & Reviews](https://www.kaggle.com/datasets/andrezaza/clapper-massive-rotten-tomatoes-movies-and-reviews) (andrezaza) | Kaggle version 4 | CC0 |
| [Wikidata](https://www.wikidata.org): IMDb ID (P345), Rotten Tomatoes ID (P1258) and English Wikipedia article titles | queried live at download time | CC0 |
| [English Wikipedia](https://en.wikipedia.org): full article text, through the MediaWiki API | downloaded live, with the revision ID of each article | CC BY-SA 4.0 |
| Full critic reviews, scraped from the critics' websites | collected 2026-10-11/12 | copyrighted by their authors |

Wikidata and Wikipedia change over time, so a fresh download can link a slightly different set of films, or get newer versions of the articles. Our copies were downloaded on 2026-10-14.

Each film's Wikipedia text is stored once, in `films.jsonl` (`wikipedia_extract`), with its `wikipedia_title`, `wikipedia_url`, `wikipedia_page_id` and `wikipedia_revision_id`. The revision ID identifies the exact version used (`https://en.wikipedia.org/w/index.php?oldid=<revision ID>`). Wikipedia text is licensed CC BY-SA 4.0, so keep the article links for attribution if the data is shared. The full articles include each film's plot (with its ending) and its critical reception.

## About the scraped reviews

`data_scrape.py` fetched each critic review's link (`reviewUrl`). It obeyed each site's `robots.txt` and `Crawl-delay`, waited at least 2 seconds between requests to the same site, and never got around paywalls. A page was kept only if it contained the Rotten Tomatoes quote. 56,838 full critic reviews were recovered; 56,785 of them remain after cleaning.

These texts are copyrighted articles, used only for research inside this project. **Do not commit them to git or share the Drive file publicly.**

The scraper is kept for documentation and is not part of `make`. Running it again sends about 170,000 requests to about 2,800 websites and takes about 10 hours.
