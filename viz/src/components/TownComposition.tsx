/** @jsxImportSource preact */
// Town-wide composition: parcels, levy, and avg tax-per-parcel split by tenure cohort.
// Reads town_aggregates.json (cohort grain) — same data driving the parcel drawer's
// Tax Context section.

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

type CohortHistory = {
  summary: {
    current_effective_rate: number;
    year_min: number;
    year_max: number;
    adp_start: number;
    cumulative_position_full_history: Array<{ cohort: string; dollars: number }>;
    cumulative_position_adp_era: Array<{ cohort: string; dollars: number }>;
  };
  annual: Array<{
    year: number;
    total_assessed: number;
    total_parcels: number;
    implied_levy: number;
    cohorts: Array<{
      cohort: string;
      n_parcels: number;
      sum_assessed: number;
      avg_assessed: number;
      share_of_assessed: number;
      share_of_parcels: number;
      implied_dollar_position: number;
    }>;
  }>;
};

const COHORT_ORDER = [
  'no_deed_since_1989',
  'tenure_pre_2015',
  'tenure_2015_2019',
  'tenure_pandemic_2020_2022',
  'tenure_post_pandemic_2023plus',
];

const COHORT_LABEL: Record<string, string> = {
  no_deed_since_1989: 'No deed since 1989',
  tenure_pre_2015: 'Pre-2015',
  tenure_2015_2019: '2015–2019',
  tenure_pandemic_2020_2022: 'Pandemic 2020–22',
  tenure_post_pandemic_2023plus: 'Post-pandemic 2023+',
};

const COHORT_FILL: Record<string, string> = {
  no_deed_since_1989: '#ff0000',
  tenure_pre_2015: '#ff8800',
  tenure_2015_2019: '#ffe600',
  tenure_pandemic_2020_2022: '#88dd00',
  tenure_post_pandemic_2023plus: '#00cc44',
};

const fmtMoney = (n: number) => '$' + n.toLocaleString('en-US', { maximumFractionDigits: 0 });
const fmtMoneyM = (n: number) => '$' + (n / 1e6).toFixed(2) + 'M';
const fmtPct = (n: number) => n.toFixed(1) + '%';
const fmtNum = (n: number) => n.toLocaleString('en-US');

function Donut({
  data,
  size = 240,
  thickness = 50,
}: {
  data: Array<{ key: string; value: number; color: string; label: string }>;
  size?: number;
  thickness?: number;
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
        <path d={s.path} fill={s.color} stroke="#fff" stroke-width="1.5">
          <title>{`${s.label}: ${s.pct.toFixed(1)}% (${fmtMoney(s.value)})`}</title>
        </path>
      ))}
    </svg>
  );
}

function Legend({ cohorts, valueOf, totalLabel, total }: {
  cohorts: Cohort[];
  valueOf: (c: Cohort) => number;
  totalLabel: string;
  total: number;
}) {
  return (
    <div style="display:flex;flex-direction:column;gap:0.3rem;font-size:0.85rem;font-variant-numeric:tabular-nums">
      {COHORT_ORDER.map((key) => {
        const c = cohorts.find((x) => x.cohort === key);
        if (!c) return null;
        const v = valueOf(c);
        const p = (v / total) * 100;
        return (
          <div style="display:flex;align-items:center;gap:0.5rem">
            <span style={`display:inline-block;width:14px;height:14px;border-radius:3px;background:${COHORT_FILL[key]};border:1px solid #555`} />
            <span style="flex:1">{COHORT_LABEL[key]}</span>
            <span style="color:#5b6270">{fmtPct(p)}</span>
          </div>
        );
      })}
      <div style="border-top:1px solid #e3e6ea;padding-top:0.3rem;margin-top:0.2rem;display:flex;justify-content:space-between;color:#5b6270;font-size:0.78rem">
        <span>{totalLabel}</span>
        <span>{typeof total === 'number' && total > 1e6 ? fmtMoneyM(total) : fmtNum(total)}</span>
      </div>
    </div>
  );
}

