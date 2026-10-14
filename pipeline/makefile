VENV = $(abspath ../.venv)
PYTHON = $(VENV)/bin/python
RAW = ../data/raw
IMDB_SPOILER = $(RAW)/imdb_spoiler
ROTTEN_TOMATOES = $(RAW)/rotten_tomatoes
WIKIDATA = $(RAW)/wikidata
INSPECTION = ../data/inspection
LINKED = ../data/linked
PROCESSED = ../data/processed
SCRAPED = ../data/scraped
SAMPLED = ../data/sampled
DOCUMENTS = ../data/documents

all: requirements collect link cleaning sample merge

clean:
	rm -rf $(RAW) $(INSPECTION) $(LINKED) $(PROCESSED) $(SAMPLED) $(DOCUMENTS)

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

wikidata: $(WIKIDATA)/links.csv

$(WIKIDATA)/links.csv: wikidata_links.rq
	mkdir -p $(WIKIDATA)
	curl -fL -G https://query.wikidata.org/sparql -H "Accept: text/csv" -H "User-Agent: PRrevIews/0.1 (FEUP PRI student project)" --data-urlencode query@wikidata_links.rq -o $(WIKIDATA)/links.csv
	@if grep -q "Exception" $(WIKIDATA)/links.csv; then echo "Wikidata stopped the query halfway. Run make again."; exit 1; fi

inspect: requirements collect
	mkdir -p $(INSPECTION)
	$(PYTHON) data_inspect.py

link: requirements collect
	mkdir -p $(LINKED)
	$(PYTHON) data_link.py

cleaning: link
	@test -f $(SCRAPED)/full_reviews.jsonl || echo "WARNING: $(SCRAPED)/full_reviews.jsonl not found, so critic reviews will only have their short quotes. See README.md."
	mkdir -p $(PROCESSED)
	$(PYTHON) data_clean.py

sample: cleaning
	mkdir -p $(SAMPLED)
	$(PYTHON) data_sample.py

merge: sample
	mkdir -p $(DOCUMENTS)
	$(PYTHON) data_merge.py

scrape: link
	mkdir -p $(SCRAPED)
	$(PYTHON) data_scrape.py

.DELETE_ON_ERROR:

.PHONY: all clean requirements collect imdb_spoiler rotten_tomatoes wikidata inspect link cleaning sample merge scrape
