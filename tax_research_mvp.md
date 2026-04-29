# Research Plan: Property Tax Burden Distribution in Fair Haven, NJ (v2)

**Prepared:** April 2026 | **Subject municipality:** Fair Haven Borough, Monmouth County, NJ (district code 14; ~6,100 residents; ~2,200 households; ~$2.83B aggregate true value) | **Investigator profile:** Resident, technical (Python/scraping/dashboards), publishing to a public website, operating under-the-radar relative to town government.

**v2 changes:** H2 reframed around passive sales chasing per IAAO Standard on Ratio Studies and the Berry tax-shift methodology (Cook County, U Chicago Center for Municipal Finance). Sections 1.2, 2.2, 6.1, and 8.1 revised. MVP appendix appended.

## Executive framing and the central pivot

The user's core claim is that **post-2020 movers (often younger families) bear a disproportionate share of Fair Haven's property tax burden**, with two plausible mechanisms: stale or unequal assessments favoring long-tenured owners, and Board of Education underfunding relative to where revenue originates. Before any data is touched, one structural fact reshapes the inquiry: **Fair Haven is an annual-reassessment town under Monmouth County's Assessment Demonstration Program (ADP)**, with a 2025 Director's Ratio of **101.96%** against $2.77B in assessed value, meaning municipality-wide assessments track market value within ~2% on aggregate.

This does not refute the user's claim. It narrows the *mechanism* by which it could be true. The "stale assessment" hypothesis as commonly framed in non-ADP NJ towns (where ratios drift to 40-60% between decade-spaced revaluations) is structurally weak here. The right hypothesis for an ADP town is **passive sales chasing**: a mass-appraisal model where recent sales are the strongest training signal pins recently-sold parcels tightly to their sale prices while non-sold parcels drift, producing a tenure-correlated horizontal inequity that does not show up in aggregate Director's Ratio statistics. This is the statistical analogue of the *Van Decker* welcome-stranger doctrine and the central methodology of Christopher Berry's Cook County work that produced the headline $1.7B and $2.2B tax-shift figures.

This document delivers all eight requested sections plus an MVP appendix at the end.

## 1. Hypothesis construction

### 1.1 New Jersey property tax mechanics relevant to Fair Haven (2026)

Fair Haven's tax bill is built from six levies summing to roughly **$1.574 per $100 of assessed value** in the most recent published rate sheet: municipal $0.343, county budget $0.199, county library $0.014, **local school (Fair Haven SD) $0.713**, **regional school (Rumson-Fair Haven Regional HS) $0.277**, and county open space $0.028. Schools account for roughly **63%** of every Fair Haven tax bill. The local levy is voted by the BOE; the regional levy is set by the Rumson-Fair Haven Regional district and apportioned between Fair Haven and Rumson by a statutory formula (typically a hybrid of equalized property valuation and resident enrollment, the actual formula must be confirmed from the regional district's User-Friendly Budget).

**Monmouth County's Assessment Demonstration Program (ADP)** is governed by P.L. 2013, c. 15 (N.J.S.A. 54:1-101 et seq.). It requires annual reassessment to 100% of current market value via mass-appraisal modeling against arms-length sales (valuation date October 1 of pretax year), with a **5-year rolling cycle of physical (or "remote virtual") interior inspections**, roughly 20% of parcels each year. Appeals must be filed by **January 15** (vs. April 1 statewide). Fair Haven (district 14) participates and contracts with Realty Data Systems for inspection cycles; assessor Greg Hutchinson holds Thursday office hours. Critically, in ADP towns, **Chapter 123's ±15% common-level corridor effectively does not apply** because assessments must equal true value annually, meaning a Fair Haven taxpayer can challenge an over-assessment without first overcoming a 15% statutory band, but it also means systemic under-assessments of long-tenured owners cannot easily hide behind that same band. The 2025 Director's Ratio of **101.96%** confirms the system is working at the aggregate level. The remaining question is whether *individual* parcels deviate systematically from the true-value standard in ways correlated with tenure.

### 1.2 Hypotheses

**H1 (Primary, burden distribution).** Property tax burden in Fair Haven, measured as effective tax rate (annual tax bill ÷ current market value) and as absolute dollar bill, skews disproportionately toward households who purchased their property after January 2020 relative to households who purchased before 2015, even after controlling for property characteristics (square footage, lot size, year built, bedroom/bathroom count, neighborhood).
- **H1-null.** Effective tax rates and burden shares show no statistically significant cohort effect by year-of-purchase once property characteristics are controlled.

**H2 (Secondary, assessment mechanism).** Fair Haven's annual mass-appraisal model exhibits **passive sales chasing**: recently-sold parcels are pinned tightly to their sale price (because the sale is the model's strongest training signal), while non-sold parcels drift below true market value. The result is a tenure-correlated horizontal inequity in which long-tenured owners systematically underpay their fair share and recent buyers systematically overpay, even though the town-wide aggregate Director's Ratio remains near 100%.
- **H2-null.** The empirical CDF of assessment-to-sale-price ratios shows no discontinuity at ratio = 1.0 (no cliff signature of sales chasing per IAAO and the CCAO `assessr::detect_chasing()` test); a hedonic model trained on recent sales and applied to the unsold population shows no systematic tenure correlation in its residuals; per-parcel dollar delta from fair share does not cluster by tenure cohort.
- **Doctrinal anchor.** This is the statistical analogue of the *West Milford v. Van Decker* "welcome stranger" pattern (NJ Supreme Court 1990) and the U.S. Supreme Court's *Allegheny Pittsburgh Coal* (1989). The legal version requires intentional spot reassessment; the statistical version emerges passively from any mass-appraisal model that treats recent sales as ground truth without compensating for differential information density across the parcel population. ADP eliminates the overt legal version. It does not immunize against the passive statistical version. The IAAO formally defines sales chasing in its Standard on Ratio Studies (April 2013) and Indiana 50 IAC 27-2-11; Cook County's open-source `assessr` R package implements the canonical CDF gap detection test.

**H3 (Tertiary, BOE funding).** Fair Haven's Board of Education budget is suppressed relative to (a) its share of the total municipal tax levy, (b) per-pupil spending in demographically comparable Monmouth County K-8 districts (Rumson Borough, Little Silver, Shrewsbury Borough), and (c) the proportion of new-mover households with school-age children driving school demand.
- **H3-null.** Per-pupil spending and BOE budget growth track or exceed comparable districts and inflation; the BOE share of total levy is consistent with peer towns.

### 1.3 Operational definitions

