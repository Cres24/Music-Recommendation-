"""Sanity tests for the recommender: the three personas from the project
document, plus structural checks (counts, caps, unique songs).

Run:  uv run python machine/test_recommender.py
Exits non-zero if any assertion fails.
"""

from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import recommender  # noqa: E402
from rules import GENRE_GROUPS, FEATURES  # noqa: E402

PERSONAS = {
    "gym person": {
        "answers": {"q1": ["C"], "q2": ["C"], "q3": ["D"], "q4": "D", "q5": "C"},
        "genres": {"C"},
    },
    "study person": {
        "answers": {"q1": ["G"], "q2": ["E"], "q3": ["B"], "q4": "A", "q5": "F"},
        "genres": {"G"},
    },
    "sad indie fan": {
        "answers": {"q1": ["F"], "q2": ["B"], "q3": ["C"], "q4": "E", "q5": "B"},
        "genres": {"F"},
    },
}


def run(label, answers):
    art = recommender.load()
    results, meta = recommender.recommend(answers)
    print(f"\n=== {label} ===")
    print(f"candidates={meta['candidates']:,}  seeds_matched={meta['seeds_matched']}")
    for r in results[:10]:
        print(f"  {r['rank']:2d}. {r['score']:.3f}  {r['track_name']} — "
              f"{r['artists']} [{r['track_genre']} / {r['cluster_name']}]")

    # Structural checks.
    assert len(results) == 20, f"expected 20 results, got {len(results)}"
    names = [r["track_name"] for r in results]
    assert len(set(names)) == len(names), "duplicate tracks in results"
    artists = [r["artists"] for r in results]
    for a in set(artists):
        assert artists.count(a) <= 2, f"artist cap exceeded: {a}"

    # Feature means over the returned songs (native units).
    indices = _result_rows(results)
    means = {}
    for i, feature in enumerate(FEATURES):
        values = art.min[i] + art.X[indices, i] * art.range[i]  # back to native
        means[feature] = float(values.mean())
    genres = {results[j]["track_genre"] for j in range(len(results))}
    return results, means, genres


def _result_rows(results):
    return np.array([r["row"] for r in results])


def main():
    failures = []

    results, means, genres = run(**_args("gym person"))
    allowed = {g for L in PERSONAS["gym person"]["genres"] for g in GENRE_GROUPS[L]}
    try:
        assert genres <= allowed, f"genre filter leaked: {genres - allowed}"
        assert means["energy"] > 0.60, f"energy too low: {means['energy']:.2f}"
        assert means["tempo"] > 115, f"tempo too slow: {means['tempo']:.0f} BPM"
        assert means["danceability"] > 0.55, f"not danceable: {means['danceability']:.2f}"
    except AssertionError as e:
        failures.append(f"gym person: {e}")

    results, means, genres = run(**_args("study person"))
    allowed = {g for L in PERSONAS["study person"]["genres"] for g in GENRE_GROUPS[L]}
    try:
        assert genres <= allowed, f"genre filter leaked: {genres - allowed}"
        assert means["instrumentalness"] > 0.40, \
            f"not instrumental enough: {means['instrumentalness']:.2f}"
        assert means["energy"] < 0.50, f"too energetic: {means['energy']:.2f}"
        assert means["speechiness"] < 0.30, f"too speechy: {means['speechiness']:.2f}"
    except AssertionError as e:
        failures.append(f"study person: {e}")

    results, means, genres = run(**_args("sad indie fan"))
    allowed = {g for L in PERSONAS["sad indie fan"]["genres"] for g in GENRE_GROUPS[L]}
    try:
        assert genres <= allowed, f"genre filter leaked: {genres - allowed}"
        assert means["valence"] < 0.45, f"not sad enough: {means['valence']:.2f}"
        assert means["energy"] < 0.55, f"too energetic: {means['energy']:.2f}"
        assert means["instrumentalness"] < 0.12, \
            f"too instrumental: {means['instrumentalness']:.2f}"
    except AssertionError as e:
        failures.append(f"sad indie fan: {e}")

    print()
    if failures:
        for f in failures:
            print(f"FAIL  {f}")
        sys.exit(1)
    print("ALL CHECKS PASSED")


def _args(label):
    spec = PERSONAS[label]
    return {"label": label, "answers": spec["answers"]}


if __name__ == "__main__":
    main()
