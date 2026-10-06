"""Build the compact runtime artifact for the recommender.

Reads the clustered dataset (dataset/tracks_clustered.csv: the cleaned
dataset + cluster / cluster_name columns), scales the 9 audio features
to 0-1 (MinMax), and packs everything the runtime needs into ONE file:

  machine/artifacts/artifact.npz

Contents:
  features      float16 (N, 9)   scaled 0-1
  popularity    uint8   (N,)     raw 0-100
  explicit      bool    (N,)
  genre_codes   uint16  (N,)  + genre_names     (114,)
  artist_codes  int32   (N,)  + artist_names
  cluster_codes uint8   (N,)  + cluster_names   (k,)
  track names                 CSR blob (offsets + utf-8 bytes)
  track ids                   CSR blob (Spotify ids, for later playback)
  centroids     float16 (k, 9)  cluster centres in scaled space
  scaler_min/   float64 (9,)    to map native-unit targets -> scaled
  scaler_max
  feature_mean, popularity_mean (defaults for a neutral profile)

Why compact: the Vercel lambda limit (vercel.json) is 15mb and the raw
CSV is 19MB. This script asserts the artifact stays under 12MB.
Runtime needs numpy only -- no pandas / sklearn on the server.

Run:  uv run python machine/build_artifact.py
"""

from pathlib import Path

import numpy as np
import pandas as pd

import sys

sys.path.insert(0, str(Path(__file__).parent))
from rules import FEATURES  # noqa: E402

BASE = Path(__file__).parent
SRC = BASE / "dataset" / "tracks_clustered.csv"
OUT_DIR = BASE / "artifacts"
OUT = OUT_DIR / "artifact.npz"
MAX_BYTES = 12 * 1024 * 1024


def _csr(values):
    """UTF-8 blob + int32 offsets (compact storage for variable strings)."""
    lens = np.fromiter((len(v.encode("utf-8")) for v in values), dtype=np.int64,
                       count=len(values))
    offsets = np.zeros(len(values) + 1, dtype=np.int64)
    np.cumsum(lens, out=offsets[1:])
    data = np.frombuffer("".join(values).encode("utf-8"), dtype=np.uint8)
    return offsets.astype(np.int32), data


def _names(values):
    """Unique string list + int codes (pandas.factorize)."""
    codes, uniques = pd.factorize(values)
    codes = np.asarray(codes)
    if codes.max() <= np.iinfo(np.uint16).max:
        codes = codes.astype(np.uint16)
    else:
        codes = codes.astype(np.int32)
    encoded = [str(v).encode("utf-8") for v in uniques]
    return codes, np.array(encoded)  # numpy picks an S dtype automatically


def main():
    df = pd.read_csv(SRC)
    n = len(df)
    print(f"loaded {n:,} rows")

    # MinMax scale the 9 audio features to 0-1.
    raw = df[FEATURES].to_numpy(dtype=np.float64)
    lo, hi = raw.min(axis=0), raw.max(axis=0)
    assert np.all(hi > lo), "feature with zero range"
    scaled = (raw - lo) / (hi - lo)
    assert scaled.min() >= 0.0 and scaled.max() <= 1.0

    features = scaled.astype(np.float16)
    popularity = df["popularity"].to_numpy(dtype=np.uint8)
    explicit = df["explicit"].to_numpy(dtype=bool)

    genre_codes, genre_names = _names(df["track_genre"])
    artist_codes, artist_names = _names(df["artists"])
    cluster_codes, cluster_names = _names(df["cluster_name"])
    cluster_codes = cluster_codes.astype(np.uint8)
    track_offsets, track_data = _csr(df["track_name"].tolist())
    # Spotify track ids: needed later for playback (embed player / API).
    # Kept as a CSR blob and decoded lazily per row at runtime.
    id_offsets, id_data = _csr(df["track_id"].tolist())

    # Cluster centroids in scaled space (used for novelty scoring + filters).
    k = len(cluster_names)
    centroids = np.zeros((k, len(FEATURES)), dtype=np.float64)
    for c in range(k):
        centroids[c] = scaled[cluster_codes == c].mean(axis=0)

    arrays = {
        "features": features,
        "popularity": popularity,
        "explicit": explicit,
        "genre_codes": genre_codes,
        "genre_names": genre_names,
        "artist_codes": artist_codes,
        "artist_names": artist_names,
        "cluster_codes": cluster_codes,
        "cluster_names": cluster_names,
        "track_offsets": track_offsets,
        "track_data": track_data,
        "track_id_offsets": id_offsets,
        "track_id_data": id_data,
        "centroids": centroids.astype(np.float16),
        "scaler_min": lo,
        "scaler_max": hi,
        "feature_mean": scaled.mean(axis=0).astype(np.float32),
        "popularity_mean": np.float64(df["popularity"].mean()),
        "feature_names": np.array([f.encode("utf-8") for f in FEATURES]),
    }

    OUT_DIR.mkdir(exist_ok=True)
    np.savez_compressed(OUT, **arrays)

    print("\narray sizes (uncompressed):")
    for name, arr in sorted(arrays.items(), key=lambda kv: -kv[1].nbytes):
        print(f"  {name:<16} {arr.shape!s:<16} {arr.dtype!s:<10} {arr.nbytes / 1e6:7.2f} MB")
    size = OUT.stat().st_size
    print(f"\nwrote {OUT}")
    print(f"artifact size: {size / 1e6:.2f} MB (limit {MAX_BYTES / 1e6:.0f} MB)")
    assert size < MAX_BYTES, f"artifact too big for the Vercel lambda: {size / 1e6:.1f} MB"


if __name__ == "__main__":
    main()
