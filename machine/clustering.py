"""Categorize tracks with unsupervised ML (K-Means).

Steps:
  1. Load machine/dataset/dataset.csv (cleaned).
  2. Scale the audio features.
  3. Sweep k = 2..20 -> elbow (inertia) + silhouette (10k sample),
     pick k by silhouette within the preferred 8-15 window.
  4. Fit KMeans, profile each cluster, auto-name it from its profile.
  5. Save PCA / elbow / silhouette / cluster-genre plots and the
     clustered dataset (original columns + cluster + cluster_name).

Outputs:
  machine/dataset/tracks_clustered.csv
  machine/dataset/cluster_names.csv
  machine/plots/{elbow,silhouette,pca_clusters,cluster_genre_heatmap}.png
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_samples, silhouette_score
from sklearn.preprocessing import StandardScaler

BASE = Path(__file__).parent
DATASET = BASE / "dataset" / "dataset.csv"
OUT_CSV = BASE / "dataset" / "tracks_clustered.csv"
OUT_NAMES = BASE / "dataset" / "cluster_names.csv"
PLOTS = BASE / "plots"

FEATURES = [
    "danceability",
    "energy",
    "speechiness",
    "acousticness",
    "instrumentalness",
    "liveness",
    "valence",
    "loudness",
    "tempo",
]
K_RANGE = range(2, 21)
K_PREFERRED = range(8, 16)  # user asked for ~8-15 clusters
RANDOM_STATE = 42
SAMPLE_SIZE = 10_000


def load():
    df = pd.read_csv(DATASET)
    X = StandardScaler().fit_transform(df[FEATURES])
    return df, X


def choose_k(X):
    rng = np.random.default_rng(RANDOM_STATE)
    sample_idx = rng.choice(len(X), size=min(SAMPLE_SIZE, len(X)), replace=False)
    rows = []
    for k in K_RANGE:
        model = KMeans(n_clusters=k, n_init=10, random_state=RANDOM_STATE).fit(X)
        sil = silhouette_score(X[sample_idx], model.labels_[sample_idx])
        rows.append((k, model.inertia_, sil))
        print(f"k={k:2d}  inertia={model.inertia_:>12,.0f}  silhouette={sil:.4f}")

    best_preferred = max(rows, key=lambda r: r[2] if r[0] in K_PREFERRED else -1)
    return rows, best_preferred[0]


def plot_elbow_silhouette(rows, k):
    ks = [r[0] for r in rows]
    inertia = [r[1] for r in rows]
    sil = [r[2] for r in rows]

    fig, ax = plt.subplots(1, 2, figsize=(12, 4.5))
    ax[0].plot(ks, inertia, "o-")
    ax[0].axvline(k, color="tab:red", ls="--", label=f"chosen k={k}")
    ax[0].set(title="Elbow method", xlabel="k", ylabel="inertia")
    ax[0].legend()
    ax[1].plot(ks, sil, "o-", color="tab:green")
    ax[1].axvline(k, color="tab:red", ls="--", label=f"chosen k={k}")
    ax[1].set(title="Silhouette score (10k sample)", xlabel="k", ylabel="silhouette")
    ax[1].legend()
    fig.tight_layout()
    fig.savefig(PLOTS / "elbow_silhouette.png", dpi=150)
    plt.close(fig)


def profile_and_name(df, labels, X):
    scaled = pd.DataFrame(X, columns=FEATURES)
    scaled["cluster"] = labels
    raw = df[FEATURES].copy()
    raw["cluster"] = labels

    z = scaled.groupby("cluster").mean()  # z-scores: StandardScaler was fit globally
    means = raw.groupby("cluster").mean()
    sizes = pd.Series(labels).value_counts().sort_index()

    print("\ncluster profiles (raw means | z vs global):")
    for c in means.index:
        top = z.loc[c].reindex(z.loc[c].abs().sort_values(ascending=False).index)[:4]
        detail = ", ".join(f"{f}={means.loc[c, f]:.2f}({top[f]:+.1f}σ)" for f in top.index)
        print(f"  [{c}] n={sizes[c]:,}  {detail}")

    names = {}
    used = set()
    for c in means.index:
        name = _rule_name(means.loc[c], z.loc[c])
        if name in used:  # keep names unique, disambiguate by top feature
            word = _word(z.loc[c])
            name = f"{name} ({word})"
        used.add(name)
        names[c] = name
    return names, z, means, sizes


def _rule_name(m, z):
    """Name a cluster from its average feature profile."""
    if m.instrumentalness > 0.4:
        return "Instrumental focus"
    if m.speechiness > 0.22:
        return "Spoken word"
    if m.energy > 0.7 and m.danceability > 0.65:
        return "High-energy dance"
    if m.acousticness > 0.55 and m.energy < 0.4:
        return "Chill acoustic"
    if m.valence < 0.4 and m.tempo < 105:
        return "Sad and slow"
    if m.liveness > 0.35:
        return "Live energy"
    if m.energy > 0.65:
        return "Driving rock energy"
    if m.danceability > 0.62:
        return "Smooth groove"
    if m.acousticness > 0.45:
        return "Soft acoustic"
    if m.valence > 0.6:
        return "Feel-good upbeat"
    if m.energy < 0.4:
        return "Mellow and calm"
    return "Balanced mix"


WORD_MAP = {
    ("tempo", True): "fast-paced",
    ("tempo", False): "slow-burning",
    ("loudness", True): "loud",
    ("loudness", False): "soft-spoken",
    ("valence", True): "feel-good",
    ("valence", False): "darker",
    ("liveness", True): "live-feel",
    ("speechiness", True): "talk-heavy",
    ("acousticness", True): "acoustic",
    ("acousticness", False): "electronic-leaning",
    ("instrumentalness", True): "instrumental",
    ("energy", True): "high-octane",
    ("energy", False): "laid-back",
    ("danceability", True): "groovy",
    ("danceability", False): "off-kilter",
}


def _word(z):
    for f in z.abs().sort_values(ascending=False).index:
        if (f, z[f] > 0) in WORD_MAP:
            return WORD_MAP[(f, z[f] > 0)]
    return "variant"


def plot_pca(X, labels, names, n_components):
    proj = PCA(n_components=2, random_state=RANDOM_STATE).fit_transform(X)
    rng = np.random.default_rng(RANDOM_STATE)
    idx = rng.choice(len(proj), size=min(20_000, len(proj)), replace=False)

    fig, ax = plt.subplots(figsize=(11, 8))
    sc = ax.scatter(proj[idx, 0], proj[idx, 1], c=labels[idx], cmap="tab20", s=6, alpha=0.5)
    handles = [
        plt.Line2D([], [], marker="o", ls="", color=sc.cmap(sc.norm(c)), label=f"{c}: {names[c]}")
        for c in sorted(names)
    ]
    ax.legend(handles=handles, title="cluster", bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=8)
    ax.set(
        title=f"Tracks by K-Means cluster (PCA, {n_components[0]:.0%} + {n_components[1]:.0%} var)",
        xlabel="PC1",
        ylabel="PC2",
    )
    fig.tight_layout()
    fig.savefig(PLOTS / "pca_clusters.png", dpi=150)
    plt.close(fig)


def plot_genre_heatmap(df, labels):
    ct = pd.crosstab(df.track_genre, labels)
    share = ct.div(ct.sum(axis=1), axis=0)  # genre -> cluster share
    top = share.max(axis=1).sort_values(ascending=False).head(30).index  # most cluster-specific genres
    view = share.loc[top]

    fig, ax = plt.subplots(figsize=(9, 10))
    im = ax.imshow(view.values, cmap="viridis", aspect="auto", vmin=0, vmax=1)
    ax.set_xticks(range(view.shape[1]), [str(c) for c in view.columns])
    ax.set_yticks(range(view.shape[0]), view.index, fontsize=7)
    ax.set(xlabel="cluster", title="track_genre share per cluster (top 30 most distinct genres)")
    fig.colorbar(im, ax=ax, label="share of genre in cluster")
    fig.tight_layout()
    fig.savefig(PLOTS / "cluster_genre_heatmap.png", dpi=150)
    plt.close(fig)


def main():
    PLOTS.mkdir(exist_ok=True)
    df, X = load()
    print(f"loaded {len(df):,} rows x {len(FEATURES)} features")

    rows, k = choose_k(X)
    print(f"\nchosen k = {k} (best silhouette in {K_PREFERRED.start}-{K_PREFERRED.stop - 1})")
    plot_elbow_silhouette(rows, k)

    model = KMeans(n_clusters=k, n_init=10, random_state=RANDOM_STATE).fit(X)
    labels = model.labels_
    sil = silhouette_score(X, labels)
    print(f"final silhouette (full data): {sil:.4f}")

    names, z, means, sizes = profile_and_name(df, labels, X)
    print("\ncluster names:")
    for c, n in names.items():
        print(f"  [{c}] {n}  (n={sizes[c]:,})")

    df["cluster"] = labels
    df["cluster_name"] = df.cluster.map(names)
    df.to_csv(OUT_CSV, index=False)
    pd.DataFrame({"cluster": list(names), "name": [names[c] for c in names]}).to_csv(
        OUT_NAMES, index=False
    )

    pca = PCA(n_components=2, random_state=RANDOM_STATE).fit(X)
    plot_pca(X, labels, names, pca.explained_variance_ratio_)
    plot_genre_heatmap(df, labels)

    print(f"\nwrote {OUT_CSV}")
    print(f"wrote {OUT_NAMES}")
    print(f"wrote {PLOTS}/elbow_silhouette.png, pca_clusters.png, cluster_genre_heatmap.png")


if __name__ == "__main__":
    main()
