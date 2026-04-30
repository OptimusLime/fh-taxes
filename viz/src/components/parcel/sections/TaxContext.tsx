/** @jsxImportSource preact */
import { money, num, pct, isPresent } from '../format';

type Cohort = {
  cohort: string;
  n_parcels: number;
  pct_of_parcels: number;
  sum_tax: number;
  pct_of_tax_pool: number;
  sum_assessed: number;
  pct_of_assessed: number;
  avg_tax_per_parcel: number;
  avg_assessed_per_parcel: number;
};

type Aggregates = {
  total_parcels: number;
  parcels_with_tax_data: number;
  total_tax_pool: number;
  total_assessed_value: number;
  cohorts: Cohort[];
};

type Props = {
  parcelCohort: string;
  parcelTax: number | null | undefined;
  parcelAssessed: number | null | undefined;
  aggregates: Aggregates | null;
  nonArmsOnly?: boolean;
};

const COHORT_LABEL: Record<string, string> = {
  no_deed_since_1989: 'No deed since 1989',
  tenure_pre_2015: 'Last transfer pre-2015',
  tenure_2015_2019: 'Last transfer 2015–2019',
  tenure_pandemic_2020_2022: 'Last transfer 2020–2022 (pandemic)',
  tenure_post_pandemic_2023plus: 'Last transfer 2023+ (post-pandemic)',
};

const COHORT_FILL: Record<string, string> = {
  no_deed_since_1989: '#b06d2f',
  tenure_pre_2015: '#deb887',
  tenure_2015_2019: '#5fb1be',
  tenure_pandemic_2020_2022: '#9b6bd1',
  tenure_post_pandemic_2023plus: '#d96c8f',
};

const COHORT_DEFINITION: Record<string, string> = {
  no_deed_since_1989:
    'No deed events on record since 1989 — no transfers of any kind, arms-length or family. Title held continuously by the same owner (or estate) through every assessment regime change. The most extreme long-tenure case.',
  tenure_pre_2015:
    'Most recent deed event (arms-length OR family/exempt transfer) was before January 1, 2015 — predating Monmouth County\'s Assessment Demonstration Program (ADP) annual revaluation. Long-tenured under the legacy decadal-revaluation regime.',
  tenure_2015_2019:
    'Most recent deed event 2015–2019 — the early ADP years before the COVID housing surge. Assessment baseline set under the new annual-mass-appraisal regime.',
  tenure_pandemic_2020_2022:
    'Most recent deed event during the 2020–2022 pandemic housing market — when COVID money supply expansion drove rapid price appreciation. Assessments calibrated against pandemic-peak comparables.',
  tenure_post_pandemic_2023plus:
    'Most recent deed event 2023 or later — sustained-inflation era as millennials aged into family-purchase years. Most recent comparables; least likely to be drifting from market.',
};

const NON_ARMS_NOTE =
  'This parcel has had non-arms-length transfers only (e.g., between family, estate, or exempt entity). The assessor has no clean market-price anchor for this parcel — sale-chasing inequity risk is elevated.';

// Donut chart with hover-to-label slices
function Donut({
  data,
  size = 130,
  thickness = 22,
  highlightCohort,
}: {
  data: Array<{ key: string; value: number; color: string; label: string }>;
  size?: number;
  thickness?: number;
  highlightCohort?: string;
}) {
  const total = data.reduce((s, d) => s + d.value, 0);
  if (total <= 0) return null;
  const r = size / 2;
  const inner = r - thickness;
  let acc = 0;
  const slices = data.map((d) => {
    const startAng = (acc / total) * Math.PI * 2 - Math.PI / 2;
    acc += d.value;
    const endAng = (acc / total) * Math.PI * 2 - Math.PI / 2;
    const x1 = r + r * Math.cos(startAng);
    const y1 = r + r * Math.sin(startAng);
    const x2 = r + r * Math.cos(endAng);
    const y2 = r + r * Math.sin(endAng);
    const ix1 = r + inner * Math.cos(endAng);
    const iy1 = r + inner * Math.sin(endAng);
    const ix2 = r + inner * Math.cos(startAng);
    const iy2 = r + inner * Math.sin(startAng);
    const large = endAng - startAng > Math.PI ? 1 : 0;
    const path = [
      `M${x1.toFixed(2)},${y1.toFixed(2)}`,
      `A${r},${r} 0 ${large} 1 ${x2.toFixed(2)},${y2.toFixed(2)}`,
      `L${ix1.toFixed(2)},${iy1.toFixed(2)}`,
      `A${inner},${inner} 0 ${large} 0 ${ix2.toFixed(2)},${iy2.toFixed(2)}`,
      'Z',
    ].join(' ');
    return { ...d, path, pct: (d.value / total) * 100 };
  });
  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
      {slices.map((s) => (
        <path
          d={s.path}
          fill={s.color}
          stroke="#fff"
          stroke-width="1"
          opacity={highlightCohort && s.key !== highlightCohort ? 0.35 : 1}
        >
          <title>{`${s.label}: ${s.pct.toFixed(1)}%`}</title>
        </path>
      ))}
    </svg>
  );
}