| Term | Definition |
|---|---|
| **Recent mover / "young family"** | Household whose parcel last sold on or after **January 1, 2020** per Monmouth Clerk deed records / SR1A. (Demographic "young family" overlay uses ACS B25007 + B11005: householder under 45 with own children under 18 at block-group level.) |
| **Long-tenured owner** | Parcel last sold **before January 1, 2015** (10+ years held as of analysis date), excluding intra-family transfers (NU codes) and refinance-related quitclaims. |
| **Tenure cohorts** | Pre-2010, 2010-2015, 2016-2019, 2020-2022, 2023-2026 (five buckets). |
| **Tax burden share** | Annual tax bill (assessment × $1.574/100) as a percentage of total Fair Haven levy and as effective rate against contemporaneous market value (Zillow/Redfin estimate or recent comp). |
| **Passive sales chasing** | Mass-appraisal behavior in which recent-sale parcels track their sale price tightly (because the sale dominates the training signal) while non-sold comparable parcels drift. Detectable via CDF gap test on assessment-to-sale ratios and via hedonic-model residual analysis on the unsold population. |
| **Effective tax rate (ETR)** | Tax bill ÷ market value (not ÷ assessed value, which mechanically equals the general rate in a 100%-ratio town). |
| **Fair bill** | (parcel's estimated true market value / sum of all parcels' estimated true market value) × total municipal levy. |
| **Dollar delta from fair share** | actual_bill − fair_bill. Positive = parcel overpays; negative = parcel underpays. By construction sums to zero across the town. |
| **Equalization / Director's Ratio** | NJ Treasury annual figure; Fair Haven 2025 = 101.96%. Computed only on recent sales, so it cannot detect inequity in the unsold population. |
| **COD (Coefficient of Dispersion)** | Average absolute deviation of individual assessment ratios from the median ratio, ÷ median, ×100. IAAO standard: ≤15% for residential is acceptable; ≤10% is good. Published in Monmouth's annual MARS report. Computed on recent sales, so subject to the same limitation as the Director's Ratio. |
| **PRD (Price-Related Differential)** | Mean ratio ÷ weighted-mean ratio. >1.03 indicates regressivity (low-value properties over-assessed). |

## 2. Ideal evidence

For each hypothesis, the table below states what would constitute strong, moderate, weak, and falsifying evidence, plus the specific statistical artifacts that would persuade a skeptical reader.

### 2.1 H1, burden skews young/recent

**Strong evidence:** OLS regression of log(annual tax bill) on tenure-cohort dummies, controlling for log(sqft), lot size, year built, bedrooms, bathrooms, and neighborhood fixed effects, shows post-2020 cohort coefficient ≥ +5% with p<0.01 and adjusted-R² > 0.75. Median effective tax rate for the 2020-2026 cohort exceeds the pre-2015 cohort by ≥10% in relative terms. Mann-Whitney U comparing ETR distributions across cohorts shows significant rightward shift for recent cohorts.

**Moderate evidence:** Cohort coefficients positive but modest (+2-4%); statistically significant but explanatory weight competes with property-characteristic controls. Visual cohort bar charts show monotonic gradient.

**Weak evidence:** Direction of effect correct but not statistically distinguishable from zero; effect dissolves under finer geographic controls.

**Falsifying:** Cohort effect is null or reversed (long-tenured owners pay higher ETR per market-value dollar, perhaps because they hold larger / older / more land-heavy parcels that the model values aggressively).

### 2.2 H2: passive sales chasing produces tenure-correlated horizontal inequity

**Strong evidence:** Empirical CDF of assessment-to-sale-price ratios shows a clear discontinuity (cliff) at ratio = 1.0, and `assessr::detect_chasing()` returns TRUE on Fair Haven sales 2018-2025; held-out hedonic model trained on recent sales and applied to the full parcel population produces residuals that are systematically negative for long-tenured parcels (model says they're worth more than the assessor records); per-parcel dollar delta from fair share has a tenure cohort coefficient ≥ +$500 for post-2020 buyers and ≤ -$500 for pre-2015 holders, statistically significant at p<0.01; spatial autocorrelation (Moran's I) on residuals is positive and significant, confirming geographic clustering of underassessment; the sum of negative deltas (total underpayment) maps cleanly onto a long-tenured cohort and the sum of positive deltas (total overpayment) maps onto a recent-buyer cohort.

**Moderate evidence:** CDF discontinuity is visible but `detect_chasing()` returns FALSE; cohort coefficients on dollar delta are directionally correct but smaller than $500; residuals show clustering but Moran's I is borderline.

**Weak evidence:** Tenure coefficient on delta has the right sign but is statistically indistinguishable from zero; CDF is smooth.

**Falsifying:** CDF of assessment-to-sale-price ratios is smooth and centered near 1.0 with no cliff; held-out model residuals show no tenure correlation; per-parcel dollar deltas do not cluster by cohort. **This outcome would mean Monmouth's ADP model is genuinely calibrating against sold and unsold parcels symmetrically, the most demanding standard the system can be held to, and would itself be a publishable result.**

### 2.3 H3, BOE underfunded relative to revenue origin

**Strong evidence:** Fair Haven SD per-pupil spending is materially below Rumson Borough SD (already known to be ~$26,317 vs. ~$21,890, a ~17% gap) and below Little Silver / Shrewsbury after controlling for enrollment scale and special-needs population; BOE share of total levy has declined over a 10-year window while municipal share has risen; tax revenue from the post-2020 cohort (which contains a disproportionate share of school-age children per ACS B11005) substantially exceeds what flows back to schools per child.

**Moderate evidence:** Modest underfunding relative to peers; flat BOE share over time despite enrollment stability.

**Weak evidence:** Spending lags peers but enrollment trend explains most of the gap.

**Falsifying:** Per-pupil spending tracks or exceeds peers; BOE share of levy stable or rising; declining enrollment fully explains any apparent budget pressure (Fair Haven enrollment has been roughly flat-to-slightly-declining at ~954-964 K-8 students 2022-2025).

### 2.4 Persuasive visualizations

A reader-ready dashboard should include: a **scatter plot of assessment-to-market ratio against last sale year** with LOESS smoother and cohort-mean overlays; a **choropleth at parcel level** of dollar delta from fair share, with a diverging color scale centered at zero; **stacked bar charts of cohort tax-bill distribution** (deciles); a **time-series chart of BOE budget vs. total municipal levy vs. CPI** indexed to a common base year; and a **comparative per-pupil spending chart** for Fair Haven, Rumson, Little Silver, and Shrewsbury over a 10-year window. The single most persuasive single-chart artifact is **the parcel-level dollar-delta map** filterable by tenure cohort, which makes the underpayer/overpayer distribution visible at a glance.

## 3. Ideal datasets

The investigation requires fourteen discrete datasets. Each is named below with its specific role in the analysis and its primary source.

**Tier 1 (foundational, must have for MVP):** NJ MOD-IV parcel records (assessed value, building characteristics, sale price/date, deductions, 75-80 fields per parcel) via NJGIN's Monmouth County file geodatabase or Rutgers Bloustein's historical MOD-IV database back to 1989; **NJ statewide parcel polygons** from NJGIN for spatial joins; **NJ Division of Taxation Equalization / Director's Ratio tables** for Fair Haven's annual 100%-true-value standard; **NJ DLGS Property Tax Tables** (Excel, 1998-2025) for historical levy-by-purpose breakdowns; **NJ DOT SR1A sales file** (annual, statewide deed-level with NU codes); **US Census ACS 5-year tables** B25007, B25026, B11005, B19013, B25077, B25103 at block-group level (~3-4 BGs intersect Fair Haven).

