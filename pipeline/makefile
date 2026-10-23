VENV = $(abspath ../.venv)
PYTHON = $(VENV)/bin/python
RAW = ../data/raw
IMDB_SPOILER = $(RAW)/imdb_spoiler
ROTTEN_TOMATOES = $(RAW)/rotten_tomatoes
WIKIDATA = $(RAW)/wikidata
WIKIPEDIA = $(RAW)/wikipedia
SNAPSHOT = ../snapshot
INSPECTION = ../data/inspection
LINKED = ../data/linked
PROCESSED = ../data/processed
SCRAPED = ../data/scraped
SAMPLED = ../data/sampled
DOCUMENTS = ../data/documents
ANALYSIS = ../data/analysis

all: requirements collect link wikipedia cleaning sample merge analysis

clean:
	rm -rf $(RAW) $(INSPECTION) $(LINKED) $(PROCESSED) $(SAMPLED) $(DOCUMENTS) $(ANALYSIS)

requirements: $(PYTHON)
	$(PYTHON) -m pip install -r ../requirements.txt

$(PYTHON):
	python3 -m venv $(VENV)

collect: imdb_spoiler rotten_tomatoes wikidata

imdb_spoiler: $(IMDB_SPOILER)/IMDB_reviews.json

$(IMDB_SPOILER)/IMDB_reviews.json:
	mkdir -p $(IMDB_SPOILER)
	curl -fL -o $(IMDB_SPOILER)/imdb_spoiler.zip "https://www.kaggle.com/api/v1/datasets/download/rmisra/imdb-spoiler-dataset?datasetVersionNumber=1"
	unzip -o $(IMDB_SPOILER)/imdb_spoiler.zip -d $(IMDB_SPOILER)
	rm $(IMDB_SPOILER)/imdb_spoiler.zip

rotten_tomatoes: $(ROTTEN_TOMATOES)/rotten_tomatoes_movie_reviews.csv

$(ROTTEN_TOMATOES)/rotten_tomatoes_movie_reviews.csv:
	mkdir -p $(ROTTEN_TOMATOES)
	curl -fL -o $(ROTTEN_TOMATOES)/rotten_tomatoes.zip "https://www.kaggle.com/api/v1/datasets/download/andrezaza/clapper-massive-rotten-tomatoes-movies-and-reviews?datasetVersionNumber=4"
	unzip -o $(ROTTEN_TOMATOES)/rotten_tomatoes.zip -d $(ROTTEN_TOMATOES)
	rm $(ROTTEN_TOMATOES)/rotten_tomatoes.zip

wikidata: $(WIKIDATA)/links.csv $(WIKIDATA)/wikipedia_titles.csv

$(WIKIDATA)/links.csv: $(SNAPSHOT)/links.csv
	mkdir -p $(WIKIDATA)
	cp $(SNAPSHOT)/links.csv $(WIKIDATA)/links.csv

$(WIKIDATA)/wikipedia_titles.csv: $(SNAPSHOT)/wikipedia_titles.csv
	mkdir -p $(WIKIDATA)
	cp $(SNAPSHOT)/wikipedia_titles.csv $(WIKIDATA)/wikipedia_titles.csv

refresh: requirements imdb_spoiler rotten_tomatoes
	rm -rf $(WIKIDATA) $(WIKIPEDIA)
	mkdir -p $(WIKIDATA) $(WIKIPEDIA) $(LINKED) $(SNAPSHOT)
	curl -fL -G https://query.wikidata.org/sparql -H "Accept: text/csv" -H "User-Agent: PRrevIews/0.1 (FEUP PRI student project)" --data-urlencode query@wikidata_links.rq -o $(WIKIDATA)/links.csv
	@if grep -q "java.util.concurrent" $(WIKIDATA)/links.csv; then echo "Wikidata stopped the query halfway. Run make refresh again."; exit 1; fi
	$(PYTHON) data_wikipedia_titles.py
	$(PYTHON) data_link.py
	$(PYTHON) data_wikipedia.py
	cp $(WIKIDATA)/links.csv $(WIKIDATA)/wikipedia_titles.csv $(WIKIPEDIA)/film_articles.jsonl $(SNAPSHOT)

inspect: requirements collect
	mkdir -p $(INSPECTION)
	$(PYTHON) data_inspect.py

link: requirements collect
	mkdir -p $(LINKED)
	$(PYTHON) data_link.py

wikipedia: $(WIKIPEDIA)/film_articles.jsonl

$(WIKIPEDIA)/film_articles.jsonl: $(SNAPSHOT)/film_articles.jsonl
	mkdir -p $(WIKIPEDIA)
	cp $(SNAPSHOT)/film_articles.jsonl $(WIKIPEDIA)/film_articles.jsonl

cleaning: link
	@test -f $(SCRAPED)/full_reviews.jsonl || echo "WARNING: $(SCRAPED)/full_reviews.jsonl not found, so critic reviews will only have their short quotes. See README.md."
	mkdir -p $(PROCESSED)
	$(PYTHON) data_clean.py

sample: cleaning
	mkdir -p $(SAMPLED)
	$(PYTHON) data_sample.py

merge: sample wikipedia
	mkdir -p $(DOCUMENTS)
	$(PYTHON) data_merge.py

analysis: merge
	mkdir -p $(ANALYSIS)
	$(PYTHON) data_analysis.py

scrape: link
	mkdir -p $(SCRAPED)
	$(PYTHON) data_scrape.py

.DELETE_ON_ERROR:

.PHONY: all clean requirements collect imdb_spoiler rotten_tomatoes wikidata refresh inspect link wikipedia cleaning sample merge analysis scrape