// Tiny "this-parcel vs town" donut: 1 colored slice + grey rest
function SinglePctDonut({
  pct: pctVal,
  color,
  size = 130,
  thickness = 22,
  centerLabel,
  centerSub,
}: {
  pct: number;
  color: string;
  size?: number;
  thickness?: number;
  centerLabel: string;
  centerSub: string;
}) {
  const r = size / 2;
  const inner = r - thickness;
  const ang = (Math.min(Math.max(pctVal, 0), 100) / 100) * Math.PI * 2;
  // Avoid degenerate full circle issue: use two arcs if pct close to 100
  const startAng = -Math.PI / 2;
  const endAng = startAng + ang;
  const large = ang > Math.PI ? 1 : 0;
  const x1 = r + r * Math.cos(startAng);
  const y1 = r + r * Math.sin(startAng);
  const x2 = r + r * Math.cos(endAng);
  const y2 = r + r * Math.sin(endAng);
  const ix1 = r + inner * Math.cos(endAng);
  const iy1 = r + inner * Math.sin(endAng);
  const ix2 = r + inner * Math.cos(startAng);
  const iy2 = r + inner * Math.sin(startAng);
  const fillPath =
    pctVal > 0
      ? `M${x1},${y1} A${r},${r} 0 ${large} 1 ${x2},${y2} L${ix1},${iy1} A${inner},${inner} 0 ${large} 0 ${ix2},${iy2} Z`
      : '';
  return (
    <div style="position:relative;width:fit-content">
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        <circle cx={r} cy={r} r={r} fill="#e3e6ea" />
        <circle cx={r} cy={r} r={inner} fill="#fff" />
        {fillPath && <path d={fillPath} fill={color} />}
      </svg>
      <div
        style={`position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;font-variant-numeric:tabular-nums`}
      >
        <div style="font-size:1.05rem;font-weight:700;color:#0e1116">{centerLabel}</div>
        <div style="font-size:0.65rem;color:#5b6270;text-transform:uppercase;letter-spacing:0.04em">{centerSub}</div>
      </div>
    </div>
  );
}

