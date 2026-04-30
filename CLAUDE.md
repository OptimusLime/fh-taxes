<!-- GSD:project-start source:PROJECT.md -->
## Project

**Fair Haven Tax Assessment Analysis**

A data investigation and public-facing dashboard analyzing property tax burden distribution in Fair Haven Borough, NJ (Monmouth County, district 14). The project tests whether post-2020 movers bear a disproportionate share of the tax burden via passive sales chasing in Monmouth County's Assessment Demonstration Program (ADP), using the Berry tax-shift methodology (Cook County / U Chicago Center for Municipal Finance) and the IAAO sales-chasing CDF gap test. Output is a parcel-level dollar-delta GeoJSON rendered as an interactive Leaflet map, with methodology white paper.

**Core Value:** A reproducible, defensible parcel-level dollar-delta artifact (Berry tax-shift + CDF gap test) that either (a) demonstrates tenure-correlated horizontal inequity in Fair Haven assessments, or (b) documents that ADP works as designed. Either outcome is publishable. Pre-commitment to publish either way is what distinguishes investigation from advocacy.

### Constraints

- **Tech stack**: Python (geopandas, statsmodels, scipy, scikit-learn for k-means, pdfplumber/camelot for DLGS PDFs). PostgreSQL + PostGIS keyed by PAMS_PIN if data volume warrants; SQLite/parquet acceptable for v1. Leaflet (static HTML) for the public map. PySAL deferred to v2.
- **Legal — Daniel's Law (N.J.S.A. 47:1B-1 et seq.)**: Must register as Redactor on OIP portal before publication; suppress matched parcels or redact owner names; mandatory $1,000-per-violation statutory damages. Default public visualizations to aggregate / BG level where individual identifiability is a concern; parcel-level map ships with owner names suppressed entirely.
- **Legal — defamation / anti-SLAPP**: Stick to verifiable facts (assessment, sale price, ratio, dollar delta). Avoid imputing motives. Frame as systemic critique not individual indictment. NJ UPEPA (N.J.S.A. 2A:53A-49 et seq.) provides anti-SLAPP cover for matters of public concern.
- **Legal — scraping**: Reasonable rate limits (1-2 req/s), identifying user-agent with contact email, respect robots.txt. Post-*hiQ v. LinkedIn* / *Van Buren* ToS violations are civil contract claims, not CFAA criminal.
- **Legal — voter file**: N.J.S.A. 19:31-18.1 — non-commercial use only, ≤$375/yr cap, request goes to Monmouth County Superintendent of Elections (invisible to FH Borough). DPPA does NOT cover voter rolls — joining MOD-IV with voter file is allowed.
- **Operational tipoff hierarchy**: Operate strictly in bottom four tiers (NJOGIS bulk → county voter → OPRS scraping → public meeting observer). No OPRA to Fair Haven Borough until analysis is mature. No MVC data ever (DPPA $2,500 floor + fees).
- **Pre-commitment**: Publish result regardless of direction. Falsification of H1+H2+H3 is itself a publishable finding.
<!-- GSD:project-end -->

<!-- GSD:stack-start source:STACK.md -->
## Technology Stack

Technology stack not yet documented. Will populate after codebase mapping or first phase.
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

### TEMP-FILE BAN (HARD RULE — NO EXCEPTIONS)

**`/tmp` (and any other system temp dir like `/var/folders`, `~/.cache`, `$TMPDIR`) is FORBIDDEN for ALL agent-generated artifacts.** This includes — but is not limited to — sandbox parcel lists, scratch parquets, raw HTTP captures, PDF samples, log files, ad-hoc scripts, Python heredocs that write files, and "I'll just put this here for a sec" caches.

**Why:** the user cannot reproduce, inspect, or audit anything written to `/tmp`. Files there vanish on reboot, are invisible to `git`, and break the chain of evidence between what the agent claims it did and what actually exists.

**Where to put scratch instead:**
- One-off scripts and probes → `temporary_scripts/<topic>/`
- Sandbox/exploration data (test parcel lists, captured responses, throwaway parquets) → `temporary_scripts/sandbox/`
- Test fixtures that need to live with the test → `tests/fixtures/<area>/`
- Production raw cache → `data/raw/<source>/` (already gitignored where appropriate)
- Production processed artifacts → `data/processed/`

**Enforcement:** if the agent finds itself about to write to `/tmp`, `/var/folders`, `$TMPDIR`, or any system temp path, STOP and use `temporary_scripts/sandbox/` instead. There is no "fast/temporary" exception. The user has explicitly invoked this rule by name.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->
## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, or `.github/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->



<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
