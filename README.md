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

The first run downloads about 500 MB from Kaggle (pinned versions). The IMDb ↔ Rotten Tomatoes links from Wikidata, the Wikipedia titles and the Wikipedia article of every film are not downloaded from the live sites: they are copied from the `snapshot/` folder of this repository, taken on 2026-10-23, so every machine builds the same documents. After the first run, `make` takes about 2 minutes, charts included, and never downloads twice: a download is only repeated if its file is deleted.

**4. Use the results** in `data/documents/`:

| File | Contents |
|---|---|
| `reviews.jsonl` | 438,629 review documents, one per line: 179,290 critic and 259,339 audience reviews about 1,493 films |
| `films.jsonl` | 1,493 film documents, each with its full English Wikipedia article when one exists (all films but one) |
| `merge_stats.csv` | document counts |


## Pipeline stages

All commands run from the `pipeline/` folder.

| Command | What it does | Output |
|---|---|---|
| `make` | Runs every stage below, in order | |
| `make requirements` | Creates `.venv/` and installs `requirements.txt` | `.venv/` |
| `make collect` | Downloads IMDb Spoiler (Kaggle, version 1) and Rotten Tomatoes/Clapper (Kaggle, version 4), and copies the IMDb ↔ Rotten Tomatoes links and the English Wikipedia title of each of our films from `snapshot/` | `data/raw/` |
| `make link` | Matches IMDb and Rotten Tomatoes films through Wikidata and keeps only our films | `data/linked/` |
| `make wikipedia` | Copies the full plain-text English Wikipedia article of each linked film from `snapshot/` | `data/raw/wikipedia/film_articles.jsonl` |
| `make cleaning` | Removes duplicates and placeholders, fixes dates, scores and formats, attaches the scraped full texts | `data/processed/`, with `cleaning_stats.csv` |
| `make sample` | Keeps the films with both critic and audience reviews, at most 200 reviews per film from each source | `data/sampled/`, with `sample_stats.csv` |
| `make merge` | Builds the final documents | `data/documents/` |
| `make analysis` | Exploratory analysis of the final documents: charts (PNG and PDF) and their figures | `data/analysis/`, with `analysis_stats.csv` and `distinctive_words.csv` |
| `make inspect` | Optional: data-quality report for each raw Kaggle file (needs about 4.5 GB of memory) | `data/inspection/` |
| `make refresh` | Optional, and it changes the documents: queries Wikidata and Wikipedia again (about 12 minutes) and replaces the files in `snapshot/`. Run it only to update the collection on purpose, then commit the new snapshot | `snapshot/` |
| `make clean` | Deletes everything the pipeline generated, except `data/scraped/` and `snapshot/` | |

To rebuild everything from scratch: `make clean all`.

## Repository layout

```
feup-pri/
├── README.md
├── requirements.txt               Python packages, all with pinned versions
├── snapshot/                      the data taken from Wikidata and Wikipedia on 2026-10-23
│   ├── links.csv                  IMDb ↔ Rotten Tomatoes links
│   ├── wikipedia_titles.csv       English Wikipedia title of each film
│   └── film_articles.jsonl        English Wikipedia article of each film
└── pipeline/
    ├── makefile                   the pipeline stages
    ├── wikidata_links.rq          Wikidata query for the IMDb ↔ Rotten Tomatoes links (make refresh)
    ├── data_wikipedia_titles.py   English Wikipedia titles from the Wikidata API (make refresh)
    ├── data_inspect.py            make inspect
    ├── data_link.py               make link
    ├── data_wikipedia.py          English Wikipedia articles through the MediaWiki API (make refresh)
    ├── data_clean.py              make cleaning
    ├── data_sample.py             make sample
    ├── data_merge.py              make merge
    ├── data_analysis.py           make analysis
    ├── data_scrape.py             the scraper that produced full_reviews.jsonl (not run by make)
    └── utils.py                   shared helpers
```
