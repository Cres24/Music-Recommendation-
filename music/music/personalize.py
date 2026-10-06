"""Map saved MusicPreference answers to recommender answer letters.

The choice order in accounts.forms.MusicPreferenceForm was built from the
same project document as machine/rules.py, so this is a straight 1:1
translation. Keep the two in sync if either side gains options.
"""

from accounts.forms import MusicPreferenceForm

GENRE = {
    "pop": "A",
    "rock_metal": "B",
    "hiphop_rap": "C",
    "rnb_soul": "D",
    "electronic_edm": "E",
    "indie_alternative": "F",
    "classical_jazz": "G",
    "country_folk": "H",
    "kpop_jpop": "I",
    "mixed": "J",
}

PRIORITY = {
    "melody": "A",
    "lyrics": "B",
    "beat": "C",
    "vocals": "D",
    "instrumentals": "E",
    "vibe": "F",
}

MOOD = {
    "happy": "A",
    "relaxing": "B",
    "sad": "C",
    "energetic": "D",
    "dark": "E",
    "romantic": "F",
    "nostalgic": "G",
}

CONTEXT = {
    "study": "A",
    "gaming": "B",
    "travel": "C",
    "exercise": "D",
    "relaxing": "E",
    "party": "F",
    "always": "G",
}

PLAYLIST = {
    "popular": "A",
    "lyrics": "B",
    "beat": "C",
    "vocals": "D",
    "unique": "E",
    "mood": "F",
    "memory": "G",
}

_FIELDS = (
    ("favorite_genre", GENRE),
    ("song_priority", PRIORITY),
    ("preferred_mood", MOOD),
    ("listening_context", CONTEXT),
    ("playlist_preference", PLAYLIST),
)


def answers_from_preference(preference):
    """MusicPreference -> the answers dict machine/recommender.py expects."""
    answers = {}
    for field, mapping in _FIELDS:
        value = getattr(preference, field, "")
        letter = mapping.get(value)
        if letter is None:
            continue
        if field == "favorite_genre":
            answers["q1"] = [letter]
        elif field == "song_priority":
            answers["q2"] = [letter]
        elif field == "preferred_mood":
            answers["q3"] = [letter]
        elif field == "listening_context":
            answers["q4"] = letter
        elif field == "playlist_preference":
            answers["q5"] = letter
    return answers


def summary_from_preference(preference):
    """Human-readable labels of the saved choices, for the page header."""
    labels = []
    for field, _ in _FIELDS:
        field_obj = MusicPreferenceForm.base_fields[field]
        value = getattr(preference, field, "")
        labels.append(dict(field_obj.choices).get(value, value))
    return labels
