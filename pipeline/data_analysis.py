import json
import math
import re
from collections import Counter

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from utils import log, write_stats

DOCUMENTS = "../data/documents"
ANALYSIS = "../data/analysis"

MAX_WORDS = 800
MIN_SCORED = 10
GAP = 25
SAMPLE_EVERY = 13
MIN_COUNT = 100
TOP_WORDS = 10
KEEP = ["perspective", "text_kind", "score", "word_count", "film_imdb_id"]

COLORS = {"audience": "#2a78d6", "critic": "#eb6834", "full": "#6250d6", "quote": "#1baf7a", "other": "#c9c8c2", "mean": "#e34948", "neutral": "#898781"}
GROUP_COLORS = {"audience/full": COLORS["audience"], "critic/full": COLORS["critic"], "critic/quote": COLORS["quote"]}
INK, INK2, MUTED, GRID, AXIS = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
REPORT_WIDTH = 3.33
REPORT_STYLE = {
    "font.family": "DejaVu Sans", "font.size": 7, "axes.labelsize": 7, "xtick.labelsize": 6.5, "ytick.labelsize": 6.5,
    "legend.fontsize": 6.5, "text.color": INK, "axes.labelcolor": INK2, "xtick.color": MUTED, "ytick.color": MUTED,
    "axes.edgecolor": AXIS, "axes.linewidth": 0.6, "xtick.major.width": 0.6, "ytick.major.width": 0.6,
    "xtick.major.size": 2.5, "ytick.major.size": 2.5, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.5,
    "axes.spines.top": False, "axes.spines.right": False, "axes.axisbelow": True, "legend.frameon": False,
}

STOP = set("""a about above after again against all also am an and another any are aren't around as at back be because been before being below between both but by can can't cannot could couldn't did didn't do does doesn't doing don't down during each even ever every few first for from further get gets getting go goes going got had hadn't has hasn't have haven't having he he'd he'll he's her here here's hers herself him himself his how how's however i i'd i'll i'm i've if in into is isn't it it's its itself just know last let's like little lot made make makes many may me might more most much must mustn't my myself never new no nor not now of off old on once one only or other ought our ours ourselves out over own quite rather really right same say says see seems shan't she she'd she'll she's should shouldn't since so some something still such take than that that's the their theirs them themselves then there there's these they they'd they'll they're they've thing things this those though three through time times to too two under until up upon us very want was wasn't way we we'd we'll we're we've well were weren't what what's when when's where where's whether which while who who's whole whom whose why why's will with without won't work would wouldn't year years yet you you'd you'll you're you've your yours yourself yourselves""".split())
FOREIGN = set("que de la el en los las una por con para del um uma".split())
TOKEN = re.compile(r"[a-z]+(?:'[a-z]+)?")


def save(fig, name):
    fig.savefig(f"{ANALYSIS}/{name}.png", dpi=200, bbox_inches="tight")
    fig.savefig(f"{ANALYSIS}/{name}.pdf", bbox_inches="tight")
    plt.close(fig)


def load_reviews():
    rows = []
    with open(f"{DOCUMENTS}/reviews.jsonl", encoding="utf-8") as file:
        for line in file:
            review = json.loads(line)
            rows.append({key: review.get(key) for key in KEEP})
    reviews = pd.DataFrame(rows)
    reviews["group"] = reviews["perspective"] + "/" + reviews["text_kind"]
    return reviews


def text_length(reviews):
    bins = np.linspace(0, MAX_WORDS, 61)
    order = sorted(reviews["group"].unique())
    fig, ax = plt.subplots(1, 2, figsize=(11, 4))
    for group in order:
        words = reviews.loc[reviews["group"] == group, "word_count"]
        over = (words > MAX_WORDS).mean() * 100
        ax[0].hist(words[words <= MAX_WORDS], bins=bins, histtype="step", linewidth=1.6, color=GROUP_COLORS[group], label=f"{group} ({over:.0f}% > {MAX_WORDS})")
    ax[0].set_yscale("log")
    ax[0].set_title(f"Review length (view limited to {MAX_WORDS} words)")
    ax[0].set_xlabel("words")
    ax[0].set_ylabel("reviews per bin (log scale)")
    ax[0].legend(loc="upper center", bbox_to_anchor=(0.5, -0.22), ncol=1, frameon=False, fontsize=8)
    data = [reviews.loc[(reviews["group"] == group) & (reviews["word_count"] >= 1), "word_count"] for group in order]
    ax[1].boxplot(data, tick_labels=order, showfliers=False, widths=0.5)
    ax[1].set_yscale("log")
    for position, words in enumerate(data, start=1):
        ax[1].text(position + 0.3, words.median(), f"median {words.median():.0f}", va="center", ha="left", fontsize=8)
    ax[1].set_xlim(0.5, len(order) + 1.0)
    ax[1].set_title("Word count by perspective and text kind (all texts)")
    ax[1].set_ylabel("words (log scale)")
    ax[1].grid(axis="y", alpha=0.3)
    fig.tight_layout()
    save(fig, "text_length")


