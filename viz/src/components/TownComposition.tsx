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

export default function TownComposition({ aggregates }: { aggregates: Aggregates }) {
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

      <div style="font-size:0.78rem;color:#5b6270;line-height:1.55;border-top:1px solid #e3e6ea;padding-top:0.8rem">
        <strong>Reading the skew column.</strong> A positive value (e.g., +3.3pp) means a group pays a larger share
        of the levy than its share of parcels — they're paying more than their "head count" share. Negative means
        the opposite. The expected H1 pattern: pre-2015 / pre-pandemic groups carry <em>negative</em> skew, newer
        cohorts carry <em>positive</em> skew. This is descriptive only; whether it survives controls for property
        size, age, and lot is the Plan&nbsp;4 hedonic test.
      </div>
    </main>
  );
}
