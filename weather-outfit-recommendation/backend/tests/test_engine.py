import datetime as dt

from app.engine import analyze, update_offset
from app.schemas import EventIn
from app.weather import TZ, Hour

DAY = dt.date(2026, 10, 14)


def day_hours(temp=9.0, rain_from=None, wind=3.0):
    out = []
    for h in range(24):
        t = dt.datetime.combine(DAY, dt.time(h), tzinfo=TZ)
        rain = rain_from is not None and h >= rain_from
        out.append(Hour(t, temp, temp - 1, 1.2 if rain else 0.0, 90 if rain else 5, wind, 1, 80))
    return out


def run(events, hours, transport="transit", offset=0.0):
    return analyze(day=DAY, events=events, hours=hours, transport=transport, offset=offset)


def date_event():
    return [EventIn(title="Date night", start=dt.datetime(2026, 10, 14, 19, 0), end=dt.datetime(2026, 10, 14, 22, 0))]


def test_rainy_date_gets_umbrella_and_avoids_white_shoes():
    r = run(date_event(), day_hours(rain_from=17))
    assert r["situation"] == "rain_dressy"
    assert "Umbrella" in r["bring"] and "white shoes" in r["avoid"]
    assert "18:00" in r["headline"] and "19:00" in r["headline"]  # first rainy hour inside the exposure window


def test_wind_replaces_umbrella_with_rain_jacket():
    r = run(date_event(), day_hours(rain_from=17, wind=12))
    assert "Umbrella" not in r["bring"] and "Rain jacket" in r["bring"]
    assert r["sacrifice"]


def test_cold_day():
    r = run([], day_hours(temp=-8))
    assert r["situation"] == "cold" and "Hat" in r["wear"]


def test_snow_is_slippery():
    r = run([], day_hours(temp=-1, rain_from=0))
    assert r["situation"] == "ice" and "Ice grips" in r["bring"]


def test_offset_makes_user_dress_warmer():
    cold_user = run([], day_hours(temp=12), offset=4)
    normal = run([], day_hours(temp=12), offset=0)
    assert cold_user["effective_temp"] < normal["effective_temp"]


def test_feedback_moves_offset_gently():
    assert update_offset(0, "cold") == 0.8
    assert update_offset(0.8, "right") == 0.8
    assert update_offset(8, "cold") == 8


# ---- gender-aware verdicts ----
def smart_event():
    return [EventIn(title="Client dinner", start=dt.datetime(2026, 10, 14, 19, 0), end=dt.datetime(2026, 10, 14, 22, 0))]


def run_g(events, hours, gender):
    return analyze(day=DAY, events=events, hours=hours, transport="transit", offset=0.0, gender=gender)


def test_gender_changes_dressy_outfit():
    m = run_g(smart_event(), day_hours(temp=20), "male")
    f = run_g(smart_event(), day_hours(temp=20), "female")
    assert "Dress shirt" in m["wear"] and "Blouse" not in m["wear"]
    assert "Blouse" in f["wear"] and "Dress shirt" not in f["wear"]
    assert m["gender"] == "male" and f["gender"] == "female"


def test_heels_flagged_on_rainy_dressy_day_for_women_only():
    m = run_g(smart_event(), day_hours(rain_from=17), "male")
    f = run_g(smart_event(), day_hours(rain_from=17), "female")
    assert "Heels" in f["avoid"] and "Heels" not in m["avoid"]


def test_no_gender_keeps_neutral_suggestions():
    n = run_g(smart_event(), day_hours(temp=20), None)
    assert "Blouse" not in n["wear"] and "Dress shirt" not in n["wear"] and n["gender"] is None


def test_events_are_english_only():
    from app.events import classify
    assert classify("Promenad i parken")["outdoor"] is True   # "park" is English
    assert classify("middag")["dress"] == "casual"             # Swedish keyword no longer recognised
    assert classify("konsert")["outdoor"] is False
