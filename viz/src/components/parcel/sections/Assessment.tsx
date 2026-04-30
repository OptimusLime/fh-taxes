/** @jsxImportSource preact */
import { money, pct, isPresent, deltaPct } from '../format';

type Reno = {
  tier: 'high' | 'medium' | 'low';
  confidence: number;
  signals: string[];
  first_event_year: number | null;
  last_event_year: number | null;
  events: Array<Record<string, any>>;
};

type Props = { ca: Record<string, any>; renovations?: Reno | null };

const TIER_COLOR: Record<string, string> = {
  high: '#0a7c2f',
  medium: '#0a7caa',
  low: '#9e6900',
};
const TIER_LABEL: Record<string, string> = {
  high: 'High confidence',
  medium: 'Medium confidence',
  low: 'Low confidence',
};
const SIGNAL_LABEL: Record<string, string> = {
  step_up: 'Annual improvement-value jump',
  cum_step_up: '3-year cumulative jump',
  eff_age: 'Assessor effective-age compression (gut/rebuild)',
  eff_age_partial: 'Assessor effective-age compression (partial)',
  desc_change: 'Building-description change',
  year_built_change: 'Year-built recoded forward',
};

function fmtMoney(v: number): string {
  return '$' + Math.round(v).toLocaleString('en-US');
}

