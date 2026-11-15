#!/usr/bin/env python3

import glob
from argparse import ArgumentParser
from pathlib import Path


def qrels_to_trec(qrels: Path) -> None:
    for qrel_file in glob.glob(qrels.joinpath("*.txt").as_posix()):
        lines = open(qrel_file).readlines()

        filename = Path(qrel_file).stem

        for line in lines:
            doc_id = line.strip()
            print(f"{int(filename)} 0 {doc_id} 1")


if __name__ == "__main__":
    parser = ArgumentParser(description="Convert QRELs to TREC format")
    parser.add_argument(
        "--qrels",
        type=Path,
        default="qrels/",
        help="Path to QREL data.",
    )
    args = parser.parse_args()

    qrels_to_trec(args.qrels)