export default function TaxContext({ parcelCohort, parcelTax, parcelAssessed, aggregates, nonArmsOnly }: Props) {
  if (!aggregates || !aggregates.cohorts || aggregates.cohorts.length === 0) {
    return null;
  }
  const cohortRow = aggregates.cohorts.find((c) => c.cohort === parcelCohort);
  const myPct = isPresent(parcelTax) && aggregates.total_tax_pool > 0
    ? (Number(parcelTax) / aggregates.total_tax_pool) * 100
    : 0;
  const cohortColor = COHORT_FILL[parcelCohort] || '#888';
  const cohortLabel = COHORT_LABEL[parcelCohort] || parcelCohort;
  const definition = COHORT_DEFINITION[parcelCohort] || '';

  // Pie data: cohort tax-pool slices
  const pieData = aggregates.cohorts.map((c) => ({
    key: c.cohort,
    value: c.sum_tax,
    color: COHORT_FILL[c.cohort] || '#888',
    label: COHORT_LABEL[c.cohort] || c.cohort,
  }));

  return (
    <section class="pd-section">
      <h2 class="pd-section-title">Tax Context · Cohort Position</h2>
      <p class="pd-section-subtitle">
        How this parcel and its tenure cohort sit inside Fair Haven's <strong>{money(aggregates.total_tax_pool)}</strong>{' '}
        annual levy across <strong>{num(aggregates.parcels_with_tax_data)}</strong> taxed parcels.
      </p>

      {/* Cohort definition card */}
      <div
        style={`background:${cohortColor}1a;border-left:4px solid ${cohortColor};padding:0.7rem 0.9rem;border-radius:0 4px 4px 0;margin-bottom:0.9rem`}
      >
        <div style={`font-size:0.72rem;text-transform:uppercase;letter-spacing:0.06em;color:${cohortColor};font-weight:700;margin-bottom:0.2rem`}>
          Cohort: {cohortLabel}
        </div>
        <div style="font-size:0.84rem;color:var(--pd-fg);line-height:1.5">{definition}</div>
      </div>

      {nonArmsOnly && (
        <div
          style="background:#fff3df;border-left:4px solid #b85c00;padding:0.6rem 0.85rem;border-radius:0 4px 4px 0;margin-bottom:0.9rem;font-size:0.82rem;line-height:1.45"
        >
          <strong style="color:#b85c00;text-transform:uppercase;font-size:0.7rem;letter-spacing:0.05em">
            ⚠ Non-arms transfers only
          </strong>
          <div style="margin-top:0.2rem;color:var(--pd-fg)">{NON_ARMS_NOTE}</div>
        </div>
      )}

      {/* Two donuts side by side */}
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:0.8rem;margin-bottom:0.9rem">
        <div style="background:var(--pd-card-bg);border:1px solid var(--pd-border);border-radius:6px;padding:0.7rem;display:flex;flex-direction:column;align-items:center;gap:0.4rem">
          <div style="font-size:0.68rem;text-transform:uppercase;letter-spacing:0.05em;color:var(--pd-muted);font-weight:600;text-align:center">
            This Parcel<br />of Town Levy
          </div>
          <SinglePctDonut
            pct={myPct}
            color={cohortColor}
            centerLabel={myPct < 0.01 ? '<0.01%' : `${myPct.toFixed(3)}%`}
            centerSub={money(parcelTax)}
          />
          <div style="font-size:0.72rem;color:var(--pd-muted);text-align:center;line-height:1.35">
            of the {money(aggregates.total_tax_pool)} pool<br />
            <span style="color:var(--pd-faint)">(1 of {num(aggregates.parcels_with_tax_data)} parcels)</span>
          </div>
        </div>

        <div style="background:var(--pd-card-bg);border:1px solid var(--pd-border);border-radius:6px;padding:0.7rem;display:flex;flex-direction:column;align-items:center;gap:0.4rem">
          <div style="font-size:0.68rem;text-transform:uppercase;letter-spacing:0.05em;color:var(--pd-muted);font-weight:600;text-align:center">
            Cohort Share<br />of Town Levy
          </div>
          <Donut data={pieData} highlightCohort={parcelCohort} />
          {cohortRow && (
            <div style="font-size:0.72rem;color:var(--pd-muted);text-align:center;line-height:1.35">
              <strong style={`color:${cohortColor};font-size:0.85rem`}>{pct(cohortRow.pct_of_tax_pool)}</strong>{' '}
              of pool<br />
              <span style="color:var(--pd-faint)">from {pct(cohortRow.pct_of_parcels)} of parcels</span>
            </div>
          )}
        </div>
      </div>

      {/* Cohort comparison table */}
      <h3 style="font-size:0.72rem;text-transform:uppercase;letter-spacing:0.05em;color:var(--pd-muted);margin:0 0 0.5rem;font-weight:700">
        All cohorts
      </h3>
      <table class="pd-table">
        <thead>
          <tr>
            <th>Cohort</th>
            <th class="num">Parcels</th>
            <th class="num">% Town</th>
            <th class="num">% Levy</th>
            <th class="num">Avg Tax</th>
          </tr>
        </thead>
        <tbody>
          {aggregates.cohorts.map((c) => {
            const isMine = c.cohort === parcelCohort;
            return (
              <tr
                style={isMine ? `background:${COHORT_FILL[c.cohort]}22 !important;font-weight:600` : ''}
              >
                <td>
                  <span
                    style={`display:inline-block;width:10px;height:10px;border-radius:2px;background:${COHORT_FILL[c.cohort]};margin-right:6px;vertical-align:middle`}
                  />
                  {COHORT_LABEL[c.cohort] || c.cohort}
                </td>
                <td class="num">{num(c.n_parcels)}</td>
                <td class="num">{pct(c.pct_of_parcels)}</td>
                <td class="num">{pct(c.pct_of_tax_pool)}</td>
                <td class="num">{money(c.avg_tax_per_parcel)}</td>
              </tr>
            );
          })}
        </tbody>
      </table>

      <p
        style="font-size:0.74rem;color:var(--pd-faint);margin-top:0.6rem;font-style:italic;line-height:1.4"
      >
        Cohorts where %&nbsp;Town &gt; %&nbsp;Levy contribute disproportionately less than their share
        — the descriptive H1/H2 signal. Hedonic OLS (Plan 4) controls for property characteristics
        before assigning Berry tax-shift dollars.
      </p>
    </section>
  );
}