function DonutCard({
  title,
  subtitle,
  cohorts,
  valueOf,
  total,
  totalLabel,
}: {
  title: string;
  subtitle: string;
  cohorts: Cohort[];
  valueOf: (c: Cohort) => number;
  total: number;
  totalLabel: string;
}) {
  const data = COHORT_ORDER
    .map((key) => {
      const c = cohorts.find((x) => x.cohort === key);
      return c ? { key, value: valueOf(c), color: COHORT_FILL[key], label: COHORT_LABEL[key] } : null;
    })
    .filter(Boolean) as Array<{ key: string; value: number; color: string; label: string }>;
  return (
    <div style="background:#fff;border:1px solid #e3e6ea;border-radius:8px;padding:1.2rem;display:flex;flex-direction:column;gap:0.6rem">
      <div>
        <h2 style="margin:0;font-size:1.05rem;font-weight:700">{title}</h2>
        <p style="margin:0.2rem 0 0;font-size:0.82rem;color:#5b6270">{subtitle}</p>
      </div>
      <div style="display:flex;align-items:center;gap:1.2rem">
        <Donut data={data} />
        <div style="flex:1;min-width:0">
          <Legend cohorts={cohorts} valueOf={valueOf} totalLabel={totalLabel} total={total} />
        </div>
      </div>
    </div>
  );
}

// Horizontal bar chart of avg tax per parcel by cohort (max H1 visibility)
function AvgTaxBars({ cohorts }: { cohorts: Cohort[] }) {
  const ordered = COHORT_ORDER.map((k) => cohorts.find((c) => c.cohort === k)).filter(Boolean) as Cohort[];
  const max = Math.max(...ordered.map((c) => c.avg_tax_per_parcel));
  return (
    <div style="display:flex;flex-direction:column;gap:0.55rem;font-variant-numeric:tabular-nums">
      {ordered.map((c) => {
        const w = (c.avg_tax_per_parcel / max) * 100;
        return (
          <div>
            <div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:0.15rem">
              <span style="font-size:0.85rem;font-weight:500">{COHORT_LABEL[c.cohort]}</span>
              <span style="font-size:0.85rem;font-weight:600">{fmtMoney(c.avg_tax_per_parcel)}</span>
            </div>
            <div style="height:22px;background:#f0f1f3;border-radius:3px;overflow:hidden">
              <div style={`height:100%;width:${w}%;background:${COHORT_FILL[c.cohort]};transition:width 200ms`} />
            </div>
            <div style="font-size:0.72rem;color:#5b6270;margin-top:0.1rem">
              {fmtNum(c.n_parcels)} parcels · {fmtMoneyM(c.sum_tax)} total levy contribution
            </div>
          </div>
        );
      })}
    </div>
  );
}

