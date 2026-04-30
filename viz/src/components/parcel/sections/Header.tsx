/** @jsxImportSource preact */
import { isPresent } from '../format';

type Props = {
  pin: string;
  identity: Record<string, any>;
  cohort?: { cohort?: string; tags?: string[]; latest_arms_length_year?: number | null };
};

const COHORT_LABEL: Record<string, string> = {
  never_sold: '🌳 Never sold (since 1989)',
  tenure_pre_2015: 'Tenure: Pre-2015',
  tenure_2015_2019: 'Tenure: 2015–2019',
  tenure_pandemic_2020_2022: 'Tenure: Pandemic (2020–22)',
  tenure_post_pandemic_2023plus: 'Tenure: Post-pandemic (2023+)',
};

export default function Header({ pin, identity, cohort }: Props) {
  const title = identity?.property_location || pin;
  const subtitleParts = [pin];
  if (identity?.block || identity?.lot) {
    subtitleParts.push(`block ${identity.block ?? '—'} · lot ${identity.lot ?? '—'}`);
  }
  if (identity?.qualifier) subtitleParts.push(`qual ${identity.qualifier}`);
  if (cohort?.latest_arms_length_year) {
    subtitleParts.push(`last arms-length sale ${cohort.latest_arms_length_year}`);
  } else if (cohort?.cohort === 'never_sold') {
    subtitleParts.push('no arms-length sale on record (since 1989)');
  }

  const badges: { label: string; cls: string }[] = [];
  if (cohort?.cohort && COHORT_LABEL[cohort.cohort]) {
    badges.push({ label: COHORT_LABEL[cohort.cohort], cls: 'accent' });
  }
  if (identity?.zone) badges.push({ label: `Zone ${identity.zone}`, cls: 'neutral' });
  if (identity?.property_class) badges.push({ label: `Class ${identity.property_class}`, cls: 'neutral' });
  if (identity?.bldg_class) badges.push({ label: `Bldg cls ${identity.bldg_class}`, cls: 'neutral' });
  if (identity?.waterfront) badges.push({ label: '🌊 Waterfront', cls: 'good' });

  return (
    <header class="pd-header">
      <div class="pd-header-eyebrow">Property Record</div>
      <h1 class="pd-title">{title}</h1>
      <p class="pd-subtitle">{subtitleParts.filter(isPresent).join(' · ')}</p>
      <div class="pd-badges">
        {badges.map((b) => (
          <span class={`pd-badge ${b.cls}`}>{b.label}</span>
        ))}
      </div>
    </header>
  );
}
