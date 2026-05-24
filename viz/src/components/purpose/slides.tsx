/** @jsxImportSource preact */
// Fair for Fair Haven — slide deck content.
//
// Each slide is a self-contained Preact component rendered by Deck.tsx.
// All visual tokens live in viz/src/styles/purpose-brand.css; this file
// composes them. Word count per slide is intentionally minimal — leaves
// room for imagery. Inline SVGs use brand pastels for synthetic artwork.

import ImageSlot from './ImageSlot';

type Accent = 'petal' | 'bloom' | 'sky' | 'leaf' | 'plum' | 'blush';

export type SlideDef = {
  id: string;
  title: string;
  accent: Accent;
  Component: () => any;
};

const accentStyle = (a: Accent) => ({ '--p-accent': `var(--p-${a})` } as any);

// --- Inline SVG helpers (brand-consistent, flat, thick strokes) ---

function LineChart({ points, color, w = 280, h = 160, fill }: {
  points: number[]; color: string; w?: number; h?: number; fill?: string;
}) {
  const max = Math.max(...points);
  const min = Math.min(...points);
  const range = max - min || 1;
  const pad = 20;
  const iw = w - pad * 2;
  const ih = h - pad * 2;
  const pts = points.map((v, i) => {
    const x = pad + (i / (points.length - 1)) * iw;
    const y = pad + ih - ((v - min) / range) * ih;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });
  const pathD = pts.map((p, i) => `${i === 0 ? 'M' : 'L'}${p}`).join(' ');
  const fillD = fill ? `${pathD} L${pad + iw},${pad + ih} L${pad},${pad + ih} Z` : undefined;
  return (
    <svg viewBox={`0 0 ${w} ${h}`} style="width:100%;height:auto;max-height:200px">
      {fill && fillD && <path d={fillD} fill={fill} opacity="0.3" />}
      <path d={pathD} fill="none" stroke={color} stroke-width="4" stroke-linecap="round" stroke-linejoin="round" />
    </svg>
  );
}

function FlowerSVG({ size = 80, color = 'var(--p-petal)' }: { size?: number; color?: string }) {
  const r = size / 2;
  const petalR = r * 0.38;
  const petals = Array.from({ length: 6 }, (_, i) => {
    const angle = (i / 6) * Math.PI * 2;
    const cx = r + Math.cos(angle) * r * 0.45;
    const cy = r + Math.sin(angle) * r * 0.45;
    return <ellipse cx={cx} cy={cy} rx={petalR} ry={petalR * 0.7} fill={color} stroke="var(--p-ink)" stroke-width="2.5"
      transform={`rotate(${(i * 60) + 30} ${cx} ${cy})`} />;
  });
  return (
    <svg viewBox={`0 0 ${size} ${size}`} style={`width:${size}px;height:${size}px`}>
      {petals}
      <circle cx={r} cy={r} r={r * 0.2} fill="var(--p-bloom)" stroke="var(--p-ink)" stroke-width="2.5" />
    </svg>
  );
}

function DonutSplit({ a, b, colorA, colorB, size = 140 }: {
  a: number; b: number; colorA: string; colorB: string; size?: number;
}) {
  const r = size / 2;
  const inner = r * 0.55;
  const total = a + b;
  const angA = (a / total) * Math.PI * 2;
  const x1 = r + r * Math.cos(-Math.PI / 2);
  const y1 = r + r * Math.sin(-Math.PI / 2);
  const x2 = r + r * Math.cos(-Math.PI / 2 + angA);
  const y2 = r + r * Math.sin(-Math.PI / 2 + angA);
  const ix2 = r + inner * Math.cos(-Math.PI / 2 + angA);
  const iy2 = r + inner * Math.sin(-Math.PI / 2 + angA);
  const ix1 = r + inner * Math.cos(-Math.PI / 2);
  const iy1 = r + inner * Math.sin(-Math.PI / 2);
  const large = angA > Math.PI ? 1 : 0;
  const pathA = `M${x1},${y1} A${r},${r} 0 ${large} 1 ${x2},${y2} L${ix2},${iy2} A${inner},${inner} 0 ${large} 0 ${ix1},${iy1} Z`;
  return (
    <svg viewBox={`0 0 ${size} ${size}`} style={`width:${size}px;height:${size}px`}>
      <circle cx={r} cy={r} r={r} fill={colorB} stroke="var(--p-ink)" stroke-width="3" />
      <circle cx={r} cy={r} r={inner} fill="var(--p-paper)" stroke="var(--p-ink)" stroke-width="3" />
      <path d={pathA} fill={colorA} stroke="var(--p-ink)" stroke-width="3" />
    </svg>
  );
}

