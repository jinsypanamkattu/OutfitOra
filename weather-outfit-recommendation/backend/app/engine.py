"""Recommendation engine: exposure windows -> weather summary -> clothing rules -> text.
Pure functions, no I/O, so it is easy to unit test with fixture weather."""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from . import ml
from .events import classify
from .schemas import EventIn
from .texts import ITEMS, LABELS, NO_EVENTS_NOTE, SACRIFICE, TEMPLATES
from .weather import TZ, Hour

# Minutes actually spent outside around an event, per transport mode.
EXPOSURE_MIN = {"walk": 20, "bike": 20, "transit": 15, "car": 5}
# Shift of perceived temperature caused by activity/wind exposure.
ACTIVITY_ADJ = {"walk": 0.0, "bike": -1.0, "transit": 0.0, "car": 4.0}
DRESS_RANK = {"sport": 0, "casual": 1, "smart": 2, "formal": 3}
DRESSY = ("smart", "formal")

# (upper bound of effective temperature in °C, garments). First match wins.
BANDS = [
    (-15, ["thermal", "down_jacket", "winter_boots"]),
    (-5, ["sweater", "winter_coat", "winter_boots"]),
    (2, ["sweater", "warm_coat", "boots"]),
    (8, ["sweater", "jacket", "boots"]),
    (13, ["long_sleeve", "light_jacket", "sneakers"]),
    (18, ["long_sleeve", "sneakers"]),
    (24, ["tshirt", "sneakers"]),
    (99, ["tshirt", "shorts", "sneakers"]),
]
# Dress-code swaps. The shared outerwear swaps apply to everyone; tops and shoes depend on gender.
DRESS_SWAP = {"jacket": "wool_coat", "light_jacket": "blazer", "sneakers": "leather_shoes", "boots": "leather_boots"}
GENDER_DRESS_SWAP = {
    "male": {"tshirt": "dress_shirt", "long_sleeve": "dress_shirt"},
    "female": {"tshirt": "blouse", "long_sleeve": "blouse", "sneakers": "flats", "leather_shoes": "flats",
               "boots": "ankle_boots",  "shorts": "sundress"},
}
# Casual gender differences: women get tights under the warm-coat layers in freezing weather.
GENDER_COLD_EXTRA = {"male": [], "female": ["tights"]}
# Footwear that is a poor choice on wet or icy ground, per gender (only flagged for dressy events).
GENDER_SLIPPERY_AVOID = {"male": [], "female": ["heels"]}


def local(d: dt.datetime) -> dt.datetime:
    return d.replace(tzinfo=TZ) if d.tzinfo is None else d.astimezone(TZ)


def hours_in(hours: list[Hour], a: dt.datetime, b: dt.datetime) -> list[Hour]:
    one = dt.timedelta(hours=1)
    return [h for h in hours if h.time < b and h.time + one > a]


def is_rainy(h: Hour) -> bool:
    return h.precip >= 0.2 or (h.pop >= 60 and h.precip >= 0.05)


@dataclass
class Summary:
    temp_min: float
    feels_min: float
    feels_max: float
    precip_sum: float
    pop_max: float
    wind_max: float
    uv_max: float
    rain_start: dt.datetime | None


def summarize(hs: list[Hour]) -> Summary | None:
    if not hs:
        return None
    hs = sorted(hs, key=lambda h: h.time)
    rainy = [h for h in hs if is_rainy(h)]
    return Summary(
        temp_min=min(h.temp for h in hs),
        feels_min=min(h.feels for h in hs),
        feels_max=max(h.feels for h in hs),
        precip_sum=sum(h.precip for h in hs),
        pop_max=max(h.pop for h in hs),
        wind_max=max(h.wind for h in hs),
        uv_max=max(h.uv for h in hs),
        rain_start=rainy[0].time if rainy else None,
    )


def _uniq(items: list[str]) -> list[str]:
    return list(dict.fromkeys(items))


