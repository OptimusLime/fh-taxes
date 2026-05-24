/** @jsxImportSource preact */
// Deck shell — keyboard nav, dots, counter. Loads slide components from
// slides.tsx. State is local; URL hash mirrors current slide for shareable
// links (e.g. /purpose#05).

import { useEffect, useState, useCallback } from 'preact/hooks';
import { SLIDES } from './slides';

function parseHashIndex(): number {
  if (typeof window === 'undefined') return 0;
  const m = /^#(\d+)/.exec(window.location.hash);
  if (!m) return 0;
  const n = parseInt(m[1], 10) - 1;
  if (!Number.isFinite(n)) return 0;
  return Math.max(0, Math.min(SLIDES.length - 1, n));
}

export default function Deck() {
  const last = SLIDES.length - 1;
  const [i, setI] = useState<number>(0);

  useEffect(() => { setI(parseHashIndex()); }, []);

  const go = useCallback(
    (delta: number) => setI((x) => Math.max(0, Math.min(last, x + delta))),
    [last]
  );
  const jump = useCallback(
    (n: number) => setI(Math.max(0, Math.min(last, n))),
    [last]
  );

  useEffect(() => {
    // Mirror to URL hash (1-indexed for human-readability)
    if (typeof window !== 'undefined') {
      const want = '#' + String(i + 1).padStart(2, '0');
      if (window.location.hash !== want) {
        history.replaceState(null, '', want);
      }
    }
  }, [i]);

  useEffect(() => {
    const h = (e: KeyboardEvent) => {
      // Don't steal keys from form fields
      const t = e.target as HTMLElement | null;
      if (t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.isContentEditable)) return;
      switch (e.key) {
        case 'ArrowRight':
        case 'PageDown':
        case ' ':
          e.preventDefault(); go(1); break;
        case 'ArrowLeft':
        case 'PageUp':
          e.preventDefault(); go(-1); break;
        case 'Home':
          e.preventDefault(); jump(0); break;
        case 'End':
          e.preventDefault(); jump(last); break;
      }
    };
    window.addEventListener('keydown', h);
    return () => window.removeEventListener('keydown', h);
  }, [go, jump, last]);

  const Slide = SLIDES[i].Component;

  return (
    <div class="p-stage">
      <div class="p-chrome">
        <div class="p-chrome-title">Fair for Fair Haven</div>
        <div class="p-chrome-counter">
          {String(i + 1).padStart(2, '0')} / {String(SLIDES.length).padStart(2, '0')}
        </div>
      </div>

      <Slide />

      <div class="p-nav">
        <button
          class="p-nav-btn"
          onClick={() => go(-1)}
          disabled={i === 0}
          aria-label="Previous slide"
        >
          ← Prev
        </button>
        <div class="p-dots" role="tablist" aria-label="Slide navigator">
          {SLIDES.map((s, idx) => (
            <button
              class={`p-dot ${idx === i ? 'p-dot--current' : ''}`}
              onClick={() => jump(idx)}
              title={`${idx + 1}. ${s.title}`}
              aria-label={`Slide ${idx + 1}: ${s.title}`}
              aria-current={idx === i ? 'true' : undefined}
            />
          ))}
        </div>
        <button
          class="p-nav-btn"
          onClick={() => go(1)}
          disabled={i === last}
          aria-label="Next slide"
        >
          Next →
        </button>
      </div>
    </div>
  );
}
