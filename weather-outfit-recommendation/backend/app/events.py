"""Classify an event as indoor/outdoor and pick a dress code from English keywords."""
from __future__ import annotations

OUTDOOR = (
    "walk", "run", "hike", "picnic", "park", "bbq", "grill", "market", "festival", "concert", "match",
    "football", "game", "bike", "cycling", "outdoor", "terrace", "patio", "beach", "skiing", "skating",
)
FORMAL = ("wedding", "gala", "funeral", "formal")
SMART = (
    "date", "dinner", "restaurant", "interview", "presentation", "client", "meeting", "theatre", "theater",
    "opera", "cocktail", "after work", "afterwork",
)
SPORT = (
    "gym", "workout", "training", "yoga", "run", "swim", "football", "hike", "cycling", "skiing",
    "padel", "tennis",
)
WORK = ("meeting", "interview", "presentation", "client", "work")


def _has(text: str, words: tuple[str, ...]) -> bool:
    return any(w in text for w in words)


def classify(title: str, location: str | None = None) -> dict:
    text = f"{title} {location or ''}".lower()
    outdoor = _has(text, OUTDOOR)
    if _has(text, SPORT):
        dress = "sport"
    elif _has(text, FORMAL):
        dress = "formal"
    elif _has(text, SMART):
        dress = "smart"
    else:
        dress = "casual"
    if dress == "sport":
        kind = "sport"
    elif outdoor:
        kind = "outdoor"
    elif _has(text, WORK):
        kind = "work"
    elif dress in ("smart", "formal"):
        kind = "social"
    else:
        kind = "other"
    return {"kind": kind, "outdoor": outdoor, "dress": dress}
