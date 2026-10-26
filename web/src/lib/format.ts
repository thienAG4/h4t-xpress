// Formatting helpers - dates, times and numbers in the business time zone (Vietnam)

const TIME_ZONE = "Asia/Ho_Chi_Minh";

export function formatDateTime(value: string | null | undefined): string {
  if (!value) return "-";
  return new Intl.DateTimeFormat("en-GB", {
    timeZone: TIME_ZONE,
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

/** "2026-10-26" -> "Mon, 26 Oct" (date-only strings are not shifted by time zone). */
export function formatDay(isoDate: string): string {
  const [year, month, day] = isoDate.split("-").map(Number);
  // Built from parts: separators of Intl output differ between browsers and Node.
  const parts = new Intl.DateTimeFormat("en-GB", {
    weekday: "short",
    day: "2-digit",
    month: "short",
    timeZone: "UTC",
  }).formatToParts(new Date(Date.UTC(year, month - 1, day)));
  const part = (type: Intl.DateTimeFormatPartTypes) => parts.find((p) => p.type === type)?.value ?? "";
  return `${part("weekday")}, ${part("day")} ${part("month")}`;
}

/** "07:00:00" -> "07:00" */
export function formatTime(value: string): string {
  return value.slice(0, 5);
}

export function formatPhone(phone: string | null | undefined): string {
  if (!phone) return "-";
  return phone.replace(/^(\d{4})(\d{3})(\d{3})$/, "$1 $2 $3");
}

export function formatMoney(value: string | number): string {
  return `${new Intl.NumberFormat("vi-VN").format(Number(value))} ₫`;
}

/** ISO date-time -> "14:05" in business time. */
export function formatClock(value: string | null | undefined): string {
  if (!value) return "-";
  return new Intl.DateTimeFormat("en-GB", {
    timeZone: TIME_ZONE,
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

/** "12 min ago", "in 35 min", "3 h ago", "4 d ago" - for live boards. */
export function formatRelative(value: string | null | undefined, now = Date.now()): string {
  if (!value) return "-";
  const minutes = Math.round((new Date(value).getTime() - now) / 60_000);
  const size = Math.abs(minutes);
  if (size === 0) return "now";
  let text = `${size} min`;
  if (size >= 48 * 60) text = `${Math.round(size / 1440)} d`;
  else if (size >= 60) text = `${Math.round(size / 60)} h`;
  return minutes > 0 ? `in ${text}` : `${text} ago`;
}

export function formatKm(value: number | null | undefined): string {
  if (value === null || value === undefined) return "-";
  return `${value.toFixed(1)} km`;
}

/** Value for <input type="datetime-local"> in business time, e.g. "2026-10-25T14:30". */
export function toLocalInput(value: Date): string {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: TIME_ZONE,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  }).formatToParts(value);
  const part = (type: Intl.DateTimeFormatPartTypes) => parts.find((p) => p.type === type)?.value ?? "";
  return `${part("year")}-${part("month")}-${part("day")}T${part("hour")}:${part("minute")}`;
}

/** Back from the datetime-local value (Vietnam has no daylight saving: always UTC+7). */
export function fromLocalInput(value: string): string {
  return new Date(`${value}:00+07:00`).toISOString();
}

/** "2026-10-26" for a business day `days` after today. */
export function businessDate(days = 0): string {
  return toLocalInput(new Date(Date.now() + days * 86_400_000)).slice(0, 10);
}
