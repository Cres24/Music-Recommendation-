"""Content-based song recommender (numpy only, no pandas/sklearn).

Pipeline:  answers -> build_profile() -> filter_candidates() ->
score_songs() -> rerank_mmr() -> recommend()

Answers format (dict, letters as listed in rules.py):
    {
      "q1": ["A", "F"],   # genres (multi)
      "q2": ["B"],        # what they care about (multi)
      "q3": ["C", "G"],   # moods (multi)
      "q4": "A",          # listening context (single)
      "q5": "B",          # playlist taste (single)
      "seeds": [{"track_name": "...", "artists": "..."}],  # optional
    }

All scoring happens in the artifact's 0-1 scaled space; rules.py holds
the native-unit targets that get converted here.
"""

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from rules import (  # noqa: E402
    FEATURES,
    GENRE_GROUPS,
    MOOD_TARGETS,
    Q2_RULES,
    Q4_RULES,
    Q5_RULES,
    SCORE_WEIGHTS,
    SCORE_WEIGHTS_NOVELTY,
    MMR_LAMBDA,
    MMR_POOL,
    MAX_PER_ARTIST,
    MIN_CANDIDATES,
    SEED_BLEND,
    NOVELTY_SCALE,
)

ARTIFACT = Path(__file__).parent / "artifacts" / "artifact.npz"
D = len(FEATURES)
SQRT_D = float(np.sqrt(D))


def _decode(arr):
    return [x.decode("utf-8") for x in arr]


class Artifact:
    def __init__(self, npz):
        self.min = npz["scaler_min"].astype(np.float64)
        self.max = npz["scaler_max"].astype(np.float64)
        self.range = np.where(self.max > self.min, self.max - self.min, 1.0)

        self.X = npz["features"].astype(np.float32)      # (N, D) scaled 0-1
        self.pop = npz["popularity"].astype(np.float32)  # 0-100
        self.explicit = npz["explicit"].astype(bool)

        self.genre_codes = npz["genre_codes"]
        self.genre_names = _decode(npz["genre_names"])
        self.genre_code_of = {g: i for i, g in enumerate(self.genre_names)}
        self.artist_codes = npz["artist_codes"]
        self.artist_names = _decode(npz["artist_names"])
        self.cluster_codes = npz["cluster_codes"]
        self.cluster_names = _decode(npz["cluster_names"])

        offsets, data = npz["track_offsets"], npz["track_data"]
        self.track_names = [
            bytes(data[offsets[i]:offsets[i + 1]]).decode("utf-8")
            for i in range(len(offsets) - 1)
        ]
        self.track_names_cf = [t.casefold() for t in self.track_names]

        self.centroids = npz["centroids"].astype(np.float32)
        self.feature_mean = npz["feature_mean"].astype(np.float32)
        self.popularity_mean = float(npz["popularity_mean"])
        self.index = {f: i for i, f in enumerate(FEATURES)}
        self.n = len(self.X)

    def to_scaled(self, feature, native_value):
        """Map a native-unit value (e.g. tempo=135) into scaled space."""
        i = self.index[feature]
        return float(np.clip((native_value - self.min[i]) / self.range[i], 0.0, 1.0))

    def display(self, i):
        return {
            "track_name": self.track_names[i],
            "artists": self.artist_names[self.artist_codes[i]],
            "track_genre": self.genre_names[self.genre_codes[i]],
            "cluster_name": self.cluster_names[self.cluster_codes[i]],
            "popularity": int(self.pop[i]),
            "explicit": bool(self.explicit[i]),
        }


@lru_cache(maxsize=1)
def load() -> Artifact:
    return Artifact(np.load(ARTIFACT, allow_pickle=False))


@dataclass
class Profile:
    target: np.ndarray                 # (D,) scaled space
    weights: np.ndarray                # (D,) similarity feature weights
    filters: dict = field(default_factory=dict)   # feature -> (lo, hi) scaled
    genres: np.ndarray | None = None   # allowed genre codes, None = no filter
    popularity_target: float = 0.0
    popularity_weight: float = 1.0
    novelty: bool = False

    def score_weights(self):
        return SCORE_WEIGHTS_NOVELTY if self.novelty else SCORE_WEIGHTS


def _as_list(value):
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    return list(value)


