import { useState } from "react";
import { sendFeedback } from "../api.js";
import HourlyChart from "./HourlyChart.jsx";

function Chips({ label, items, kind }) {
  if (!items?.length) return null;
  return (
    <div className="group">
      <h3>{label}</h3>
      <ul className={`chips ${kind}`}>{items.map((i) => <li key={i}>{i}</li>)}</ul>
    </div>
  );
}

const VOTES = [["cold", "🥶", "Too cold"], ["right", "👌", "Just right"], ["hot", "🥵", "Too hot"]];

export default function VerdictCard({ v, loading, offset, weights, onLearn }) {
  const [voted, setVoted] = useState(null);

  const vote = async (value) => {
    setVoted(value);
    // One online-learning step: the server returns updated personal-comfort weights; we keep them in localStorage.
    const current = weights ?? [offset, 0, 0, 0, 0, 0, 0, 0];
    const r = await sendFeedback(offset, value, current, v.comfort.features).catch(() => null);
    if (r) onLearn(r);
  };

  return (
    <article className={`verdict${loading ? " is-loading" : ""}`} aria-live="polite">
      <div className="hero">
        <div className="temp" aria-label={`Feels like ${v.feels_like} degrees`}>{v.feels_like}°</div>
        <div>
          <p className="headline">{v.headline}</p>
          <p className="meta">📍 {v.city} · 📅 {new Date(`${v.day}T12:00`).toLocaleDateString("en-GB", { weekday: "short", day: "numeric", month: "short" })}</p>
        </div>
      </div>
      <div className="groups">
        <Chips label="👕 Wear" items={v.wear} kind="wear" />
        <Chips label="🎒 Bring" items={v.bring} kind="bring" />
        <Chips label="🚫 Avoid" items={v.avoid} kind="avoid" />
      </div>
     
      
      <HourlyChart hours={v.hours} events={v.events} day={v.day} />
      <div className="vote" role="group" aria-label="Feedback">
        {VOTES.map(([k, icon, label]) => (
          <button key={k} type="button" aria-label={label} title={label} className={voted === k ? "on" : ""}
                  disabled={voted !== null} onClick={() => vote(k)}>{icon}</button>
        ))}
      </div>
    </article>
  );
}
