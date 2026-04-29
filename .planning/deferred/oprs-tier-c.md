# Deferred: OPRS Tier-C Endpoints

**Status:** Pinned for v2 (post-MVP). Documented here so it doesn't get lost.

## What's deferred

Items 5-10 from the OPRS endpoint inventory. These are real, public, reachable,
and valuable — but they answer different research questions than the core
hedonic + Berry tax-shift + CDF gap test, and they require different
infrastructure than the per-parcel CGI-style scraping currently in
`datasets/collect_oprs.py`.

## Endpoint catalogue (deferred)

### 5. Tax Map Sheets (`/TaxBoard/TaxMap.aspx`)

Scanned images of municipal tax map pages showing parcel boundaries. Fair
Haven has roughly 15 map sheets (per the `Map Page:` field on PRCs). One-time
aggregate download — not per-parcel.

**Why deferred:** Visual context only; the GeoJSON polygons we already have
from NJGIN serve the same purpose for any analytical map we ship.

**When to revisit:** If a public-facing artifact wants to overlay official
tax-map sheets on the choropleth, or if a parcel's exact boundary is in
dispute and we want to cross-reference the map sheet.

**Cost:** ~15 map-sheet PDFs at maybe 5-10 MB each = ~100-150 MB total.

### 6. Tax Appeal Judgments (`CustomSearch/SearchInput.aspx?iId=481`)

Per-parcel appeal docket showing original assessment, judgment amount, year
of judgment, and disposition. Identifies parcels that have **successfully**
contested their assessment — a self-selected cohort signal worth analyzing
on its own (long-tenured owners who knew enough to appeal vs. recent buyers
who didn't).

**Why deferred:** Different scraping infrastructure. This is ASP.NET
WebForms with VIEWSTATE / EVENTVALIDATION token replay — Playwright required,
much slower per-parcel than the simple CGI scraping in collect_oprs.py.

**When to revisit:** After MVP results. If the H1 cohort effect is positive,
the "appeal cohort" subset is the natural follow-up dataset to characterize
who *successfully* fought their assessment vs. who didn't.

**Cost:** ~2,061 parcels × 1-2 ASP.NET requests each. Possibly slower than
1 req/s due to VIEWSTATE handshake overhead. Estimate 1-2 hours of script
time on top of OPRS Tier-1.

**Implementation notes:** Use Playwright with persistent browser context;
form fields are ddlInput1 (county), ddlInput2 (municipality), ddlInput3
(property class), txtInput1/2/3 (block/lot/qualifier). VIEWSTATE token is
~5 KB and must be replayed verbatim from the previous response on every
postback.

### 7. Tax Rate Certifications (`CustomSearch/SearchInput.aspx?iId=484`)

Per-year per-municipality official rate certificates from the Monmouth
County Tax Board. Cross-checks the DLGS Municipal Tax Summary numbers we
already have.

**Why deferred:** Redundant with DLGS for current year; only adds value if
investigating historical pre-1998 years that DLGS doesn't cover.

**When to revisit:** Probably never for this project. Listed for completeness.

**Cost:** ~30 PDFs (one per year of historical record).

### 8. County Clerk Deed Images (`clerk/ClerkHome.aspx?op=basic`)

Full PDF deeds for every recorded property transfer 1996-present. Indexed
by Book/Page (which we already have from `m4.cgi` and `sr.cgi` for every
sale). Each deed is a multi-page legal document with:

- Full grantor + grantee details
- Legal description of the property
- Consideration (sale price)
- Mortgage info (if recorded together)
- Conveyance type (warranty deed, quitclaim, bargain-and-sale, etc.)
- Sometimes: easements, restrictions, riders

**Why deferred:** Massive scope. Storage cost: ~3-5 deeds per parcel × 2,061
parcels = ~6,000-10,000 deed PDFs at 1-5 MB each → **10-50 GB of additional
data**. Each deed PDF is also a scanned image, so OCR is needed for any text
analysis, multiplying the per-deed processing cost.

**When to revisit:** Only if a specific investigation needs primary-source
deed text. For example: identifying parcels that transferred via quitclaim
(potential family gifts that should have been NU-coded but weren't), or
finding deed riders that mention waterfront access (a real Fair Haven
feature not captured in MOD-IV).

**Cost:** 10-50 GB storage. Scrape rate likely capped by deed-image generation
on the clerk's server (each deed is rendered on demand from a microfiche
archive). Probably 10-20 hours of script time + significant storage planning.

**Access posture:** Public, no auth, no clickwrap. Same green-tier as the
PRC portal. But scraping volume will be visible in the county's logs at this
scale — consider 30-second pacing and explicit "research" intent in any
follow-up communication if questioned.

### 9. Subdivision Maps (`clerk/SubMap.aspx?op=home`)

Visual subdivision plats for parcels with `.01`, `.02` suffixes (subdivided
lots). Supplements item 5.

**Why deferred:** Niche — only useful for the specific parcels that have
subdivision history and only if we need to understand the original-vs-current
boundary geometry.

**When to revisit:** If any subdivided parcel appears as a heavy outlier in
the Berry tax-shift analysis and we need historical boundary context.

### 10. Consolidated Records Search (`GoogleWithUC/Default.aspx`)

Generic search interface across all OPRS records. Provides no new data —
just a different UI for items 1-9.

**Why deferred:** Not a data source — just a search UI.

**When to revisit:** Never for this project. Listed for completeness.

## Decision criteria for promoting any item out of Tier-C

Promote to active scope ONLY when:
1. MVP analysis (Tier 1-4 + statistical pipeline) is complete and committed,
   AND
2. The MVP results raise a specific question that requires the deferred
   data (e.g., "appeal-cohort behavior" needs item 6; "deed text mining"
   needs item 8), AND
3. The user explicitly authorizes the scope expansion.

Do not preemptively scrape any Tier-C endpoint. The current Tier-1
comprehensive collection (m4 + sr + prc PDF + ch75 PDF + taxlist PDF) is
already a substantial dataset and answers the H1/H2 questions on its own.

## What will be reused when Tier-C is activated

`datasets/collect_oprs.py` already has:
- VPN-swap-friendly batched architecture
- Atomic writes (append component types, no rewrite needed)
- Idempotent cache layout (subdir per parcel)
- Auto-abort on rolling error rate
- Status reporter

Adding a new endpoint = one new component name + one new URL builder + one
new validator. The infrastructure scales.

For ASP.NET endpoints (item 6) we'll need a separate companion script that
reuses the same cache convention but uses Playwright for the VIEWSTATE dance.
Suggested name: `datasets/collect_oprs_appeals.py`.

For the County Clerk deed images (item 8) we'll need a separate large-scale
storage backend (object store or git-lfs) and a different rate-limit posture.
Suggested name: `datasets/collect_clerk_deeds.py`.

---

*Pinned: 2026-04-29*
*Re-evaluation trigger: after MVP analysis ships and decision gate is reached*
