/** @jsxImportSource preact */
import Header from './sections/Header';
import Identity from './sections/Identity';
import Building from './sections/Building';
import Assessment from './sections/Assessment';
import TaxContext from './sections/TaxContext';
import Sales from './sections/Sales';
import History from './sections/History';
import DataQuality from './sections/DataQuality';

export type ParcelRecord = {
  identity: Record<string, any>;
  lot_geometry: Record<string, any>;
  building: Record<string, any>;
  current_assessment: Record<string, any>;
  sales_history: Array<Record<string, any>>;
  unified_sales?: Array<Record<string, any>>;
  modiv_last_sale: Record<string, any>;
  history: Array<Record<string, any>>;
  data_quality_flags: string[];
  renovations?: {
    tier: 'high' | 'medium' | 'low' | 'weak';
    confidence: number;
    signals: string[];
    first_event_year: number | null;
    last_event_year: number | null;
    events: Array<Record<string, any>>;
  } | null;
  cohort?: { cohort?: string; tags?: string[]; latest_arms_length_year?: number | null };
};

export type Aggregates = {
  total_parcels: number;
  parcels_with_tax_data: number;
  total_tax_pool: number;
  total_assessed_value: number;
  cohorts: Array<any>;
} | null;

type Props = {
  pin: string;
  record: ParcelRecord;
  variant?: 'page' | 'drawer';
  aggregates?: Aggregates;
};

export default function ParcelDetail({ pin, record, variant = 'page', aggregates = null }: Props) {
  const cls = variant === 'drawer' ? 'pd pd-drawer' : 'pd pd-page';
  return (
    <article class={cls}>
      <Header pin={pin} identity={record.identity} cohort={record.cohort} />
      <Assessment ca={record.current_assessment} renovations={record.renovations as any} />
      <TaxContext
        parcelCohort={record.cohort?.cohort || 'unknown'}
        parcelTax={record.current_assessment?.last_year_tax}
        parcelAssessed={record.current_assessment?.net_value}
        aggregates={aggregates}
        nonArmsOnly={(record.cohort as any)?.non_arms_only}
      />
      <Identity identity={record.identity} lot={record.lot_geometry} />
      <Building building={record.building} />
      <Sales unifiedSales={(record.unified_sales || []) as any} modivLast={record.modiv_last_sale} />
      <History history={record.history as any} />
      <DataQuality flags={record.data_quality_flags || []} />
    </article>
  );
}