def recommend(sm: Summary, dress: str, transport: str, offset: float, gender: str | None = None) -> dict:
    eff = sm.feels_min + ACTIVITY_ADJ[transport] - offset
    eff_clothes = eff + (6 if dress == "sport" else 0)

    wear = list(next(items for limit, items in BANDS if eff_clothes <= limit))
    if dress in DRESSY:
        wear = [DRESS_SWAP.get(i, i) for i in wear]
        wear = [GENDER_DRESS_SWAP.get(gender, {}).get(i, i) for i in wear]
    if eff <= 2:
        wear += GENDER_COLD_EXTRA.get(gender, [])
    if eff <= 5:
        wear.append("hat")
    if eff <= 2:
        wear.append("gloves")
    if eff <= -5:
        wear.append("scarf")

    bring: list[str] = []
    avoid: list[str] = []
    sacrifice = None
    rain = sm.rain_start is not None
    snow = rain and sm.temp_min <= 0.5
    windy = sm.wind_max >= 10
    slippery = sm.temp_min <= 1 and sm.precip_sum >= 0.1

    if rain and not snow:
        if dress in DRESSY:
            if windy:
                bring.append("rain_jacket")
                sacrifice = "wind_vs_umbrella"
            else:
                bring.append("umbrella")
                sacrifice = "umbrella_for_style"
            avoid += ["white_shoes", "suede"]
        else:
            bring.append("rain_jacket")
    if snow and dress in DRESSY:
        avoid += ["white_shoes", "suede"]
    if slippery:
        bring.append("grip_shoes")
        avoid.append("smooth_soles")
    if (rain or slippery) and dress in DRESSY:
        avoid += GENDER_SLIPPERY_AVOID.get(gender, [])
    if sm.uv_max >= 6:
        bring += ["sunglasses", "sunscreen"]
    if sm.feels_max - sm.feels_min > 8:
        bring.append("layers")
    if eff >= 27:
        bring.append("water")

    if slippery:
        situation = "ice"
    elif rain and dress in DRESSY:
        situation = "rain_dressy"
    elif rain:
        situation = "rain"
    elif windy:
        situation = "wind"
    elif eff <= 5:
        situation = "cold"
    elif eff >= 24:
        situation = "heat"
    else:
        situation = "nice"

    return {
        "eff": eff, "wear": _uniq(wear), "bring": _uniq(bring), "avoid": _uniq(avoid),
        "sacrifice": sacrifice, "situation": situation,
    }


def _names(keys: list[str]) -> list[str]:
    return [ITEMS[k] for k in keys]


def _join(items: list[str]) -> str:
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + " and " + items[-1]


