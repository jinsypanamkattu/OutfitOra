"""Personal comfort model: online ridge regression trained with normalised LMS (a form of SGD).

The old engine had one number, a global "you run cold by X degrees" offset. This model generalises it
to a *context-dependent* offset:

    offset(x) = w . x            x = [1, wind, bike, car, walk, sport, rain, dressy]

so it can learn things like "I run cold when I cycle in wind" without being cold everywhere.
Every "too cold / just right / too hot" vote is one training example:

    target = prediction + {cold: +2, right: 0, hot: -2}
    w     += LR * (target - prediction) * x / (x.x)        # normalised LMS step
    w[1:] *= (1 - LR * L2)                                  # ridge shrinkage, bias is not shrunk

Design choices
- Pure Python, no numpy: the vectors have 8 numbers.
- Stateless server: the weights live in the browser (localStorage) and travel with each request,
  so nothing is stored server-side (GDPR-friendly, same as the old offset).
- With context x = [1, 0, ...] the update is identical to the old EMA rule (0 -> 0.8 on "cold").
"""
from __future__ import annotations

FEATURES = ("bias", "wind", "bike", "car", "walk", "sport", "rain", "dressy")
N_FEATURES = len(FEATURES)

MAX_OFFSET = 8.0                       # °C, same clamp as the old offset
STEP = {"cold": 2.0, "right": 0.0, "hot": -2.0}
LR = 0.4                               # learning rate (0.4 reproduces the old EMA step)
L2 = 0.02                              # ridge strength; pulls context weights toward 0


def _clamp(v: float, lim: float = MAX_OFFSET) -> float:
    return max(-lim, min(lim, v))


def init_weights(offset: float = 0.0) -> list[float]:
    """Fresh model. Seeds the bias with a legacy global offset so existing users keep their calibration."""
    return [_clamp(offset)] + [0.0] * (N_FEATURES - 1)


def features(*, wind_max: float, rain: bool, transport: str, dress: str) -> list[float]:
    """Context vector for one judged day. Wind is scaled to ~0..2 so all features have similar range."""
    return [
        1.0,
        min(max(wind_max, 0.0) / 10.0, 2.0),
        1.0 if transport == "bike" else 0.0,
        1.0 if transport == "car" else 0.0,
        1.0 if transport == "walk" else 0.0,       # transit is the baseline
        1.0 if dress == "sport" else 0.0,
        1.0 if rain else 0.0,
        1.0 if dress in ("smart", "formal") else 0.0,
    ]


def predict(weights: list[float], x: list[float]) -> float:
    """Personal offset in °C for this context (+ means you run cold, so dress warmer)."""
    return _clamp(sum(w * xi for w, xi in zip(weights, x)))


def update(weights: list[float], x: list[float], feedback: str) -> list[float]:
    """One online learning step from a single vote. Returns new weights; inputs are not mutated."""
    pred = predict(weights, x)
    err = STEP[feedback]
    # Anti-windup: don't keep pushing a prediction that is already at its limit.
    if (pred >= MAX_OFFSET and err > 0) or (pred <= -MAX_OFFSET and err < 0):
        return list(weights)

    norm = sum(xi * xi for xi in x) or 1.0
    new = [w + LR * err * xi / norm for w, xi in zip(weights, x)]
    new = [new[0]] + [w * (1 - LR * L2) for w in new[1:]]
    return [round(_clamp(w), 4) for w in new]


def explain(weights: list[float], x: list[float]) -> list[dict]:
    """Per-feature contribution to today's offset, largest first (for a 'why' line in the UI)."""
    parts = [{"feature": f, "delta": round(w * xi, 2)} for f, w, xi in zip(FEATURES, weights, x) if w * xi]
    return sorted(parts, key=lambda p: abs(p["delta"]), reverse=True)