**Tier 2 (high-value, beyond MVP):** **Monmouth County OPRS** (`oprs.co.monmouth.nj.us`) for per-parcel sale histories, Property Record Cards, photos, and deed images; **Monmouth County tax appeal judgments** via OPRS (parcel-linked); NJ DOE **Fall Enrollment** workbooks (annual ZIP/Excel, district + school grain, 10+ year archive); NJ DOE **Taxpayers' Guide to Education Spending** (TGES) with 17 indicators per district; NJ DOE **User-Friendly Budget** statewide CSV; **Fair Haven Borough budget archive** at `fairhavennj.org/finance/pages/municipal-budgets` (PDFs back to 2016); **Fair Haven SD budget archive** at `fairhaven.edu` (current + prior year PDFs; older via Wayback Machine); **Monmouth County Clerk deed images** (free online via OPRS Clerk module, post-1970 imaged).

**Tier 3 (supplementary):** **Redfin stingray API endpoints** (reverse-engineered, JSON; market-value proxy for held-out validation); **NJ DCA Construction Reporter** (aggregate permit volumes, Socrata API at `data.nj.gov/Reference-Data/NJ-Construction-Permit-Data/w9se-dmra`); **Monmouth County voter file** via Monmouth Superintendent of Elections (name, address, DOB, party, voter history, for tenure/age overlay where ACS BG-level data is too coarse); **Wayback Machine snapshots** of Fair Haven Borough and SD sites for historical budget docs; **L2/Stephen P. Morse** commercial NJ voter aggregator as backup for the voter file.

**Datasets explicitly excluded:** **MOREMLS / FlexMLS** (not legally accessible without REALTOR® licensure); **NJ MVC vehicle/license data** (DPPA-protected); **parcel-level Fair Haven building permits** (Rumson shared construction office; OPRA-only and high tipoff risk); **Zillow scraping at scale** (heavy anti-bot stack, ToS prohibition; use Redfin instead).

## 4. Data source accessibility table

Color rating: **🟢 GREEN** = anonymous, automatable, free or trivial cost; **🟡 YELLOW** = friction (fee, manual download per record, account, rate limits, or PDF parsing) but still anonymous; **🔴 RED** = formal request required, would tip off Fair Haven, restricted, or legally constrained.

The **MVP-critical** column flags the three datasets needed to ship the parcel-level dollar-delta GeoJSON deliverable described in the appendix.