def analyze(*, day: dt.date, events: list[EventIn], hours: list[Hour], transport: str, offset: float,
            weights: list[float] | None = None, gender: str | None = None) -> dict:
    exp = dt.timedelta(minutes=EXPOSURE_MIN[transport])
    infos: list[dict] = []
    all_hours: dict[dt.datetime, Hour] = {}

    for e in sorted(events, key=lambda x: local(x.start)):
        s = local(e.start)
        en = local(e.end) if e.end and local(e.end) > s else s + dt.timedelta(hours=1)
        if s.date() != day:
            continue
        c = classify(e.title, e.location)
        windows = [(s - exp, s), (en, en + exp)]       # commute there and back
        if c["outdoor"]:
            windows.append((s, en))                    # the event itself
        hs = {h.time: h for a, b in windows for h in hours_in(hours, a, b)}
        all_hours.update(hs)
        infos.append({"title": e.title, "start": s, "end": en, **c, "sm": summarize(list(hs.values()))})

    if not infos:  # no events: judge a generic commute
        base = dt.datetime.combine(day, dt.time(0), tzinfo=TZ)
        for a, b in [(base.replace(hour=7, minute=30), base.replace(hour=9)),
                     (base.replace(hour=16, minute=30), base.replace(hour=18))]:
            all_hours.update({h.time: h for h in hours_in(hours, a, b)})

    day_sm = summarize(list(all_hours.values()))
    if day_sm is None:
        raise ValueError("no_forecast")

    dress = max((i["dress"] for i in infos), key=DRESS_RANK.get, default="casual")

    # Personal comfort model: context-dependent offset if the client sent learned weights,
    # otherwise fall back to the legacy global offset.
    x = ml.features(wind_max=day_sm.wind_max, rain=day_sm.rain_start is not None, transport=transport, dress=dress)
    if weights is not None:
        offset = ml.predict(weights, x)
    rec = recommend(day_sm, dress, transport, offset, gender)

    # The event the verdict talks about: dressiest one that gets rained on, else dressiest.
    focus = max(infos, key=lambda i: (bool(i["sm"] and i["sm"].rain_start), DRESS_RANK[i["dress"]]), default=None)
    rain_at = focus["sm"].rain_start if focus and focus["sm"] and focus["sm"].rain_start else day_sm.rain_start

    fields = {
        "event": focus["title"] if focus else "",
        "time": focus["start"].strftime("%H:%M") if focus else "",
        "rain_time": rain_at.strftime("%H:%M") if rain_at else "",
        "temp": round(day_sm.feels_min),
        "wind": round(day_sm.wind_max),
        "bring": _join(_names(rec["bring"])) or "rain gear",
        "avoid": _join(_names(rec["avoid"])),
        "wear": _join(_names(rec["wear"][:4])),
    }
    headline = TEMPLATES[rec["situation"]].format(**fields)

    sacrifice_text = SACRIFICE[rec["sacrifice"]] if rec["sacrifice"] else None
    lines = [headline, f"{LABELS['wear']}: {fields['wear']}."]
    if rec["bring"]:
        lines.append(f"{LABELS['bring']}: {_join(_names(rec['bring']))}.")
    if rec["avoid"]:
        lines.append(f"{LABELS['avoid']}: {fields['avoid']}.")
    if sacrifice_text:
        lines.append(f"{LABELS['sacrifice']}: {sacrifice_text}")
    if not infos:
        lines.append(NO_EVENTS_NOTE)

    def ev_out(i: dict) -> dict:
        sm = i["sm"]
        return {
            "title": i["title"], "start": i["start"].isoformat(), "end": i["end"].isoformat(),
            "kind": i["kind"], "dress": i["dress"], "outdoor": i["outdoor"],
            "feels_min": round(sm.feels_min) if sm else None,
            "rain_from": sm.rain_start.strftime("%H:%M") if sm and sm.rain_start else None,
            "wind_max": round(sm.wind_max) if sm else None,
        }

    d0 = dt.datetime.combine(day, dt.time(6), tzinfo=TZ)
    chart = [{"time": h.time.strftime("%H:%M"), "temp": round(h.temp, 1), "feels": round(h.feels, 1),
              "precip": round(h.precip, 2), "pop": h.pop}
             for h in hours if d0 <= h.time <= d0 + dt.timedelta(hours=17)]

    return {
        "day": day.isoformat(), "situation": rec["situation"], "gender": gender,
        "headline": headline, "text": "\n".join(lines),
        "wear": _names(rec["wear"]), "bring": _names(rec["bring"]),
        "avoid": _names(rec["avoid"]), "sacrifice": sacrifice_text,
        "feels_like": round(day_sm.feels_min), "effective_temp": round(rec["eff"], 1),
        "events": [ev_out(i) for i in infos], "hours": chart,
        "comfort": {
            "offset": round(offset, 2), "features": x, "personalised": weights is not None,
            "why": ml.explain(weights, x) if weights is not None else [],
        },
    }


def update_offset(offset: float, feedback: str) -> float:
    """Exponential-moving-average step toward 'colder' (+) or 'hotter' (-). Clamped to ±8 °C."""
    target = {"cold": offset + 2.0, "hot": offset - 2.0, "right": offset}[feedback]
    return max(-8.0, min(8.0, round(offset + 0.4 * (target - offset), 2)))
