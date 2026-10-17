import datetime as dt
from typing import Literal
from pydantic import BaseModel, Field, field_validator

from .ml import MAX_OFFSET, N_FEATURES


class EventIn(BaseModel):
    title: str = Field(max_length=200)
    start: dt.datetime
    end: dt.datetime | None = None
    location: str | None = Field(default=None, max_length=200)


class VerdictRequest(BaseModel):
    lat: float = 59.3293          # Stockholm
    lon: float = 18.0686
    city: str = "Stockholm"
    day: dt.date | None = None    # defaults to today (Europe/Stockholm)
    events: list[EventIn] = Field(default_factory=list, max_length=30)
    transport: Literal["walk", "bike", "transit", "car"] = "transit"
    gender: Literal["male", "female"] | None = None       # None = neutral clothing suggestions
    temp_offset: float = Field(default=0.0, ge=-8, le=8)  # + = you run cold (legacy global offset)
    # Learned personal comfort model (see ml.py). When present it overrides temp_offset.
    comfort_weights: list[float] | None = Field(default=None, min_length=N_FEATURES, max_length=N_FEATURES)

    @field_validator("comfort_weights")
    @classmethod
    def _w_range(cls, v):
        if v is not None and any(abs(w) > MAX_OFFSET for w in v):
            raise ValueError("weights out of range")
        return v


class FeedbackRequest(BaseModel):
    offset: float = Field(default=0.0, ge=-8, le=8)
    feedback: Literal["cold", "right", "hot"]
    # Optional: train the personal comfort model with the context the verdict was made in.
    weights: list[float] | None = Field(default=None, min_length=N_FEATURES, max_length=N_FEATURES)
    features: list[float] | None = Field(default=None, min_length=N_FEATURES, max_length=N_FEATURES)

    @field_validator("weights")
    @classmethod
    def _w_range(cls, v):
        if v is not None and any(abs(w) > MAX_OFFSET for w in v):
            raise ValueError("weights out of range")
        return v

    @field_validator("features")
    @classmethod
    def _f_range(cls, v):
        if v is not None and any(not 0 <= x <= 2 for x in v):
            raise ValueError("features out of range")
        return v


class IcsRequest(BaseModel):
    content: str = Field(max_length=2_000_000)
    day: dt.date | None = None