function FlowerRow({ count = 5 }: { count?: number }) {
  const colors = ['var(--p-petal)', 'var(--p-bloom)', 'var(--p-plum)', 'var(--p-leaf)', 'var(--p-sky)'];
  return (
    <div style="display:flex;gap:0.8rem;align-items:center;flex-wrap:wrap">
      {Array.from({ length: count }, (_, i) => (
        <FlowerSVG size={48} color={colors[i % colors.length]} />
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// 01 — Cover
// ---------------------------------------------------------------------------
function Slide01Cover() {
  return (
    <section class="p-slide p-slide--split" style={accentStyle('petal')}>
      <div class="p-cover" style={accentStyle('petal')}>
        <div class="p-cover-text">
          <div>
            <div class="p-tag">A vision · 2026</div>
          </div>
          <div>
            <h1 class="p-hero">Fair for<br />Fair Haven</h1>
            <p class="p-body" style="margin-top:1.2rem;font-size:1.2rem;max-width:28ch">
              Bloom in the dark times.
            </p>
          </div>
          <FlowerRow count={6} />
        </div>
        <div class="p-cover-art" style="align-items:center;justify-content:center">
          <svg viewBox="0 0 300 300" style="width:100%;max-width:280px;height:auto">
            {/* Large cherry blossom tree silhouette */}
            <rect x="140" y="180" width="20" height="100" fill="var(--p-ink)" rx="0" />
            {[[-30,-40],[30,-40],[0,-70],[-50,-20],[50,-20],[-20,-60],[20,-60],[0,-30],[-40,-50],[40,-50]].map(([dx, dy], i) => (
              <circle cx={150 + dx} cy={140 + dy} r={28 + (i % 3) * 4} fill="var(--p-petal)" stroke="var(--p-ink)" stroke-width="3" opacity={0.85} />
            ))}
            <rect x="0" y="275" width="300" height="25" fill="var(--p-leaf)" stroke="var(--p-ink)" stroke-width="3" />
          </svg>
        </div>
      </div>
    </section>
  );
}

// ---------------------------------------------------------------------------
// 02 — The mood
// ---------------------------------------------------------------------------
function Slide02Mood() {
  const declining = [100, 97, 92, 88, 82, 78, 71, 65, 60, 55, 50, 46];
  return (
    <section class="p-slide" style={accentStyle('blush')}>
      <div class="p-eyebrow">Where we are</div>
      <div class="p-row">
        <div class="p-col" style="justify-content:center">
          <h2 class="p-hero">Everyone's<br />sour.</h2>
          <p class="p-body">
            Money is tight. The line points down. The country feels like the 70s.
            And that feeling — that the line keeps pointing down forever — is the
            feeling that gets people most wrong.
          </p>
        </div>
        <div class="p-col" style="justify-content:center;align-items:center">
          <div class="p-panel" style="padding:1.5rem;align-items:center">
            <LineChart points={declining} color="var(--p-ink)" fill="var(--p-blush)" />
            <p style="font-family:var(--p-font-display);font-size:0.75rem;text-transform:uppercase;letter-spacing:0.1em;color:var(--p-muted);margin:0.5rem 0 0">The feeling</p>
          </div>
        </div>
      </div>
    </section>
  );
}

// ---------------------------------------------------------------------------
// 03 — Two views
// ---------------------------------------------------------------------------
function Slide03TwoViews() {
  const down = [90, 85, 78, 70, 60, 50, 42, 35, 28, 22];
  const up = [30, 28, 25, 22, 24, 30, 40, 55, 72, 90];
  return (
    <section class="p-slide p-slide--split">
      <div class="p-grid-2">
        <div style={{ background: 'var(--p-sky)' }}>
          <div class="p-tag">View one</div>
          <h2 class="p-title">It all<br />crashes.</h2>
          <LineChart points={down} color="var(--p-ink)" w={240} h={120} />
          <p class="p-body">The line points down — forever.</p>
        </div>
        <div style={{ background: 'var(--p-leaf)' }}>
          <div class="p-tag">View two</div>
          <h2 class="p-title">The line<br />points up.</h2>
          <LineChart points={up} color="var(--p-ink)" fill="var(--p-leaf)" w={240} h={120} />
          <p class="p-body">Eventually. Always.</p>
        </div>
      </div>
    </section>
  );
}

// ---------------------------------------------------------------------------
// 04 — Optimism pays
// ---------------------------------------------------------------------------
function Slide04OptimismPays() {
  // Stylized long-run chart: dips that always recover higher
  const longRun = [20, 30, 25, 40, 35, 55, 45, 60, 50, 70, 65, 80, 72, 90, 85, 100];
  return (
    <section class="p-slide" style={accentStyle('bloom')}>
      <div class="p-eyebrow">The pattern</div>
      <div class="p-row" style="align-items:stretch">
        <div class="p-col" style="justify-content:center;flex:1.2">
          <h2 class="p-title">Optimism pays<br />the longest<br />dividend.</h2>
          <p class="p-body">
            History rewards the people who believed the line could point up
            <em> while</em> it was pointing down. Every time. Across every
            generation.
          </p>
        </div>
        <div class="p-col" style="justify-content:center;align-items:center">
          <div class="p-panel" style="padding:1.5rem;align-items:center">
            <LineChart points={longRun} color="var(--p-ink)" fill="var(--p-bloom)" w={260} h={160} />
            <p style="font-family:var(--p-font-display);font-size:0.7rem;text-transform:uppercase;letter-spacing:0.1em;color:var(--p-muted);margin:0.5rem 0 0">Long run · always up</p>
          </div>
        </div>
      </div>
    </section>
  );
}

// ---------------------------------------------------------------------------
// 05 — Music in the dark (Brecht)
// ---------------------------------------------------------------------------
function Slide05Brecht() {
  return (
    <section class="p-slide" style={accentStyle('plum')}>
      <div class="p-eyebrow">Borrowed wisdom</div>
      <div class="p-row" style="align-items:center;justify-content:center">
        <div style="max-width:30ch">
          <p class="p-quote">
            "In the dark times,<br />will there also be singing?<br /><br />
            Yes. There will also be singing.<br />
            <span style="background:var(--p-bloom);padding:0 6px">About the dark times.</span>"
          </p>
          <p class="p-attribution">— Bertolt Brecht, 1939</p>
        </div>
        <div style="margin-left:var(--p-gap);display:flex;flex-direction:column;gap:1rem;align-items:center">
          <FlowerSVG size={100} color="var(--p-plum)" />
          <FlowerSVG size={60} color="var(--p-petal)" />
        </div>
      </div>
    </section>
  );
}

// ---------------------------------------------------------------------------
// 06 — 2009 buyers
// ---------------------------------------------------------------------------
function Slide06_2009() {
  // Stylized NJ home price index: 2006 peak → 2009 trough → 2025 recovery
  const homePrice = [100, 98, 92, 72, 68, 66, 65, 67, 70, 74, 78, 82, 88, 95, 108, 125, 145, 160, 170, 180];
  return (
    <section class="p-slide" style={accentStyle('leaf')}>
      <div class="p-eyebrow">A worked example</div>
      <div class="p-row">
        <div class="p-col" style="justify-content:center;flex:1.1">
          <h2 class="p-title">Be 2009 buyers.<br />Not 2009 sellers.</h2>
          <p class="p-body">
            After 2008, everyone thought real estate was dead. The people who
            bought in 2009 are doing far better than the people who sold.
          </p>
          <p class="p-body">
            <strong>Fair Haven is in a 2009 moment.</strong> Invest as if the down
            didn't exist. One day it won't.
          </p>
        </div>
        <div class="p-col" style="justify-content:center;align-items:center">
          <div class="p-panel" style="padding:1.2rem;align-items:center;gap:0.4rem">
            <p style="font-family:var(--p-font-display);font-size:0.7rem;text-transform:uppercase;letter-spacing:0.1em;color:var(--p-muted);margin:0">Home prices · 2006–2025</p>
            <LineChart points={homePrice} color="var(--p-ink)" fill="var(--p-leaf)" w={240} h={140} />
            <div style="display:flex;gap:1rem;font-size:0.72rem;font-family:var(--p-font-display);letter-spacing:0.06em">
              <span>← 2008 crash</span>
              <span style="color:var(--p-muted)">recovery →</span>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

// ---------------------------------------------------------------------------
// 07 — Flower Power returns (meme)
// ---------------------------------------------------------------------------
function Slide07FlowerPower() {
  return (
    <section class="p-slide" style={accentStyle('petal')}>
      <div class="p-row" style="align-items:stretch">
        <div class="p-col" style="justify-content:center;flex:1.1">
          <div class="p-tag" style="background:var(--p-bloom)">Meme break</div>
          <h2 class="p-hero" style="font-size:clamp(2.5rem,6vw,5rem)">
            Somehow,<br />
            <span style="background:var(--p-bloom);padding:0 8px">Flower Power</span><br />
            has returned.
          </h2>
        </div>
        <div class="p-col" style="justify-content:center;align-items:center;gap:1rem">
          {/* Flower crown arrangement */}
          <svg viewBox="0 0 200 120" style="width:100%;max-width:240px;height:auto">
            {[
              [30, 50, 'var(--p-petal)'], [60, 30, 'var(--p-bloom)'], [100, 20, 'var(--p-plum)'],
              [140, 30, 'var(--p-leaf)'], [170, 50, 'var(--p-sky)'],
              [50, 70, 'var(--p-bloom)'], [80, 55, 'var(--p-petal)'], [120, 55, 'var(--p-leaf)'], [150, 70, 'var(--p-plum)'],
            ].map(([cx, cy, fill]) => (
              <g>
                <circle cx={cx as number} cy={cy as number} r={16} fill={fill as string} stroke="var(--p-ink)" stroke-width="2.5" />
                <circle cx={cx as number} cy={cy as number} r={5} fill="var(--p-bloom)" stroke="var(--p-ink)" stroke-width="1.5" />
              </g>
            ))}
            <path d="M25,85 Q100,95 175,85" fill="none" stroke="var(--p-ink)" stroke-width="3" stroke-linecap="round" />
          </svg>
          <ImageSlot label="Palpatine 'somehow returned' — drop your own image" />
        </div>
      </div>
    </section>
  );
}

// ---------------------------------------------------------------------------
// 08 — Who lives here (50/50)
// ---------------------------------------------------------------------------
function Slide08WhoLives() {
  return (
    <section class="p-slide" style={accentStyle('sky')}>
      <div class="p-eyebrow">Who's here now</div>
      <div class="p-row" style="align-items:center">
        <div class="p-col" style="flex:1.4;justify-content:center;gap:0.4rem">
          <h2 class="p-stat">50/50</h2>
          <p class="p-body" style="margin-top:0.6rem">
            Half here pre-2015. Half here since. Millennials buying the houses
            they grew up in. New families chasing the schools.
          </p>
        </div>
        <div class="p-col" style="justify-content:center;align-items:center;gap:1rem">
          <DonutSplit a={50} b={50} colorA="var(--p-bloom)" colorB="var(--p-sky)" size={160} />
          <div style="display:flex;gap:1rem;font-size:0.78rem;font-family:var(--p-font-display);letter-spacing:0.06em;text-transform:uppercase">
            <span><span style="display:inline-block;width:12px;height:12px;background:var(--p-bloom);border:2px solid var(--p-ink);margin-right:4px;vertical-align:middle"></span>Pre-2015</span>
            <span><span style="display:inline-block;width:12px;height:12px;background:var(--p-sky);border:2px solid var(--p-ink);margin-right:4px;vertical-align:middle"></span>Post-2015</span>
          </div>
        </div>
      </div>
    </section>
  );
}

// ---------------------------------------------------------------------------
// 09 — Schools: invest, don't austerity
// ---------------------------------------------------------------------------
function Slide09Schools() {
  return (
    <section class="p-slide" style={accentStyle('leaf')}>
      <div class="p-eyebrow">The next ten years · 1 of 4</div>
      <div class="p-row">
        <div class="p-col" style="justify-content:center;flex:1.2">
          <h2 class="p-title">Invest.<br />Don't austerity.</h2>
          <p class="p-body">
            When other towns pull back, we <strong>quadruple down</strong> on the
            public school. Montessori-forward in the early grades. Accelerated
            STEM by third. Best-in-class in Monmouth.
          </p>
          <p class="p-body" style="color:var(--p-muted)">
            Lower per-pupil cost. Better outcomes. Takes 5–10 years.
          </p>
        </div>
        <div class="p-col" style="justify-content:center;align-items:center">
          {/* Cost vs outcome chart (conceptual) */}
          <div class="p-panel" style="padding:1.2rem;align-items:center;gap:0.5rem">
            <svg viewBox="0 0 200 140" style="width:100%;max-width:220px;height:auto">
              <text x="10" y="12" font-size="8" fill="var(--p-muted)" font-family="var(--p-font-display)">OUTCOMES</text>
              <text x="150" y="135" font-size="8" fill="var(--p-muted)" font-family="var(--p-font-display)">COST</text>
              <line x1="20" y1="120" x2="190" y2="120" stroke="var(--p-ink)" stroke-width="2" />
              <line x1="20" y1="120" x2="20" y2="15" stroke="var(--p-ink)" stroke-width="2" />
              {/* Traditional: high cost, medium outcome */}
              <circle cx="140" cy="65" r="14" fill="var(--p-blush)" stroke="var(--p-ink)" stroke-width="2.5" />
              <text x="140" y="69" text-anchor="middle" font-size="7" font-family="var(--p-font-display)">TRAD</text>
              {/* Montessori: lower cost, higher outcome */}
              <circle cx="80" cy="35" r="14" fill="var(--p-leaf)" stroke="var(--p-ink)" stroke-width="2.5" />
              <text x="80" y="39" text-anchor="middle" font-size="7" font-family="var(--p-font-display)">MONT</text>
              <path d="M125,60 L95,42" stroke="var(--p-ink)" stroke-width="1.5" stroke-dasharray="4,3" marker-end="url(#arrowhead)" />
            </svg>
            <p style="font-family:var(--p-font-display);font-size:0.65rem;text-transform:uppercase;letter-spacing:0.1em;color:var(--p-muted);margin:0">Lower cost · better outcomes</p>
          </div>
        </div>
      </div>
    </section>
  );
}

// ---------------------------------------------------------------------------
// 10 — Tax line (unflinching)
// ---------------------------------------------------------------------------
function Slide10Taxes() {
  return (
    <section class="p-slide" style={accentStyle('bloom')}>
      <div class="p-eyebrow">The next ten years · 2 of 4</div>
      <div class="p-row" style="align-items:stretch">
        <div class="p-col" style="justify-content:center;flex:1.3">
          <h2 class="p-title">Raise taxes.<br />Aim for a surplus.</h2>
          <p class="p-body">
            Schools determine asset values. Equalize assessments first — fix
            the historical inaccuracies — then fund the future.
          </p>
          <p class="p-body">
            Fixed-income owners use state and federal programs. That's the right
            tool. It's not the town's tool.
          </p>
        </div>
        <div class="p-panel" style="background:var(--p-paper);max-width:22rem;justify-content:center;gap:1rem">
          <div class="p-tag" style="background:var(--p-bloom)">The line</div>
          <p class="p-quote" style="font-size:clamp(1.2rem,2.4vw,1.8rem)">
            Not a shortfall.<br />A surplus.
          </p>
          {/* Arrow up glyph */}
          <svg viewBox="0 0 60 60" style="width:60px;height:60px">
            <polygon points="30,5 55,40 40,40 40,55 20,55 20,40 5,40" fill="var(--p-leaf)" stroke="var(--p-ink)" stroke-width="3" />
          </svg>
        </div>
      </div>
    </section>
  );
}

// ---------------------------------------------------------------------------
// 11 — It's amazing
// ---------------------------------------------------------------------------
function Slide11Amazing() {
  return (
    <section class="p-slide" style={accentStyle('petal')}>
      <div class="p-eyebrow">Stop saying "good enough"</div>
      <div class="p-row" style="align-items:center">
        <div class="p-col" style="justify-content:center;flex:1.4">
          <h2 class="p-hero" style="font-size:clamp(2.5rem,6.5vw,6rem)">
            Fair Haven<br />isn't good<br />enough.<br />
            <span style="background:var(--p-bloom);padding:0 8px">It's amazing.</span>
          </h2>
        </div>
        <div class="p-col" style="justify-content:center;align-items:center;gap:0.5rem">
          {/* Celebratory flower burst */}
          <svg viewBox="0 0 180 180" style="width:100%;max-width:200px;height:auto">
            {[0, 45, 90, 135, 180, 225, 270, 315].map((angle, i) => {
              const rad = (angle * Math.PI) / 180;
              const cx = 90 + Math.cos(rad) * 55;
              const cy = 90 + Math.sin(rad) * 55;
              const colors = ['var(--p-petal)', 'var(--p-bloom)', 'var(--p-leaf)', 'var(--p-sky)', 'var(--p-plum)', 'var(--p-blush)', 'var(--p-petal)', 'var(--p-bloom)'];
              return <circle cx={cx} cy={cy} r={22} fill={colors[i]} stroke="var(--p-ink)" stroke-width="2.5" />;
            })}
            <circle cx="90" cy="90" r="28" fill="var(--p-bloom)" stroke="var(--p-ink)" stroke-width="3" />
            <text x="90" y="96" text-anchor="middle" font-size="14" font-family="var(--p-font-display)" fill="var(--p-ink)">✺</text>
          </svg>
        </div>
      </div>
    </section>
  );
}

// ---------------------------------------------------------------------------
// 12 — The Bookends (SOUTH = cherry blossoms, NORTH = dock per user correction)
// ---------------------------------------------------------------------------
function Slide12Bookends() {
  return (
    <section class="p-slide" style={accentStyle('leaf')}>
      <div class="p-eyebrow">The next ten years · 3 of 4 · The project</div>
      <h2 class="p-title">The Bookends of Fair Haven.</h2>
      <div class="p-bookends">
        <div class="p-bookend-cell p-bookend-cell--south">
          <div class="p-tag">South bookend</div>
          <h3>Under the<br />Cherry Blossoms</h3>
          <ul>
            <li>New park + playground</li>
            <li>Entrance to Fair Haven Woods</li>
            <li>Wildflower garden</li>
            <li>Spring celebration</li>
          </ul>
        </div>
        <div class="p-bookend-cell p-bookend-cell--heart">
          <div class="p-tag">The heart</div>
          <h3>Fair Haven Road</h3>
          <ul>
            <li>The school</li>
            <li>Borough Hall frontage</li>
            <li>Farmer's market corridor</li>
            <li>Wildflowers, sparkling each spring</li>
          </ul>
        </div>
        <div class="p-bookend-cell p-bookend-cell--north">
          <div class="p-tag">North bookend</div>
          <h3>At the Dock</h3>
          <ul>
            <li>New playground (inactive for now)</li>
            <li>Modest boardwalk extension</li>
            <li>Long-term: buy the marina</li>
            <li>Quaint waterfront walk</li>
          </ul>
        </div>
      </div>
    </section>
  );
}

// ---------------------------------------------------------------------------
// 13 — Spring festival
// ---------------------------------------------------------------------------
function Slide13Festival() {
  return (
    <section class="p-slide" style={accentStyle('bloom')}>
      <div class="p-eyebrow">The activation</div>
      <div class="p-row">
        <div class="p-col" style="justify-content:center;flex:1.2">
          <h2 class="p-title">Shut down<br />Fair Haven Road.</h2>
          <p class="p-body">
            One day a year. Ridge to the dock. Farmer's market. Family race.
            Face painting in the forest. The future of the school front-and-center.
            <strong>Fund the volunteers.</strong>
          </p>
        </div>
        <div class="p-col" style="justify-content:center;align-items:center">
          {/* Festival banner SVG */}
          <svg viewBox="0 0 200 160" style="width:100%;max-width:220px;height:auto">
            {/* Bunting / banner flags */}
            <path d="M20,30 Q100,50 180,30" fill="none" stroke="var(--p-ink)" stroke-width="2.5" />
            {[40, 70, 100, 130, 160].map((x, i) => {
              const colors = ['var(--p-petal)', 'var(--p-bloom)', 'var(--p-leaf)', 'var(--p-plum)', 'var(--p-sky)'];
              return <polygon points={`${x - 8},33 ${x + 8},33 ${x},55`} fill={colors[i]} stroke="var(--p-ink)" stroke-width="2" />;
            })}
            {/* People silhouettes */}
            {[50, 80, 110, 140, 160].map((x, i) => {
              const h = 30 + (i % 2) * 8;
              return (
                <g>
                  <circle cx={x} cy={130 - h} r={6} fill="var(--p-ink)" />
                  <rect x={x - 4} y={136 - h} width={8} height={h - 8} fill="var(--p-ink)" rx="0" />
                </g>
              );
            })}
            {/* Ground */}
            <rect x="0" y="140" width="200" height="20" fill="var(--p-leaf)" stroke="var(--p-ink)" stroke-width="2" />
          </svg>
        </div>
      </div>
    </section>
  );
}

// ---------------------------------------------------------------------------
// 14 — Volunteers
// ---------------------------------------------------------------------------
function Slide14Volunteers() {
  return (
    <section class="p-slide" style={accentStyle('leaf')}>
      <div class="p-eyebrow">The next ten years · 4 of 4</div>
      <div class="p-row" style="align-items:center">
        <div class="p-col" style="justify-content:center;flex:1.4;gap:1.2rem">
          <h2 class="p-title">More spaces<br />for more<br />volunteers.</h2>
          <p class="p-quote" style="font-size:clamp(0.95rem,1.6vw,1.3rem);text-transform:none;font-family:var(--p-font-body);font-weight:500;max-width:34ch">
            "A society grows great when its people plant seeds for trees whose
            shade they'll never sit in."
          </p>
          <p class="p-attribution">— old proverb</p>
        </div>
        <div class="p-col" style="justify-content:center;align-items:center">
          {/* Tree with seeds / planting metaphor */}
          <svg viewBox="0 0 160 180" style="width:100%;max-width:160px;height:auto">
            <rect x="72" y="110" width="16" height="60" fill="var(--p-ink)" />
            {/* Canopy */}
            <circle cx="80" cy="70" r="50" fill="var(--p-leaf)" stroke="var(--p-ink)" stroke-width="3" />
            <circle cx="60" cy="55" r="20" fill="var(--p-leaf)" stroke="var(--p-ink)" stroke-width="2" />
            <circle cx="100" cy="55" r="20" fill="var(--p-leaf)" stroke="var(--p-ink)" stroke-width="2" />
            <circle cx="80" cy="40" r="18" fill="var(--p-leaf)" stroke="var(--p-ink)" stroke-width="2" />
            {/* Small seeds falling */}
            {[[45, 125], [115, 130], [35, 140], [130, 145], [55, 155]].map(([x, y]) => (
              <circle cx={x} cy={y} r={3} fill="var(--p-bloom)" stroke="var(--p-ink)" stroke-width="1.5" />
            ))}
            <rect x="0" y="168" width="160" height="12" fill="var(--p-blush)" stroke="var(--p-ink)" stroke-width="2" />
          </svg>
        </div>
      </div>
    </section>
  );
}

// ---------------------------------------------------------------------------
// 15 — The door
// ---------------------------------------------------------------------------
function Slide15TheDoor() {
  return (
    <section class="p-slide p-slide--split">
      <div class="p-grid-2">
        <div style={{ background: 'var(--p-leaf)' }}>
          <div class="p-tag">If you're a builder</div>
          <h2 class="p-title">Welcome.</h2>
          <p class="p-body">
            If you feel the calling to make the places and people around you
            better — you're home.
          </p>
          <FlowerSVG size={64} color="var(--p-bloom)" />
        </div>
        <div style={{ background: 'var(--p-plum)' }}>
          <div class="p-tag" style="background:var(--p-paper)">If you're a cynic</div>
          <h2 class="p-title">Find the door.</h2>
          <p class="p-body">
            We don't care about D or R. We care about growth. Negativity, ego,
            and opportunism: out.
          </p>
          {/* Door icon */}
          <svg viewBox="0 0 50 70" style="width:50px;height:70px">
            <rect x="5" y="5" width="40" height="60" fill="var(--p-paper)" stroke="var(--p-ink)" stroke-width="3" />
            <circle cx="38" cy="38" r="3" fill="var(--p-ink)" />
            <line x1="5" y1="5" x2="25" y2="0" stroke="var(--p-ink)" stroke-width="2" />
            <line x1="45" y1="5" x2="48" y2="2" stroke="var(--p-ink)" stroke-width="2" />
          </svg>
        </div>
      </div>
    </section>
  );
}

// ---------------------------------------------------------------------------
// 16 — Closing
// ---------------------------------------------------------------------------
function Slide16Closing() {
  return (
    <section class="p-slide" style={accentStyle('petal')}>
      <div class="p-row" style="align-items:center;justify-content:center">
        <div class="p-col" style="flex:1.3;justify-content:center;align-items:flex-start;gap:1rem">
          <div class="p-tag">Fair for Fair Haven</div>
          <h2 class="p-hero" style="font-size:clamp(2.6rem,7vw,6.5rem)">
            Bloom<br />in the<br />dark.
          </h2>
          <p class="p-body" style="margin-top:0.5rem;font-size:1.1rem">
            We are the Town of Flowers.<br />
            Plant something.
          </p>
          <FlowerRow count={8} />
        </div>
        <div class="p-col" style="justify-content:center;align-items:center">
          {/* Large flower arrangement */}
          <svg viewBox="0 0 200 220" style="width:100%;max-width:200px;height:auto">
            {/* Vase */}
            <path d="M70,180 Q60,200 75,215 L125,215 Q140,200 130,180 Z" fill="var(--p-sky)" stroke="var(--p-ink)" stroke-width="3" />
            {/* Stems */}
            {[80, 100, 120].map((x) => (
              <line x1={x} y1={180} x2={x + (x - 100) * 0.3} y2={60} stroke="var(--p-ink)" stroke-width="2.5" />
            ))}
            {/* Flowers at top */}
            {[
              [74, 55, 22, 'var(--p-petal)'],
              [100, 40, 26, 'var(--p-bloom)'],
              [126, 55, 22, 'var(--p-plum)'],
              [88, 80, 18, 'var(--p-leaf)'],
              [112, 80, 18, 'var(--p-blush)'],
            ].map(([cx, cy, r, fill]) => (
              <g>
                <circle cx={cx as number} cy={cy as number} r={r as number} fill={fill as string} stroke="var(--p-ink)" stroke-width="2.5" />
                <circle cx={cx as number} cy={cy as number} r={(r as number) * 0.35} fill="var(--p-bloom)" stroke="var(--p-ink)" stroke-width="1.5" />
              </g>
            ))}
          </svg>
        </div>
      </div>
    </section>
  );
}

// ---------------------------------------------------------------------------
// Slide manifest
// ---------------------------------------------------------------------------

export const SLIDES: SlideDef[] = [
  { id: '01-cover',         title: 'Fair for Fair Haven',          accent: 'petal', Component: Slide01Cover },
  { id: '02-mood',          title: "Everyone's sour",              accent: 'blush', Component: Slide02Mood },
  { id: '03-two-views',     title: 'Two views',                    accent: 'sky',   Component: Slide03TwoViews },
  { id: '04-optimism',      title: 'Optimism pays',                accent: 'bloom', Component: Slide04OptimismPays },
  { id: '05-brecht',        title: 'Music in the dark',            accent: 'plum',  Component: Slide05Brecht },
  { id: '06-2009',          title: 'Be 2009 buyers',               accent: 'leaf',  Component: Slide06_2009 },
  { id: '07-flower-power',  title: 'Flower Power has returned',    accent: 'petal', Component: Slide07FlowerPower },
  { id: '08-who-lives',     title: '50 / 50',                      accent: 'sky',   Component: Slide08WhoLives },
  { id: '09-schools',       title: "Invest. Don't austerity.",     accent: 'leaf',  Component: Slide09Schools },
  { id: '10-taxes',         title: 'Raise taxes. Aim for surplus.', accent: 'bloom', Component: Slide10Taxes },
  { id: '11-amazing',       title: "It's amazing",                 accent: 'petal', Component: Slide11Amazing },
  { id: '12-bookends',      title: 'The Bookends',                 accent: 'leaf',  Component: Slide12Bookends },
  { id: '13-festival',      title: 'Shut down Fair Haven Road',    accent: 'bloom', Component: Slide13Festival },
  { id: '14-volunteers',    title: 'More spaces, more volunteers', accent: 'leaf',  Component: Slide14Volunteers },
  { id: '15-door',          title: 'Builders / cynics',            accent: 'plum',  Component: Slide15TheDoor },
  { id: '16-closing',       title: 'Bloom in the dark',            accent: 'petal', Component: Slide16Closing },
];
