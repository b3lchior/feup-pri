RAW = ../data/raw
PROCESSED = ../data/processed
IMDB_SPOILER = $(RAW)/imdb_spoiler
ROTTEN_TOMATOES = $(RAW)/rotten_tomatoes

all: collect extract_movies

collect: imdb_spoiler rotten_tomatoes

imdb_spoiler: $(IMDB_SPOILER)/IMDB_reviews.json

$(IMDB_SPOILER)/IMDB_reviews.json:
	mkdir -p $(IMDB_SPOILER)
	curl -fL -o $(IMDB_SPOILER)/imdb_spoiler.zip https://www.kaggle.com/api/v1/datasets/download/rmisra/imdb-spoiler-dataset
	unzip -o $(IMDB_SPOILER)/imdb_spoiler.zip -d $(IMDB_SPOILER)
	rm $(IMDB_SPOILER)/imdb_spoiler.zip

$(IMDB_SPOILER)/title.basics.tsv:
	mkdir -p $(IMDB_SPOILER)
	curl -fL --compressed -o $(IMDB_SPOILER)/title.basics.tsv.gz https://datasets.imdbws.com/title.basics.tsv.gz
	gunzip -f $(IMDB_SPOILER)/title.basics.tsv.gz

rotten_tomatoes: $(ROTTEN_TOMATOES)/rotten_tomatoes_critic_reviews.csv

$(ROTTEN_TOMATOES)/rotten_tomatoes_critic_reviews.csv:
	mkdir -p $(ROTTEN_TOMATOES)
	curl -fL -o $(ROTTEN_TOMATOES)/rotten_tomatoes.zip https://www.kaggle.com/api/v1/datasets/download/stefanoleone992/rotten-tomatoes-movies-and-critic-reviews-dataset
	unzip -o $(ROTTEN_TOMATOES)/rotten_tomatoes.zip -d $(ROTTEN_TOMATOES)
	rm $(ROTTEN_TOMATOES)/rotten_tomatoes.zip

extract_movies: $(IMDB_SPOILER)/IMDB_reviews.json \
		$(IMDB_SPOILER)/IMDB_movie_details.json \
		$(IMDB_SPOILER)/title.basics.tsv \
		$(ROTTEN_TOMATOES)/rotten_tomatoes_critic_reviews.csv \
		$(ROTTEN_TOMATOES)/rotten_tomatoes_movies.csv
	python3 extract_reviewed_movies.py

wikipedia: extract_movies
	python3 ../../wikipedia_film.py --search \
		--titles-file ../data/processed/wikipedia_titles.txt \
		--out ../data/processed/reviewed_films.jsonl

.PHONY: all collect imdb_spoiler rotten_tomatoes extract_movies wikipedia