def _apply_rule(rule, target, weights, filters, art, mood_features=None):
    """Apply one rules entry. Returns the popularity weight multiplier
    (popularity is scored separately from the audio features)."""
    pop_mult = 1.0
    for feature, value in rule.get("targets", {}).items():
        if feature == "popularity":
            continue
        target[art.index[feature]] = art.to_scaled(feature, value)
        if mood_features is not None:
            mood_features.add(feature)
    for feature, mult in rule.get("weights", {}).items():
        if feature == "popularity":
            pop_mult *= mult
        else:
            weights[art.index[feature]] *= mult
    for feature, (lo, hi) in rule.get("filters", {}).items():
        filters[feature] = (art.to_scaled(feature, lo), art.to_scaled(feature, hi))
    return pop_mult


def build_profile(answers: dict) -> Profile:
    art = load()
    target = art.feature_mean.copy()
    weights = np.ones(D, dtype=np.float32)
    filters = {}
    mood_features = set()
    popularity_target = art.popularity_mean

    q1 = _as_list(answers.get("q1"))
    q2 = _as_list(answers.get("q2"))
    q3 = _as_list(answers.get("q3"))
    q4 = answers.get("q4")
    q5 = answers.get("q5")

    # Q5-G ("reminds me of a memory") pulls in the nostalgic mood.
    moods = list(q3)
    if q5 == "G" and "G" not in moods:
        moods.append("G")

    # Q3: average the targets of every chosen mood.
    if moods:
        collected, pop_targets = {}, []
        for mood in moods:
            for feature, value in MOOD_TARGETS[mood].items():
                if feature == "popularity":
                    pop_targets.append(value)
                else:
                    collected.setdefault(feature, []).append(value)
        if pop_targets:
            popularity_target = float(np.mean(pop_targets))
        for feature, values in collected.items():
            target[art.index[feature]] = art.to_scaled(feature, float(np.mean(values)))
            mood_features.add(feature)

    # Q4: adjust for the listening context (applied after the mood).
    popularity_weight = 1.0
    if q4 in Q4_RULES:
        popularity_weight *= _apply_rule(Q4_RULES[q4], target, weights, filters, art)

    # Q2: weights + filters for what the listener cares about.
    for letter in q2:
        if letter in Q2_RULES:
            popularity_weight *= _apply_rule(Q2_RULES[letter], target, weights, filters, art)

    # Q5: playlist taste.
    novelty = False
    if q5 in Q5_RULES:
        rule = Q5_RULES[q5]
        popularity_weight *= _apply_rule(rule, target, weights, filters, art)
        if rule.get("popularity_target") is not None:
            popularity_target = rule["popularity_target"]
        novelty = bool(rule.get("novelty"))
        if rule.get("double_mood_weights"):
            for feature in mood_features:
                weights[art.index[feature]] *= 2.0

    # Q1: genre filter (J / missing / empty = no filter).
    genres = None
    letters = [L for L in q1 if L in GENRE_GROUPS and L != "J"]
    if letters:
        codes = set()
        for letter in letters:
            for genre in GENRE_GROUPS[letter]:
                codes.add(art.genre_code_of[genre])
        genres = np.array(sorted(codes), dtype=art.genre_codes.dtype)

    return Profile(
        target=target,
        weights=weights,
        filters=filters,
        genres=genres,
        popularity_target=float(popularity_target),
        popularity_weight=float(popularity_weight),
        novelty=novelty,
    )


def filter_candidates(profile: Profile) -> np.ndarray:
    """Return candidate row indices, relaxing filters in tiers so the
    caller never runs out of songs: all -> drop cluster -> drop
    feature filters -> drop genre."""
    art = load()

    genre_mask = np.ones(art.n, dtype=bool)
    if profile.genres is not None:
        genre_mask = np.isin(art.genre_codes, profile.genres)

    feature_mask = np.ones(art.n, dtype=bool)
    for feature, (lo, hi) in profile.filters.items():
        col = art.X[:, art.index[feature]]
        feature_mask &= (col >= lo) & (col <= hi)

    # The 3 clusters whose centroids sit closest to the target vector.
    dist = np.linalg.norm(art.centroids - profile.target, axis=1)
    top_clusters = np.argsort(dist)[:3]
    cluster_mask = np.isin(art.cluster_codes, top_clusters)

    tiers = [
        genre_mask & feature_mask & cluster_mask,
        genre_mask & feature_mask,
        genre_mask,
        np.ones(art.n, dtype=bool),
    ]
    for tier in tiers:
        idx = np.flatnonzero(tier)
        if len(idx) >= MIN_CANDIDATES:
            return idx
    idx = np.flatnonzero(tiers[-1])
    return idx if len(idx) else np.arange(art.n)


