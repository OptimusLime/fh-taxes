# OPRS Sample Artifacts

This directory previously held HTML + PDF responses from `tax1.co.monmouth.nj.us`
for two test parcels (block 3 lot 33 and block 10 lot 14). They were used to
develop the parsing logic in `datasets/collect_oprs.py` and `src/fairhaven_tax/`.

The samples have been moved to `docs/specs/.local_samples/` (gitignored) because
they contain real owner names from public Fair Haven assessor records. The
project's operational posture is under-the-radar relative to the town and
identifiable PII does not belong in a public repository.

## Regenerating the samples

```bash
# Confirm the collector is configured for Fair Haven
uv run python -c "
from datasets.collect_oprs import _new_session, fetch_component
from pathlib import Path
sess = _new_session()
out = Path('docs/specs/.local_samples')
for pin in ['1314_3_33', '1314_10_14']:
    fetch_component(sess, pin, 'm4.html', out, 2)
"
```

## Field reference (from the parser's perspective)

`m4.cgi&hist=1` returns a "Property Detail" page with these labeled fields:

- Block / Lot / Qual / District / Class
- Prop Loc, Street, City State, Zip
- Square Ft, Year Built, Style (1-9 typology code)
- Bldg Desc (compact code like `2S-AL-O-DG-1U`)
- Land Desc (lot dimensions like `75X150`), Acreage, Zone, Map Page
- Updated date (assessor's last record touch — proxy for ADP inspection cycle)
- Taxes (1st-half / 2nd-half)
- Sale Information section (most recent sale)
- Sr1a sale-history table (date, book, page, price, NU code, ratio, grantee)
- TAX-LIST-HISTORY (8 years of land/improvement/total assessments with `&hist=1`)

`sr.cgi?ssi=N&block=B&lot=L` returns sale-detail page per ssi:

- Date Recorded, R.T. fee, RTF Exempt code
- Grantor name + address
- Grantee name + address
- Block / Class / Lot / Cl.4 Type / Qual / Condo flag
- Year-of-sale assessment: Year, Land, Buildings, Total
- Property Location, Floor Area (sqft), Year Built
- REMARKS field
- RATIO (sales ratio)
- "SALES BETWEEN IMMEDIATE FAMILY" flag
- Additional blocks/lots × 5 slots
- NU code, Serial number

`prc.cgi?h00=B&h01=L&h02=&ccdd=1314` redirects to a session-bound PDF at
`/tmp/prc-1314-B-L--{rand}.pdf`. The upstream Apache returns the PDF binary
with `Content-Type: text/html`, so the response body has HTTP headers
prepended — slice from the `%PDF` marker to extract the real PDF.

The PDF includes structural fields the HTML view omits: bedrooms, bathrooms,
room count, kitchen count, story breakdowns, garage/porch/patio sqft,
fireplaces, AC type, heating type, exterior material, roof type/material,
foundation, condition grade, sewer/water service, topography, road type, and
sketch geometry.

`taxlist.cgi?h00=B&h01=L&h02=&year=Y&ccdd=1314` and
`ch75.cgi?h00=B&h01=L&h02=&i24=2&ccdd=1314` work the same way (HTML frame
that loads a session-bound PDF). These are valid PDFs (no header-stripping
needed).
