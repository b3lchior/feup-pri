import json, os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import pandas as pd
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROOT, "data", "documents")
FIGS = os.path.join(ROOT, "eda", "figs")
os.makedirs(FIGS, exist_ok=True)

MAX_WORDS = 800
MIN_SCORED = 10

def savefig(name):
    plt.tight_layout(); plt.savefig(f"{FIGS}/{name}.png", dpi=200); plt.close()

KEEP = ["perspective", "text", "text_kind", "score", "word_count", "film_imdb_id"]

def load_reviews(path):
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            d = json.loads(line)
            rows.append({k: d.get(k) for k in KEEP})
    return pd.DataFrame(rows)

rev = load_reviews(f"{DOCS}/reviews.jsonl")
films = pd.read_json(f"{DOCS}/films.jsonl", lines=True)
rev["group"] = rev["perspective"] + "/" + rev["text_kind"]



# Review length
bins = np.linspace(0, MAX_WORDS, 61)
order = sorted(rev["group"].unique())
over = {g: (rev.loc[rev["group"] == g, "word_count"] > MAX_WORDS).mean() * 100 for g in order}

fig, ax = plt.subplots(1, 2, figsize=(11, 4))
for g in order:
    wc = rev.loc[rev["group"] == g, "word_count"]
    ax[0].hist(wc[wc <= MAX_WORDS], bins=bins, histtype="step", linewidth=1.6,
               label=f"{g} ({over[g]:.0f}% > {MAX_WORDS})")
ax[0].set_yscale("log")
ax[0].set_title(f"Review length (view limited to {MAX_WORDS} words)")
ax[0].set_xlabel("words"); ax[0].set_ylabel("reviews per bin (log scale)")
ax[0].legend(loc="upper center", bbox_to_anchor=(0.5, -0.22), ncol=1, frameon=False, fontsize=8)

data = [rev.loc[(rev["group"] == g) & (rev["word_count"] >= 1), "word_count"] for g in order]
ax[1].boxplot(data, tick_labels=order, showfliers=False, widths=0.5)
ax[1].set_yscale("log")
for i, d in enumerate(data, start=1):
    ax[1].text(i + 0.3, d.median(), f"median {d.median():.0f}", va="center", ha="left", fontsize=8)
ax[1].set_xlim(0.5, len(order) + 1.0)
ax[1].set_title("Word count by perspective and text kind (all texts)")
ax[1].set_ylabel("words (log scale)"); ax[1].grid(axis="y", alpha=.3)
savefig("text_length")



# Reviews per film 
per = rev.groupby(["film_imdb_id", "perspective"]).size().unstack(fill_value=0)
fig, ax = plt.subplots(1, 2, figsize=(10, 3.5), sharex=True)
for a, p in zip(ax, ["audience", "critic"]):
    a.hist(per[p], bins=40)
    a.set_title(f"{p.capitalize()} reviews per film")
    a.set_xlabel("reviews per film (capped at 200 by sampling)")
    a.set_ylabel("films")
savefig("reviews_per_film")



#  Film text kind share by perspective 
share = rev.groupby(["perspective", "text_kind"]).size().unstack(fill_value=0)
share = share.div(share.sum(axis=1), axis=0) * 100
ax = share.plot.barh(stacked=True, figsize=(7, 3), title="Text kind by perspective")
ax.set_xlabel("share of reviews (%)"); ax.set_ylabel("")
ax.legend(title="text kind", loc="upper center", bbox_to_anchor=(0.5, -0.25), ncol=2, frameon=False)
savefig("text_kind_share")



# 4. Film text lengths
fields = {"Plot summary": films["plot_summary"], "Wikipedia extract": films["wikipedia_extract"]}
lengths = {}
for name, s in fields.items():
    w = s.fillna("").astype(str).str.split().str.len()
    if (w > 0).any():
        lengths[f"{name}\n(n={int((w > 0).sum())} of {len(w)})"] = w[w > 0]
if lengths:
    fig, ax = plt.subplots(figsize=(7, 3.5))
    ax.boxplot(list(lengths.values()), tick_labels=list(lengths.keys()), vert=False, showfliers=False)
    ax.set_title("Film text fields: length")
    ax.set_xlabel("words"); ax.grid(axis="x", alpha=.3)
    savefig("film_text_length")



# Audience vs critic score gap per film
m = films.dropna(subset=["tomatometer", "audience_score"]).copy()
m["gap"] = m["audience_score"] - m["tomatometer"]

fig, ax = plt.subplots(figsize=(6.5, 3.5))
ax.hist(m["gap"], bins=40)
ax.axvline(0, color="black", linewidth=1)
ax.axvline(m["gap"].mean(), color="red", linestyle="--", label=f"mean = {m['gap'].mean():+.1f}")
ax.axvline(25, color="gray", linestyle=":", label=f"{(m['gap'] >= 25).sum()} films ≥ +25")
ax.set_xlabel("audience score − Tomatometer (points)"); ax.set_ylabel("films"); ax.legend()
ax.set_title(f"Audience score − Tomatometer (n={len(m)} films)")
savefig("gap")