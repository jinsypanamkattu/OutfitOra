import { useEffect, useRef, useState } from "react";
import { getVerdict } from "./api.js";
import CityPicker from "./components/CityPicker.jsx";
import EventEditor from "./components/EventEditor.jsx";
import DayStats from "./components/DayStats.jsx";
import VerdictCard from "./components/VerdictCard.jsx";

const DEFAULTS = { city: { name: "Stockholm", lat: 59.3293, lon: 18.0686 }, transport: "transit", gender: null, offset: 0, weights: null, scene: "auto" };
// Background scenes. "Auto" picks one from the verdict (and time of day); the picker lets you force any of them.
const SCENES = [
  ["sunny", "☀️", "Sunny"], ["sunset", "🌇", "Sunset"], ["night", "🌙", "Night"], ["heat", "🥵", "Heatwave"],
  ["overcast", "☁️", "Overcast"], ["fog", "🌫️", "Fog"], ["drizzle", "🌦️", "Drizzle"], ["rain", "🌧️", "Rain"],
  ["storm", "⛈️", "Thunderstorm"], ["frost", "❄️", "Frost"], ["snow", "🌨️", "Snow"], ["wind", "💨", "Windy"],
];
function autoScene(v, day) {
  const mood = v?.situation ?? "nice";
  const wet = Math.max(0, ...(v?.hours ?? []).map((h) => h.precip ?? 0));
  if (mood === "rain" || mood === "rain_dressy") return wet >= 2.5 ? "storm" : wet < 0.6 ? "drizzle" : "rain";
  if (mood === "ice") return "snow";
  if (mood === "cold") return "frost";
  if (mood === "wind") return "wind";
  if (mood === "heat") return "heat";
  if (day === today()) { // clear day: follow the clock
    const h = new Date().getHours();
    if (h >= 21 || h < 5) return "night";
    if (h >= 18) return "sunset";
  }
  return "sunny";
}
const GENDERS = [["male", "Male"], ["female", "Female"]];
const TRANSPORT = [["walk", "🚶", "Walk"], ["bike", "🚲", "Bike"], ["transit", "🚌", "Transit"], ["car", "🚗", "Car"]];

const load = () => {
  try { return { ...DEFAULTS, ...JSON.parse(localStorage.getItem("woj-settings") || "{}") }; }
  catch { return DEFAULTS; }
};
const today = () => new Date().toLocaleDateString("en-CA", { timeZone: "Europe/Stockholm" });

export default function App() {
  const [s, setS] = useState(load);
  const [day, setDay] = useState(today());
  const [events, setEvents] = useState([]);
  const [verdict, setVerdict] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const latest = useRef(0);

  useEffect(() => { localStorage.setItem("woj-settings", JSON.stringify(s)); }, [s]);

  // Re-judge automatically whenever an input changes.
  useEffect(() => {
    const id = ++latest.current;
    setLoading(true);
    setError("");
    getVerdict({
      lat: s.city.lat, lon: s.city.lon, city: s.city.name, day,
      events: events.map((e) => ({ title: e.title, start: `${day}T${e.start}`, end: e.end ? `${day}T${e.end}` : null })),
      transport: s.transport, gender: s.gender, temp_offset: s.offset, comfort_weights: s.weights,
    })
      .then((v) => id === latest.current && setVerdict(v))
      .catch((e) => id === latest.current && setError(e.message))
      .finally(() => id === latest.current && setLoading(false));
  }, [s.city, s.transport, s.gender, s.offset, s.weights, day, events]);

  const scene = s.scene === "auto" ? autoScene(verdict, day) : s.scene;

  return (
    <div className="app" data-mood={verdict?.situation ?? "nice"}>
      <div className="scenes" aria-hidden="true">
        {SCENES.map(([n]) => <div key={n} className={`scene scene-${n}${scene === n ? " active" : ""}`} />)}
      </div>
      <header className="top">
        <div className="brand">
          <span className="logo" aria-hidden="true">
          <svg viewBox="0 0 64 64">
            <circle cx="32" cy="32" r="30" fill="#e8f1fb" />
            <circle cx="47" cy="17" r="8" fill="#ffd84d" />
            <path
              d="M10 36a22 22 0 0 1 44 0a7.3 7.3 0 0 1-14.7 0a7.3 7.3 0 0 1-14.6 0a7.3 7.3 0 0 1-14.7 0z"
              fill="#ff8a7a"
            />
            <path
              d="M32 36v13a4 4 0 0 1-8 0"
              fill="none"
              stroke="#4f739e"
              strokeWidth="3"
              strokeLinecap="round"
            />
          </svg>
        </span>
          <div>
            <h1>OutfitOra </h1>
            <p className="tagline">Our daily style forecast.</p>
          </div>
        </div>
        <div className="controls">
          <CityPicker city={s.city} onPick={(city) => setS({ ...s, city })} onError={setError} />
          <input className="pill" type="date" aria-label="Day" value={day} onChange={(e) => e.target.value && setDay(e.target.value)} />
          <div className="segmented text" role="radiogroup" aria-label="Gender">
            {GENDERS.map(([k, label]) => (
              <button key={k} type="button" role="radio" aria-checked={s.gender === k}
                      className={s.gender === k ? "on" : ""}
                      onClick={() => setS({ ...s, gender: s.gender === k ? null : k })}>{label}</button>
            ))}
          </div>
          <div className="segmented" role="radiogroup" aria-label="How you get around">
            {TRANSPORT.map(([k, icon, label]) => (
              <button key={k} type="button" role="radio" aria-checked={s.transport === k} aria-label={label} title={label}
                      className={s.transport === k ? "on" : ""} onClick={() => setS({ ...s, transport: k })}>{icon}</button>
            ))}
          </div>
        </div>
      </header>

      <main>
        <div className="side">
          <h2 className="section-title"><span>1</span> Your day</h2>
          <EventEditor events={events} setEvents={setEvents} day={day} onError={setError} />
          <DayStats v={verdict} offset={s.offset} />
        </div>
        <div className="result">
          <h2 className="section-title"><span>2</span> The verdict</h2>
          {error && <p role="alert" className="error">{error}</p>}
          {verdict
            ? <VerdictCard key={`${verdict.day}-${verdict.city}`} v={verdict} loading={loading}
                           offset={s.offset} weights={s.weights}
                           onLearn={(r) => setS({ ...s, offset: r.offset, weights: r.weights ?? s.weights })} />
            : !error && <div className="verdict skeleton" aria-busy="true" />}
        </div>
      </main>

      <footer className="foot">
       
      </footer>
    </div>
  );
}
