SHELL := /bin/bash

export HOST_UID := $(shell id -u)
export HOST_GID := $(shell id -g)

SOLR := http://localhost:8983/solr
CORE := reviews
SOURCE := ../data/documents/reviews.jsonl
INDEX := ../data/solr/home

.PHONY: all up schema populate down clean

all: up schema populate

up:
	mkdir -p $(INDEX)
	docker compose up -d
	timeout 120 bash -c 'until curl -sf $(SOLR)/$(CORE)/admin/ping > /dev/null; do sleep 2; done'

schema:
	@if curl -sf $(SOLR)/$(CORE)/schema/fields/film_imdb_id > /dev/null; then \
		echo "schema already loaded (run make clean to start over)"; \
	else \
		curl -s --fail-with-body -X POST -H 'Content-Type: application/json' --data-binary @schema.json $(SOLR)/$(CORE)/schema; \
	fi

populate: $(SOURCE)
	curl -s --fail-with-body -X POST -H 'Content-Type: application/json' -T $(SOURCE) '$(SOLR)/$(CORE)/update/json/docs?commit=true'

down:
	docker compose down

clean:
	docker compose down
	rm -rf $(INDEX)
