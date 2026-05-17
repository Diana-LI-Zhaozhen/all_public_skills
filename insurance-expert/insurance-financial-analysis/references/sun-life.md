# Sun Life Financial / 永明金融 (SLF) — IFRS 17 Analysis Reference
## Annual Reports FY2023-2025 (SEC EDGAR 40-F)
### Analyzed: 2026-05-17

> ⚠️ **Limited SEC data**: All 3 years (FY2023-FY2025) are cover-only iXBRL filings. No IFRS 17 financial metrics (revenue, CSM, balance sheet) available from SEC. Full financial statements filed as exhibits to the 40-F or on Canadian SEDAR+.

## Filing Details

| Report | Filing Date | Source | Status |
|--------|-------------|--------|--------|
| FY2023 40-F | 2024-02-08 | SEC EDGAR | ⚠️ Cover only (1.8MB HTM, 377KB TXT) |
| FY2024 40-F | 2025-02-13 | SEC EDGAR | ⚠️ Cover only (1.7MB HTM, 360KB TXT) |
| FY2025 40-F | 2026-02-12 | SEC EDGAR | ⚠️ Cover only (1.8MB HTM, 364KB TXT) |

## What's Available

| Metric | Value |
|--------|-------|
| Reinsurance retention policy | 40% (FY2025, FY2024) / 50% (FY2023) |
| Actuarial pension assumptions | 0.00%-0.20% |

## What's NOT Available from SEC EDGAR
- ❌ Insurance Revenue (IFRS 17)
- ❌ CSM balances and movements
- ❌ Investment portfolio breakdown
- ❌ Balance sheet and income statement
- ❌ NBV, Embedded Value, ROE

## Company Profile

| Item | Detail |
|------|--------|
| Stock code | SLF (NYSE/TSX) |
| Status | Pure life insurer |
| Headquarters | Toronto, Canada |
| Regions | Canada, US, Asia (Hong Kong, China, Philippines, etc.), Asset Management |
| IFRS basis | Reports under IFRS 17 |

## Data Source Notes
- Sun Life is a Canadian filer — full 40-F exhibits contain financial statements but are NOT in iXBRL format
- Canadian filings also available via SEDAR+
- SLF is NOT listed in Hong Kong (no H-share)
- To complete this analysis: download full annual reports from Sun Life IR website

## SEC 40-F Cover-Only Issue — Resolution Path

**Root cause:** Canadian issuers filing Form 40-F with SEC submit only a cover page as the primary document. The filing index shows exhibits (`a2025q4slfmdalive.htm` - MD&A, `annualaifmasterlivermasterq.htm` - AIF) but these are pointers accessible through SEC's interactive iXBRL viewer.

**SEC EDGAR exhibits are blocked** — attempts to download exhibit files return SEC error pages ("Your Request Originates from an Undeclared Automated Tool").

**To fix:**

### Option A: Download via SEC iXBRL Viewer (requires browser)
```
https://www.sec.gov/ix?doc=/Archives/edgar/data/1097362/0001097362-26-000010/slf-20251231.htm
```

### Option B: Download from Sun Life Investor Relations
Go to https://www.sunlife.com/en/investors/ → Annual Reports section
Sun Life publishes full annual reports as downloadable PDFs.

### Option C: SEDAR+ (Canadian securities regulator)
Search for "Sun Life Financial" at https://www.sedarplus.ca/
Note: SEDAR+ blocks automated access; requires manual browser interaction.

See `pdf-encoding-troubleshooting` skill for full workflow on SEC 40-F cover-only filings.
