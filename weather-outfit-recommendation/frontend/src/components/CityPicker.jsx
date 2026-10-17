import { useEffect, useState } from "react";
import { searchCity } from "../api.js";

export default function CityPicker({ city, onPick, onError }) {
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");
  const [results, setResults] = useState([]);

  useEffect(() => {
    if (q.trim().length < 2) { setResults([]); return; }
    let stale = false;
    const timer = setTimeout(() => {
      searchCity(q.trim()).then((r) => !stale && setResults(r)).catch((e) => onError(e.message));
    }, 300);
    return () => { stale = true; clearTimeout(timer); };
  }, [q]);

  const pick = (r) => { onPick({ name: r.name, lat: r.lat, lon: r.lon }); setOpen(false); setQ(""); setResults([]); };

  return (
    <div className="city">
      <button type="button" className="pill" aria-expanded={open} onClick={() => setOpen(!open)}>📍 {city.name}</button>
      {open && (
        <div className="popover">
          <input autoFocus placeholder="Search city" value={q} onChange={(e) => setQ(e.target.value)}
                 onKeyDown={(e) => e.key === "Escape" && setOpen(false)} aria-label="Search city" />
          <ul>
            {results.map((r) => (
              <li key={`${r.lat},${r.lon}`}>
                <button type="button" onClick={() => pick(r)}>{r.name}{r.region ? `, ${r.region}` : ""}</button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
