"""Clean machine/dataset/dataset.csv.

Steps:
  1. Strip leading/trailing whitespace from all string cells.
  2. Drop the unnamed pandas index column.
  3. Drop rows with empty track_name / artists / album_name.
  4. Dedupe on (track_id, track_genre); cross-genre duplicates are kept.
  5. Write back to dataset.csv with a fresh 0-based index.

A one-time backup is saved to dataset_raw.csv before the first overwrite.
"""

import csv
from pathlib import Path

DATASET = Path(__file__).parent / "dataset" / "dataset.csv"
BACKUP = Path(__file__).parent / "dataset" / "dataset_raw.csv"
REQUIRED = ("track_name", "artists", "album_name")
KEY = ("track_id", "track_genre")


def clean():
    with DATASET.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = [c for c in reader.fieldnames if c != ""]
        rows = []
        for row in reader:
            row = {k: v.strip() for k, v in row.items() if k != ""}
            if not all(row[c] for c in REQUIRED):
                continue
            rows.append(row)

    seen = set()
    deduped = []
    for row in rows:
        k = tuple(row[c] for c in KEY)
        if k in seen:
            continue
        seen.add(k)
        deduped.append(row)

    if not BACKUP.exists():
        BACKUP.write_text(DATASET.read_text(encoding="utf-8"), encoding="utf-8")

    with DATASET.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(deduped)

    return len(rows), len(deduped), len(fieldnames)


def verify():
    with DATASET.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert all("" not in r for r in rows), "unnamed column still present"
    assert all(v == v.strip() for r in rows for v in r.values()), "whitespace remains"
    assert all(all(r[c] for c in REQUIRED) for r in rows), "empty required field"
    keys = [(r["track_id"], r["track_genre"]) for r in rows]
    assert len(keys) == len(set(keys)), "duplicate (track_id, track_genre)"
    return len(rows)


if __name__ == "__main__":
    before, after, cols = clean()
    checked = verify()
    print(f"rows:   {before} -> {after}")
    print(f"cols:   {cols}")
    print(f"verify: {checked} rows clean")
    print(f"backup: {BACKUP}")
