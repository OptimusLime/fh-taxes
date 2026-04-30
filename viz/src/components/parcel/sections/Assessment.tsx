/** @jsxImportSource preact */
import { money, pct, isPresent, deltaPct } from '../format';

type Props = { ca: Record<string, any> };

export default function Assessment({ ca }: Props) {
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
