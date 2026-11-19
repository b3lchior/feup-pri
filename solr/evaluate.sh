#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 3 ]]; then
  echo "Usage: $0 <queries_dir> <qrels_dir> <core> [out_dir]" >&2
  exit 1
fi

OUT="${4:-}"

./scripts/qrels2trec.py --qrels "$2" > qrels_trec.txt

./scripts/query_solr.py \
    --queries "$1" \
    --collection "$3" \
| ./scripts/solr2trec.py > results_trec.txt

./trec_eval/trec_eval \
    -q -m all_trec \
    qrels_trec.txt results_trec.txt > trec_eval_all.txt

if [[ -n "$OUT" ]]; then
  mkdir -p "$OUT"
  cp trec_eval_all.txt "$OUT/trec_eval.txt"
  ./scripts/plot_pr.py --out "$OUT" < trec_eval_all.txt
else
  ./scripts/plot_pr.py < trec_eval_all.txt
fi

rm -f qrels_trec.txt results_trec.txt trec_eval_all.txt