function RenovationBadge({ r }: { r: Reno }) {
  const color = TIER_COLOR[r.tier] || '#5b6270';
  const span =
    r.first_event_year && r.last_event_year && r.first_event_year !== r.last_event_year
      ? `${r.first_event_year}–${r.last_event_year}`
      : `${r.last_event_year ?? r.first_event_year}`;
  return (
    <div
      style={`background:${color}14;border-left:4px solid ${color};padding:0.6rem 0.8rem;border-radius:0 4px 4px 0;margin-bottom:0.7rem`}
    >
      <div style="display:flex;align-items:baseline;justify-content:space-between;gap:0.6rem;flex-wrap:wrap">
        <div>
          <div
            style={`font-size:0.72rem;text-transform:uppercase;letter-spacing:0.06em;color:${color};font-weight:700`}
          >
            🛠 Suspected renovation · {TIER_LABEL[r.tier]} (score {r.confidence.toFixed(1)})
          </div>
          <div style="font-size:0.82rem;color:var(--pd-fg);margin-top:0.15rem">
            Year{(r.first_event_year ?? 0) !== (r.last_event_year ?? 0) ? 's' : ''}: <strong>{span}</strong>{' '}
            · signals: <strong>{r.signals.length}</strong> ({r.signals.map((s) => SIGNAL_LABEL[s] || s).join(', ')})
          </div>
        </div>
      </div>
      <details style="margin-top:0.4rem;font-size:0.78rem;color:var(--pd-muted)">
        <summary style="cursor:pointer;font-weight:600">View {r.events.length} event{r.events.length !== 1 ? 's' : ''}</summary>
        <table class="pd-table" style="margin-top:0.4rem">
          <thead>
            <tr>
              <th>Year</th>
              <th>Signal</th>
              <th>Detail</th>
            </tr>
          </thead>
          <tbody>
            {r.events.map((e) => {
              const detail: string[] = [];
              if (e.signal === 'step_up') {
                if (isPresent(e.delta_imp)) detail.push(`+${fmtMoney(e.delta_imp)}`);
                if (isPresent(e.pct_imp)) detail.push(`${(e.pct_imp * 100).toFixed(1)}%`);
                if (isPresent(e.mad_z)) detail.push(`z=${Number(e.mad_z).toFixed(1)}`);
              } else if (e.signal === 'cum_step_up') {
                if (isPresent(e.cum_delta_imp)) detail.push(`3yr +${fmtMoney(e.cum_delta_imp)}`);
                if (isPresent(e.cum_pct_imp)) detail.push(`${(e.cum_pct_imp * 100).toFixed(0)}%`);
              } else if (e.signal === 'eff_age' || e.signal === 'eff_age_partial') {
                if (isPresent(e.reno_gap)) detail.push(`${e.reno_gap}-yr gap`);
                if (isPresent(e.eff_age)) detail.push(`eff_age ${e.eff_age}`);
              } else if (e.signal === 'desc_change') {
                if (e.prev_desc && e.building_description) {
                  detail.push(`${e.prev_desc} → ${e.building_description}`);
                }
              } else if (e.signal === 'year_built_change') {
                if (isPresent(e.old_year_built) && isPresent(e.new_year_built)) {
                  detail.push(`${Math.round(e.old_year_built)} → ${Math.round(e.new_year_built)}`);
                }
              }
              return (
                <tr>
                  <td style="white-space:nowrap;font-variant-numeric:tabular-nums">{e.year ?? '—'}</td>
                  <td>{SIGNAL_LABEL[e.signal] || e.signal}</td>
                  <td style="font-variant-numeric:tabular-nums">{detail.join(' · ')}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
        <div style="margin-top:0.4rem;color:var(--pd-faint);font-size:0.72rem">
          Derived from <code>scripts/derive_renovation_events.py</code> — improvement-value step-ups,
          effective-age compression, and building-description changes. Not a permit record.
        </div>
      </details>
    </div>
  );
}

export default function Assessment({ ca, renovations }: Props) {
  if (!ca) return null;

  const tiles = [
    { label: 'Land', value: ca.land_value },
    { label: 'Improvements', value: ca.improvement_value },
    { label: 'Net Assessed', value: ca.net_value },
  ];

  const ch75 = isPresent(ca.notice_year_ch75) || isPresent(ca.current_year_assessment_ch75);
  const change = deltaPct(ca.current_year_assessment_ch75, ca.prior_year_assessment_ch75);

  return (
    <section class="pd-section">
      <h2 class="pd-section-title">Current Assessment</h2>
      <p class="pd-section-subtitle">From MOD-IV / NJGIN tax-list snapshot.</p>
      {renovations && <RenovationBadge r={renovations} />}
      <div class="pd-money-row">
        {tiles.map((t) => (
          <div class="pd-money-card">
            <div class="label">{t.label}</div>
            <div class="value">{money(t.value)}</div>
          </div>
        ))}
      </div>
      {isPresent(ca.last_year_tax) && (
        <div class="pd-callout">
          <strong>Last year tax:</strong> {money(ca.last_year_tax)}
        </div>
      )}

      {ch75 && (
        <>
          <h2 class="pd-section-title" style="margin-top:1rem">
            Chapter 75 Notice {ca.notice_year_ch75 ? `(${ca.notice_year_ch75})` : ''}
          </h2>
          <p class="pd-section-subtitle">Official annual notice mailed by the assessor.</p>
          <div class="pd-money-row">
            <div class="pd-money-card">
              <div class="label">Prior Year</div>
              <div class="value">{money(ca.prior_year_assessment_ch75)}</div>
            </div>
            <div class="pd-money-card">
              <div class="label">Current Year</div>
              <div class="value">{money(ca.current_year_assessment_ch75)}</div>
            </div>
            <div class="pd-money-card">
              <div class="label">Change</div>
              <div class="value">
                {change ? (
                  <span class={`pd-delta ${change.direction}`}>{change.label}</span>
                ) : isPresent(ca.assessment_change_pct_ch75) ? (
                  pct(ca.assessment_change_pct_ch75)
                ) : (
                  '—'
                )}
              </div>
            </div>
          </div>

          {(isPresent(ca.tax_1h_paid) || isPresent(ca.tax_2h_paid) || isPresent(ca.actual_tax_paid_total)) && (
            <dl class="pd-stat-grid" style="margin-top:0.6rem">
              <dt>Tax (1H)</dt>
              <dd>{money(ca.tax_1h_paid)}</dd>
              <dt>Tax (2H)</dt>
              <dd>{money(ca.tax_2h_paid)}</dd>
              <dt>Tax (total)</dt>
              <dd>{money(ca.actual_tax_paid_total)}</dd>
              {isPresent(ca.deduction_codes) && (
                <>
                  <dt>Deduction codes</dt>
                  <dd>{Array.isArray(ca.deduction_codes) ? ca.deduction_codes.join(', ') : String(ca.deduction_codes)}</dd>
                </>
              )}
              {isPresent(ca.deduction_amount) && Number(ca.deduction_amount) > 0 && (
                <>
                  <dt>Deduction amount</dt>
                  <dd>{money(ca.deduction_amount)}</dd>
                </>
              )}
            </dl>
          )}
        </>
      )}
    </section>
  );
}
