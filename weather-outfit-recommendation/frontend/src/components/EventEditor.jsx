import { useMemo, useState } from "react";
import { parseIcs } from "../api.js";

const HISTORY_KEY = "woj-event-history";
const HISTORY_MAX = 30;

function loadHistory() {
  try {
    const h = JSON.parse(localStorage.getItem(HISTORY_KEY) || "[]");
    return Array.isArray(h) ? h.filter((x) => x && typeof x.title === "string") : [];
  } catch { return []; }
}

export default function EventEditor({ events, setEvents, day, onError }) {
  const [title, setTitle] = useState("");
  const [start, setStart] = useState("19:00");
  const [end, setEnd] = useState("21:00");
  const [history, setHistory] = useState(loadHistory);
  const [focused, setFocused] = useState(false);
  const [active, setActive] = useState(-1);

  const saveHistory = (h) => {
    setHistory(h);
    try { localStorage.setItem(HISTORY_KEY, JSON.stringify(h)); } catch { /* storage full/blocked: ignore */ }
  };

  // Past titles that match what is typed (all of them when the box is empty), newest first.
  const suggestions = useMemo(() => {
    const q = title.trim().toLowerCase();
    return history
      .filter((h) => h.title.toLowerCase() !== q && (!q || h.title.toLowerCase().includes(q)))
      .slice(0, 6);
  }, [history, title]);

  const showList = focused && suggestions.length > 0;

  const choose = (h) => {
    setTitle(h.title);
    if (h.start) setStart(h.start);
    if (h.end !== undefined) setEnd(h.end);
    setActive(-1);
    setFocused(false);
  };

  const forget = (h) => saveHistory(history.filter((x) => x.title !== h.title));

  const onTitleKey = (e) => {
    if (!showList) return;
    if (e.key === "ArrowDown") { e.preventDefault(); setActive((active + 1) % suggestions.length); }
    else if (e.key === "ArrowUp") { e.preventDefault(); setActive((active - 1 + suggestions.length) % suggestions.length); }
    else if (e.key === "Enter" && active >= 0) { e.preventDefault(); choose(suggestions[active]); }
    else if (e.key === "Escape") { setFocused(false); setActive(-1); }
  };

  const add = (e) => {
    e.preventDefault();
    const name = title.trim();
    if (!name) return;
    setEvents([...events, { title: name, start, end }]);
    // Remember it (most recent first, no case-insensitive duplicates).
    const rest = history.filter((h) => h.title.toLowerCase() !== name.toLowerCase());
    saveHistory([{ title: name, start, end }, ...rest].slice(0, HISTORY_MAX));
    setTitle("");
    setActive(-1);
  };

  const importFile = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      const found = await parseIcs(await file.text(), day);
      setEvents([...events, ...found.map((x) => ({ title: x.title, start: x.start.slice(11, 16), end: x.end ? x.end.slice(11, 16) : "" }))]);
    } catch (err) { onError(err.message); }
    e.target.value = "";
  };

  const sorted = events.map((ev, i) => ({ ...ev, i })).sort((a, b) => a.start.localeCompare(b.start));

  return (
    <section className="events">
      {sorted.length === 0 && (
        <div className="empty">
          <span aria-hidden="true">🗓️</span>
          <p><strong>Nothing planned yet</strong><br />Add an event or import a calendar and the advice adapts to when you are outside.</p>
        </div>
      )}
      {sorted.length > 0 && (
        <ol className="timeline">
          {sorted.map((ev) => (
            <li key={ev.i}>
              <time>{ev.start}</time>
              <span className="name">{ev.title}</span>
              <button type="button" aria-label={`Remove ${ev.title}`} onClick={() => setEvents(events.filter((_, j) => j !== ev.i))}>×</button>
            </li>
          ))}
        </ol>
      )}
      <form onSubmit={add} className="add">
        <div className="suggest">
          <input className="title" placeholder="Add an event" aria-label="Event title" value={title} maxLength={200}
                 autoComplete="off" role="combobox" aria-expanded={showList} aria-autocomplete="list"
                 onChange={(e) => { setTitle(e.target.value); setActive(-1); }}
                 onFocus={() => setFocused(true)}
                 onBlur={() => setFocused(false)}
                 onKeyDown={onTitleKey} />
          {showList && (
            <ul className="suggest-list" role="listbox">
              {suggestions.map((h, i) => (
                <li key={h.title} role="option" aria-selected={i === active} className={i === active ? "active" : ""}
                    onMouseDown={(e) => { e.preventDefault(); choose(h); }}>
                  <span className="s-title">{h.title}</span>
                  {h.start && <time>{h.start}</time>}
                  <button type="button" aria-label={`Forget ${h.title}`} tabIndex={-1}
                          onMouseDown={(e) => { e.preventDefault(); e.stopPropagation(); forget(h); }}>×</button>
                </li>
              ))}
            </ul>
          )}
        </div>
        <div className="times">
          <input type="time" aria-label="Start time" value={start} onChange={(e) => setStart(e.target.value)} required />
          <input type="time" aria-label="End time" value={end} onChange={(e) => setEnd(e.target.value)} />
          <button type="submit" className="plus" aria-label="Add event">+</button>
          <label className="file" title="Import calendar file (.ics)" aria-label="Import calendar file">
            📎<input type="file" accept=".ics,text/calendar" onChange={importFile} />
          </label>
        </div>
      </form>
    </section>
  );
}
