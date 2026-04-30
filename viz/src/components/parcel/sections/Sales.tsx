/** @jsxImportSource preact */
import { useState, useRef, useCallback } from 'preact/hooks';
import { money, date, isPresent, joinPresent } from '../format';

type Sale = {
  date?: string;
  year?: number;
  price?: number;
  nu_code?: string;
  deed_book?: string;
  deed_page?: string;
  grantor?: string;
  grantee?: string;
  family_sale?: boolean;
  sales_ratio_assessor?: number;
  sale_assessment?: number;
  is_arms_length?: boolean;
  source?: string;
  remarks?: string;
};

type Props = {
  unifiedSales: Sale[];
  modivLast: Record<string, any>;
};

const W = 800;
const H = 130;
const padX = 36;
const padY = 22;

function SalesScatter({ sales }: { sales: Sale[] }) {
  const pts = sales.filter((s) => isPresent(s.price) && Number(s.price) > 1000 && isPresent(s.year));
  const svgRef = useRef<SVGSVGElement | null>(null);
  const [hover, setHover] = useState<{ idx: number; cx: number; cy: number } | null>(null);

  if (pts.length === 0) return null;

  const xs = pts.map((p) => Number(p.year));
  const ys = pts.map((p) => Number(p.price));
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);
  const padPx = (n: number) => Math.max(1000, n * 0.05);
  const yMin = Math.max(0, minY - padPx(minY));
  const yMax = maxY + padPx(maxY);

  // Spread same-year points horizontally a bit so they don't overlap
  const sx = (year: number, idxInYear: number, cohortSize: number) => {
    const base = padX + ((year - minX) / Math.max(1, maxX - minX)) * (W - 2 * padX);
    if (cohortSize <= 1) return base;
    const offset = (idxInYear - (cohortSize - 1) / 2) * 8;
    return base + offset;
  };
  const sy = (price: number) =>
    H - padY - ((price - yMin) / Math.max(1, yMax - yMin)) * (H - 2 * padY);

  // Group same-year for jitter
  const yearGroups: Record<number, number[]> = {};
  pts.forEach((p, i) => {
    const y = Number(p.year);
    if (!yearGroups[y]) yearGroups[y] = [];
    yearGroups[y].push(i);
  });
  const idxInYearMap: Record<number, number> = {};
  Object.values(yearGroups).forEach((ids) => ids.forEach((id, k) => (idxInYearMap[id] = k)));

  const yTicks = 3;
  const yTickValues = Array.from({ length: yTicks }, (_, i) => yMin + ((yMax - yMin) * i) / (yTicks - 1));
  const xTickYears = maxX - minX <= 8
    ? Array.from({ length: maxX - minX + 1 }, (_, i) => minX + i)
    : [minX, Math.round((minX * 2 + maxX) / 3), Math.round((minX + maxX * 2) / 3), maxX];

  const onMove = useCallback(
    (e: MouseEvent) => {
      if (!svgRef.current) return;
      const rect = svgRef.current.getBoundingClientRect();
      const xRatio = (e.clientX - rect.left) / rect.width;
      const yRatio = (e.clientY - rect.top) / rect.height;
      const xV = xRatio * W;
      const yV = yRatio * H;
      let nearest = -1;
      let nearestD = Infinity;
      pts.forEach((p, i) => {
        const cohortSize = yearGroups[Number(p.year)].length;
        const cx = sx(Number(p.year), idxInYearMap[i], cohortSize);
        const cy = sy(Number(p.price));
        const d = Math.hypot(cx - xV, cy - yV);
        if (d < nearestD) {
          nearestD = d;
          nearest = i;
        }
      });
      if (nearest >= 0 && nearestD < 25) {
        const p = pts[nearest];
        const cohortSize = yearGroups[Number(p.year)].length;
        const cxV = sx(Number(p.year), idxInYearMap[nearest], cohortSize);
        const cyV = sy(Number(p.price));
        const cx = (cxV / W) * rect.width;
        const cy = (cyV / H) * rect.height;
        setHover({ idx: nearest, cx, cy });
      } else {
        setHover(null);
      }
    },
    [pts]
  );

  const onLeave = useCallback(() => setHover(null), []);

  const hoveredSale = hover ? pts[hover.idx] : null;

  return (
    <div class="pd-spark-wrap">
      <svg
        ref={svgRef}
        class="pd-spark"
        viewBox={`0 0 ${W} ${H}`}
        preserveAspectRatio="none"
        style="height: 130px"
        onMouseMove={onMove}
        onMouseLeave={onLeave}
      >
        {yTickValues.map((v) => (
          <g>
            <line x1={padX} x2={W - padX} y1={sy(v)} y2={sy(v)} stroke="#e3e6ea" stroke-width="0.5" />
            <text x={4} y={sy(v) + 3} class="pd-spark-axis">
              {v >= 1_000_000 ? `$${(v / 1_000_000).toFixed(1)}M` : `$${(v / 1_000).toFixed(0)}K`}
            </text>
          </g>
        ))}
        {xTickYears.map((yr) => (
          <text x={(padX + ((yr - minX) / Math.max(1, maxX - minX)) * (W - 2 * padX))} y={H - 3} text-anchor="middle" class="pd-spark-axis">
            {yr}
          </text>
        ))}
        {pts.map((p, i) => {
          const cohortSize = yearGroups[Number(p.year)].length;
          const cx = sx(Number(p.year), idxInYearMap[i], cohortSize);
          const cy = sy(Number(p.price));
          const armsLen = p.is_arms_length !== false;
          return (
            <circle
              cx={cx}
              cy={cy}
              r={hover?.idx === i ? 6 : 4}
              fill={armsLen ? '#1f7a3a' : '#b85c00'}
              stroke="#fff"
              stroke-width="1"
              opacity={armsLen ? 1 : 0.7}
            />
          );
        })}
      </svg>
      {hoveredSale && hover && (
        <div class="pd-spark-tip" style={`left: ${hover.cx}px; top: ${hover.cy}px;`}>
          <div style="font-weight:600;font-size:0.85rem;margin-bottom:2px">{hoveredSale.date}</div>
          <div class="tip-row"><span class="tip-key">Price</span><strong>{money(hoveredSale.price)}</strong></div>
          {isPresent(hoveredSale.sale_assessment) && (
            <div class="tip-row"><span class="tip-key">Asmt@sale</span>{money(hoveredSale.sale_assessment)}</div>
          )}
          {isPresent(hoveredSale.nu_code) && (
            <div class="tip-row"><span class="tip-key">NU</span>{hoveredSale.nu_code}</div>
          )}
          <div class="tip-row"><span class="tip-key">Type</span>
            {hoveredSale.is_arms_length !== false ? 'arms-length' : 'non-arms (family/exempt)'}
          </div>
          {(hoveredSale.deed_book || hoveredSale.deed_page) && (
            <div class="tip-row"><span class="tip-key">Deed</span>{joinPresent([hoveredSale.deed_book, hoveredSale.deed_page]) || '—'}</div>
          )}
          <div class="tip-row" style="margin-top:3px;border-top:1px solid #444;padding-top:3px">
            <span class="tip-key">Source</span>{hoveredSale.source}
          </div>
        </div>
      )}
      <div class="pd-spark-summary">
        <span><strong>{pts.length}</strong> sale event{pts.length === 1 ? '' : 's'} ({minX}–{maxX})</span>
        <span style="color:#1f7a3a">● arms-length</span>
        <span style="color:#b85c00">● non-arms-length</span>
      </div>
    </div>
  );
}

