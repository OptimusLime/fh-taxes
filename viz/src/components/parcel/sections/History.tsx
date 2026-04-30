/** @jsxImportSource preact */
import { money, isPresent } from '../format';

type Row = {
  year: number;
  land_value?: number;
  improvement_value?: number;
  net_value?: number;
  sale_price?: number;
  sale_assessment?: number;
  deed_date?: string;
};

type Props = { history: Row[] };

function Sparkline({ rows }: { rows: Row[] }) {
  const pts = rows.filter((r) => isPresent(r.net_value));
  if (pts.length < 2) return null;
  const W = 800;
  const H = 60;
  const padX = 8;
  const padY = 6;
  const xs = pts.map((p) => p.year);
  const ys = pts.map((p) => Number(p.net_value));
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);
  const sx = (x: number) => padX + ((x - minX) / Math.max(1, maxX - minX)) * (W - 2 * padX);
  const sy = (y: number) => H - padY - ((y - minY) / Math.max(1, maxY - minY)) * (H - 2 * padY);
  const linePath = pts
    .map((p, i) => `${i === 0 ? 'M' : 'L'}${sx(p.year).toFixed(1)},${sy(Number(p.net_value)).toFixed(1)}`)
    .join(' ');
  const areaPath =
    `M${sx(pts[0].year).toFixed(1)},${(H - padY).toFixed(1)} ` +
    pts.map((p) => `L${sx(p.year).toFixed(1)},${sy(Number(p.net_value)).toFixed(1)}`).join(' ') +
    ` L${sx(pts[pts.length - 1].year).toFixed(1)},${(H - padY).toFixed(1)} Z`;
  const sales = pts.filter((p) => isPresent(p.deed_date) || isPresent(p.sale_price));

  const first = pts[0];
  const last = pts[pts.length - 1];
  const totalGrowth =
    isPresent(first.net_value) && isPresent(last.net_value) && Number(first.net_value) > 0
      ? ((Number(last.net_value) - Number(first.net_value)) / Number(first.net_value)) * 100
      : null;

  return (
    <div class="pd-spark-wrap">
      <svg class="pd-spark" viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none">
        <path d={areaPath} class="pd-spark-area" />
        <path d={linePath} class="pd-spark-line" />
        {sales.map((p) => (
          <circle
            cx={sx(p.year)}
            cy={sy(Number(p.net_value))}
            r="3"
            class="pd-spark-dot-event"
            data-year={p.year}
          />
        ))}
      </svg>
      <div class="pd-spark-summary">
        <span>
          <strong>{minX}</strong> {money(first.net_value)}
        </span>
        <span>
          {totalGrowth != null && (
            <>
              Δ <strong>{totalGrowth >= 0 ? '+' : ''}{totalGrowth.toFixed(0)}%</strong>
            </>
          )}
        </span>
        <span>
          <strong>{maxX}</strong> {money(last.net_value)}
        </span>
      </div>
    </div>
  );
}

export default function History({ history }: Props) {
  if (!history || history.length === 0) {
    return (
      <section class="pd-section">
        <h2 class="pd-section-title">Assessment Trajectory (Bloustein 1989-2025)</h2>
        <div class="pd-empty">No historical rows on record.</div>
      </section>
    );
  }
  const saleYears = new Set(history.filter((h) => isPresent(h.deed_date) || isPresent(h.sale_price)).map((h) => h.year));

  return (
    <section class="pd-section">
      <h2 class="pd-section-title">Assessment Trajectory</h2>
      <p class="pd-section-subtitle">
        Bloustein historical MOD-IV {history[0]?.year}-{history[history.length - 1]?.year} ·{' '}
        green dots = recorded sale events.
      </p>
      <Sparkline rows={history} />
      <details class="pd-collapse" style="margin-top:0.6rem">
        <summary>▸ Show year-by-year ({history.length} rows)</summary>
        <table class="pd-table" style="margin-top:0.4rem">
          <thead>
            <tr>
              <th>Year</th>
              <th class="num">Land</th>
              <th class="num">Improvements</th>
              <th class="num">Net</th>
              <th class="num">Sale@</th>
              <th>Deed</th>
            </tr>
          </thead>
          <tbody>
            {history.map((h) => (
              <tr class={saleYears.has(h.year) ? 'sale-row' : ''}>
                <td>{h.year}</td>
                <td class="num">{money(h.land_value)}</td>
                <td class="num">{money(h.improvement_value)}</td>
                <td class="num">{money(h.net_value)}</td>
                <td class="num">{isPresent(h.sale_assessment) ? money(h.sale_assessment) : ''}</td>
                <td class="deed">{h.deed_date ? String(h.deed_date).slice(0, 10) : ''}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </section>
  );
}
