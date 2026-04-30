/** @jsxImportSource preact */
import { money, date, isPresent, joinPresent, yesNo } from '../format';

type Sale = {
  sale_date?: string;
  sale_price?: number;
  nu_code?: string;
  deed_book?: string;
  deed_page?: string;
  grantor?: string;
  grantee?: string;
  family_sale_flag?: boolean;
  sales_ratio_assessor?: number;
};

type Props = {
  sales: Sale[];
  modivLast: Record<string, any>;
};

export default function Sales({ sales, modivLast }: Props) {
  const hasSales = Array.isArray(sales) && sales.length > 0;
  const hasModiv = modivLast && isPresent(modivLast.date);

  return (
    <section class="pd-section">
      <h2 class="pd-section-title">Sales History</h2>
      <p class="pd-section-subtitle">SR1A 2018-2025 enriched with sr.cgi grantor/grantee.</p>

      {hasSales ? (
        <table class="pd-table">
          <thead>
            <tr>
              <th>Date</th>
              <th class="num">Price</th>
              <th>NU</th>
              <th>Deed</th>
              <th>Family?</th>
            </tr>
          </thead>
          <tbody>
            {sales.map((s) => (
              <>
                <tr class="sale-row">
                  <td>{date(s.sale_date)}</td>
                  <td class="num">{money(s.sale_price)}</td>
                  <td>{s.nu_code || '—'}</td>
                  <td class="deed">{joinPresent([s.deed_book, s.deed_page]) || '—'}</td>
                  <td>{s.family_sale_flag ? '⚠ yes' : 'no'}</td>
                </tr>
                {(s.grantor || s.grantee) && (
                  <tr>
                    <td colSpan={5} style="font-size:0.72rem;color:var(--pd-muted);padding-left:1rem">
                      {s.grantor && (
                        <>
                          <span class="pd-key">grantor</span> {s.grantor}
                        </>
                      )}
                      {s.grantor && s.grantee && ' → '}
                      {s.grantee && (
                        <>
                          <span class="pd-key">grantee</span> {s.grantee}
                        </>
                      )}
                      {isPresent(s.sales_ratio_assessor) && (
                        <>
                          {' · '}
                          <span class="pd-key">assessor ratio</span> {Number(s.sales_ratio_assessor).toFixed(3)}
                        </>
                      )}
                    </td>
                  </tr>
                )}
              </>
            ))}
          </tbody>
        </table>
      ) : (
        <div class="pd-empty">No arms-length sales 2018-2025 on record.</div>
      )}

      {hasModiv && (
        <div class="pd-callout" style="margin-top:0.8rem">
          <strong>MOD-IV last-recorded sale:</strong> {date(modivLast.date)} ·{' '}
          {money(modivLast.price)} · NU {modivLast.nu_code || '—'} · deed{' '}
          {joinPresent([modivLast.deed_book, modivLast.deed_page]) || '—'}
        </div>
      )}
    </section>
  );
}
