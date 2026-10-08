RAW = ../data/raw
IMDB_SPOILER = $(RAW)/imdb_spoiler
ROTTEN_TOMATOES = $(RAW)/rotten_tomatoes

all: collect

collect: imdb_spoiler rotten_tomatoes

imdb_spoiler: $(IMDB_SPOILER)/IMDB_reviews.json

$(IMDB_SPOILER)/IMDB_reviews.json:
	mkdir -p $(IMDB_SPOILER)
	curl -fL -o $(IMDB_SPOILER)/imdb_spoiler.zip https://www.kaggle.com/api/v1/datasets/download/rmisra/imdb-spoiler-dataset
	unzip -o $(IMDB_SPOILER)/imdb_spoiler.zip -d $(IMDB_SPOILER)
	rm $(IMDB_SPOILER)/imdb_spoiler.zip

rotten_tomatoes: $(ROTTEN_TOMATOES)/rotten_tomatoes_critic_reviews.csv

$(ROTTEN_TOMATOES)/rotten_tomatoes_critic_reviews.csv:
	mkdir -p $(ROTTEN_TOMATOES)
	curl -fL -o $(ROTTEN_TOMATOES)/rotten_tomatoes.zip https://www.kaggle.com/api/v1/datasets/download/stefanoleone992/rotten-tomatoes-movies-and-critic-reviews-dataset
	unzip -o $(ROTTEN_TOMATOES)/rotten_tomatoes.zip -d $(ROTTEN_TOMATOES)
	rm $(ROTTEN_TOMATOES)/rotten_tomatoes.zip

.PHONY: all collect imdb_spoiler rotten_tomatoes
