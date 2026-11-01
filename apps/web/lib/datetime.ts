// Report timestamps are always shown in UTC with the zone named. toLocaleString() with no
// arguments uses the runtime's own locale and time zone, so the server render and the browser
// disagreed (a React hydration error) and the reader could not tell which zone a time was in.
const dateTime = new Intl.DateTimeFormat("en-US", {
  timeZone: "UTC",
  dateStyle: "medium",
  timeStyle: "short",
});
const dateOnly = new Intl.DateTimeFormat("en-US", { timeZone: "UTC", dateStyle: "medium" });

export function formatUtcDateTime(value: string | number | Date): string {
  return `${dateTime.format(new Date(value))} UTC`;
}

export function formatUtcDate(value: string | number | Date): string {
  return dateOnly.format(new Date(value));
}
