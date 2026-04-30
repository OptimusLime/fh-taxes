/** @jsxImportSource preact */
import { useRef, useState, useCallback } from 'preact/hooks';
import { money, isPresent } from '../format';

type Row = {
  year: number;
  land_value?: number;
  improvement_value?: number;
  net_value?: number;
  sale_price?: number;
  sale_assessment?: number;
  sale_nu_code?: string;
  deed_date?: string;
  deed_book?: string;
  deed_page?: string;
};

type Props = { history: Row[] };

const W = 800;
const H = 110;
const padX = 24;
const padY = 18;

function InteractiveSparkline({ rows }: { rows: Row[] }) {
  const pts = rows.filter((r) => isPresent(r.net_value));
  const svgRef = useRef<SVGSVGElement | null>(null);
  const [hover, setHover] = useState<{ idx: number; x: number; y: number } | null>(null);

  if (pts.length < 2) return null;

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

  const yTicks = 3;
  const yTickValues = Array.from({ length: yTicks }, (_, i) =>
    minY + ((maxY - minY) * i) / (yTicks - 1)
  );
  const xTickYears = [minX, Math.round((minX + maxX) / 2), maxX];

  const sales = pts.filter((p) => isPresent(p.deed_date) || isPresent(p.sale_price));

  const onMove = useCallback(
    (e: MouseEvent) => {
      if (!svgRef.current) return;
      const rect = svgRef.current.getBoundingClientRect();
      const xRatio = (e.clientX - rect.left) / rect.width;
      const xVirtual = xRatio * W;
      // Find nearest point by x distance
      let nearestIdx = 0;
      let nearestDist = Infinity;
      pts.forEach((p, i) => {
        const d = Math.abs(sx(p.year) - xVirtual);
        if (d < nearestDist) {
          nearestDist = d;
          nearestIdx = i;
        }
      });
      const p = pts[nearestIdx];
      // Position tooltip in screen coords (CSS px relative to wrap)
      const cx = (sx(p.year) / W) * rect.width;
      const cy = (sy(Number(p.net_value)) / H) * rect.height;
      setHover({ idx: nearestIdx, x: cx, y: cy });
    },
    [pts]
  );

  const onLeave = useCallback(() => setHover(null), []);

  const hovered = hover ? pts[hover.idx] : null;
  const first = pts[0];
  const last = pts[pts.length - 1];
  const totalGrowth =
    isPresent(first.net_value) && isPresent(last.net_value) && Number(first.net_value) > 0
      ? ((Number(last.net_value) - Number(first.net_value)) / Number(first.net_value)) * 100
      : null;

  return (
    <div class="pd-spark-wrap">
      <svg
        ref={svgRef}
        class="pd-spark"
        viewBox={`0 0 ${W} ${H}`}
        preserveAspectRatio="none"
        onMouseMove={onMove}
        onMouseLeave={onLeave}
        style="height: 110px"
      >
        {/* Y-axis grid + labels */}
        {yTickValues.map((v) => (
          <g>
            <line
              x1={padX}
              x2={W - padX}
              y1={sy(v)}
              y2={sy(v)}
              stroke="#e3e6ea"
              stroke-width="0.5"
            />
            <text x={4} y={sy(v) + 3} class="pd-spark-axis">
              {v >= 1_000_000 ? `$${(v / 1_000_000).toFixed(1)}M` : `$${(v / 1_000).toFixed(0)}K`}
            </text>
          </g>
        ))}
        {/* X-axis labels */}
        {xTickYears.map((yr) => (
          <text x={sx(yr)} y={H - 3} text-anchor="middle" class="pd-spark-axis">
            {yr}
          </text>
        ))}

        <path d={areaPath} class="pd-spark-area" />
        <path d={linePath} class="pd-spark-line" />

        {/* Sale event markers */}
        {sales.map((p) => (
          <circle
            cx={sx(p.year)}
            cy={sy(Number(p.net_value))}
            r="4"
            class="pd-spark-dot-event"
            data-year={p.year}
          />
        ))}

        {/* Hover cursor + point */}
        {hovered && hover && (
          <>
            <line
              x1={sx(hovered.year)}
              x2={sx(hovered.year)}
              y1={padY}
              y2={H - padY}
              class="pd-spark-cursor active"
            />
            <circle
              cx={sx(hovered.year)}
              cy={sy(Number(hovered.net_value))}
              r="5"
              class="pd-spark-hover-pt active"
            />
          </>
        )}
      </svg>

      {hovered && hover && (
        <div
          class="pd-spark-tip"
          style={`left: ${hover.x}px; top: ${hover.y}px;`}
        >
          <div style="font-weight:600;font-size:0.85rem;margin-bottom:2px">{hovered.year}</div>
          <div class="tip-row"><span class="tip-key">Net</span><strong>{money(hovered.net_value)}</strong></div>
          <div class="tip-row"><span class="tip-key">Land</span>{money(hovered.land_value)}</div>
          <div class="tip-row"><span class="tip-key">Imp.</span>{money(hovered.improvement_value)}</div>
          {isPresent(hovered.sale_price) && (
            <div class="tip-row" style="margin-top:3px;border-top:1px solid #444;padding-top:3px">
              <span class="tip-key">Sale</span>
              <strong>{money(hovered.sale_price)}</strong>
            </div>
          )}
          {isPresent(hovered.sale_assessment) && (
            <div class="tip-row"><span class="tip-key">Sale@asmt</span>{money(hovered.sale_assessment)}</div>
          )}
          {isPresent(hovered.deed_date) && (
            <div class="tip-row"><span class="tip-key">Deed</span>{String(hovered.deed_date).slice(0, 10)}</div>
          )}
          {isPresent(hovered.sale_nu_code) && (
            <div class="tip-row"><span class="tip-key">NU</span>{hovered.sale_nu_code}</div>
          )}
        </div>
      )}

      <div class="pd-spark-summary">
        <span><strong>{minX}</strong> {money(first.net_value)}</span>
        {totalGrowth != null && (
          <span>Δ <strong>{totalGrowth >= 0 ? '+' : ''}{totalGrowth.toFixed(0)}%</strong> over {maxX - minX} yrs</span>
        )}
        <span><strong>{maxX}</strong> {money(last.net_value)}</span>
      </div>
    </div>
  );
}

export default function History({ history }: Props) {
  const [collapsed, setCollapsed] = useState(false);
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
        Bloustein historical MOD-IV {history[0]?.year}–{history[history.length - 1]?.year} ·{' '}
        green dots = recorded sale events · hover the chart for year-by-year detail.
      </p>
      <InteractiveSparkline rows={history} />

      <div style="display:flex;align-items:center;justify-content:space-between;margin-top:0.9rem;margin-bottom:0.4rem">
        <h3 style="font-size:0.78rem;text-transform:uppercase;letter-spacing:0.05em;color:var(--pd-muted);margin:0;font-weight:700">
          Year-by-year ({history.length} rows)
        </h3>
        <button
          type="button"
          onClick={() => setCollapsed((c) => !c)}
          style="background:none;border:1px solid var(--pd-border);border-radius:3px;padding:2px 8px;font-size:0.72rem;color:var(--pd-muted);cursor:pointer"
        >
          {collapsed ? 'expand' : 'collapse'}
        </button>
      </div>

      {!collapsed && (
        <table class="pd-table">
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
      )}
    </section>
  );
}
