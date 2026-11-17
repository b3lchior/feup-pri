SHELL := /bin/bash

export HOST_UID := $(shell id -u)
export HOST_GID := $(shell id -g)

SOLR := http://localhost:8983/solr
CORE := reviews
SOURCE := ../data/documents/reviews.jsonl
INDEX := ../data/solr/home
IMPROVED_CORE := reviews_improved

.PHONY: all up schema populate improved improved-schema down clean trec_eval

all: up schema populate

up:
	mkdir -p $(INDEX)
	docker compose up -d
	timeout 120 bash -c 'until curl -sf $(SOLR)/$(CORE)/admin/ping > /dev/null; do sleep 2; done'

schema:
	@if curl -sf $(SOLR)/$(CORE)/schema/fields/film_imdb_id > /dev/null; then \
		echo "schema already loaded (run make clean to start over)"; \
	else \
		curl -s --fail-with-body -X POST -H 'Content-Type: application/json' --data-binary @baseline_schema.json $(SOLR)/$(CORE)/schema; \
	fi

populate: $(SOURCE)
	curl -s --fail-with-body -X POST -H 'Content-Type: application/json' -T $(SOURCE) '$(SOLR)/$(CORE)/update/json/docs?commit=true'

improved: improved-schema
	$(MAKE) populate CORE=$(IMPROVED_CORE)

improved-schema: up
	@if ! curl -sf $(SOLR)/$(IMPROVED_CORE)/admin/ping > /dev/null; then \
		docker compose exec -T solr solr create -c $(IMPROVED_CORE); \
	fi
	@if curl -sf $(SOLR)/$(IMPROVED_CORE)/schema/fieldtypes/review_text_en > /dev/null; then \
		echo "improved schema already loaded; use a new IMPROVED_CORE after changing the schema or stopwords"; \
	else \
		docker compose cp config/stopwords_en.txt solr:/var/solr/data/$(IMPROVED_CORE)/conf/stopwords_en.txt && \
		curl -s --fail-with-body -X POST -H 'Content-Type: application/json' --data-binary @improved_schema.json $(SOLR)/$(IMPROVED_CORE)/schema; \
	fi

down:
	docker compose down

clean:
	docker compose down
	rm -rf $(INDEX)

trec_eval:
	git clone https://github.com/usnistgov/trec_eval.git trec_eval
	$(MAKE) -C trec_eval
