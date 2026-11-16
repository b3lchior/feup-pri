#!/usr/bin/env python3

import argparse
import glob
import json
import sys
from pathlib import Path

import requests


def fetch_solr_results(query_file, solr_uri, collection):
    try:
        query_params = json.load(open(query_file))
    except FileNotFoundError:
        print(f"Error: Query file {query_file} not found.")
        sys.exit(1)

    uri = f"{solr_uri}/{collection}/select"

    try:
        response = requests.post(uri, json=query_params)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Error querying Solr: {e}")
        sys.exit(1)

    return response.json()


def main(query_folder: Path, solr_uri, collection):
    results = {}

    for query_file in glob.glob(query_folder.joinpath("*.json").as_posix()):
        filename = Path(query_file).stem
        results[int(filename)] = fetch_solr_results(query_file, solr_uri, collection)

    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Fetch search results from Solr and output them in JSON format."
    )
    parser.add_argument(
        "--queries",
        type=Path,
        required=True,
        help="Path to the directory containing JSON files with Solr query parameters",
    )
    parser.add_argument(
        "--uri",
        type=str,
        default="http://localhost:8983/solr",
        help="The URI of the Solr instance (default: http://localhost:8983/solr).",
    )
    parser.add_argument(
        "--collection",
        type=str,
        default="reviews",
        help="Name of the Solr core to query (default: 'reviews').",
    )
    args = parser.parse_args()

    main(args.queries, args.uri, args.collection)
