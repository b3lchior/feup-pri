#!/usr/bin/env python3

import argparse
import json
import sys


def solr_to_trec(solr_response, run_id="run0"):
    for query_id, response in solr_response.items():
        try:
            docs = response["response"]["docs"]

            for rank, doc in enumerate(docs, start=1):
                print(f"{int(query_id)} Q0 {doc['film_imdb_id']} {rank} {doc['score']} {run_id}")

        except KeyError:
            print("Error: Invalid Solr response format. 'film_imdb_id' or 'docs' key not found.")
            sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert Solr results to TREC format.")
    parser.add_argument(
        "--run-id",
        type=str,
        default="run0",
        help="Experiment or system identifier (default: run0).",
    )
    args = parser.parse_args()

    solr_response = json.load(sys.stdin)

    solr_to_trec(solr_response, args.run_id)
