VENV = $(abspath ../.venv)
PYTHON = $(VENV)/bin/python
RAW = ../data/raw
IMDB_SPOILER = $(RAW)/imdb_spoiler
ROTTEN_TOMATOES = $(RAW)/rotten_tomatoes
INSPECTION = ../data/inspection
PROCESSED = ../data/processed

all: requirements collect inspect cleaning

clean:
	rm -rf $(RAW) $(INSPECTION) $(PROCESSED)

requirements: $(PYTHON)
	$(PYTHON) -m pip install -r ../requirements.txt

$(PYTHON):
	python3 -m venv $(VENV)

collect: imdb_spoiler rotten_tomatoes

imdb_spoiler: $(IMDB_SPOILER)/IMDB_reviews.json

$(IMDB_SPOILER)/IMDB_reviews.json:
	mkdir -p $(IMDB_SPOILER)
	curl -fL -o $(IMDB_SPOILER)/imdb_spoiler.zip https://www.kaggle.com/api/v1/datasets/download/rmisra/imdb-spoiler-dataset
	unzip -o $(IMDB_SPOILER)/imdb_spoiler.zip -d $(IMDB_SPOILER)
	rm $(IMDB_SPOILER)/imdb_spoiler.zip

rotten_tomatoes: $(ROTTEN_TOMATOES)/rotten_tomatoes_movie_reviews.csv

$(ROTTEN_TOMATOES)/rotten_tomatoes_movie_reviews.csv:
	mkdir -p $(ROTTEN_TOMATOES)
	curl -fL -o $(ROTTEN_TOMATOES)/rotten_tomatoes.zip https://www.kaggle.com/api/v1/datasets/download/andrezaza/clapper-massive-rotten-tomatoes-movies-and-reviews
	unzip -o $(ROTTEN_TOMATOES)/rotten_tomatoes.zip -d $(ROTTEN_TOMATOES)
	rm $(ROTTEN_TOMATOES)/rotten_tomatoes.zip

inspect: requirements collect
	mkdir -p $(INSPECTION)
	$(PYTHON) data_inspect.py

cleaning: requirements collect
	mkdir -p $(PROCESSED)
	$(PYTHON) data_clean.py

.PHONY: all clean requirements collect imdb_spoiler rotten_tomatoes inspect cleaning
