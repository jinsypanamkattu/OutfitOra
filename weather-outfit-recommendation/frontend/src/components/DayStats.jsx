import { summarise } from "./HourlyChart.jsx";

const clock = (hhmm, plus = 0) => {
  const m = Number(hhmm.slice(0, 2)) * 60 + Number(hhmm.slice(3, 5)) + plus;
  return `${String(Math.floor(m / 60) % 24).padStart(2, "0")}:${String(m % 60).padStart(2, "0")}`;
};

export default function DayStats({ v, offset }) {
  const hours = v?.hours;
  if (!hours?.length) return null;
  const { iMin, iMax, wet, total, dry } = summarise(hours);
  const lo = hours[iMin], hi = hours[iMax];
  const tiles = [
    ["🌡️", "Feels-like range", `${lo.feels}° → ${hi.feels}°`, `Coldest ${lo.time}, warmest ${hi.time}`],
    ["🌧️", "Rain today", total > 0 ? `${total.toFixed(1)} mm` : "None", wet.length ? `${wet.length} wet hour${wet.length > 1 ? "s" : ""}` : "Dry all day"],
    ["☂️", "Best dry window", dry ? `${hours[dry.start].time}–${clock(hours[dry.end].time, 60)}` : "—", dry ? `${dry.end - dry.start + 1} hour${dry.end > dry.start ? "s" : ""} without rain` : "Rain all day"],
    ["📅", "Events planned", String(v.events?.length ?? 0), v.events?.length ? "Shaded on the chart" : "Add one to plan around it"],
  ];
  const shift = Math.abs(offset) >= 0.5;

  return (
    <>
      <section className="stats" aria-label="Day at a glance">
        {tiles.map(([icon, label, value, sub]) => (
          <div className="stat" key={label}>
            <span className="stat-icon" aria-hidden="true">{icon}</span>
            <span className="stat-label">{label}</span>
            <strong className="stat-value">{value}</strong>
            <span className="stat-sub">{sub}</span>
          </div>
        ))}
      </section>
      <section className="profile">
        <span className="stat-icon" aria-hidden="true">🧠</span>
        <div>
          <strong>Your comfort profile</strong>
          <p>{shift
            ? `Dressing ${Math.abs(offset).toFixed(1)}° ${offset > 0 ? "colder" : "warmer"} than the forecast, learned from your feedback.`
            : "Not personalised yet. Vote 🥶 👌 🥵 on the verdict and the app learns how warm you like to dress."}</p>
        </div>
      </section>
    </>
  );
}
