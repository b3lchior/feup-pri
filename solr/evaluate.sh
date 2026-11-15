#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 3 ]]; then
  echo "Usage: $0 <queries_dir> <qrels_dir> <core>" >&2
  exit 1
fi

./scripts/qrels2trec.py --qrels "$2" > qrels_trec.txt

./scripts/query_solr.py \
    --queries "$1" \
    --collection "$3" \
| ./scripts/solr2trec.py > results_trec.txt

./trec_eval/trec_eval \
    -q -m all_trec \
    qrels_trec.txt results_trec.txt \
| ./scripts/plot_pr.py

rm -f qrels_trec.txt results_trec.txt
