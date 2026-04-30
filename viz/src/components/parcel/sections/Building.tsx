/** @jsxImportSource preact */
import { isPresent, intRound, num, sqft, joinPresent } from '../format';

type Props = { building: Record<string, any> };

export default function Building({ building: b }: Props) {
  if (!b) return null;
  const heroes = [
    { label: 'Bedrooms', value: isPresent(b.bedrooms) ? intRound(b.bedrooms) : '—' },
    { label: 'Bathrooms', value: isPresent(b.bathrooms) ? intRound(b.bathrooms) : '—' },
    { label: 'Livable sf', value: isPresent(b.livable_area) ? num(b.livable_area) : '—' },
  ];

  const detail: [string, any][] = [
    ['Year built', isPresent(b.year_built) ? intRound(b.year_built) : null],
    ['Effective age', isPresent(b.eff_age) ? `${intRound(b.eff_age)} yr` : null],
    ['Building code', b.bldg_desc],
    ['Style', b.style_code],
    ['Total rooms', isPresent(b.room_count) ? intRound(b.room_count) : null],
    ['Kitchens', isPresent(b.kitchens) ? intRound(b.kitchens) : null],
    ['Fireplaces', isPresent(b.fireplaces) ? intRound(b.fireplaces) : null],
    [
      'Story breakdown',
      joinPresent(
        [
          isPresent(b.first_story_sf) ? `1st ${num(b.first_story_sf)} sf` : null,
          isPresent(b.upper_story_sf) ? `upper ${num(b.upper_story_sf)} sf` : null,
          isPresent(b.half_story_sf) ? `½ ${num(b.half_story_sf)} sf` : null,
        ],
        ' · '
      ),
    ],
    ['Condition', b.condition],
    ['Quality grade', b.quality_grade],
    ['Foundation', b.foundation],
    ['Exterior', b.exterior],
    ['Roof', joinPresent([b.roof_type, b.roof_material])],
    ['Heating', joinPresent([b.heating_type, isPresent(b.heating_sf) ? sqft(b.heating_sf) : null], ' · ')],
    ['AC', joinPresent([b.ac_type, isPresent(b.ac_sf) ? sqft(b.ac_sf) : null], ' · ')],
    ['Garage', joinPresent([b.garage_type, isPresent(b.garage_sf) ? sqft(b.garage_sf) : null], ' · ')],
    ['Porch', isPresent(b.porch_sf) ? sqft(b.porch_sf) : null],
    ['Patio', isPresent(b.patio_sf) ? sqft(b.patio_sf) : null],
    ['Shed', isPresent(b.shed_sf) ? sqft(b.shed_sf) : null],
    ['Sewer / Water', joinPresent([b.sewer, b.water])],
    ['Topography / Road', joinPresent([b.topography, b.road_type])],
    ['Dwellings', isPresent(b.dwellings) ? intRound(b.dwellings) : null],
  ].filter(([_, v]) => isPresent(v));

  return (
    <section class="pd-section">
      <h2 class="pd-section-title">Building</h2>
      <div class="pd-hero">
        {heroes.map((h) => (
          <div class="pd-hero-cell">
            <div class="pd-hero-num">{h.value}</div>
            <div class="pd-hero-label">{h.label}</div>
          </div>
        ))}
      </div>
      <dl class="pd-stat-grid">
        {detail.map(([k, v]) => (
          <>
            <dt>{k}</dt>
            <dd>{String(v)}</dd>
          </>
        ))}
      </dl>
    </section>
  );
}
