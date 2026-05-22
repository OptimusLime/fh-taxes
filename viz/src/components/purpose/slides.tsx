/** @jsxImportSource preact */
// Fair for Fairhaven — slide deck content.
//
// Each slide is a self-contained Preact component rendered by Deck.tsx.
// All visual tokens live in viz/src/styles/purpose-brand.css; this file
// composes them. Word count per slide is intentionally minimal — leaves
// room for imagery sourced later.

import ImageSlot from './ImageSlot';

type Accent = 'petal' | 'bloom' | 'sky' | 'leaf' | 'plum' | 'blush';

export type SlideDef = {
  id: string;
  title: string;        // for nav / overview
  accent: Accent;
  Component: () => any;
};

const accentStyle = (a: Accent) => ({ '--p-accent': `var(--p-${a})` } as any);

// ---------------------------------------------------------------------------
// 01 — Cover
// ---------------------------------------------------------------------------
function Slide01Cover() {
  return (
    <section class="p-slide p-slide--split" style={accentStyle('petal')}>
      <div class="p-cover" style={accentStyle('petal')}>
        <div class="p-cover-text">
          <div>
            <div class="p-tag">A manifesto · 2026</div>
          </div>
          <div>
            <h1 class="p-hero">Fair for<br />Fairhaven</h1>
            <p class="p-body" style="margin-top:1.2rem;font-size:1.2rem;max-width:28ch">
              Bloom in the dark times.
            </p>
          </div>
          <div class="p-flower-strip">✺ ❀ ✿ ❁ ✼ ❃</div>
        </div>
        <div class="p-cover-art">
          <ImageSlot label="Cherry blossoms over Fairhaven Road, spring" />
        </div>
      </div>
    </section>
  );
}

// ---------------------------------------------------------------------------
// 02 — The mood
// ---------------------------------------------------------------------------
function Slide02Mood() {
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
        <ImageSlot label="1970s newsstand / gas line / TIME cover" />
      </div>
    </section>
  );
}

// ---------------------------------------------------------------------------
// 03 — Two views
// ---------------------------------------------------------------------------
function Slide03TwoViews() {
  return (
    <section class="p-slide p-slide--split">
      <div class="p-grid-2">
        <div style={{ background: 'var(--p-sky)' }}>
          <div class="p-tag">View one</div>
          <h2 class="p-title">It all<br />crashes.</h2>
          <p class="p-body">The line points down — forever.</p>
        </div>
        <div style={{ background: 'var(--p-leaf)' }}>
          <div class="p-tag">View two</div>
          <h2 class="p-title">The line<br />points up.</h2>
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
  return (
    <section class="p-slide" style={accentStyle('bloom')}>
      <div class="p-eyebrow">The pattern</div>
      <div class="p-row" style="align-items:stretch">
        <div class="p-col" style="justify-content:center;flex:1.2">
          <h2 class="p-title">Optimism pays<br />the longest<br />dividend.</h2>
          <p class="p-body">
            History rewards the people who believed the line could point up
            <em> while</em> it was pointing down. Every time. Across every
            generation. As long as there are people, this will be true.
          </p>
        </div>
        <ImageSlot label="Rising chart / sunrise / S&P long-run" />
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
      </div>
    </section>
  );
}

// ---------------------------------------------------------------------------
// 06 — 2009 buyers
// ---------------------------------------------------------------------------
function Slide06_2009() {
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
            <strong>Fairhaven is in a 2009 moment.</strong> Invest as if the down
            didn't exist. One day it won't.
          </p>
        </div>
        <ImageSlot label="2008–2025 home-price chart, Monmouth County" />
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
        <ImageSlot label="Palpatine 'somehow returned' meme — flower crown overlay" />
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
        <ImageSlot label="Sidewalk crowd / kids on bikes / Fairhaven block" />
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
        <ImageSlot label="Montessori classroom / kids reading / school hallway" />
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
        <div class="p-panel" style="background:var(--p-paper);max-width:24rem">
          <div class="p-tag">The line</div>
          <p class="p-quote" style="font-size:clamp(1.2rem,2.4vw,1.8rem)">
            Not a shortfall.<br />A surplus.
          </p>
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
            Fairhaven<br />isn't good<br />enough.<br />
            <span style="background:var(--p-bloom);padding:0 8px">It's amazing.</span>
          </h2>
        </div>
        <ImageSlot label="River view / dock at dusk / Fairhaven aerial" />
      </div>
    </section>
  );
}

