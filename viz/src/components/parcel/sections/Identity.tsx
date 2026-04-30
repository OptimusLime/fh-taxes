/** @jsxImportSource preact */
import { isPresent, joinPresent } from '../format';

type Props = { identity: Record<string, any>; lot: Record<string, any> };

export default function Identity({ identity, lot }: Props) {
  const rows: [string, any][] = [
    ['Block / Lot / Qual', joinPresent([identity?.block, identity?.lot, identity?.qualifier])],
    ['Owner mailing', identity?.owner_mailing_address],
    ['Map page', identity?.map_page],
    ['Lot description', lot?.land_desc],
    [
      'Acreage',
      isPresent(lot?.lot_size_acres) ? Number(lot.lot_size_acres).toFixed(3) : null,
    ],
    [
      'Polygon area',
      isPresent(lot?.shape_area_sqft)
        ? `${Number(lot.shape_area_sqft).toLocaleString('en-US', { maximumFractionDigits: 0 })} sf`
        : null,
    ],
  ].filter(([_, v]) => isPresent(v));

  return (
    <section class="pd-section">
      <h2 class="pd-section-title">Identity & Lot</h2>
      <dl class="pd-stat-grid">
        {rows.map(([k, v]) => (
          <>
            <dt>{k}</dt>
            <dd>{String(v)}</dd>
          </>
        ))}
      </dl>
    </section>
  );
}
