// Helpers de présentation partagés par plusieurs pages. Une seule locale, un seul endroit.

export const LOCALE = "fr-FR";

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleString(LOCALE, {
    day: "2-digit", month: "long", year: "numeric", hour: "2-digit", minute: "2-digit",
  });
}

// Date + heure compactes d'une cellule de tableau (« 27/08/2026 14:05 »).
export function formatDateTime(iso: string, withSeconds = false): string {
  return new Date(iso).toLocaleString(LOCALE, {
    day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit",
    ...(withSeconds ? { second: "2-digit" } : {}),
  });
}

export function formatDateShort(iso: string): string {
  return new Date(iso).toLocaleString(LOCALE, {
    day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit",
  });
}

export function formatDuration(ms: number): string {
  return ms >= 1000 ? `${(ms / 1000).toFixed(1)}s` : `${ms}ms`;
}

// Date d'une ligne de liste : « 27 août » dans l'année courante, « 27 août 2025 » sinon.
export function formatDayMonth(iso: string): string {
  const date = new Date(iso);
  const sameYear = date.getFullYear() === new Date().getFullYear();
  return date.toLocaleDateString(LOCALE, {
    day: "numeric", month: "long", ...(sameYear ? {} : { year: "numeric" }),
  });
}

// Date d'une ligne de boîte de réception : l'heure seule quand c'est aujourd'hui (le jour
// n'apporte rien, l'heure dit tout), la date sinon.
export function formatTimeOrDayMonth(iso: string): string {
  const date = new Date(iso);
  const now = new Date();
  const today =
    date.getFullYear() === now.getFullYear() &&
    date.getMonth() === now.getMonth() &&
    date.getDate() === now.getDate();
  if (today) return date.toLocaleTimeString(LOCALE, { hour: "2-digit", minute: "2-digit" });
  return formatDayMonth(iso);
}

export function formatNumber(n: number): string {
  return n.toLocaleString(LOCALE);
}

// « 2026-08 » → « août 2026 ».
export function formatMonth(month: string): string {
  const [y, m] = month.split("-").map(Number);
  return new Date(y, m - 1, 1).toLocaleDateString(LOCALE, { month: "long", year: "numeric" });
}
