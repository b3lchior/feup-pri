# Solr retrieval (Milestone 2)

Two retrieval setups over the same 438,629 reviews, run in one Solr 10 container:

| Setup | Core | Schema | Queries |
|---|---|---|---|
| baseline | `reviews` | `baseline_schema.json` (tokenizer, accent folding, lowercase) | `queries/baseline/` |
| analysis only | `reviews_improved` | `improved_schema.json` (adds possessive removal, stopwords, Porter stemming) | `queries/baseline/` |
| improved | `reviews_improved` | `improved_schema.json` | `queries/improved/` (adds field boosts, phrase boosts, minimum match, English-only filter) |

## Requirements

Docker, `make`, `git`, `gcc`, and the Python environment of the repository (`../.venv`, with `requests`, `matplotlib`, `numpy`). Activate it before running any script: `source ../.venv/bin/activate`.

## Build

```sh
make              # starts Solr, loads baseline_schema.json, indexes ../data/documents/reviews.jsonl into core reviews
make improved     # creates core reviews_improved, loads improved_schema.json and the stopwords, indexes the same file
make trec_eval    # once: downloads and compiles trec_eval into trec_eval/
```

Each index build takes about 2 minutes and about 1 GB under `../data/solr/home`. After changing a schema or the stopword list, rebuild from scratch with `make clean && make && make improved`. Never run `make populate` on an existing index: replaced documents stay in the index until segments merge and distort the scores.

## Queries

Every file in `queries/<setup>/` is a Solr JSON request. The file name is the query id (`0001.json` is query 1) and must match `qrels/0001.txt`. To run one:

```sh
curl -s -X POST -H 'Content-Type: application/json' -d @queries/baseline/0001.json http://localhost:8983/solr/reviews/select
```

Results are grouped by film (`group.field=film_imdb_id`), so each row is one film ranked by its best-matching review.

## Judging

`qrels/NNNN.txt` lists, one per line, the `film_imdb_id` of every film judged relevant for query NNNN. Unlisted films count as not relevant, so every film in the top 30 of every setup must be judged.

```sh
make pool     # writes ../data/judging/pool/NNNN.md with the films not judged yet
```

Read a sheet, then add the `film_imdb_id` of every film you judge relevant to `qrels/NNNN.txt`, one per line, with no blank lines. `trec_eval` fails on duplicates, so afterwards run `sort -u qrels/NNNN.txt -o qrels/NNNN.txt`.

The sheets are written to `../data/`, which is git-ignored, because they contain review text.

## Evaluate

```sh
make evaluate
```

Runs the three configurations, saves `trec_eval.txt` and the precision-recall plots of each in `results/baseline/`, `results/analysis_only/` and `results/improved/`, and writes the comparison table and `results/comparison.png`. Run it only after the pool is judged.

## Files

```
Makefile, docker-compose.yml    build and run
baseline_schema.json, improved_schema.json, config/stopwords_en.txt
queries/, qrels/, results/
scripts/query_solr.py           queries a core with every JSON file of a folder
scripts/solr2trec.py            Solr results to TREC run format (one row per film)
scripts/qrels2trec.py           qrels files to TREC format
scripts/plot_pr.py              precision-recall plots
scripts/pool_sheet.py           judging sheets for films not judged yet
scripts/compare.py              comparison table and chart of the setups
evaluate.sh                     one evaluation: queries, qrels, core, output folder
filmsSchema.json                schema of a films core, not used yet
```
