// Shared formatting helpers for parcel detail components.

export const isPresent = (v: unknown): boolean =>
  v !== null && v !== undefined && v !== '' && !(typeof v === 'number' && Number.isNaN(v));

export const num = (v: unknown, digits = 0): string => {
  if (!isPresent(v)) return '—';
  const n = typeof v === 'number' ? v : parseFloat(String(v));
  if (Number.isNaN(n)) return String(v);
  return n.toLocaleString('en-US', { maximumFractionDigits: digits });
};

export const money = (v: unknown): string => {
  if (!isPresent(v)) return '—';
  const n = typeof v === 'number' ? v : parseFloat(String(v));
  if (Number.isNaN(n)) return String(v);
  return n.toLocaleString('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  });
};

export const moneyShort = (v: unknown): string => {
  if (!isPresent(v)) return '—';
  const n = typeof v === 'number' ? v : parseFloat(String(v));
  if (Number.isNaN(n)) return String(v);
  if (Math.abs(n) >= 1_000_000) return `$${(n / 1_000_000).toFixed(2)}M`;
  if (Math.abs(n) >= 1_000) return `$${(n / 1_000).toFixed(0)}K`;
  return money(n);
};

export const pct = (v: unknown, digits = 1): string => {
  if (!isPresent(v)) return '—';
  const n = typeof v === 'number' ? v : parseFloat(String(v));
  if (Number.isNaN(n)) return String(v);
  return `${n.toFixed(digits)}%`;
};

export const sqft = (v: unknown): string => (isPresent(v) ? `${num(v)} sf` : '—');

export const yearOnly = (v: unknown): string => {
  if (!isPresent(v)) return '—';
  const s = String(v);
  // ISO date "2003-07-22" → "2003"
  return s.length >= 4 ? s.slice(0, 4) : s;
};

export const intRound = (v: unknown): string => {
  if (!isPresent(v)) return '—';
  const n = typeof v === 'number' ? v : parseFloat(String(v));
  if (Number.isNaN(n)) return String(v);
  return String(Math.round(n));
};

export const date = (v: unknown): string => {
  if (!isPresent(v)) return '—';
  const s = String(v);
  // Already YYYY-MM-DD or YYYY-MM-DDT...
  return s.length >= 10 ? s.slice(0, 10) : s;
};

export const yesNo = (v: unknown): string => (v ? 'yes' : 'no');

// Compose like "1S-AL-O-1U" or " / "-joined fields, dropping empties.
export const joinPresent = (parts: unknown[], sep = ' / '): string =>
  parts.filter(isPresent).map(String).join(sep);

// Returns an object describing whether and how a value increased relative to base.
export const deltaPct = (current: unknown, prior: unknown) => {
  if (!isPresent(current) || !isPresent(prior)) return null;
  const c = Number(current), p = Number(prior);
  if (Number.isNaN(c) || Number.isNaN(p) || p === 0) return null;
  const d = ((c - p) / p) * 100;
  return {
    pct: d,
    label: `${d >= 0 ? '+' : ''}${d.toFixed(1)}%`,
    direction: Math.abs(d) < 0.05 ? 'flat' : d > 0 ? 'up' : 'down',
  };
};