export default function Sales({ unifiedSales, modivLast }: Props) {
  const sales = (unifiedSales || []).slice(); // already reverse-chrono from joiner

  return (
    <section class="pd-section">
      <h2 class="pd-section-title">Sales History</h2>
      <p class="pd-section-subtitle">
        All recorded deed events 1989–present (Bloustein) merged with SR1A 2018-2025 grantor/grantee detail.
        Reverse-chronological — most recent first. Arms-length filtering uses NU codes.
      </p>

      {sales.length === 0 ? (
        <div class="pd-empty">No deed events on record since 1989.</div>
      ) : (
        <>
          <SalesScatter sales={sales} />

          <table class="pd-table" style="margin-top:0.7rem">
            <thead>
              <tr>
                <th>Date</th>
                <th class="num">Price</th>
                <th class="num">Asmt@sale</th>
                <th>NU</th>
                <th>Deed</th>
                <th>Type</th>
              </tr>
            </thead>
            <tbody>
              {sales.map((s) => {
                const armsLen = s.is_arms_length !== false;
                return (
                  <>
                    <tr class={armsLen ? '' : 'sale-row'}>
                      <td>{date(s.date)}</td>
                      <td class="num">{money(s.price)}</td>
                      <td class="num">{isPresent(s.sale_assessment) ? money(s.sale_assessment) : '—'}</td>
                      <td>{s.nu_code || '—'}</td>
                      <td class="deed">{joinPresent([s.deed_book, s.deed_page]) || '—'}</td>
                      <td>
                        <span
                          style={`display:inline-block;padding:1px 6px;border-radius:3px;font-size:0.72rem;background:${armsLen ? '#e3f4e8' : '#fff3df'};color:${armsLen ? '#1f7a3a' : '#b85c00'}`}
                        >
                          {armsLen ? 'arms' : 'non-arms'}
                        </span>
                      </td>
                    </tr>
                    {(s.grantor || s.grantee) && (
                      <tr>
                        <td colSpan={6} style="font-size:0.72rem;color:var(--pd-muted);padding-left:1rem">
                          {s.grantor && (<><span class="pd-key">grantor</span> {s.grantor}</>)}
                          {s.grantor && s.grantee && ' → '}
                          {s.grantee && (<><span class="pd-key">grantee</span> {s.grantee}</>)}
                          {isPresent(s.sales_ratio_assessor) && (
                            <>{' · '}<span class="pd-key">assessor ratio</span> {Number(s.sales_ratio_assessor).toFixed(3)}</>
                          )}
                        </td>
                      </tr>
                    )}
                  </>
                );
              })}
            </tbody>
          </table>
        </>
      )}

      {modivLast && isPresent(modivLast.date) && sales.length === 0 && (
        <div class="pd-callout" style="margin-top:0.8rem">
          <strong>MOD-IV last-recorded:</strong> {date(modivLast.date)} ·{' '}
          {money(modivLast.price)} · NU {modivLast.nu_code || '—'} · deed{' '}
          {joinPresent([modivLast.deed_book, modivLast.deed_page]) || '—'}
        </div>
      )}
    </section>
  );
}