// Aggregate split block (e.g., pre-2015 vs 2015+)
function SplitBlock({
  title,
  subtitle,
  groups,
  total,
}: {
  title: string;
  subtitle: string;
  groups: Array<{ label: string; n: number; tax: number; color: string }>;
  total: { n: number; tax: number };
}) {
  return (
    <div style="background:#fff;border:1px solid #e3e6ea;border-radius:8px;padding:1.1rem">
      <h3 style="margin:0;font-size:0.95rem;font-weight:700">{title}</h3>
      <p style="margin:0.15rem 0 0.7rem;font-size:0.78rem;color:#5b6270">{subtitle}</p>
      <table style="width:100%;border-collapse:collapse;font-size:0.85rem;font-variant-numeric:tabular-nums">
        <thead>
          <tr style="text-align:right;color:#5b6270;font-size:0.72rem;text-transform:uppercase;letter-spacing:0.04em">
            <th style="text-align:left;padding:0.25rem 0.4rem 0.25rem 0">Group</th>
            <th style="padding:0.25rem 0.4rem">Parcels</th>
            <th style="padding:0.25rem 0.4rem">% Parcels</th>
            <th style="padding:0.25rem 0.4rem">Levy</th>
            <th style="padding:0.25rem 0.4rem">% Levy</th>
            <th style="padding:0.25rem 0 0.25rem 0.4rem">Avg/Parcel</th>
          </tr>
        </thead>
        <tbody>
          {groups.map((g) => {
            const pctP = (g.n / total.n) * 100;
            const pctT = (g.tax / total.tax) * 100;
            const skew = pctT - pctP;
            return (
              <tr style="border-top:1px solid #e3e6ea">
                <td style="padding:0.4rem 0.4rem 0.4rem 0">
                  <span style={`display:inline-block;width:12px;height:12px;border-radius:2px;background:${g.color};margin-right:6px;vertical-align:middle`} />
                  {g.label}
                </td>
                <td style="text-align:right;padding:0.4rem">{fmtNum(g.n)}</td>
                <td style="text-align:right;padding:0.4rem;color:#5b6270">{fmtPct(pctP)}</td>
                <td style="text-align:right;padding:0.4rem">{fmtMoneyM(g.tax)}</td>
                <td style="text-align:right;padding:0.4rem;color:#5b6270">{fmtPct(pctT)}</td>
                <td style={`text-align:right;padding:0.4rem 0 0.4rem 0.4rem;font-weight:600;color:${skew > 0 ? '#0a7c2f' : skew < 0 ? '#a13b00' : '#0e1116'}`}>
                  {fmtMoney(g.tax / g.n)}
                  <span style="display:block;font-size:0.7rem;font-weight:500;color:#5b6270">
                    {skew >= 0 ? '+' : ''}{skew.toFixed(1)}pp skew
                  </span>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

// Cumulative-undertaxation block: time series + cumulative dollar position.
function CumulativeBlock({ history }: { history: CohortHistory }) {
  // Filter to ADP era for the share-trajectory chart
  const adpYears = history.annual.filter((y) => y.year >= history.summary.adp_start);
  if (adpYears.length === 0) return null;

  // Chart geometry
  const W = 720;
  const H = 240;
  const PAD_L = 48;
  const PAD_R = 16;
  const PAD_T = 16;
  const PAD_B = 28;
  const innerW = W - PAD_L - PAD_R;
  const innerH = H - PAD_T - PAD_B;
  const years = adpYears.map((y) => y.year);
  const x0 = years[0];
  const x1 = years[years.length - 1];
  const xScale = (yr: number) => PAD_L + ((yr - x0) / (x1 - x0)) * innerW;

  // Series: share_of_assessed - share_of_parcels per cohort per year (in pp)
  const series = COHORT_ORDER.map((cohort) => {
    const pts = adpYears.map((row) => {
      const c = row.cohorts.find((cc) => cc.cohort === cohort);
      const gap = c ? (c.share_of_assessed - c.share_of_parcels) * 100 : 0;
      return { year: row.year, gap };
    });
    return { cohort, pts };
  });

  // Y axis: symmetric range based on max abs gap
  const maxAbs = Math.max(...series.flatMap((s) => s.pts.map((p) => Math.abs(p.gap))));
  const yMax = Math.ceil(maxAbs * 1.1);
  const yMin = -yMax;
  const yScale = (v: number) => PAD_T + ((yMax - v) / (yMax - yMin)) * innerH;

  // X axis ticks: every 2 years
  const xTicks: number[] = [];
  for (let yr = x0; yr <= x1; yr += 2) xTicks.push(yr);
  if (xTicks[xTicks.length - 1] !== x1) xTicks.push(x1);

  // Y axis ticks: 0, ±yMax/2, ±yMax
  const yTicks = [-yMax, -yMax / 2, 0, yMax / 2, yMax];

  const adpCum = history.summary.cumulative_position_adp_era;
  const span = `${history.summary.adp_start}–${history.summary.year_max}`;

  return (
    <div style="background:#fff;border:1px solid #e3e6ea;border-radius:8px;padding:1.2rem;margin-bottom:1.25rem">
      <h2 style="margin:0;font-size:1.05rem;font-weight:700">
        Cohort Trajectory Over the ADP Era ({span})
      </h2>
      <p style="margin:0.2rem 0 0.8rem;font-size:0.82rem;color:#5b6270;line-height:1.5;max-width:780px">
        For each year and cohort: <strong>(share of total assessed value) − (share of total parcels)</strong>,
        in percentage points. A positive value means the cohort's parcels carry more assessed value than their
        head-count share would imply (they're carrying more than equal-split parity). Zero means the two shares
        match. The bands are colored by cohort; you can read the year-over-year drift directly.
      </p>

      <svg width="100%" viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="xMidYMid meet">
        {/* zero line */}
        <line x1={PAD_L} y1={yScale(0)} x2={W - PAD_R} y2={yScale(0)} stroke="#0e1116" stroke-width="0.7" />
        {/* y ticks */}
        {yTicks.map((v) => (
          <g>
            <line x1={PAD_L} y1={yScale(v)} x2={W - PAD_R} y2={yScale(v)} stroke="#e3e6ea" stroke-width="0.5" />
            <text x={PAD_L - 6} y={yScale(v) + 3} text-anchor="end" font-size="10" fill="#5b6270" font-family="system-ui">
              {v >= 0 ? '+' : ''}{v.toFixed(1)}pp
            </text>
          </g>
        ))}
        {/* x ticks */}
        {xTicks.map((yr) => (
          <g>
            <line x1={xScale(yr)} y1={H - PAD_B} x2={xScale(yr)} y2={H - PAD_B + 3} stroke="#5b6270" stroke-width="0.5" />
            <text x={xScale(yr)} y={H - PAD_B + 14} text-anchor="middle" font-size="10" fill="#5b6270" font-family="system-ui">
              {yr}
            </text>
          </g>
        ))}
        {/* series lines */}
        {series.map((s) => {
          const d = s.pts
            .map((p, i) => `${i === 0 ? 'M' : 'L'}${xScale(p.year).toFixed(1)},${yScale(p.gap).toFixed(1)}`)
            .join(' ');
          return (
            <g>
              <path d={d} fill="none" stroke={COHORT_FILL[s.cohort]} stroke-width="2.2" />
              {s.pts.map((p) => (
                <circle cx={xScale(p.year)} cy={yScale(p.gap)} r="2.2" fill={COHORT_FILL[s.cohort]}>
                  <title>{`${COHORT_LABEL[s.cohort]} · ${p.year} · ${p.gap >= 0 ? '+' : ''}${p.gap.toFixed(2)}pp`}</title>
                </circle>
              ))}
            </g>
          );
        })}
      </svg>

      {/* Cumulative position table */}
      <div style="margin-top:1rem">
        <h3 style="margin:0;font-size:0.95rem;font-weight:700">Cumulative implied dollar position, ADP era</h3>
        <p style="margin:0.15rem 0 0.6rem;font-size:0.78rem;color:#5b6270;line-height:1.5;max-width:780px">
          Sum across years of <em>(share-of-assessed − share-of-parcels)</em> × <em>implied annual levy</em>,
          where implied levy = total assessed × {(history.summary.current_effective_rate * 100).toFixed(2)}%
          (current effective rate). <strong>Positive</strong> = cohort cumulatively carried more value-share than
          head-count-share. <strong>Negative</strong> = cumulatively carried less.
        </p>
        <table style="width:100%;border-collapse:collapse;font-size:0.85rem;font-variant-numeric:tabular-nums">
          <thead>
            <tr style="text-align:right;color:#5b6270;font-size:0.72rem;text-transform:uppercase;letter-spacing:0.04em">
              <th style="text-align:left;padding:0.25rem 0.4rem 0.25rem 0">Cohort</th>
              <th style="padding:0.25rem 0">Cumulative position</th>
            </tr>
          </thead>
          <tbody>
            {COHORT_ORDER.map((key) => {
              const row = adpCum.find((r) => r.cohort === key);
              if (!row) return null;
              const d = row.dollars;
              const color = d > 0 ? '#0a7c2f' : d < 0 ? '#a13b00' : '#0e1116';
              return (
                <tr style="border-top:1px solid #e3e6ea">
                  <td style="padding:0.4rem 0.4rem 0.4rem 0">
                    <span style={`display:inline-block;width:12px;height:12px;border-radius:2px;background:${COHORT_FILL[key]};margin-right:6px;vertical-align:middle`} />
                    {COHORT_LABEL[key]}
                  </td>
                  <td style={`text-align:right;padding:0.4rem 0;font-weight:700;color:${color}`}>
                    {d >= 0 ? '+' : ''}${(d / 1e6).toFixed(2)}M
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div style="margin-top:0.8rem;font-size:0.78rem;color:#5b6270;line-height:1.55;background:#fff8e1;border-left:3px solid #c89000;padding:0.6rem 0.8rem;border-radius:0 4px 4px 0">
        <strong style="color:#9e6900">Caveat — this is a descriptive floor, not a fair-share verdict.</strong>{' '}
        Head-count parity assumes parcels are equal-value, which they aren't (newer-cohort houses tend to be
        larger or more recently renovated). Plan&nbsp;4's hedonic model produces the proper per-parcel fair-share
        benchmark. What this view <em>does</em> show is the trajectory: which cohort's value-share has been
        rising vs falling under the ADP regime, and the cumulative dollar order-of-magnitude that produces.
      </div>
    </div>
  );
}

export default function TownComposition({
  aggregates,
  history,
}: {
  aggregates: Aggregates;
  history?: CohortHistory | null;
}) {
  const cohorts = aggregates.cohorts;
  const totalP = aggregates.total_parcels;
  const totalT = aggregates.total_tax_pool;

  const groupSum = (keys: string[]) => {
    const sub = cohorts.filter((c) => keys.includes(c.cohort));
    return { n: sub.reduce((s, c) => s + c.n_parcels, 0), tax: sub.reduce((s, c) => s + c.sum_tax, 0) };
  };
  const pre2015 = groupSum(['no_deed_since_1989', 'tenure_pre_2015']);
  const post2015 = groupSum(['tenure_2015_2019', 'tenure_pandemic_2020_2022', 'tenure_post_pandemic_2023plus']);
  const prePandemic = groupSum(['no_deed_since_1989', 'tenure_pre_2015', 'tenure_2015_2019']);
  const pandemicPlus = groupSum(['tenure_pandemic_2020_2022', 'tenure_post_pandemic_2023plus']);

  return (
    <main style="max-width:1200px;margin:0 auto;padding:1.5rem 1.25rem 4rem">
      <header style="margin-bottom:1.5rem">
        <h1 style="margin:0;font-size:1.6rem;font-weight:700">Fair Haven Tax Composition by Tenure Cohort</h1>
        <p style="margin:0.3rem 0 0;color:#5b6270;font-size:0.92rem;line-height:1.5;max-width:780px">
          How Fair Haven's <strong>{fmtNum(totalP)}</strong> parcels and <strong>{fmtMoneyM(totalT)}</strong> annual
          tax levy distribute across tenure cohorts. Cohorts are keyed on the most recent deed event of any kind
          (arms-length or family/exempt), with <em>No deed since 1989</em> as the truly-untransferred set. The
          color scale runs old → new; right-skew of the levy share toward newer cohorts is the H1 signal we expect
          if the assessor's mass-appraisal is sales-chasing.
        </p>
      </header>

      <div style="display:grid;grid-template-columns:1fr 1fr;gap:1rem;margin-bottom:1.25rem">
        <DonutCard
          title="Parcels by Cohort"
          subtitle={`${fmtNum(totalP)} parcels — denominator`}
          cohorts={cohorts}
          valueOf={(c) => c.n_parcels}
          total={totalP}
          totalLabel="Total parcels"
        />
        <DonutCard
          title="Tax Levy by Cohort"
          subtitle={`${fmtMoneyM(totalT)} — annual levy contribution`}
          cohorts={cohorts}
          valueOf={(c) => c.sum_tax}
          total={totalT}
          totalLabel="Total annual levy"
        />
      </div>

      <div style="background:#fff;border:1px solid #e3e6ea;border-radius:8px;padding:1.2rem;margin-bottom:1.25rem">
        <h2 style="margin:0;font-size:1.05rem;font-weight:700">Average Tax Bill per Parcel by Cohort</h2>
        <p style="margin:0.2rem 0 1rem;font-size:0.82rem;color:#5b6270">
          The cleanest view of the H1 hypothesis. If long-tenured owners pay less per parcel than recent buyers
          for comparable houses, the bars should slope up toward newer cohorts. Note this does <em>not</em> control
          for property characteristics yet — that's the hedonic model in Plan&nbsp;4.
        </p>
        <AvgTaxBars cohorts={cohorts} />
      </div>

      <div style="display:grid;grid-template-columns:1fr 1fr;gap:1rem;margin-bottom:1.25rem">
        <SplitBlock
          title="Pre-ADP vs ADP-era owners"
          subtitle="ADP (Monmouth's Assessment Demonstration Program) began ~2015. Pre-ADP owners had assessments set under decadal-revaluation."
          groups={[
            { label: 'Pre-2015', n: pre2015.n, tax: pre2015.tax, color: '#ff5500' },
            { label: '2015 onward', n: post2015.n, tax: post2015.tax, color: '#44dd22' },
          ]}
          total={{ n: totalP, tax: totalT }}
        />
        <SplitBlock
          title="Pre-pandemic vs pandemic-era owners"
          subtitle="The COVID housing surge (2020+) drove rapid price appreciation; assessments calibrated against pandemic-peak comparables."
          groups={[
            { label: 'Pre-pandemic', n: prePandemic.n, tax: prePandemic.tax, color: '#ffaa00' },
            { label: 'Pandemic+', n: pandemicPlus.n, tax: pandemicPlus.tax, color: '#22cc55' },
          ]}
          total={{ n: totalP, tax: totalT }}
        />
      </div>

      <div style="font-size:0.78rem;color:#5b6270;line-height:1.55;border-top:1px solid #e3e6ea;padding-top:0.8rem;margin-bottom:1.5rem">
        <strong>Reading the skew column.</strong> A positive value (e.g., +3.3pp) means a group pays a larger share
        of the levy than its share of parcels — they're paying more than their "head count" share. Negative means
        the opposite. The expected H1 pattern: pre-2015 / pre-pandemic groups carry <em>negative</em> skew, newer
        cohorts carry <em>positive</em> skew. This is descriptive only; whether it survives controls for property
        size, age, and lot is the Plan&nbsp;4 hedonic test.
      </div>

      {history && <CumulativeBlock history={history} />}
    </main>
  );
}
