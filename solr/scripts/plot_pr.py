#!/usr/bin/env python3

import sys

import matplotlib.pyplot as plt
import numpy as np


def main(trec_eval_stdout: list):
    results = {x: {} for x in set([x.split()[1] for x in trec_eval_stdout])}

    for metric in trec_eval_stdout:
        (name, query_id, value) = metric.split()
        results[query_id][name] = value

    del results["all"]

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

    plt.title("Precision-Recall Curve")

    axis_kwargs = {
        "fontsize": 9,
        "verticalalignment": "baseline",
        "style": "italic",
    }

    plt.xlabel("Recall", fontdict=axis_kwargs)
    plt.ylabel("Precision", fontdict=axis_kwargs)
    plt.xlim(-0.005, 1.005)
    plt.ylim(-0.005, 1.005)
    plt.legend(loc="lower left", prop={"size": 10})
    plt.grid(True)
    plt.grid(linestyle="--", linewidth=0.5)
    plt.tight_layout()

    plt.show()


if __name__ == "__main__":
    trec_eval_stdout = sys.stdin.readlines()

    main(trec_eval_stdout)
