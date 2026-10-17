import { useRef, useState } from "react";

const W = 720, H = 270, PAD = { l: 40, r: 16, t: 18, b: 30 };
const RAIN_H = 64; // max height of the rain bars
const minutes = (hhmm) => Number(hhmm.slice(0, 2)) * 60 + Number(hhmm.slice(3, 5));
const clock = (m) => `${String(Math.floor(m / 60) % 24).padStart(2, "0")}:${String(m % 60).padStart(2, "0")}`;
const localToday = () => new Date().toLocaleDateString("en-CA");

// Catmull-Rom -> cubic Bezier, so the temperature curve is smooth instead of jagged.
function smooth(pts) {
  return pts.map((p, i) => {
    if (i === 0) return `M${p[0]},${p[1]}`;
    const p0 = pts[i - 2] || pts[i - 1], p1 = pts[i - 1], p3 = pts[i + 1] || p, t = 0.18;
    return `C${p1[0] + (p[0] - p0[0]) * t},${p1[1] + (p[1] - p0[1]) * t} ${p[0] - (p3[0] - p1[0]) * t},${p[1] - (p3[1] - p1[1]) * t} ${p[0]},${p[1]}`;
  }).join(" ");
}

// SVG text never wraps by itself, so break event titles into short lines (max 3, last one gets "…").
const CHAR_W = 6.2, LINE_H = 12, MAX_LINES = 3;
function wrapLabel(text, maxChars) {
  const words = text.trim().split(/\s+/).flatMap((w) => w.length > maxChars ? w.match(new RegExp(`.{1,${maxChars}}`, "g")) : [w]);
  const lines = [];
  let cur = "";
  for (const w of words) {
    if (!cur) cur = w;
    else if ((cur + " " + w).length <= maxChars) cur += " " + w;
    else { lines.push(cur); cur = w; }
  }
  if (cur) lines.push(cur);
  if (lines.length > MAX_LINES) {
    const kept = lines.slice(0, MAX_LINES);
    kept[MAX_LINES - 1] = kept[MAX_LINES - 1].slice(0, Math.max(maxChars - 1, 1)) + "…";
    return kept;
  }
  return lines;
}

export function summarise(hours) {
  const feels = hours.map((h) => h.feels);
  const iMin = feels.indexOf(Math.min(...feels)), iMax = feels.indexOf(Math.max(...feels));
  const wet = hours.filter((h) => h.precip > 0.05);
  const total = hours.reduce((a, h) => a + (h.precip > 0.05 ? h.precip : 0), 0);
  // longest run of dry hours
  let best = null, run = null;
  hours.forEach((h, i) => {
    if (h.precip <= 0.05) { run = run ? { ...run, end: i } : { start: i, end: i }; if (!best || run.end - run.start > best.end - best.start) best = run; }
    else run = null;
  });
  return { iMin, iMax, wet, total, dry: best };
}

