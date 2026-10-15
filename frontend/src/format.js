// Dates and times from the API arrive as ISO strings in UTC. These show them in the viewer's own time
// zone and date style (undefined = the browser's language).
const DATE = new Intl.DateTimeFormat(undefined, { day: "numeric", month: "short", year: "numeric" });
const DATE_TIME = new Intl.DateTimeFormat(undefined, {
  day: "numeric",
  month: "short",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
});

// For example "15 Oct 2026".
export function formatDate(iso) {
  return DATE.format(new Date(iso));
}

// For example "15 Oct 2026, 14:05".
export function formatDateTime(iso) {
  return DATE_TIME.format(new Date(iso));
}

// A calendar date from the API (YYYY-MM-DD), for example "5 Oct". The date is read and shown in UTC, so it
// never shifts to the day before in a time zone west of UTC.
const DAY_MONTH = new Intl.DateTimeFormat(undefined, { day: "numeric", month: "short", timeZone: "UTC" });

export function formatDayMonth(isoDate) {
  return DAY_MONTH.format(new Date(isoDate));
}
