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