| # | Dataset | What it provides | Source / URL | Format | Update freq | Access mechanism | Automation | Cost (Fair Haven scale) | Tipoff to FH? | Color | MVP-critical |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | NJGIN Monmouth Parcels + MOD-IV (FGDB/SHP) | Parcel polygons + 75-field assessment records, sale price/date, year built | `njogis-newjersey.opendata.arcgis.com` | FGDB/Shapefile | Annual (spring) | Direct download | Very high | Free | None | 🟢 | **YES** |
| 2 | Rutgers Bloustein MOD-IV Historical DB | MOD-IV time series 1989-present | `modiv.rutgers.edu` | CSV / web search | Annual | Web UI + login | High | Free (registration) | None | 🟢 | No |
| 3 | Monmouth OPRS, Assessment & sales | Per-parcel PRC, photos, sale history, deductions, assessment timeline | `oprs.co.monmouth.nj.us/oprs/External.aspx?iId=12` and `?iId=13` | ASP.NET WebForms | Daily | Scraping (VIEWSTATE replay) | High; ~2,200 parcels trivial | Free | None (county portal) | 🟢 | No |
| 4 | Monmouth OPRS, Tax appeal judgments | Parcel-linked appeal docket, original vs. judgment assessment | `oprs.co.monmouth.nj.us/oprs/CustomSearch/SearchInput.aspx?iId=481` | ASP.NET | Annual cycle | Scraping | High | Free | None | 🟢 | No |
| 5 | NJ Division of Taxation Equalization Tables | Annual Director's Ratio per municipality back to ~2003 | `nj.gov/treasury/taxation/lpt/county_equalized.shtml` | PDF | Annual | Stable URL pattern | Medium (PDF parsing) | Free | None | 🟢 | Optional |
| 6 | NJ DOT SR1A Sales File | Statewide deed-level sales w/ NU codes | `nj.gov/treasury/taxation/lpt/statdata.shtml` | Bulk file | Annual | Direct download | High | Free (redacted); OPRA to DOT for unredacted | None to FH (Treasury, not borough) | 🟢 | **YES** |
| 7 | NJ DLGS Property Tax Tables (1998-2025) | Annual levy by purpose: muni / county / school / regional / open space | `nj.gov/dca/dlgs/resources/Property_Tax_info.shtml` | Excel | Annual | Stable URL pattern (`YYtaxes.xls`) | Very high | Free | None | 🟢 | **YES** |
| 8 | NJ DLGS UFB Database (datahub) | All municipalities since 2015, staffing, debt, spending categories | `datahub.dca.nj.gov/datasets/user-friendly-budget-database` | CSV/API | Annual | API/download | Very high | Free | None | 🟢 | No |
| 9 | US Census API + IPUMS NHGIS | ACS 5-year B25007/B25026/B11005/B19013/B25077/B25103 at BG | `api.census.gov/data/2023/acs/acs5`; `nhgis.org` | JSON / CSV | Annual | API (free key) | Very high | Free | None | 🟢 | No (v2) |
| 10 | Census Geocoder API | Address → tract + block group | `geocoding.geo.census.gov` | JSON | Real-time | Batch endpoint | Very high | Free | None | 🟢 | No (v2) |
| 11 | NJ DOE Fall Enrollment workbooks | District/school enrollment by grade, race, FRPL | `nj.gov/education/doedata/enr/` | Excel ZIP | Annual | Direct download | Very high | Free | None | 🟢 | No (H3) |
| 12 | NJ DOE TGES (per-pupil spending) | 17 indicators per district; comparable district benchmarks | `nj.gov/education/guide/2025tges.shtml` | HTML/Excel | Annual | Scrape / download | High | Free | None | 🟢 | No (H3) |
| 13 | NJ DOE School Performance Reports | District/school PDFs + downloadable databases 2011-2024 | `nj.gov/education/sprreports/` | PDF + DB | Annual | Stable URL by CC-DDDD code | High (DB), medium (PDF) | Free | None | 🟢 | No |
| 14 | Fair Haven Borough budget PDFs | Adopted budgets, UFBs 2016-2025; AFR | `fairhavennj.org/finance/pages/municipal-budgets` | PDF | Annual | Direct download | Medium (PDF parsing) | Free | Low (web logs only) | 🟢 | No |
| 15 | Fair Haven SD budget PDFs | BOE budget, ACFR, AMR, meeting minutes | `fairhaven.edu/district/administration/business_office_school_budget` | PDF | Annual | Direct download | Medium | Free | Low (small site) | 🟢 | No |
| 16 | Wayback Machine archives | Pre-2020 Fair Haven Borough/SD content | `web.archive.org` | HTML/PDF | Variable | Direct fetch | Medium | Free | None | 🟢 | No |
| 17 | NJGIN parcel polygons (statewide) | Spatial join key | `njogis-newjersey.opendata.arcgis.com` | SHP/FGDB/REST | Annual | Direct download | Very high | Free | None | 🟢 | (in #1) |
| 18 | Monmouth County Clerk deed images | Full deed PDFs post-1970, indexed pre-1970 | `oprs.co.monmouth.nj.us/oprs/clerk/ClerkHome.aspx?op=basic` | Web/PDF | Real-time | Scraping | High | Free online (cert. copies $10+) | None | 🟢 | No |
| 19 | NJ DCA Construction Reporter | Aggregate permit volumes by muni-month | `data.nj.gov/Reference-Data/NJ-Construction-Permit-Data/w9se-dmra` | Socrata API | Monthly | API | Very high | Free | None | 🟢 | No |
| 20 | Monmouth County voter file | Name, address, DOB, party, voter history | Monmouth County Superintendent of Elections (OPRA-equivalent) | CSV/Excel | On request | Per N.J.S.A. 19:31-18.1 | Manual request, then automatable | ≤$375 statutory cap | None to FH (county-level) | 🟡 | No (v2) |
| 21 | Statewide voter file (commercial) | Same fields, statewide | L2 Inc.; Stephen P. Morse NJ tool | CSV | Periodic | Purchase | High | $200-$1,500 typical | None | 🟡 | No |
| 22 | Redfin stingray endpoints | Active listings, sale history, Estimate | `redfin.com/stingray/api/...` (reverse-engineered) | JSON | Real-time | Scraping (proxy advised) | Medium | $0-$100 in proxy costs | None | 🟡 | No (v2) |
| 23 | Zillow listings & Zestimates | Comp data; market-value proxy | `zillow.com` | HTML/JSON | Real-time | Heavy anti-bot; commercial scraping APIs | Low without paid API | $50-$500/mo if needed | None | 🟡 | No |
| 24 | NJ DOT SR1A unredacted detail | Pre-redaction grantor/grantee | OPRA to NJ Treasury | OPRA | On request | Formal request | N/A | Statutory copy fees | None to FH | 🟡 | No |
| 25 | RFH Regional apportionment formula | Regional school cost-share formula | RFH UFB (`rumsonfairhaven.org`) | PDF | Annual | Direct download | Medium (PDF parsing) | Free | Low | 🟢 | No (H3) |
| 26 | Fair Haven parcel-level building permits | Per-parcel permit history (additions, renovations) | Rumson shared construction office | OPRA | On request | Manual request | None pre-OPRA | Copy fees | **High** (small shared office; staff would notice) | 🔴 | No |
| 27 | Fair Haven internal assessor correspondence | Reassessment methodology notes; AFR-A applications | OPRA to Fair Haven Clerk | OPRA | On request | Formal request | None | Copy fees | **Highest** (clerk + assessor see request) | 🔴 | No |
| 28 | Fair Haven BOE internal budget worksheets | Detail beyond published UFB | OPRA to BOE Business Administrator | OPRA | On request | Formal request | None | Copy fees | **High** (small district) | 🔴 | No |
| 29 | MOREMLS / FlexMLS | Active and sold MLS listings | Monmouth Ocean Regional REALTORS | License-gated | Real-time | REALTOR® license required | None | License + dues; not realistically obtainable | None | 🔴 | No |
| 30 | Daniel's Law-protected residents list | Identity of covered persons (judges, prosecutors, LEOs) requiring address suppression | OIP Daniel's Law Portal (`danielslaw.nj.gov`) | Registry | Continuous | Register as Redactor | High | Free | None | 🟡 | Pre-publication only |

**Bottom line on accessibility:** Approximately **95% of the data needed to test all three hypotheses is in the green zone**, anonymous, free, automatable, and invisible to Fair Haven Borough. **The MVP requires only three datasets (#1, #6, #7), all green, all single-shot downloads.** The two genuinely red items (parcel-level permits, internal assessor methodology) are not necessary for the primary analyses.

## 5. Acquisition plan per source

### 5.1 Order of operations, cheap-to-expensive validation pyramid

The MVP appendix at the end of this document collapses steps 1-3 into a single executable pipeline. The fuller acquisition sequence below applies to v2 work after MVP.

1. **Levy structure baseline:** Pull NJ DLGS Property Tax Tables for 1998-2025; build a 28-year time series of Fair Haven's levy-by-purpose. Pull NJ DOT Equalization Tables for the same window. This single artifact tells you whether the BOE share of total levy has shifted, whether municipal share has risen, and how the Director's Ratio has tracked. **It may resolve H3 directionally on its own.**
2. **Parcel universe:** Download NJGIN's Monmouth County Parcels+MOD-IV file geodatabase. Filter to district 14 (Fair Haven). You now have ~2,200 parcels with current assessed value, year built, square footage, lot size, building class. Note: OWNER_NAME is redacted in the NJOGIS distribution per Daniel's Law, that's fine for the primary analysis, which is parcel-level not person-level.
3. **Sales history + PRC scraping:** Build a Playwright scraper for Monmouth OPRS (`oprs.co.monmouth.nj.us`), starting with the Sales Data view (`iId=13`) filtered to district 14, then per-parcel PRC fetches. Use sticky-session ASP.NET pattern with VIEWSTATE replay; rate-limit to 1-2 requests/second; identifying user-agent with a contact email; respect robots.txt. ~2,200 parcels × 2-3 page hits = ~5,000 requests, completable at conservative pacing. Capture: full sale history (date, price, NU code, deed reference), PRC building details, photo URLs. **Note: for MVP this step is unnecessary because MOD-IV's per-parcel last-sale fields are sufficient. OPRS scraping is needed for v2 multi-sale history per parcel.**
4. **Tax appeal cohort:** Scrape the OPRS tax-appeal-judgments search (`iId=481`) for Fair Haven for all available years. This identifies parcels that have *successfully* challenged their assessment, likely a self-selected subset of long-tenured owners with sophistication or motivation. Their cohort distribution is itself an important descriptive signal.
5. **SR1A and Director's Ratio history:** Pull SR1A annual files from NJ Treasury for 2018-2025; parse for Fair Haven sales with NU codes filtered. This is the same data Treasury uses to compute the Director's Ratio, using it directly lets you replicate Treasury's calculation and then run it within tenure cohorts, which Treasury does not publish.
6. **Census ACS join:** Use Census Geocoder API to map every Fair Haven parcel address to its block group; pull ACS 5-year tables B25007, B25026, B11005, B19013, B25077, B25103 at BG level via the Census API; join to parcel data. This produces the demographic overlay required for the "young families" claim.
7. **Schools & comparables:** Download NJ DOE Fall Enrollment workbooks for 2014-2025; pull TGES per-pupil spending for Fair Haven, Rumson Borough, Little Silver, Shrewsbury Borough, RFH Regional, and Red Bank Regional; download Fair Haven SD ACFR and BOE budget PDFs. Pull the RFH Regional UFB to extract the apportionment formula between Fair Haven and Rumson. Pull NJ DLGS UFB Database from datahub.
8. **Market-value validation:** Run Redfin stingray endpoints for Fair Haven properties to retrieve current market estimates and recent comp sales; cross-reference with held-out 2024-2026 OPRS sales to validate the assessment-to-market-value ratio per parcel. This is supplemental to the hedonic model approach in §6.
9. **Voter file overlay (yellow, ≤$375):** File a written request with the **Monmouth County Superintendent of Elections** under N.J.S.A. 19:31-18.1 for the Fair Haven voter list (name, address, DOB, party, history). Cost capped at $375 statewide per calendar year. Crucially, this request goes to the **county**, not to Fair Haven Borough, invisible to the town. As an alternative, purchase L2's NJ slice (~$200-$500) for an even cleaner under-the-radar acquisition. Include a non-commercial-use certification per statute.
10. **Optional yellow expansion:** OPRA NJ Treasury for unredacted SR1A detail (no tipoff to Fair Haven). Register with the Daniel's Law Portal as a Redactor before any public publication.

### 5.2 Specific tools and scraping notes

For the OPRS ASP.NET WebForms scraper, use **Playwright (Python)** rather than `requests`; the VIEWSTATE/EVENTVALIDATION token replay is brittle in raw HTTP. Persist a single browser context with cookies; navigate via the Sales Data form, set district = 14, iterate by date range, then deep-link into each parcel's PRC. Respect a 1-2 second pacing floor. For Census, use **`censusdata`** or direct `requests` against the API; for ACS at BG level, you'll need both state FIPS 34 and county FIPS 025 plus tract codes obtained via TIGER intersection. For PDF parsing of NJ DOT Equalization Tables and DLGS files, use **`pdfplumber`** or **`camelot`**; the file paths follow predictable annual patterns. Store everything in a **PostgreSQL + PostGIS** database keyed by PAMS_PIN (Fair Haven's parcel identifier).

For the sales-chasing detection and Berry tax-shift calculation, the canonical reference implementation is the **Cook County Assessor's Office `assessr` R package** (open source, GPL). The `detect_chasing()` function is roughly 50 lines and trivially reimplementable in Python/scipy.

### 5.3 Should the red sources be pursued?

**Recommendation: do not file OPRA with Fair Haven Borough or Rumson construction office at the start of the investigation.** OPRA filings, even anonymous ones, are visible to the responding agency, anonymous filers lose appeal rights to the Government Records Council per N.J.S.A. 47:1A-6, and an anonymous filing requires 100% deposit upfront for any request over $5. The investigative direction also becomes apparent from the request text itself; in a small borough with tight municipal-assessor-BOE social ties, this is operationally equivalent to a public announcement. The yellow alternatives (Monmouth County OPRS scraping, county voter file, Census, NJOGIS bulk) deliver the analytical core without the visibility cost. **Only file OPRA with Fair Haven if and when** the green/yellow analysis surfaces a specific question that *requires* an internal document (e.g., the assessor's mass-appraisal model parameters, the exact AFR-A application, internal BOE budget worksheets) and the user is prepared to be visible.

### 5.4 Bulk MOD-IV, confirmed pathways

The user should rely on the **NJGIN Open Data hub** for bulk MOD-IV. The Monmouth-only file geodatabase contains parcel polygons joined to MOD-IV with all 75 fields except OWNER_NAME (redacted statewide post-Daniel's Law). For historical assessment time series, **Rutgers Bloustein's MOD-IV Historical Database** (`modiv.rutgers.edu`) exposes 1989-present via a free-with-registration interface. The **NJACTB website** (`njactb.org`) historically provided MOD-IV and SR1A statewide but **discontinued public access on January 1, 2023** in compliance with Daniel's Law. Existing GitHub tooling (**`johnjreiser/NJParcelTools`**) provides Python+PostgreSQL scripts that download and ingest NJGIN MOD-IV/parcel files; reuse this rather than reinventing.

## 6. Analysis methodology

### 6.1 Sales-chasing detection and the Berry tax-shift calculation (primary analyses)

The two most important analyses, in order:

**(a) CDF gap test for sales chasing.** Pull all Fair Haven arms-length sales 2018-2025 from SR1A (NU codes 0/7/10/26/33). For each sale, compute the assessment-to-sale-price ratio using the assessment in effect the year of the sale. Plot the empirical CDF of those ratios. Run the CCAO's open-source `assessr::detect_chasing()` (R package, also reimplementable in Python in ~50 lines) which combines a CDF gap method and a distribution comparison method to detect the cliff signature. A TRUE return means recent sales were appraised at or near sale price tighter than the rest of the population, the technical IAAO definition of sales chasing per Indiana 50 IAC 27-2-11 and the IAAO Standard on Ratio Studies (April 2013).

**(b) Berry tax-shift calculation.** This is the deliverable. Steps:

1. Train a hedonic model `log(sale_price) ~ log(sqft) + log(lot_size) + year_built + bedrooms + bathrooms + spatial_component` on Fair Haven sales 2023-2025 (the held-in training set).
2. Apply the model to all ~2,200 parcels in MOD-IV to produce an estimated true market value per parcel.
3. Compute `fair_bill_i = (true_value_i / Σ true_value_j) × total_levy`.
4. Compute `actual_bill_i = assessed_value_i × tax_rate`.
5. Compute `delta_i = actual_bill_i − fair_bill_i`. By construction Σ delta_i = 0; the distribution of deltas is the inequity.
6. Tabulate the sum of positive deltas (total dollars overpaid) and sum of negative deltas (total dollars underpaid) by tenure cohort. Berry's Cook County analyses produced the headline numbers $1.7B and $2.2B with this method. Fair Haven's expected scale is much smaller (total levy ~$45M) but the relative pattern is the question.

**(c) Cohort descriptive backbone (supporting).** Bucket parcels by year of last arms-length sale into five cohorts: pre-2010, 2010-2015, 2016-2019, 2020-2022, 2023-2026. For each cohort compute: median delta_i, mean delta_i, share of cohort in the underpaying tail, share in the overpaying tail, median current annual tax bill. Report COD and PRD overall and by cohort against IAAO standards (COD ≤15% acceptable for residential, PRD between 0.98 and 1.03 acceptable). Reproduce the figure that appears annually in Monmouth's MARS report but stratified by cohort.

### 6.2 Regression analysis (inferential layer on top of the Berry calculation)

Estimate `delta_i = α + β₁·cohort + β₂·log(sqft) + β₃·log(lot_size) + β₄·year_built + β₅·bedrooms + β₆·bathrooms + γ·neighborhood_FE + ε`, with cohort as a categorical with pre-2015 as reference. Report cohort coefficients with HC3 robust standard errors. Cluster standard errors by census block group. Repeat with `log(annual_tax_bill)` and `log(effective_tax_rate)` as alternative DVs. **Robustness checks:** (a) drop top/bottom 1% on each property characteristic; (b) add interactions between cohort and `year_built` to detect renovation/age effects; (c) restrict to single-family detached (class 2) only; (d) instrument cohort with neighborhood-level new-construction permit density (from NJ DCA aggregate) to address selection.

### 6.3 Geographic / spatial analysis

Compute per-parcel residual from a hedonic model trained on 2024-2026 sales; map residuals at parcel level via a choropleth (using NJGIN parcel polygons). Test for spatial autocorrelation via **Moran's I** on residuals and on per-parcel deltas. Identify any block groups or street-level clusters where long-tenured owners systematically under-assess relative to recent buyers. The user's intuition about "Gaussian blobs around recent sales" is formally a **spatial-lag hedonic model** in the Can (1992) / Pace, Barry, Clapp & Rodriguez (1998) tradition. The standard implementation uses an inverse-distance or k-nearest-neighbors weight matrix W; PySAL (`pysal.lib.weights.KNN` or `DistanceBand`) is the Python tooling. For v1 use simple neighborhood fixed effects; introduce a spatial-lag term in v2 if Moran's I on the v1 residuals is significant.

### 6.4 Demographic overlay

Join parcel-level data to ACS 5-year estimates at the block-group level via spatial join. For each parcel, attach the BG-level: median age of householder, share of households with own children under 18 (B11005), share of households who moved in 2020 or later (B25026), median household income (B19013). Test whether **tax bill decile correlates with school-age-children share** (Spearman rank correlation, expected positive) and with **householder age** (expected negative, more recent movers tend younger). If the Monmouth voter file is acquired, repeat the age and tenure analysis at parcel grain (matching by address) for far higher fidelity than ACS BG-level estimates. This is the analysis that most directly addresses the user's "young families" framing.

### 6.5 BOE funding longitudinal analysis

Build a 15-year time series (2010-2025) using DLGS Property Tax Tables: **municipal levy, county levy, local school levy, regional school levy** in nominal and CPI-adjusted dollars; same series as **share of total levy**. Overlay enrollment from NJ DOE Fall Enrollment workbooks and per-pupil spending from TGES. Compare year-over-year growth rates of BOE budget vs. municipal budget vs. CPI vs. NJ statewide K-8 average. Compute **per-pupil spending Z-score** for Fair Haven against the four comparable Monmouth K-8/regional districts (Rumson Borough, Little Silver, Shrewsbury Borough, Red Bank Regional). Decompose the RFH Regional apportionment between Fair Haven and Rumson using the formula extracted from the RFH UFB: this matters because if the formula leans on equalized property value (as is common), Fair Haven's recent rapid appreciation would mechanically increase its regional school share even without enrollment growth, a structural mechanism worth surfacing whether or not it favors the user's narrative. Triangulate against the publicly listed 2025 levy split ($0.713 local + $0.277 regional = $0.990 of $1.574 total = 62.9% to schools).

### 6.6 Sensitivity and robustness

Re-run all primary analyses excluding waterfront parcels (assessment models systematically struggle with waterfront), excluding class 4 (commercial) parcels, and using alternative cohort cutoffs (2018 vs. 2020 as the post-COVID threshold). Compute the analyses on Rumson Borough as a placebo town, same regional HS, similar demographics, same ADP cycle, to confirm that any Fair Haven cohort effect is local rather than a Monmouth-wide ADP artifact. Document all data-quality issues (missing PRC fields, NU code ambiguities, address-to-BG geocoding failures).

### 6.7 Outputs

A reproducible Jupyter / Quarto notebook with all SQL queries and Python regressions; a parcel-level GeoJSON with per-parcel delta, ETR, cohort flag, and last sale date for the public-facing dashboard; a series of PNG/SVG figures for static reporting; a methodology white paper documenting every transformation. The dashboard itself should aggregate to the block-group level for any **publicly displayed maps** to limit individual identifiability and Daniel's Law exposure (see §7).

## 7. Legal and ethical considerations

### 7.1 Open Public Records Act (OPRA), N.J.S.A. 47:1A-1 et seq.

Written request to records custodian; **7 business days** statutory response window; copy fees of $0.05/page (letter), $0.07/page (legal), **electronic delivery free**. Special service charges allowed for extraordinary effort. **Anonymous filing is permitted** under N.J.S.A. 47:1A-5(f) but anonymous requesters lose the right to file Denial-of-Access complaints with the GRC under 47:1A-6, meaning if the request is denied, the requester has no recourse short of refiling under their real name. Anonymous requests over $5 require 100% deposit; over $25 require 50% deposit (or $10 anonymous deposit). Appeal paths are mutually exclusive: GRC (free, slow) or Superior Court Law Division (45-day deadline, $250 filing fee, faster). Prevailing requesters are entitled to attorneys' fees if the agency "knowingly and willfully" violated OPRA. **Critical operational point: any OPRA filing reveals to the responding agency that someone is asking, and what they are asking, even if filed anonymously the request text itself betrays investigative direction.**

### 7.2 Voter rolls, N.J.S.A. 19:31-18.1

Public fields per NJ statute: **name, residential address, date of birth, party affiliation, voter history since registration**. Restricted: SSN, driver's license, signature; addresses for domestic-violence/stalking-program enrollees. Cost capped statewide at $375 per calendar year; non-commercial / non-charitable-solicitation use only (violation = disorderly persons offense, fine up to $500). Request goes to county Superintendent of Elections, **invisible to Fair Haven Borough**.

### 7.3 Driver's Privacy Protection Act, 18 U.S.C. § 2721

DPPA covers MVC records and prohibits joining MVC-derived personal info absent one of 14 enumerated permissible uses. Civil penalty floor: $2,500 liquidated damages plus attorneys' fees. **DPPA does not cover voter rolls or property tax records**, joining MOD-IV with the NJ voter file is not a DPPA issue. **Avoid all MVC-sourced data** to eliminate this risk vector entirely.

### 7.4 NJ uniformity clause, Article VIII, Section 1

The NJ Constitution requires assessment "by uniform rules" and at "the same standard of value." The constitutional requirement is **equal ratio of assessed-to-true-value across the taxing district, not equal absolute amounts.** Foundational cases: *In re Appeal of Kents*, 34 N.J. 21 (1961); *Switz v. Middletown Township*, 23 N.J. 580 (1957); *Murnick v. Asbury Park*, 95 N.J. 452 (1984) (Chapter 123 is the exclusive remedy for assessment discrimination except in "egregious cases" where constitutional rights are violated); ***West Milford v. Van Decker*, 120 N.J. 354 (1990)** holds that "spot assessments" or "welcome stranger" reassessments triggered solely by sale of property are unconstitutional under the uniformity clause. *Allegheny Pittsburgh Coal v. Webster County*, 488 U.S. 336 (1989) is the federal analogue. **The H2 finding from §6.1, if positive, is the statistical evidence underlying a Van Decker-style argument**: even though no individual assessor in Fair Haven is intentionally spot-reassessing post-sale, the mass-appraisal model produces the same pattern as a matter of structural information asymmetry. In ADP towns the ±15% Chapter 123 corridor effectively does not apply because assessments must equal 100% of true value annually, which means a Fair Haven taxpayer's bar to challenge an over-assessment is materially lower than a typical NJ taxpayer's.

### 7.5 Daniel's Law, N.J.S.A. 47:1B-1 et seq.

Protects active, formerly active, and retired **judicial officers, prosecutors, law enforcement officers, and child protective investigators**, plus immediate family members in the same household. Two prongs: (1) government websites must redact home address upon request via the OIP Daniel's Law Portal (`danielslaw.nj.gov`); (2) **private persons, businesses, and associations must cease publishing protected information within 10 business days of written notice.** 2023 amendments made $1,000-per-violation statutory damages mandatory and assignable. Constitutionality upheld in *Atlas Data Privacy Corp. v. We Inform, LLC* (D.N.J., December 2024). **Operational mandate for the public dashboard:** register as a Redactor with the OIP portal; cross-reference the protected list before publication; suppress matched parcels or redact owner names while retaining aggregate statistics. **Strongly prefer aggregate / block-group-level maps for public display**; reserve parcel-level granularity for the investigator's private analytic database.

### 7.6 Defamation, false light, anti-SLAPP

Property tax fairness is a matter of public concern, attracting heightened First Amendment protection. Truthful publication of lawfully obtained public-records data is generally protected. NJ's **Uniform Public Expression Protection Act**, N.J.S.A. 2A:53A-49 to -56 (effective October 7, 2023), provides anti-SLAPP protection: special motion to dismiss within 60 days of service, automatic discovery stay, mandatory attorneys' fees to prevailing movant on matters of public concern. **Best-practice rules for the public site:** stick to verifiable facts (assessment, sale price, calculated ratio, dollar delta from fair share); avoid imputing motives ("dodging," "cheating") that imply false fact; frame analysis as systemic critique rather than individual indictment; disclose all data sources and methodology to support fair-comment defenses; explicitly filter out Daniel's Law-protected persons; default public visualizations to aggregate / BG level.

### 7.7 Web scraping legality

After *Van Buren v. United States*, 593 U.S. 374 (2021) and *hiQ v. LinkedIn*, 31 F.4th 1180 (9th Cir. 2022), scraping publicly accessible websites without authentication is generally not a CFAA violation. Terms-of-service violations are civil contract claims, not criminal. The Monmouth County OPRS portal has no clickwrap; scraping it with reasonable rate limits, an identifying user-agent with contact email, and respect for `robots.txt` is the recommended legal posture.

### 7.8 Tipoff risk hierarchy (consolidated)

From least to most visible to Fair Haven officials: bulk MOD-IV / NJOGIS / Census downloads (invisible) → county-level voter file request to Monmouth Superintendent of Elections (invisible to borough) → scraping Monmouth OPRS (county-logged IP only; not relayed to borough) → attending public BOE/Council meetings as observer (anonymous) → OPRA via attorney or MuckRock to Fair Haven (medium; intermediary visible) → anonymous OPRA to Fair Haven (medium; investigative direction revealed in request text) → speaking at BOE/Council meetings (high; minutes are public) → OPRA filed under own name with Fair Haven (highest; clerk knows requester and content). **Operate in the bottom four tiers exclusively until the analysis is mature enough to make a public case.**

## 8. Risk assessment for the hypotheses

### 8.1 What ADP rules out and what it does not

Fair Haven's 2025 Director's Ratio of **101.96%** is a town-wide aggregate, computed from the population of recent sales. By construction it cannot detect the inequity H2 targets, because the parcels that drive it (long-held, never recently sold) are absent from the ratio's input set. Likewise the published COD is computed against recent sales and tells you how tightly the model fits its training data, not how well it generalizes to the held-out population.

What ADP does rule out is the *legal* version of welcome-stranger: an assessor cannot in 2026 walk through a town reassessing only the houses that just sold, because every parcel must be revalued every year. *Van Decker* and *Allegheny Pittsburgh* both addressed this overt practice. ADP makes that pattern impossible.

What ADP does not rule out is the *statistical* version: a mass-appraisal model where recent sales serve as ground truth produces tighter assessments around those sales than around comparable unsold parcels, regardless of intent. The discontinuous jump observed at every Fair Haven sale (assessment moves to roughly the sale price the next assessment cycle) is the visible artifact of this. If the same model is meanwhile undershooting the appreciation rate on long-held parcels, the gap accumulates. Section 6.1's Berry tax-shift calculation is the test. ADP performance at the aggregate ratio level neither confirms nor refutes it.

### 8.2 Composition / selection effects on H1

Even if H1 holds, post-2020 movers do pay disproportionately, the cause may not be unfair assessment. Fair Haven's post-2020 buyers self-selected into a market with sharply appreciated prices; they bought larger or more recently renovated homes than the long-tenured stock; they paid a premium for proximity to the Blue Ribbon school district. Their higher tax bills may simply reflect that they bought more house. The regression in §6.2 explicitly controls for this with property characteristics, but residual selection (on unobservables like renovation quality post-purchase) cannot be fully eliminated. **The user should report the cohort coefficient both before and after controls and explicitly characterize what fraction of the raw cohort gap is explained by composition.** "New movers pay more because they bought bigger newer houses" is a true and policy-relevant finding, but it is a different finding from "new movers are unfairly over-assessed."

### 8.3 Counter-hypotheses the data might support

The investigation should be prepared to surface alternatives: (a) **The system is actually working**, Monmouth ADP delivers COD ≤10%, no detectable cohort signal in dollar deltas; Fair Haven's tax burden distribution reflects what residents bought, not how it's assessed. (b) **The inequity runs the other way**, long-tenured owners hold larger, more valuable lots with extensive grandfathered improvements, and pay *higher* absolute bills though lower effective rates against contemporaneous market value. (c) **The real story is the regional school apportionment**, RFH Regional's Fair Haven/Rumson cost-share formula, leaning on equalized property value, mechanically shifts cost toward whichever town appreciates faster, regardless of enrollment. Post-2020 appreciation in Fair Haven could be driving its regional share up independent of any local assessment issue. (d) **The real story is enrollment composition**, Fair Haven SD's per-pupil spending lag vs. Rumson Borough is real (~$21,890 vs. ~$26,317), but flat-to-declining K-8 enrollment (~954-964 students 2022-2025) may explain it without needing to invoke "underfunding" intent.

### 8.4 Confounders to control explicitly

Lot size (Fair Haven has substantial lot-size variance), waterfront frontage, year built clusters (interwar vs. postwar vs. modern construction), proximity to the Navesink River, school catchment microzones, condition grade from the most recent ADP inspection cycle, presence of senior/veteran/disabled deductions, and any active tax appeals or freeze-act protection. Several of these are in the MOD-IV record; condition-grade decay must be inferred from inspection-year flags on the PRC.

### 8.5 What would change the user's mind

If the CDF gap test returns FALSE, if held-out hedonic residuals show no tenure correlation, if per-parcel deltas don't cluster by cohort, if BOE share of total levy is stable or rising over a 10-year window, and if per-pupil spending tracks comparable districts after adjusting for enrollment trend, **H1, H2, and H3 are jointly falsified** and the investigation's most honest output is a public report explaining that Fair Haven's tax distribution is structurally fair under the metrics tested. The investigator should commit to publishing the result either way before seeing the data; that pre-commitment is what distinguishes investigation from advocacy.

## Concluding takeaways

The H2 reframe (passive sales chasing rather than stale assessments) preserves the spirit of the user's hypothesis while replacing a likely-falsified mechanism with the right statistical test, anchored to a literature with a sitting US Supreme Court case (*Allegheny Pittsburgh*) and a NJ Supreme Court case (*Van Decker*) and a publicly-validated methodology (Berry, Cook County, $1.7B-$2.2B tax-shift findings). The data-acquisition strategy is dominated by green-zone sources that together deliver ~95% of analytical needs invisibly to Fair Haven Borough; OPRA filings to the borough should be treated as a last resort. Daniel's Law and the NJ Uniform Public Expression Protection Act jointly define the publication envelope. The MVP appendix below collapses the entire H1+H2 test into three downloads and one Python pipeline.

---

# Appendix: MVP path to the parcel-level dollar-delta GeoJSON

**Deliverable.** A single GeoJSON file: ~2,200 Fair Haven parcel polygons, each tagged with `assessed_value`, `estimated_true_value`, `fair_bill`, `actual_bill`, `delta_dollars`, `tenure_cohort`, `last_sale_date`, `last_sale_price`. Rendered on a Leaflet/Mapbox basemap with `delta_dollars` as the color scale, diverging palette centered at zero. Filterable by cohort. Sales-chasing CDF gap test result stamped at the top.

## Inputs (three downloads, all green Tier 1)

1. **NJGIN Monmouth Parcels + MOD-IV file geodatabase** (one HTTP download). Provides parcel polygons, current assessed value, year built, sqft, lot size, building class, bedroom/bathroom counts, most recent sale date and price, and NU code per parcel.
2. **NJ DLGS Property Tax Tables** (one Excel download). Gives the exact 2026 Fair Haven general tax rate ($1.574 per $100) and the total municipal levy.
3. **NJ DOT SR1A annual files for 2020-2025**. Validates and extends the sales history that's already in MOD-IV's per-parcel single-most-recent-sale field, and provides the input for the CDF gap test.

That is it. No scraping, no OPRA, no voter file, no Census, no Redfin.

## Pipeline

1. **Load and filter.** Read the Monmouth FGDB with geopandas. Filter to MUN_CODE = 1314 (Fair Haven). Confirm parcel count ~2,200 and total assessed value ~$2.77B against the published Fair Haven figures. Drop class 4 (commercial), class 15 (exempt), and any parcels with missing core fields. Keep class 2 (residential).

2. **Build the training set.** From SR1A 2023-2025, retain Fair Haven sales with NU codes in {0, 7, 10, 26, 33}. Cross-check against MOD-IV's last-sale fields. Expect roughly 200-400 usable arms-length sales over three years given town size and turnover.

3. **Fit the hedonic.** `log(sale_price) ~ log(sqft) + log(lot_size) + year_built + bedrooms + bathrooms + waterfront_flag + neighborhood_FE`, where `neighborhood_FE` comes from k-means clustering on parcel centroids (k=5 to 8). Statsmodels OLS with HC3 robust SEs. Sanity check: R² should be >0.7 for a town this homogeneous; if not, add a spatial-lag term via PySAL.

4. **Predict.** Apply the model to all ~2,200 parcels. This produces `estimated_true_value` per parcel. Sum across the population. The aggregate should land near $2.83B (Fair Haven total true value cited in DLGS); if it's off by more than ~5%, the model has a level bias and needs a constant correction before proceeding.

5. **Compute fair vs actual.** Total levy L is read from the DLGS table. `fair_bill_i = (estimated_true_value_i / Σ estimated_true_value) × L`. `actual_bill_i = assessed_value_i × 0.01574`. `delta_i = actual_bill_i − fair_bill_i`. Verify Σ delta_i ≈ 0 to within rounding.

6. **Tag tenure.** From the last-sale-date field, assign each parcel to one of the five cohorts (pre-2010, 2010-2015, 2016-2019, 2020-2022, 2023-2026).

7. **Run the CDF gap test.** Reimplement `assessr::detect_chasing()` in Python (~50 lines from the assessr R source). Run it on the SR1A sales 2018-2025. Record TRUE/FALSE and the CDF plot.

8. **Export.** Write a single GeoJSON with all the per-parcel fields above. Build a static Leaflet HTML page with a diverging color scale, a tenure cohort filter, and a popup showing per-parcel detail. Daniel's Law: before publication, run owner names through the OIP redactor portal; for the public version, suppress owner names entirely and show only the parcel-level financials.

## What you have at the end of step 8

A static HTML map. Open it on your phone. Filter to "purchased before 2010" and you see the underpaying distribution. Filter to "purchased after 2020" and you see the overpaying distribution. The aggregate dollar shifts are computed and displayed. The CDF gap test result is stamped at the top: sales chasing detected, yes/no.

## What this MVP excludes

Census demographic overlay; voter-file age cross-reference; BOE longitudinal funding analysis; comparative per-pupil spending vs Rumson/Little Silver/Shrewsbury; spatial-lag Gaussian weighting (just simple neighborhood FEs in v1); any OPRA-derived material. All of those are v2 enhancements once the v1 artifact tells you whether the core hypothesis has signal at all. **Build v1 first; let the data argue for the v2 effort.**

## Decision gate after MVP

Three possible outcomes:

1. **Berry calculation shows tenure-correlated dollar shift > ~$200K in absolute terms across cohorts (small relative to ~$45M total levy but meaningful per household), AND the CDF gap test confirms sales chasing.** The hypothesis is supported. v2 work is justified: Census overlay, voter-file age cross-reference, spatial-lag refinement, BOE analysis, public-facing dashboard with full interactivity.

2. **Mixed: one test positive, one negative.** Diagnostic. Investigate why and what the residual structure looks like. Possibly the model needs a spatial-lag term to surface the signal; possibly the discontinuity test is being washed out by Monmouth's annual reassessment cycle smoothing the cliff.

3. **Both null.** The hypothesis is falsified. The artifact pivots to a methodology demonstration: "Monmouth ADP works as intended in Fair Haven, here is the proof, here is the methodology that anyone can apply to their own town." That itself is publishable and useful.

## Critical-path summary

Three downloads, one Python pipeline, one HTML output. Everything else in the research plan is v2 and beyond.
