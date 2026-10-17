// Detect URLs and bare domains in free text so they can be rendered as links.

// Matches either a full http(s):// URL, or a bare domain (optionally with a
// path). The TLD is required to be 2-24 letters, which avoids matching things
// like decimal numbers ("0.95") or version strings ("v1.2.3").
const PATTERN =
  /(?:https?:\/\/[^\s<>()]+)|(?:(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,24}(?:\/[^\s<>()]*)?)/g;

export interface Segment {
  text: string;
  href: string | null;
}

/** Build a navigable href from a domain or URL. */
export function toHref(value: string): string {
  return /^https?:\/\//i.test(value) ? value : `https://${value}`;
}

/** Split text into plain and linkable segments (domains / URLs). */
export function linkify(text: string): Segment[] {
  const segments: Segment[] = [];
  let last = 0;

  for (const m of text.matchAll(PATTERN)) {
    const start = m.index ?? 0;
    let matched = m[0];

    // Don't swallow trailing sentence punctuation into the link.
    const trail = matched.match(/[.,;:!?»"')\]]+$/);
    let trailing = "";
    if (trail) {
      trailing = trail[0];
      matched = matched.slice(0, matched.length - trailing.length);
    }
    if (!matched) continue;

    if (start > last) segments.push({ text: text.slice(last, start), href: null });
    segments.push({ text: matched, href: toHref(matched) });
    if (trailing) segments.push({ text: trailing, href: null });
    last = start + m[0].length;
  }

  if (last < text.length) segments.push({ text: text.slice(last), href: null });
  return segments;
}
