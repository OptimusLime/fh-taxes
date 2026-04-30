/** @jsxImportSource preact */
// Renovations section — surfaces signals from scripts/derive_renovation_events.py.
// Three signal types triangulate to a tier (high/medium/low/weak):
//   - step_up:    improvement_value YoY MAD-z >= 3 in non-sale year (+20%, +$50K)
//   - eff_age:    prc.eff_age << notice_year - year_built (gap >= 40, eff_age <= 20)
//   - desc_change: building_description string changed in non-recoding year

import { isPresent } from '../format';

type Event = {
  signal: 'step_up' | 'eff_age' | 'desc_change';
  weight: number;
  year?: number;
  delta_imp?: number;
  pct_imp?: number;
  mad_z?: number;
  reno_gap?: number;
  eff_age?: number;
  prev_desc?: string;
  building_description?: string;
};

type Renovations = {
  tier: 'high' | 'medium' | 'low' | 'weak';
  confidence: number;
  signals: string[];
  first_event_year: number | null;
  last_event_year: number | null;
  events: Event[];
};

type Props = { renovations?: Renovations | null };

const TIER_COLOR: Record<string, string> = {
  high: '#0a7c2f',
  medium: '#0a7caa',
  low: '#9e6900',
  weak: '#5b6270',
};

const TIER_LABEL: Record<string, string> = {
  high: 'High confidence',
  medium: 'Medium confidence',
  low: 'Low confidence',
  weak: 'Weak signal',
};

const SIGNAL_LABEL: Record<string, string> = {
  step_up: 'Improvement-value step-up',
  eff_age: 'Effective-age compression',
  desc_change: 'Building-description change',
};

const SIGNAL_DESC: Record<string, string> = {
  step_up:
    'Improvement value moved in a non-sale year by an idiosyncratic amount — at least +20% and +$50K, with a MAD-residualized z-score above 3 against that year\'s town-wide median move (so it\'s not just a reval-year shock).',
  eff_age:
    'The assessor\'s effective build year (notice_year − eff_age) is at least 40 years later than the original year_built, AND the effective age is ≤20. The assessor has explicitly re-baselined this property as a near-new build.',
  desc_change:
    'The building-description string changed (e.g., garage added, story upgraded) in a year that was NOT a town-wide recoding event. Suggestive but not conclusive on its own.',
};

function fmtPct(v: number): string {
  return (v * 100).toFixed(1) + '%';
}
function fmtMoney(v: number): string {
  return '$' + Math.round(v).toLocaleString('en-US');
}

function EventRow({ e }: { e: Event }) {
  const detail: string[] = [];
  if (e.signal === 'step_up') {
    if (isPresent(e.delta_imp)) detail.push(`+${fmtMoney(e.delta_imp!)}`);
    if (isPresent(e.pct_imp)) detail.push(fmtPct(e.pct_imp!));
    if (isPresent(e.mad_z)) detail.push(`z=${e.mad_z!.toFixed(1)}`);
  } else if (e.signal === 'eff_age') {
    if (isPresent(e.reno_gap)) detail.push(`${e.reno_gap}-yr gap`);
    if (isPresent(e.eff_age)) detail.push(`eff_age ${e.eff_age}`);
  } else if (e.signal === 'desc_change') {
    if (e.prev_desc && e.building_description) {
      detail.push(`${e.prev_desc} → ${e.building_description}`);
    }
  }
  return (
    <tr>
      <td style="white-space:nowrap;font-variant-numeric:tabular-nums">{e.year ?? '—'}</td>
      <td>{SIGNAL_LABEL[e.signal] || e.signal}</td>
      <td style="font-variant-numeric:tabular-nums">{detail.join(' · ')}</td>
    </tr>
  );
}

export default function Renovations({ renovations }: Props) {
  if (!renovations || !renovations.events || renovations.events.length === 0) {
    return null;
  }
  const r = renovations;
  const color = TIER_COLOR[r.tier] || '#5b6270';
  const span =
    r.first_event_year && r.last_event_year && r.first_event_year !== r.last_event_year
      ? `${r.first_event_year} – ${r.last_event_year}`
      : `${r.first_event_year}`;

  return (
    <section class="pd-section">
      <h2 class="pd-section-title">Renovation Signals</h2>
      <p class="pd-section-subtitle">
        Inferred from existing data — improvement-value step-ups, effective-age compression, and
        building-description changes. <strong>Not a permit record.</strong> See methodology link
        below.
      </p>

      <div
        style={`background:${color}14;border-left:4px solid ${color};padding:0.7rem 0.9rem;border-radius:0 4px 4px 0;margin-bottom:0.8rem`}
      >
        <div
          style={`display:flex;align-items:baseline;justify-content:space-between;gap:0.6rem;flex-wrap:wrap`}
        >
          <div>
            <div
              style={`font-size:0.72rem;text-transform:uppercase;letter-spacing:0.06em;color:${color};font-weight:700`}
            >
              {TIER_LABEL[r.tier]} · score {r.confidence.toFixed(1)}
            </div>
            <div style="font-size:0.85rem;color:var(--pd-fg);margin-top:0.15rem">
              Signals fired: <strong>{r.signals.map((s) => SIGNAL_LABEL[s] || s).join(', ')}</strong>
            </div>
          </div>
          <div style="font-size:0.78rem;color:var(--pd-muted);font-variant-numeric:tabular-nums">
            Window: <strong>{span}</strong>
          </div>
        </div>
      </div>

      <table class="pd-table">
        <thead>
          <tr>
            <th>Year</th>
            <th>Signal</th>
            <th>Detail</th>
          </tr>
        </thead>
        <tbody>
          {r.events.map((e) => (
            <EventRow e={e} />
          ))}
        </tbody>
      </table>

      <details style="margin-top:0.6rem;font-size:0.78rem;color:var(--pd-muted)">
        <summary style="cursor:pointer;font-weight:600">How these signals are computed</summary>
        <div style="padding:0.5rem 0 0;line-height:1.5">
          {Object.keys(SIGNAL_DESC).map((k) => (
            <div style="margin-bottom:0.4rem">
              <strong style="color:var(--pd-fg)">{SIGNAL_LABEL[k]}.</strong>{' '}
              {SIGNAL_DESC[k]}
            </div>
          ))}
          <div style="margin-top:0.5rem;color:var(--pd-faint)">
            Source: <code>scripts/derive_renovation_events.py</code>. Confidence weights:
            step_up=2.0, eff_age=1.5, desc_change=1.0. Tier thresholds documented inline.
          </div>
        </div>
      </details>
    </section>
  );
}
