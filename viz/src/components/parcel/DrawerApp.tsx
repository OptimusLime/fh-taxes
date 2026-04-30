/** @jsxImportSource preact */
import { useEffect, useState } from 'preact/hooks';
import ParcelDetail, { type ParcelRecord, type Aggregates } from './ParcelDetail';

type State =
  | { kind: 'idle' }
  | { kind: 'loading'; pin: string }
  | { kind: 'ready'; pin: string; record: ParcelRecord }
  | { kind: 'missing'; pin: string }
  | { kind: 'error'; pin: string; message: string };

let cache: Record<string, ParcelRecord> | null = null;
let inflight: Promise<Record<string, ParcelRecord>> | null = null;
let aggCache: Aggregates = null;
let aggInflight: Promise<Aggregates> | null = null;

function loadAll(): Promise<Record<string, ParcelRecord>> {
  if (cache) return Promise.resolve(cache);
  if (!inflight) {
    inflight = fetch('/data/parcels_full.json')
      .then((r) => {
        if (!r.ok) throw new Error(`parcels_full.json HTTP ${r.status}`);
        return r.json();
      })
      .then((data: Record<string, ParcelRecord>) => {
        cache = data;
        return data;
      });
  }
  return inflight;
}

function loadAggregates(): Promise<Aggregates> {
  if (aggCache) return Promise.resolve(aggCache);
  if (!aggInflight) {
    aggInflight = fetch('/data/town_aggregates.json')
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        aggCache = data;
        return data;
      })
      .catch(() => null);
  }
  return aggInflight;
}

export default function DrawerApp() {
  const [state, setState] = useState<State>({ kind: 'idle' });
  const [agg, setAgg] = useState<Aggregates>(null);

  useEffect(() => {
    const onSelect = (ev: Event) => {
      const ce = ev as CustomEvent<{ pin: string }>;
      const pin = ce.detail?.pin;
      if (!pin) return;
      document.getElementById('layout')?.classList.add('drawer-open');
      document.getElementById('drawer')?.setAttribute('aria-hidden', 'false');
      setState({ kind: 'loading', pin });
      loadAll()
        .then((data) => {
          const r = data[pin];
          if (r) setState({ kind: 'ready', pin, record: r });
          else setState({ kind: 'missing', pin });
        })
        .catch((e: Error) => setState({ kind: 'error', pin, message: e.message }));
    };

    const onClose = () => {
      document.getElementById('layout')?.classList.remove('drawer-open');
      document.getElementById('drawer')?.setAttribute('aria-hidden', 'true');
    };

    window.addEventListener('parcel:select', onSelect);
    document.getElementById('drawer-close')?.addEventListener('click', onClose);
    // Pre-warm caches so first click is instant.
    loadAll().catch(() => {});
    loadAggregates().then((a) => setAgg(a)).catch(() => {});
    return () => {
      window.removeEventListener('parcel:select', onSelect);
      document.getElementById('drawer-close')?.removeEventListener('click', onClose);
    };
  }, []);

  switch (state.kind) {
    case 'idle':
      return (
        <div class="pd pd-drawer">
          <div class="pd-empty">
            Click any parcel on the map to see its full assessment record.
          </div>
        </div>
      );
    case 'loading':
      return (
        <div class="pd pd-drawer">
          <div class="pd-empty">Loading {state.pin}…</div>
        </div>
      );
    case 'ready':
      return <ParcelDetail pin={state.pin} record={state.record} variant="drawer" aggregates={agg} />;
    case 'missing':
      return (
        <div class="pd pd-drawer">
          <div class="pd-empty">No record found for {state.pin}.</div>
        </div>
      );
    case 'error':
      return (
        <div class="pd pd-drawer">
          <div class="pd-empty" style="color:var(--pd-bad)">
            Error: {state.message}
          </div>
        </div>
      );
  }
}
