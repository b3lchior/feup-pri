#!/usr/bin/env python3

import argparse
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


def draw(results: dict, title: str):
    plt.figure()

    for query_id, metrics in results.items():
        recall = np.arange(0, 1.1, 0.1)

        pr_keys = [f"iprec_at_recall_{k:.2f}" for k in recall]
        iprecision = np.array([float(metrics[k]) for k in pr_keys])

        ap_score = float(metrics["map"])
        p_10 = float(metrics["P_10"])
        auc_score = float(metrics["11pt_avg"])

        line_kwargs = {
            "drawstyle": "steps-post",
            "label": f"Q{query_id}: AP={ap_score:.3f}, AUC={auc_score:.3f}, P@10={p_10:.3f}",
            "linewidth": 2,
            "markersize": 10,
        }

        plt.plot(recall, iprecision, **line_kwargs)

    plt.title(title)

    axis_kwargs = {
        "fontsize": 9,
        "verticalalignment": "baseline",
        "style": "italic",
    }

    plt.xlabel("Recall", fontdict=axis_kwargs)
    plt.ylabel("Precision", fontdict=axis_kwargs)
    plt.xlim(-0.005, 1.005)
    plt.ylim(-0.005, 1.005)
    plt.legend(loc="upper right", prop={"size": 10})
    plt.grid(True)
    plt.grid(linestyle="--", linewidth=0.5)
    plt.tight_layout()


def main(trec_eval_stdout: list, out: Path):
    results = {x: {} for x in set([x.split()[1] for x in trec_eval_stdout])}

    for metric in trec_eval_stdout:
        (name, query_id, value) = metric.split()
        results[query_id][name] = value

    del results["all"]
    results = {query_id: results[query_id] for query_id in sorted(results, key=int)}

    draw(results, "Precision-Recall Curve")

    if out is None:
        plt.show()
        return

    out.mkdir(parents=True, exist_ok=True)
    plt.savefig(out / "precision_recall.png", dpi=200)
    plt.close()

    for query_id, metrics in results.items():
        draw({query_id: metrics}, f"Precision-Recall Curve - Q{query_id}")
        plt.savefig(out / f"precision_recall_q{query_id}.png", dpi=200)
        plt.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Plot precision-recall curves from trec_eval output.")
    parser.add_argument("--out", type=Path, default=None, help="Folder to save the images in instead of showing them.")
    args = parser.parse_args()

    trec_eval_stdout = sys.stdin.readlines()

    main(trec_eval_stdout, args.out)
