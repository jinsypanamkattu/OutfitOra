import datetime as dt

import httpx
import recurring_ical_events
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from icalendar import Calendar

from . import ml
from .engine import analyze, local, update_offset
from .schemas import EventIn, FeedbackRequest, IcsRequest, VerdictRequest
from .weather import TZ, fetch_forecast, geocode

app = FastAPI(title="Weather Outfit Judge", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # add your production origin
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"ok": True}


@app.get("/api/geocode")
async def geocode_city(q: str = Query(min_length=2, max_length=60)):
    try:
        return await geocode(q)
    except httpx.HTTPError:
        raise HTTPException(502, "Geocoding service unavailable")


@app.post("/api/verdict")
async def verdict(req: VerdictRequest):
    day = req.day or dt.datetime.now(TZ).date()
    try:
        hours = await fetch_forecast(req.lat, req.lon)
    except httpx.HTTPError:
        raise HTTPException(502, "Weather service unavailable")
    try:
        out = analyze(day=day, events=req.events, hours=hours, transport=req.transport,
                      offset=req.temp_offset, weights=req.comfort_weights, gender=req.gender)
    except ValueError:
        raise HTTPException(422, "No forecast available for that day (max 3 days ahead)")
    out["city"] = req.city
    return out


@app.post("/api/ics")
def parse_ics(req: IcsRequest) -> list[EventIn]:
    """Parse an uploaded .ics file in memory (nothing is stored). All-day events are skipped."""
    try:
        cal = Calendar.from_ical(req.content)
    except Exception:
        raise HTTPException(400, "Could not read the calendar file")
    day = req.day or dt.datetime.now(TZ).date()
    events: list[EventIn] = []
    for ev in recurring_ical_events.of(cal).at((day.year, day.month, day.day)):
        start = ev.get("DTSTART").dt
        if not isinstance(start, dt.datetime):
            continue  # all-day
        end = ev.get("DTEND").dt if ev.get("DTEND") else None
        events.append(EventIn(
            title=str(ev.get("SUMMARY", "Event"))[:200],
            start=local(start),
            end=local(end) if isinstance(end, dt.datetime) else None,
            location=str(ev.get("LOCATION"))[:200] if ev.get("LOCATION") else None,
        ))
    return events


@app.post("/api/feedback")
def feedback(req: FeedbackRequest):
    if req.weights is not None and req.features is not None:   # ML path: one online learning step
        w = ml.update(req.weights, req.features, req.feedback)
        return {"weights": w, "offset": round(ml.predict(w, req.features), 2)}
    return {"offset": update_offset(req.offset, req.feedback)}  # legacy path
