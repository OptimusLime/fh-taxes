/** @jsxImportSource preact */
import Header from './sections/Header';
import Identity from './sections/Identity';
import Building from './sections/Building';
import Assessment from './sections/Assessment';
import Sales from './sections/Sales';
import History from './sections/History';
import DataQuality from './sections/DataQuality';

export type ParcelRecord = {
  identity: Record<string, any>;
  lot_geometry: Record<string, any>;
  building: Record<string, any>;
  current_assessment: Record<string, any>;
  sales_history: Array<Record<string, any>>;
  modiv_last_sale: Record<string, any>;
  history: Array<Record<string, any>>;
  data_quality_flags: string[];
};

type Props = {
  pin: string;
  record: ParcelRecord;
  variant?: 'page' | 'drawer';
};

export default function ParcelDetail({ pin, record, variant = 'page' }: Props) {
  const cls = variant === 'drawer' ? 'pd pd-drawer' : 'pd pd-page';
  return (
    <article class={cls}>
      <Header pin={pin} identity={record.identity} />
      <Identity identity={record.identity} lot={record.lot_geometry} />
      <Building building={record.building} />
      <Assessment ca={record.current_assessment} />
      <Sales sales={record.sales_history} modivLast={record.modiv_last_sale} />
      <History history={record.history as any} />
      <DataQuality flags={record.data_quality_flags || []} />
    </article>
  );
}
