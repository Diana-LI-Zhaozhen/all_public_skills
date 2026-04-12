---
name: cninfo-pdf-fetch
description: "Fetch CNInfo PDF reports by company and report type. Use when the user asks in Chinese like 给我茅台最新的年报/半年报/季度报告, or asks for 公告 PDF 下载 from cninfo.com.cn. Handles parsing, filtering, latest selection, fallback search, and output formatting."
argument-hint: "例如: 给我茅台最新的年报和半年报"
user-invocable: true
disable-model-invocation: false
---

# CNInfo PDF Fetch

## What This Skill Produces
- Download-ready CNInfo PDF links for requested reports.
- Local PDF files saved to a workspace output folder.
- A concise result list containing company, report type, title, announcement date, and direct PDF URL.
- Clear fallback behavior when data is missing, ambiguous, or temporarily unavailable.

## When to Use
- User asks for CNInfo report PDFs.
- User asks in Chinese for latest 年报, 半年报, 季度报告.
- User asks for a specific company report announcement document from http://www.cninfo.com.cn/new/index.jsp.

## Supported Request Patterns
- 给我茅台最新的年报
- 给我茅台最新的半年报和季度报告
- 下载贵州茅台最近三年的年报 PDF
- 帮我找宁德时代最新三季报

## Procedure
1. Parse user intent.
2. Resolve company identity.
3. Map requested report types.
4. Query CNInfo announcements.
5. Select the newest matching document per report type.
6. Build and validate PDF links.
7. Download PDFs to local folder.
8. Return results with quality checks.

## Fixed Defaults For This Skill
- 季度报告 means both 第一季度报告 and 第三季度报告 when available.
- If company name matching is ambiguous, auto-pick the A-share main listing.
- Always provide links and also download files.

## Step Details

### 1) Parse User Intent
- Extract company name or stock code.
- Extract report types:
  - 年报: annual report
  - 半年报: semi-annual report
  - 季度报告: includes 第一季度报告 and 第三季度报告
- Extract time scope:
  - If user says 最新, default to latest available in each requested type.
  - If user specifies a year or range, filter accordingly.

### 2) Resolve Company Identity
- Normalize company aliases (for example, 茅台 -> 贵州茅台).
- Resolve to a unique CNInfo security code first, because company names may change over time.
- Build alias set from observed historical names (for example old/new short names) and include stock code as a query term.
- If multiple matches exist, auto-pick the A-share main listing and explicitly note this assumption.

### 3) Map Report Types to CNInfo Categories
- Use category filters consistent with CNInfo announcement categories.
- Recommended mapping:
  - 年报 -> annual report category
  - 半年报 -> semi-annual report category
  - 季度报告 -> quarterly report category
- If endpoint category codes change, fall back to title keyword filtering:
  - 年度报告, 半年度报告, 第一季度报告, 第三季度报告

### 4) Query CNInfo Announcements
- Prefer the CNInfo announcement query endpoint flow.
- Sort by announcement time descending.
- Query enough rows to reliably find reports (increase page size or paginate if needed).
- Restrict by security code first, then report category/keywords.
- When user asks by company name, expand search terms to: original name + resolved stock code + discovered aliases.
- Recommended script: scripts/fetch_cninfo_notices.py (company query + report types + time mode).

### 5) Select Best Match Per Type
- For each requested type, choose the newest valid report document.
- Exclude common false positives by title keyword:
  - 摘要, 英文版, 更正公告, 提示性公告 (unless user asked for these)
- For 季度报告, return newest 第一季度报告 and newest 第三季度报告.

### 6) Build and Validate PDF URL
- Build direct PDF URL from CNInfo response fields (for example by combining the static host with adjunct path).
- Validate each URL looks like a PDF document link.
- If a direct URL is unavailable, provide the announcement detail page link and state why.

### 7) Download PDFs to Local Folder
- If stage-1 output is not already normalized, convert records into downloader input JSON using scripts/build_download_items_json.py.
- Save files under `./downloads/cninfo/<company>/`.
- Use file names in this shape:
  - `<date>_<company>_<report-type>_<title>.pdf`
- Sanitize invalid filename characters before saving.
- Skip re-downloading if the same file already exists.
- If download fails for one file, continue with others and report failed items.

### 8) Return Result
- Return concise structured output in Chinese.
- Preferred output table columns:
  - 公司
  - 报告类型
  - 公告标题
  - 公告日期
  - PDF 链接
  - 本地文件路径
- If missing types exist, include a short missing-data note.

## Decision Logic
- If company is ambiguous: auto-pick A-share listing and continue.
- If old/new company names differ: keep using resolved stock code as primary filter and use name aliases only as recall expansion.
- If query returns no data for requested period: relax period to latest and explain fallback.
- If endpoint temporarily fails: retry with a smaller request; then fall back to website search flow.
- If multiple near-identical files exist: prefer full report over summary/abstract versions.

## Quality Criteria
- At least one result per requested report type, or explicit not-found status.
- All returned links are CNInfo-origin links and point to PDF resources when possible.
- Date sorting is correct (newest first).
- Local files are saved with readable, unique names.
- Output clearly states assumptions and fallback behavior.

## Completion Checklist
- Company resolved and confirmed.
- Requested report types fully mapped.
- Results filtered for true report documents.
- Latest document selection verified.
- Files downloaded to local folder.
- Output includes links and local paths plus short caveats when needed.

## Notes
- Keep responses in Chinese if the user asks in Chinese.
- Do not fabricate links or report titles.
- If CNInfo content is unavailable at runtime, explicitly report the failure reason and return best-effort alternatives.
- For downloading, prefer using scripts/download_cninfo_pdfs.py after URLs are collected.