export default function HourlyChart({ hours, events = [], day }) {
  const svgRef = useRef(null);
  const [hover, setHover] = useState(null);
  if (!hours?.length) return null;

  const start = minutes(hours[0].time);
  const span = minutes(hours[hours.length - 1].time) - start || 1;
  const x = (m) => PAD.l + ((m - start) / span) * (W - PAD.l - PAD.r);
  const feels = hours.map((h) => h.feels);
  const lo = Math.floor(Math.min(...feels) - 2), hi = Math.ceil(Math.max(...feels) + 2);
  const bottom = H - PAD.b;
  const y = (v) => PAD.t + (1 - (v - lo) / (hi - lo)) * (bottom - PAD.t);
  const rainH = (mm) => (Math.min(mm, 3) / 3) * RAIN_H;
  const pts = hours.map((h) => [x(minutes(h.time)), y(h.feels)]);
  const line = smooth(pts);
  const area = `${line} L${pts[pts.length - 1][0]},${bottom} L${pts[0][0]},${bottom} Z`;
  const ticks = [0, 1, 2, 3, 4].map((k) => Math.round(lo + ((hi - lo) * k) / 4));
  const { iMin, iMax, wet, total, dry } = summarise(hours);

  let nowX = null;
  if (day === localToday()) {
    const d = new Date(), m = d.getHours() * 60 + d.getMinutes();
    if (m >= start && m <= start + span) nowX = x(m);
  }

  const onMove = (e) => {
    const r = svgRef.current.getBoundingClientRect();
    const px = ((e.clientX - r.left) / r.width) * W;
    let best = 0;
    pts.forEach((p, i) => { if (Math.abs(p[0] - px) < Math.abs(pts[best][0] - px)) best = i; });
    setHover(best);
  };

  const hv = hover != null ? hours[hover] : null;
  const tipW = 132, tipH = 40;
  const tipX = hv ? Math.min(Math.max(pts[hover][0] - tipW / 2, PAD.l), W - PAD.r - tipW) : 0;
  const tipY = hv ? (pts[hover][1] < 90 ? pts[hover][1] + 14 : pts[hover][1] - tipH - 12) : 0;

  const label = (i, up) => {
    const [px, py] = pts[i];
    const w = 40, ty = up ? py - 28 : py + 10;
    return (
      <g key={up ? "max" : "min"}>
        <circle cx={px} cy={py} r="5.5" fill="#fff" stroke={up ? "#d9622b" : "#2f6b8f"} strokeWidth="3" />
        <rect x={Math.min(Math.max(px - w / 2, PAD.l), W - PAD.r - w)} y={ty} width={w} height="18" rx="9" fill={up ? "#d9622b" : "#2f6b8f"} />
        <text x={Math.min(Math.max(px, PAD.l + w / 2), W - PAD.r - w / 2)} y={ty + 12.5} textAnchor="middle" className="pt-label">{up ? "▲" : "▼"} {hours[i].feels}°</text>
      </g>
    );
  };

  const rainNote = wet.length
    ? `Rain ${wet[0].time}–${clock(minutes(wet[wet.length - 1].time) + 60)}, about ${total.toFixed(1)} mm in total`
    : "No rain expected";

  return (
    <figure className="chart-card">
      <figcaption className="chart-head">
        <span className="chart-title">Hour by hour</span>
        <span className="legend">
          <i className="lg line" /> Feels like
          <i className="lg rain" /> Rain
          <i className="lg ev" /> Your events
        </span>
      </figcaption>

      <svg ref={svgRef} className="chart" viewBox={`0 0 ${W} ${H}`} role="img"
           aria-label={`Feels-like temperature from ${Math.min(...feels)} to ${Math.max(...feels)} degrees. ${rainNote}.`}
           onPointerMove={onMove} onPointerLeave={() => setHover(null)}>
        <defs>
          <linearGradient id="lineGrad" gradientUnits="userSpaceOnUse" x1="0" y1={y(hi)} x2="0" y2={y(lo)}>
            <stop offset="0" stopColor="#e2572b" /><stop offset=".5" stopColor="#e9a23b" /><stop offset="1" stopColor="#2f6b8f" />
          </linearGradient>
          <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#e9a23b" stopOpacity=".38" /><stop offset="1" stopColor="#2f6b8f" stopOpacity=".04" />
          </linearGradient>
          <linearGradient id="rainGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#4f9ac7" /><stop offset="1" stopColor="#2f6b8f" />
          </linearGradient>
        </defs>

        {ticks.map((v) => (
          <g key={v}>
            <line className="grid" x1={PAD.l} x2={W - PAD.r} y1={y(v)} y2={y(v)} />
            <text className="axis" x={PAD.l - 8} y={y(v) + 3.5} textAnchor="end">{v}°</text>
          </g>
        ))}
        {lo < 0 && hi > 0 && <line className="zero" x1={PAD.l} x2={W - PAD.r} y1={y(0)} y2={y(0)} />}

        {events.map((e, i) => {
          const s0 = minutes(e.start.slice(11, 16));
          const e0 = e.end ? minutes(e.end.slice(11, 16)) : s0 + 60;
          const a = Math.max(start, s0 - 20), b = Math.min(start + span, e0 + 20);
          const w = Math.max(x(b) - x(a), 3);
          const lines = wrapLabel(e.title, Math.max(Math.floor((w - 8) / CHAR_W), 9));
          const textW = Math.max(...lines.map((l) => l.length)) * CHAR_W;
          // keep the label inside the chart: slide it left if it would run past the right edge
          const lx = Math.max(PAD.l + 3, Math.min(x(a) + 5, W - PAD.r - textW - 3));
          return (
            <g key={i}>
              <title>{e.title}</title>
              <rect className="ev-band" x={x(a)} y={PAD.t} width={w} height={bottom - PAD.t} rx="6" />
              <text className="ev-label" x={lx} y={PAD.t + 13}>
                {lines.map((l, k) => <tspan key={k} x={lx} dy={k ? LINE_H : 0}>{l}</tspan>)}
              </text>
            </g>
          );
        })}

        {hours.map((h, i) => h.precip > 0.05 && (
          <g key={i}>
            <rect className="rain-bar" x={pts[i][0] - 7} width="14" rx="4" y={bottom - rainH(h.precip)} height={rainH(h.precip)} fill="url(#rainGrad)" />
            {h.precip >= 0.3 && <text className="rain-label" x={pts[i][0]} y={bottom - rainH(h.precip) - 4} textAnchor="middle">{h.precip.toFixed(1)}</text>}
          </g>
        ))}

        <path d={area} fill="url(#areaGrad)" />
        <path className="feels-line" d={line} fill="none" stroke="url(#lineGrad)" />
        {pts.map((p, i) => <circle key={i} cx={p[0]} cy={p[1]} r="2.6" fill="#fff" stroke="url(#lineGrad)" strokeWidth="1.5" />)}
        {iMax !== iMin && label(iMax, true)}
        {iMax !== iMin && label(iMin, false)}

        {nowX != null && (
          <g>
            <line className="now" x1={nowX} x2={nowX} y1={PAD.t} y2={bottom} />
            <rect x={nowX - 15} y={bottom + 2} width="30" height="15" rx="7.5" fill="#12222d" />
            <text x={nowX} y={bottom + 12.5} textAnchor="middle" className="pt-label">Now</text>
          </g>
        )}

        {hours.filter((_, i) => i % 3 === 0).map((h) => (
          <text key={h.time} className="axis" x={x(minutes(h.time))} y={H - 8} textAnchor="middle">{h.time.slice(0, 2)}:00</text>
        ))}

        {hv && (
          <g pointerEvents="none">
            <line className="hover-line" x1={pts[hover][0]} x2={pts[hover][0]} y1={PAD.t} y2={bottom} />
            <circle cx={pts[hover][0]} cy={pts[hover][1]} r="6" fill="#12222d" stroke="#fff" strokeWidth="2.5" />
            <rect x={tipX} y={tipY} width={tipW} height={tipH} rx="10" fill="#12222d" opacity=".94" />
            <text x={tipX + 10} y={tipY + 16} className="tip-time">{hv.time}</text>
            <text x={tipX + 10} y={tipY + 31} className="tip-body">Feels {hv.feels}° · {hv.precip > 0.05 ? `${hv.precip.toFixed(1)} mm` : "dry"}</text>
          </g>
        )}
      </svg>

      <ul className="insights">
        <li><b>▼ Coldest</b> {hours[iMin].time} at {hours[iMin].feels}°</li>
        <li><b>▲ Warmest</b> {hours[iMax].time} at {hours[iMax].feels}°</li>
        <li><b>{wet.length ? "🌧" : "☀️"}</b> {rainNote}</li>
        {dry && wet.length > 0 && <li><b>☂️ Dry window</b> {hours[dry.start].time}–{clock(minutes(hours[dry.end].time) + 60)}</li>}
      </ul>
    </figure>
  );
}
