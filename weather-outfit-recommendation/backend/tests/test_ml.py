import datetime as dt
import random

import pytest

from app import ml
from app.engine import analyze, update_offset
from app.events import classify
from app.schemas import EventIn, FeedbackRequest, VerdictRequest
from app.weather import TZ, Hour

DAY = dt.date(2026, 10, 14)


def hours(temp=9.0, wind=3.0):
    return [Hour(dt.datetime.combine(DAY, dt.time(h), tzinfo=TZ), temp, temp - 1, 0.0, 5, wind, 1, 80) for h in range(24)]


def ctx(**kw):
    base = dict(wind_max=3.0, rain=False, transport="transit", dress="casual")
    return ml.features(**{**base, **kw})


def test_features_shape_and_encoding():
    x = ctx(wind_max=25, transport="bike", dress="smart", rain=True)
    assert len(x) == ml.N_FEATURES and x[0] == 1.0
    assert x[1] == 2.0                                  # wind capped
    assert x[2] == 1.0 and x[6] == 1.0 and x[7] == 1.0  # bike, rain, dressy


def test_update_matches_legacy_ema_for_bias_only_context():
    x = [1.0] + [0.0] * (ml.N_FEATURES - 1)
    w = ml.update(ml.init_weights(0.0), x, "cold")
    assert w[0] == update_offset(0, "cold") == 0.8
    assert ml.update(w, x, "right") == w


def test_update_does_not_mutate_input_and_is_bounded():
    w = ml.init_weights(7.9)
    x = ctx(wind_max=20, transport="bike")
    snapshot = list(w)
    for _ in range(50):
        w = ml.update(w, x, "cold")
    assert snapshot == ml.init_weights(7.9)
    assert abs(ml.predict(w, x)) <= ml.MAX_OFFSET and all(abs(v) <= ml.MAX_OFFSET for v in w)


def test_learns_context_specific_coldness():
    """User is cold only when cycling in wind. Votes judge the recommendation that was shown,
    so they come from the gap between the user's true need and what the model suggested."""
    windy_bike, calm_transit = ctx(wind_max=12, transport="bike"), ctx(wind_max=1)
    need = {tuple(windy_bike): 3.0, tuple(calm_transit): 0.0}

    def vote(x, w):
        gap = need[tuple(x)] - ml.predict(w, x)
        return "cold" if gap > 0.5 else "hot" if gap < -0.5 else "right"

    w = ml.init_weights(0.0)
    for _ in range(40):
        for x in (windy_bike, calm_transit):
            w = ml.update(w, x, vote(x, w))
    assert abs(ml.predict(w, windy_bike) - 3.0) < 1.0
    assert abs(ml.predict(w, calm_transit)) < 1.0      # did not become "cold everywhere"
    assert ml.explain(w, windy_bike)[0]["feature"] in ("bias", "wind", "bike")


def test_converges_toward_hidden_personal_model():
    """Simulate a user whose true offset is a linear function of context; votes come from the true model."""
    rng = random.Random(0)
    true_w = [1.0, 2.5, 1.5, -2.0, 0.0, -1.0, 0.5, 1.0]

    def sample():
        return ctx(wind_max=rng.uniform(0, 15), rain=rng.random() < .4, dress=rng.choice(["casual", "sport", "smart"]),
                   transport=rng.choice(["walk", "bike", "transit", "car"]))

    def vote(x, w):  # the user compares what they'd want vs what the model suggested
        gap = ml.predict(true_w, x) - ml.predict(w, x)
        return "cold" if gap > 1 else "hot" if gap < -1 else "right"

    test_set = [sample() for _ in range(200)]
    mae = lambda w: sum(abs(ml.predict(true_w, x) - ml.predict(w, x)) for x in test_set) / len(test_set)

    w = ml.init_weights(0.0)
    before = mae(w)
    for _ in range(600):
        x = sample()
        w = ml.update(w, x, vote(x, w))
    assert mae(w) < before * 0.5


def test_engine_uses_weights_and_exposes_comfort():
    base = analyze(day=DAY, events=[], hours=hours(), transport="bike", offset=0.0)
    x = base["comfort"]["features"]
    w = ml.init_weights(0.0)
    for _ in range(10):
        w = ml.update(w, x, "cold")
    learned = analyze(day=DAY, events=[], hours=hours(), transport="bike", offset=0.0, weights=w)
    assert learned["effective_temp"] < base["effective_temp"]
    assert learned["comfort"]["personalised"] and learned["comfort"]["why"]
    assert not base["comfort"]["personalised"]


def test_weights_override_legacy_offset():
    w = ml.init_weights(0.0)
    r = analyze(day=DAY, events=[], hours=hours(), transport="transit", offset=5.0, weights=w)
    assert r["comfort"]["offset"] == 0.0


def test_schema_validation():
    with pytest.raises(ValueError):
        VerdictRequest(comfort_weights=[0.0] * 3)
    with pytest.raises(ValueError):
        VerdictRequest(comfort_weights=[99.0] + [0.0] * (ml.N_FEATURES - 1))
    with pytest.raises(ValueError):
        FeedbackRequest(feedback="cold", weights=[0.0] * ml.N_FEATURES, features=[5.0] * ml.N_FEATURES)
    assert VerdictRequest().comfort_weights is None


@pytest.mark.parametrize("title,dress", [("Padel", "sport"), ("Wedding", "formal"), ("Dinner", "smart")])
def test_classify_no_longer_crashes_on_non_casual_events(title, dress):
    c = classify(title)
    assert c["dress"] == dress and isinstance(c["outdoor"], bool)


def test_sporty_outdoor_event_counts_as_outdoor():
    r = analyze(day=DAY, hours=hours(), transport="walk", offset=0.0,
                events=[EventIn(title="Morning run", start=dt.datetime(2026, 10, 14, 7), end=dt.datetime(2026, 10, 14, 8))])
    assert r["events"][0]["outdoor"] and r["events"][0]["dress"] == "sport"