def score_songs(profile: Profile, candidates: np.ndarray):
    """Weighted Euclidean similarity + popularity (+ novelty)."""
    art = load()
    x = art.X[candidates]
    w = profile.weights

    dist = np.sqrt((((x - profile.target) ** 2) * w).sum(axis=1))
    dmax = float(np.sqrt(w.sum())) or 1.0
    similarity = 1.0 - np.minimum(dist / dmax, 1.0)

    pop_score = 1.0 - np.abs(art.pop[candidates] - profile.popularity_target) / 100.0
    pop_score = np.clip(pop_score, 0.0, 1.0)

    sw = profile.score_weights()
    if sw["novelty"]:
        own = art.centroids[art.cluster_codes[candidates]]
        novelty = np.clip(np.linalg.norm(x - own, axis=1) / NOVELTY_SCALE, 0.0, 1.0)
    else:
        novelty = 0.0

    final = sw["sim"] * similarity + sw["pop"] * profile.popularity_weight * pop_score
    final = final + sw["novelty"] * novelty
    return candidates, final


def rerank_mmr(candidates: np.ndarray, scores: np.ndarray, k: int = 20) -> list:
    """Maximal marginal relevance: relevance - redundancy, plus caps of
    2 songs per artist and a per-genre cap for broad mixes."""
    art = load()
    order = np.argsort(-scores, kind="stable")[:MMR_POOL]
    pool = candidates[order]
    pool_scores = scores[order]
    pool_x = art.X[pool]

    n_genres = len(np.unique(art.genre_codes[pool]))
    genre_cap = max(5, -(-k // max(n_genres, 1)))  # ceil(k / genres)

    picked, available = [], np.ones(len(pool), dtype=bool)
    artist_count, genre_count = {}, {}

    while len(picked) < k and available.any():
        best_i, best_val = -1, -np.inf
        for i in range(len(pool)):
            if not available[i]:
                continue
            artist = int(art.artist_codes[pool[i]])
            genre = int(art.genre_codes[pool[i]])
            if artist_count.get(artist, 0) >= MAX_PER_ARTIST:
                continue
            if genre_count.get(genre, 0) >= genre_cap:
                continue
            redundancy = 0.0
            if picked:
                redundancy = float(
                    np.min(np.linalg.norm(pool_x[picked] - pool_x[i], axis=1)) / SQRT_D
                )
            val = MMR_LAMBDA * pool_scores[i] - (1.0 - MMR_LAMBDA) * redundancy
            if val > best_val:
                best_val, best_i = val, i
        if best_i < 0:  # caps blocked everything: fill up without them
            best_i = int(np.flatnonzero(available)[
                np.argmax(pool_scores[available])])
        available[best_i] = False
        picked.append(best_i)
        artist = int(art.artist_codes[pool[best_i]])
        genre = int(art.genre_codes[pool[best_i]])
        artist_count[artist] = artist_count.get(artist, 0) + 1
        genre_count[genre] = genre_count.get(genre, 0) + 1

    return [int(pool[i]) for i in picked]


def match_seed(track_name: str, artists: str | None = None) -> list:
    """Row indices for a seed song: exact name (+artist) first, then
    exact name, then substring."""
    art = load()
    name = track_name.strip().casefold()
    artist = (artists or "").strip().casefold()

    exact = [i for i, t in enumerate(art.track_names_cf) if t == name]
    if artist and len(exact) > 1:
        exact = [i for i in exact
                 if artist in art.artist_names[art.artist_codes[i]].casefold()]
    if exact:
        return exact[:1]
    return [i for i, t in enumerate(art.track_names_cf) if name in t][:1]


def _apply_seeds(profile: Profile, seeds: list) -> list:
    art = load()
    rows = []
    for seed in seeds:
        rows.extend(match_seed(seed.get("track_name", ""), seed.get("artists")))
    if rows:
        seed_vec = art.X[rows].mean(axis=0)
        a, b = SEED_BLEND
        profile.target = (a * seed_vec + b * profile.target).astype(np.float32)
    return rows


def recommend(answers: dict, k: int = 20) -> list:
    profile = build_profile(answers)
    matched = _apply_seeds(profile, answers.get("seeds") or [])
    candidates = filter_candidates(profile)
    candidates, scores = score_songs(profile, candidates)
    picked = rerank_mmr(candidates, scores, k=k)

    art = load()
    results = []
    for rank, i in enumerate(picked, start=1):
        row = {"rank": rank, "row": i, "score": round(float(scores[candidates == i][0]), 4)}
        row.update(art.display(i))
        results.append(row)
    return results, {"seeds_matched": len(matched), "candidates": len(candidates)}