def reviews_per_film(reviews):
    per_film = reviews.groupby(["film_imdb_id", "perspective"]).size().unstack(fill_value=0)
    fig, ax = plt.subplots(1, 2, figsize=(10, 3.5), sharex=True)
    for axis, perspective in zip(ax, ["audience", "critic"]):
        axis.hist(per_film[perspective], bins=40, color=COLORS[perspective])
        axis.set_title(f"{perspective.capitalize()} reviews per film")
        axis.set_xlabel("reviews per film (capped at 200 by sampling)")
        axis.set_ylabel("films")
        log("films", f"at the cap of 200 {perspective} reviews", int((per_film[perspective] == 200).sum()))
    fig.tight_layout()
    save(fig, "reviews_per_film")


def text_kind_share(reviews):
    share = reviews.groupby(["perspective", "text_kind"]).size().unstack(fill_value=0)
    share = share.div(share.sum(axis=1), axis=0) * 100
    ax = share.plot.barh(stacked=True, figsize=(7, 3), title="Text kind by perspective", color=[COLORS[kind] for kind in share.columns])
    ax.set_xlabel("share of reviews (%)")
    ax.set_ylabel("")
    ax.legend(title="text kind", loc="upper center", bbox_to_anchor=(0.5, -0.25), ncol=2, frameon=False)
    ax.figure.tight_layout()
    save(ax.figure, "text_kind_share")


def film_text_length(films):
    fields = {"Plot summary": films["plot_summary"], "Wikipedia extract": films["wikipedia_extract"]}
    lengths = {}
    for name, texts in fields.items():
        words = texts.fillna("").astype(str).str.split().str.len()
        if (words > 0).any():
            lengths[f"{name}\n(n={int((words > 0).sum())} of {len(words)})"] = words[words > 0]
    if lengths:
        fig, ax = plt.subplots(figsize=(7, 3.5))
        ax.boxplot(list(lengths.values()), tick_labels=list(lengths.keys()), orientation="horizontal", showfliers=False)
        ax.set_title("Film text fields: length")
        ax.set_xlabel("words")
        ax.grid(axis="x", alpha=0.3)
        fig.tight_layout()
        save(fig, "film_text_length")


def score_gap(reviews):
    scored = reviews.dropna(subset=["score"])
    counts = scored.groupby(["film_imdb_id", "perspective"]).size().unstack(fill_value=0)
    enough = counts[(counts["audience"] >= MIN_SCORED) & (counts["critic"] >= MIN_SCORED)].index
    mean = scored[scored["film_imdb_id"].isin(enough)].groupby(["film_imdb_id", "perspective"])["score"].mean().unstack()
    gap = mean["audience"] - mean["critic"]
    fig, ax = plt.subplots(figsize=(6.5, 3.8))
    ax.hist(gap, bins=40, color=COLORS["neutral"])
    ax.axvline(0, color=INK, linewidth=1)
    ax.axvline(gap.mean(), color=COLORS["mean"], linestyle="--", label=f"mean = {gap.mean():+.2f}")
    ax.set_title(f"Audience score - critic score per film (n={len(gap)} films, ≥{MIN_SCORED} scored reviews each side)", fontsize=9)
    ax.set_xlabel("score gap (audience - critic)")
    ax.set_ylabel("films")
    ax.legend()
    fig.tight_layout()
    save(fig, "gap")
    log("films", f"with at least {MIN_SCORED} scored reviews from each perspective", len(gap))


