/** @jsxImportSource preact */
type Props = { flags: string[] };

const FLAG_LABELS: Record<string, string> = {
  missing_condition: 'Missing condition grade',
  missing_bedrooms: 'Missing bedroom count',
  missing_bathrooms: 'Missing bathroom count',
  missing_livable_area: 'Missing livable area',
  missing_year_built: 'Missing year built',
};

export default function DataQuality({ flags }: Props) {
  if (!flags || flags.length === 0) return null;
  return (
    <section class="pd-section">
      <h2 class="pd-section-title">Data Quality</h2>
      <p class="pd-section-subtitle">
        Validation gate (Plan 1) flagged the following issues for this parcel.
      </p>
      <div class="pd-badges">
        {flags.map((f) => (
          <span class="pd-badge warn">{FLAG_LABELS[f] || f}</span>
        ))}
      </div>
    </section>
  );
}