// ---------------------------------------------------------------------------
// 12 — The Bookends
// ---------------------------------------------------------------------------
function Slide12Bookends() {
  return (
    <section class="p-slide" style={accentStyle('leaf')}>
      <div class="p-eyebrow">The next ten years · 3 of 4 · The project</div>
      <h2 class="p-title">The Bookends of Fairhaven.</h2>
      <div class="p-bookends">
        <div class="p-bookend-cell p-bookend-cell--north">
          <div class="p-tag">North bookend</div>
          <h3>Under the<br />Cherry Blossoms</h3>
          <ul>
            <li>New park + playground</li>
            <li>Entrance to Fairhaven Woods</li>
            <li>Wildflower garden</li>
            <li>Spring celebration</li>
          </ul>
        </div>
        <div class="p-bookend-cell p-bookend-cell--heart">
          <div class="p-tag">The heart</div>
          <h3>Fairhaven Road</h3>
          <ul>
            <li>The school</li>
            <li>Borough Hall frontage</li>
            <li>Farmer's market corridor</li>
            <li>Wildflowers, sparkling each spring</li>
          </ul>
        </div>
        <div class="p-bookend-cell p-bookend-cell--south">
          <div class="p-tag">South bookend</div>
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
          <h2 class="p-title">Shut down<br />Fairhaven Road.</h2>
          <p class="p-body">
            One day a year. Ridge to the dock. Farmer's market. Family race.
            Face painting in the forest. The future of the school front-and-center.
            <strong>Fund the volunteers.</strong>
          </p>
        </div>
        <ImageSlot label="Festival on a closed street / face painting / banner across the road" />
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
        <ImageSlot label="Volunteer firefighter / planting day / community park" />
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
        </div>
        <div style={{ background: 'var(--p-plum)' }}>
          <div class="p-tag" style="background:var(--p-paper)">If you're a cynic</div>
          <h2 class="p-title">Find the door.</h2>
          <p class="p-body">
            We don't care about D or R. We care about growth. Negativity, ego,
            and opportunism: out.
          </p>
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
          <div class="p-tag">Fair for Fairhaven</div>
          <h2 class="p-hero" style="font-size:clamp(2.6rem,7vw,6.5rem)">
            Bloom<br />in the<br />dark.
          </h2>
          <p class="p-body" style="margin-top:0.5rem;font-size:1.1rem">
            We are the Town of Flowers.<br />
            Plant something.
          </p>
          <div class="p-flower-strip">✺ ❀ ✿ ❁ ✼ ❃ ✺ ❀</div>
        </div>
        <ImageSlot label="Wildflowers / spring meadow / Fairhaven welcome sign" />
      </div>
    </section>
  );
}

// ---------------------------------------------------------------------------
// Manifest
// ---------------------------------------------------------------------------

export const SLIDES: SlideDef[] = [
  { id: '01-cover',         title: 'Fair for Fairhaven',          accent: 'petal', Component: Slide01Cover },
  { id: '02-mood',          title: "Everyone's sour",             accent: 'blush', Component: Slide02Mood },
  { id: '03-two-views',     title: 'Two views',                   accent: 'sky',   Component: Slide03TwoViews },
  { id: '04-optimism',      title: 'Optimism pays',               accent: 'bloom', Component: Slide04OptimismPays },
  { id: '05-brecht',        title: 'Music in the dark',           accent: 'plum',  Component: Slide05Brecht },
  { id: '06-2009',          title: 'Be 2009 buyers',              accent: 'leaf',  Component: Slide06_2009 },
  { id: '07-flower-power',  title: 'Flower Power has returned',   accent: 'petal', Component: Slide07FlowerPower },
  { id: '08-who-lives',     title: '50 / 50',                     accent: 'sky',   Component: Slide08WhoLives },
  { id: '09-schools',       title: "Invest. Don't austerity.",    accent: 'leaf',  Component: Slide09Schools },
  { id: '10-taxes',         title: 'Raise taxes. Aim for surplus.', accent: 'bloom', Component: Slide10Taxes },
  { id: '11-amazing',       title: "It's amazing",                accent: 'petal', Component: Slide11Amazing },
  { id: '12-bookends',      title: 'The Bookends',                accent: 'leaf',  Component: Slide12Bookends },
  { id: '13-festival',      title: 'Shut down Fairhaven Road',    accent: 'bloom', Component: Slide13Festival },
  { id: '14-volunteers',    title: 'More spaces, more volunteers', accent: 'leaf', Component: Slide14Volunteers },
  { id: '15-door',          title: 'Builders / cynics',           accent: 'plum',  Component: Slide15TheDoor },
  { id: '16-closing',       title: 'Bloom in the dark',           accent: 'petal', Component: Slide16Closing },
];
