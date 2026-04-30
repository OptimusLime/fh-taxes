/** @jsxImportSource preact */
import { isPresent } from '../format';

type Props = {
  pin: string;
  identity: Record<string, any>;
};

export default function Header({ pin, identity }: Props) {
  const title = identity?.property_location || pin;
  const subtitleParts = [pin];
  if (identity?.block || identity?.lot) {
    subtitleParts.push(`block ${identity.block ?? '—'} · lot ${identity.lot ?? '—'}`);
  }
  if (identity?.qualifier) subtitleParts.push(`qual ${identity.qualifier}`);

  const badges: { label: string; cls: string }[] = [];
  if (identity?.zone) badges.push({ label: `Zone ${identity.zone}`, cls: 'accent' });
  if (identity?.property_class) badges.push({ label: `Class ${identity.property_class}`, cls: 'neutral' });
  if (identity?.bldg_class) badges.push({ label: `Bldg cls ${identity.bldg_class}`, cls: 'neutral' });
  if (identity?.waterfront) badges.push({ label: '🌊 Waterfront', cls: 'good' });
  if (identity?.district) badges.push({ label: `District ${identity.district}`, cls: 'neutral' });

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