def critics_vs_audiences(films):
    films = films.dropna(subset=["tomatometer", "audience_score"])
    gap = films["audience_score"] - films["tomatometer"]
    groups = [(gap.abs() < GAP, COLORS["other"], f"within {GAP} points"),
              (gap >= GAP, COLORS["audience"], f"audiences ≥ {GAP} points higher"),
              (gap <= -GAP, COLORS["critic"], f"critics ≥ {GAP} points higher")]
    extreme = films.loc[gap.idxmax()]
    with plt.rc_context(REPORT_STYLE):
        fig, ax = plt.subplots(figsize=(REPORT_WIDTH, 2.75))
        ax.plot([0, 100], [0, 100], color=AXIS, linewidth=0.7, zorder=1)
        for mask, color, label in groups:
            ax.scatter(films.loc[mask, "tomatometer"], films.loc[mask, "audience_score"], s=7, color=color, edgecolors="white", linewidths=0.3, label=f"{label} ({int(mask.sum()):,})", zorder=2)
            log("films", label, int(mask.sum()))
        ax.annotate(f"{extreme['title']} ({extreme['tomatometer']:.0f} vs. {extreme['audience_score']:.0f})", (extreme["tomatometer"], extreme["audience_score"]),
                    xytext=(1.5, 97.5), fontsize=6, color=INK2, va="top", arrowprops=dict(arrowstyle="-", color=MUTED, linewidth=0.5, shrinkA=0, shrinkB=2))
        ax.set(xlim=(0, 100), ylim=(0, 100), xlabel="Tomatometer (critics, %)", ylabel="Audience score (%)")
        ax.set_xticks(range(0, 101, 20))
        ax.set_yticks(range(0, 101, 20))
        ax.set_aspect("equal")
        ax.legend(loc="lower right", handletextpad=0.2, borderaxespad=0.2, markerscale=1.6)
        save(fig, "critics_vs_audiences")


def audience_ratings(reviews):
    ratings = (reviews.loc[reviews["perspective"] == "audience", "score"] * 10).round().astype(int).value_counts().sort_index()
    with plt.rc_context(REPORT_STYLE):
        fig, ax = plt.subplots(figsize=(REPORT_WIDTH, 1.6))
        ax.bar(ratings.index, ratings.values / 1000, width=0.55, color=COLORS["audience"])
        ax.set(xlabel="IMDb rating given by the reviewer", ylabel="Reviews (thousands)")
        ax.set_xticks(range(1, 11))
        ax.grid(axis="x", visible=False)
        save(fig, "audience_ratings")


def tokens(text):
    return [token for token in TOKEN.findall(text.lower().replace("’", "'")) if len(token) > 2 and token not in STOP and token not in FOREIGN]


def log_odds(first, second):
    first_total, second_total = sum(first.values()), sum(second.values())
    total = first_total + second_total
    rows = []
    for word, count in (first + second).items():
        if count < MIN_COUNT:
            continue
        prior = count / 2
        delta = math.log((first[word] + prior) / (first_total + total / 2 - first[word] - prior)) - math.log((second[word] + prior) / (second_total + total / 2 - second[word] - prior))
        rows.append((word, delta / math.sqrt(1 / (first[word] + prior) + 1 / (second[word] + prior))))
    return sorted(rows, key=lambda row: row[1])


def distinctive_words():
    critics, audience, seen = Counter(), Counter(), 0
    with open(f"{DOCUMENTS}/reviews.jsonl", encoding="utf-8") as file:
        for line in file:
            review = json.loads(line)
            if review["perspective"] == "critic":
                critics.update(tokens(review["quote"]))
                continue
            seen += 1
            if seen % SAMPLE_EVERY == 0:
                audience.update(tokens(review["text"]))
    rows = log_odds(critics, audience)
    panels = [("Critic quotes", COLORS["critic"], rows[::-1][:TOP_WORDS]), ("Audience reviews", COLORS["audience"], rows[:TOP_WORDS])]
    pd.DataFrame([(title, word, abs(z)) for title, _, words in panels for word, z in words], columns=["group", "word", "z_score"]).to_csv(f"{ANALYSIS}/distinctive_words.csv", index=False)
    with plt.rc_context(REPORT_STYLE):
        fig, axes = plt.subplots(1, 2, figsize=(REPORT_WIDTH, 1.95), sharex=True)
        top = max(abs(z) for _, _, words in panels for _, z in words) * 1.08
        for ax, (title, color, words) in zip(axes, panels):
            ax.barh(range(len(words)), [abs(z) for _, z in words][::-1], height=0.6, color=color)
            ax.set_yticks(range(len(words)), [word for word, _ in words][::-1])
            ax.tick_params(axis="y", length=0, labelsize=6.3, labelcolor=INK)
            ax.grid(axis="y", visible=False)
            ax.set_xlim(0, top)
            ax.set_title(title, loc="left", fontsize=7, color=INK, fontweight="bold", pad=3)
        fig.supxlabel("Distinctiveness (weighted log-odds z-score)", fontsize=7, color=INK2, y=-0.07)
        fig.subplots_adjust(wspace=0.75)
        save(fig, "distinctive_words")


if __name__ == "__main__":
    reviews = load_reviews()
    films = pd.read_json(f"{DOCUMENTS}/films.jsonl", lines=True)
    text_length(reviews)
    reviews_per_film(reviews)
    text_kind_share(reviews)
    film_text_length(films)
    score_gap(reviews)
    critics_vs_audiences(films)
    audience_ratings(reviews)
    distinctive_words()
    write_stats(f"{ANALYSIS}/analysis_stats.csv")
