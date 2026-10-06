"""Tunable questionnaire rules for the recommender.

All target values and filter bounds are in the dataset's NATIVE units
(the same units as dataset.csv, e.g. tempo in BPM, loudness in dB);
build_profile() converts them into scaled space with the scaler stored
in the artifact.

Tune the numbers here, never in recommender.py.
"""

# The 9 audio features used for recommendation (same order as the artifact).
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

# Question 1: genre filter groups (answer letter -> track_genre values).
# Verified against the 114 genres present in the cleaned dataset.
GENRE_GROUPS = {
    "A": ["pop", "power-pop", "indie-pop", "synth-pop"],
    "B": ["rock", "hard-rock", "alt-rock", "metal", "heavy-metal", "punk-rock", "grunge"],
    "C": ["hip-hop"],
    "D": ["r-n-b", "soul", "funk", "gospel"],
    "E": ["edm", "electronic", "house", "techno", "trance", "dubstep", "deep-house"],
    "F": ["indie", "alternative", "indie-pop", "emo"],
    "G": ["classical", "jazz", "piano", "opera", "blues"],
    "H": ["country", "folk", "bluegrass", "singer-songwriter", "acoustic"],
    "I": ["k-pop", "j-pop", "j-rock", "anime"],
    "J": [],  # "Other / a mix" -> no genre filter
}

# Question 2: what the listener cares about -> weights / filters.
Q2_RULES = {
    "A": {"weights": {"valence": 1.5, "danceability": 1.4, "popularity": 1.5}},
    "B": {"weights": {"speechiness": 1.2, "acousticness": 1.4},
          "filters": {"instrumentalness": (0.0, 0.1)}},
    "C": {"weights": {"danceability": 1.6, "energy": 1.4, "tempo": 1.3}},
    "D": {"weights": {"acousticness": 1.3, "valence": 1.2},
          "filters": {"instrumentalness": (0.0, 0.1)}},
    "E": {"weights": {"instrumentalness": 1.8},
          "filters": {"instrumentalness": (0.5, 1.0)}},
    "F": {"weights": {"acousticness": 1.5, "instrumentalness": 1.4, "speechiness": 0.5}},
}

# Question 3: mood -> main targets (native units). Multiple moods are averaged.
MOOD_TARGETS = {
    "A": {"valence": 0.85, "energy": 0.65},                    # happy / upbeat
    "B": {"energy": 0.25, "acousticness": 0.70},               # relaxing
    "C": {"valence": 0.18, "energy": 0.35},                    # sad / emotional
    "D": {"energy": 0.85, "tempo": 135.0},                     # energetic / hype
    "E": {"valence": 0.15, "energy": 0.85, "loudness": -5.0},  # dark / intense
    "F": {"valence": 0.60, "energy": 0.40, "acousticness": 0.65},  # romantic
    "G": {"valence": 0.50, "energy": 0.45, "acousticness": 0.60,
          "popularity": 65.0},                                 # nostalgic
}

# Question 4: listening context -> adjustments applied ON TOP of the mood.
# "targets" overwrite mood targets, "filters" are hard ranges (relaxed
# on failure), "weights" multiply the defaults.
Q4_RULES = {
    "A": {"targets": {"energy": 0.40},
          "weights": {"instrumentalness": 1.6, "speechiness": 0.4},
          "filters": {"speechiness": (0.0, 0.15)}},            # studying
    "B": {"targets": {"energy": 0.75, "instrumentalness": 0.35},
          "weights": {"instrumentalness": 1.5},
          "filters": {"speechiness": (0.0, 0.15)}},            # gaming
    "C": {},                                                   # commuting: no change
    "D": {"targets": {"energy": 0.85},
          "weights": {"danceability": 1.5},
          "filters": {"energy": (0.7, 1.0), "tempo": (120.0, 170.0)}},  # exercising
    "E": {"targets": {"energy": 0.30},
          "weights": {"acousticness": 1.4}},                   # relaxing
    "F": {"targets": {"energy": 0.80, "danceability": 0.75},
          "weights": {"popularity": 1.3},
          "filters": {"danceability": (0.65, 1.0)}},           # parties
    "G": {},                                                   # all the time
}

# Question 5: playlist taste.
Q5_RULES = {
    "A": {"popularity_target": 70.0, "weights": {"popularity": 1.5}},
    "B": {"weights": {"speechiness": 1.2, "acousticness": 1.4},
          "filters": {"instrumentalness": (0.0, 0.1)}},
    "C": {"weights": {"danceability": 1.5, "energy": 1.5}},
    "D": {"weights": {"acousticness": 1.3},
          "filters": {"instrumentalness": (0.0, 0.1)}},
    "E": {"popularity_target": 25.0, "weights": {"popularity": 1.2},
          "novelty": True},                     # unique / unusual sound
    "F": {"double_mood_weights": True},         # matches a specific mood
    "G": {"mood": "G"},                         # reminds me of a memory
}

# Final score = w.sim * similarity + w.pop * popularity_score (+ novelty).
SCORE_WEIGHTS = {"sim": 0.85, "pop": 0.15, "novelty": 0.0}
SCORE_WEIGHTS_NOVELTY = {"sim": 0.75, "pop": 0.10, "novelty": 0.15}

# Diversity re-ranking (MMR) and candidate handling.
MMR_LAMBDA = 0.7          # 0.7 * score - 0.3 * similarity to already-picked
MMR_POOL = 300            # re-rank only the top-N by score
MAX_PER_ARTIST = 2
MIN_CANDIDATES = 200      # relax filters when fewer candidates remain
SEED_BLEND = (0.6, 0.4)   # 0.6 * seed average + 0.4 * answers
NOVELTY_SCALE = 0.6       # distance-to-centroid that counts as "fully novel"
