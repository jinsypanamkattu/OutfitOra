# Weather Outfit Judge

React (Vite) frontend + Python (FastAPI) backend. Reads your day (manual events or an uploaded .ics file),
fetches hourly weather from Open-Meteo, and returns a text verdict.

## Run

Backend (Python 3.11+):

    cd backend
    python -m venv .venv && source .venv/bin/activate
    pip install -r requirements.txt
    pytest                              # engine tests
    uvicorn app.main:app --reload       # http://localhost:8000/docs

Frontend (Node 18+):

    cd frontend
    npm install
    npm run dev                         # http://localhost:5173 (proxies /api to :8000)

## How it works

1. `events.py`     classifies each event from English keywords (indoor/outdoor, dress code)
2. `engine.py`     builds exposure windows (commute there, the event if outdoors, commute back), summarizes the weather inside them,
                   picks clothing from the effective temperature (feels-like + activity - personal offset), applies rain/wind/ice/UV rules
   Clothing choices also depend on the optional `gender` field (`male` / `female`): dress-code tops and shoes differ,
   and heels are flagged as a bad idea on wet or icy ground. Leaving it unset gives neutral suggestions.
3. `texts.py`      turns the facts into a friendly English sentence
4. `ml.py`         **personal comfort model** (machine learning, see below)
5. `/api/feedback` runs one online-learning step on that model; the learned weights are kept in the browser's localStorage

## Machine learning: personal comfort model

Instead of one global "you run cold by X°" number, `ml.py` learns a *context-dependent* offset with
online ridge regression (normalised LMS, a form of SGD):

    offset(x) = w · x        x = [1, wind, bike, car, walk, sport, rain, dressy]

Each "too cold / just right / too hot" vote is a training example (`target = prediction ± 2°`), so the app can learn
e.g. "I run cold when cycling in wind" without becoming cold everywhere. Details:

- pure Python (8 numbers), no new dependencies
- stateless server: weights travel with each request (`comfort_weights`) and come back from `/api/feedback`,
  so nothing is stored server-side (GDPR unchanged)
- with a neutral context the update equals the old EMA rule, and an existing legacy offset seeds the bias term
- weights and offsets are clamped to ±8 °C, with anti-windup and L2 shrinkage on the context weights
- `tests/test_ml.py` includes a simulation where a hidden "true" user votes on the model's suggestions and the
  model's error drops by more than half

## Privacy (GDPR)

No database and no accounts: calendar data is processed in memory and never stored. Host the backend in the EU.

## Next steps

Google/Microsoft OAuth calendar sync, SMHI/MET Nordic as second weather source, more template variants per situation,
richer features for the comfort model (humidity, time of day, sun/cloud), a per-garment model, travel time via Trafiklab/OpenRouteService, web push, rate limiting, and a Dockerfile.
