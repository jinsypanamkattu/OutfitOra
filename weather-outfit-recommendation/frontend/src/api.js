async function call(url, body) {
  const res = await fetch(url, {
    method: body ? "POST" : "GET",
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(typeof err.detail === "string" ? err.detail : `Request failed (${res.status})`);
  }
  return res.json();
}

export const getVerdict = (payload) => call("/api/verdict", payload);
export const searchCity = (q) => call(`/api/geocode?q=${encodeURIComponent(q)}`);
export const parseIcs = (content, day) => call("/api/ics", { content, day });
export const sendFeedback = (offset, feedback, weights, features) =>
  call("/api/feedback", { offset, feedback, weights, features });
