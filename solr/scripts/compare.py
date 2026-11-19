#!/usr/bin/env python3

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


def read_metrics(folder: Path):
    metrics = {}
    for line in open(folder / "trec_eval.txt"):
        name, query_id, value = line.split()
        if name in ("map", "P_10"):
            metrics.setdefault(query_id, {})[name] = float(value)
    return metrics


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compare setups using their saved trec_eval results.")
    parser.add_argument("folders", nargs="+", type=Path)
    parser.add_argument("--out", type=Path, default=Path("results"))
    args = parser.parse_args()

    setups = {folder.name: read_metrics(folder) for folder in args.folders}
    names = list(setups)
    queries = sorted((q for q in setups[names[0]] if q != "all"), key=int) + ["all"]

    print("| Query | " + " | ".join(f"{n} AP | {n} P@10" for n in names) + " |")
    print("|---|" + "---|---|" * len(names))
    for q in queries:
        label = "MAP" if q == "all" else f"Q{q}"
        print(f"| {label} | " + " | ".join(f"{setups[n][q]['map']:.3f} | {setups[n][q]['P_10']:.3f}" for n in names) + " |")

    positions = np.arange(len(queries))
    width = 0.8 / len(names)
    figure, axes = plt.subplots(1, 2, figsize=(12, 4))
    for axis, metric, title in zip(axes, ["map", "P_10"], ["Average precision (last bar: MAP)", "Precision at 10 (last bar: mean)"]):
        for i, name in enumerate(names):
            axis.bar(positions + i * width, [setups[name][q][metric] for q in queries], width, label=name)
        axis.set_xticks(positions + width * (len(names) - 1) / 2)
        axis.set_xticklabels([f"Q{q}" if q != "all" else "all" for q in queries])
        axis.set_title(title)
        axis.set_ylim(0, 1)
        axis.grid(axis="y", linestyle="--", linewidth=0.5)
    axes[0].legend()
    figure.tight_layout()

    args.out.mkdir(parents=True, exist_ok=True)
    figure.savefig(args.out / "comparison.png", dpi=200)
