import argparse
import json
import re
import urllib.request
import urllib.parse
from datetime import date
from pathlib import Path


HKEX_BASE = "https://www1.hkexnews.hk"


# ── Shared utilities (keep existing API) ──────────────────────────────

def get_json(url: str, timeout: int) -> dict:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; hkex-pdf-downloader/1.0)",
            "Accept": "application/json,text/plain,*/*",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8", errors="ignore"))


def post_form(url: str, data: dict[str, str], timeout: int) -> str:
    """POST form-encoded data and return response text."""
    encoded = urllib.parse.urlencode(data).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=encoded,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; hkex-pdf-downloader/1.0)",
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "text/html,application/xhtml+xml,*/*",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="ignore")


def get_text(url: str, timeout: int) -> str:
    """GET plain text from a URL."""
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; hkex-pdf-downloader/1.0)",
            "Accept": "text/plain,*/*",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="ignore")


def normalize_stock_code(code: str) -> str:
    text = (code or "").strip()
    if not text:
        return ""
    if text.isdigit():
        return text.zfill(5)
    return text


def parse_stock_codes(raw: str) -> set[str]:
    return {normalize_stock_code(x) for x in raw.split(",") if normalize_stock_code(x)}


def parse_report_types(raw: str) -> set[str]:
    out: set[str] = set()
    for x in [s.strip().lower() for s in raw.split(",") if s.strip()]:
        if x in {"annual", "year", "yearly", "年报", "年報"}:
            out.add("annual")
        elif x in {"interim", "semi", "中报", "中報", "中期"}:
            out.add("interim")
        elif x in {"quarterly", "quarter", "季报", "季報"}:
            out.add("quarterly")
        elif x in {"results", "业绩", "業績"}:
            out.add("results")
        elif x in {"esg"}:
            out.add("esg")
        elif x in {"financial", "财务", "財務"}:
            out.add("financial")
        elif x in {"all", "*"}:
            out.add("all")
    if not out:
        out = {"annual", "interim", "quarterly", "results", "esg", "financial"}
    return out


def classify_report_type(title: str, category_long: str, t1_code: str) -> str | None:
    hay = " ".join([title or "", category_long or ""]).lower()
    if re.search(r"annual\s+report|年報|年报", hay):
        return "annual"
    if re.search(r"interim\s+report|中期報告|中期报告|中報|中报", hay):
        return "interim"
    if re.search(r"quarterly\s+report|季度報告|季度报告|季報|季报", hay):
        return "quarterly"
    if re.search(r"final\s+results|interim\s+results|quarterly\s+results|業績|业绩", hay):
        return "results"
    if re.search(r"\besg\b|環境.?社會.?管治|环境.?社会.?治理", hay):
        return "esg"
    if t1_code == "40000" or re.search(r"financial\s+statements?|財務報表|财务报表", hay):
        return "financial"
    return None


def to_output_item(record: dict, stock: dict, report_type: str) -> dict:
    web_path = str(record.get("webPath") or "").strip()
    return {
        "company": str(stock.get("sn") or "").strip(),
        "stockCode": normalize_stock_code(str(stock.get("sc") or "").strip()),
        "reportType": report_type,
        "title": str(record.get("title") or "").strip(),
        "date": str(record.get("relTime") or "").strip(),
        "url": f"{HKEX_BASE}{web_path}",
        "webPath": web_path,
        "newsId": str(record.get("newsId") or "").strip(),
        "ext": str(record.get("ext") or "").strip().lower(),
        "t1Code": str(record.get("t1Code") or "").strip(),
    }


# ── Feed mode (existing JSON feed, 7-day limit) ───────────────────────

def build_feed_url(page: int, board: str, window: str, lang: str) -> str:
    board_part = "sehk" if board.lower() == "sehk" else "gem"
    window_part = "1" if window.lower() == "latest" else "7"
    lang_part = "e" if lang.lower().startswith("e") else "c"
    filename = f"lci{board_part}{window_part}relsd{lang_part}_{page}.json"
    return f"{HKEX_BASE}/ncms/json/eds/{filename}"


def run_feed_mode(args: argparse.Namespace) -> dict:
    """Original JSON-feed mode — covers only recent 7 days."""
    stock_filter = parse_stock_codes(args.stock_codes)
    wanted_types = parse_report_types(args.report_types)
    pdf_only = args.pdf_only == "true"

    rows: list[dict] = []
    for page in range(1, max(1, args.pages) + 1):
        url = build_feed_url(page=page, board=args.board, window=args.window, lang=args.lang)
        payload = get_json(url=url, timeout=args.timeout)
        records = payload.get("newsInfoLst") or []
        if not isinstance(records, list):
            continue

        for record in records:
            if not isinstance(record, dict):
                continue
            stocks = record.get("stock") or [{"sc": "", "sn": ""}]
            ext = str(record.get("ext") or "").strip().lower()
            if pdf_only and ext != "pdf":
                continue

            for stock in stocks:
                if not isinstance(stock, dict):
                    continue
                code = normalize_stock_code(str(stock.get("sc") or "").strip())
                if stock_filter and code not in stock_filter:
                    continue

                report_type = classify_report_type(
                    title=str(record.get("title") or ""),
                    category_long=str(record.get("lTxt") or ""),
                    t1_code=str(record.get("t1Code") or ""),
                )
                if not report_type:
                    continue
                if "all" not in wanted_types and report_type not in wanted_types:
                    continue

                rows.append(to_output_item(record=record, stock=stock, report_type=report_type))

    # Deduplicate by stock+newsId+url
    uniq: dict[str, dict] = {}
    for row in rows:
        key = f"{row.get('stockCode')}|{row.get('newsId')}|{row.get('url')}"
        if key not in uniq:
            uniq[key] = row
    deduped = list(uniq.values())

    final_rows: list[dict]
    if args.per_type_mode == "latest":
        picked: dict[str, dict] = {}
        for row in deduped:
            k = f"{row.get('stockCode')}|{row.get('reportType')}"
            if k not in picked:
                picked[k] = row
        final_rows = list(picked.values())
    else:
        final_rows = deduped

    return {
        "board": args.board,
        "window": args.window,
        "lang": args.lang,
        "pages": args.pages,
        "stockCodes": sorted(stock_filter),
        "reportTypes": sorted(wanted_types),
        "pdfOnly": pdf_only,
        "perTypeMode": args.per_type_mode,
        "count": len(final_rows),
        "items": final_rows,
    }


# ── Annual-by-year mode (HKEX Disclosure title search, full history) ──

def resolve_stock(stock_code: str, timeout: int) -> tuple[int, str]:
    """Resolve HKEX internal stockId and stock name via prefix search."""
    code = stock_code.strip().zfill(5)
    url = f"{HKEX_BASE}/search/prefix.do"
    params = urllib.parse.urlencode({
        "callback": "callback",
        "lang": "EN",
        "type": "A",
        "name": code,
        "market": "SEHK",
    })
    full_url = f"{url}?{params}"

    text = get_text(full_url, timeout=timeout)
    text = text.strip()

    # JSONP format: callback({...});
    start = text.find("(")
    end = text.rfind(")")
    if start < 0 or end <= start:
        raise ValueError(f"Unexpected stock search response for {stock_code}")

    payload = json.loads(text[start + 1 : end])
    items = payload.get("stockInfo") or []
    for item in items:
        item_code = str(item.get("code") or "").strip().zfill(5)
        if item_code == code:
            return int(item["stockId"]), str(item.get("name") or "").strip()

    raise ValueError(f"Stock code not found on HKEX: {stock_code}")


def search_titlesearch(
    stock_id: int,
    from_date: str,
    to_date: str,
    timeout: int,
    title_keyword: str = "",
    t1code: str = "",
    t2gcode: str = "",
    t2code: str = "",
    market: str = "SEHK",
    lang: str = "EN",
) -> str:
    """POST to HKEX title search and return raw HTML."""
    data = {
        "lang": lang,
        "market": market,
        "searchType": "1",
        "documentType": "",
        "t1code": t1code,
        "t2Gcode": t2gcode,
        "t2code": t2code,
        "stockId": str(stock_id),
        "from": from_date,
        "to": to_date,
        "category": "0",
        "title": title_keyword,
    }
    return post_form(f"{HKEX_BASE}/search/titlesearch.xhtml", data, timeout=timeout)


def _normalize_title(raw: str) -> str:
    no_tags = re.sub(r"<[^>]+>", "", raw)
    return re.sub(r"\s+", "", no_tags).strip().lower()


def _extract_pdf_entries(html: str) -> list[tuple[str, str, str | None]]:
    """Extract (path, label, release_time) from title search HTML."""
    entries: list[tuple[str, str, str | None]] = []
    row_blocks = re.findall(r"<tr[^>]*>.*?</tr>", html, flags=re.IGNORECASE | re.DOTALL)
    for row in row_blocks:
        link_match = re.search(
            r'href="(/listedco/listconews/[^"]+\.pdf)"[^>]*>(.*?)</a>',
            row,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if not link_match:
            continue
        path, label = link_match.group(1), link_match.group(2)
        release_match = re.search(r"(\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2})", row)
        release_dt = release_match.group(1) if release_match else None
        entries.append((path, label, release_dt))

    if not entries:
        # Fallback: parse from whole page
        fallback = re.findall(
            r'href="(/listedco/listconews/[^"]+\.pdf)"[^>]*>(.*?)</a>',
            html,
            flags=re.IGNORECASE | re.DOTALL,
        )
        for path, label in fallback:
            entries.append((path, label, None))

    return entries


def find_annual_report_url(
    stock_code: str,
    year: int,
    timeout: int,
) -> str | None:
    """Find a HKEX annual report PDF URL for given stock code and year.

    Uses multiple keyword & date-range strategies to maximise hit rate.
    Returns the best (most-relevant, most-recent) URL or None.
    """
    stock_id, stock_name = resolve_stock(stock_code, timeout=timeout)

    keywords = ["年度報告", "年報", "annual report", "annual"]
    negative_tokens = ["摘要", "summary", "sustainability", "esg", "持續督導", "督導"]
    annual_tokens = ["年度報告", "年報", "annualreport"]
    year_token = str(year)

    candidate_urls: list[tuple[str, str, str | None]] = []  # (url, label, release_dt)

    for keyword in keywords:
        for from_date, to_date in (
            (f"{year}0101", f"{year}1231"),
            (f"{year + 1}0101", f"{year + 1}1231"),
        ):
            html = search_titlesearch(
                stock_id=stock_id,
                from_date=from_date,
                to_date=to_date,
                title_keyword=keyword,
                timeout=timeout,
            )

            entries = _extract_pdf_entries(html)
            for path, label, release_dt in entries:
                full_url = f"{HKEX_BASE}{path}"
                candidate_urls.append((full_url, label, release_dt))

    if not candidate_urls:
        return None

    def _quality_score(label: str) -> int:
        label_norm = _normalize_title(label)
        score = 0
        if year_token in label_norm:
            score += 100
        if any(token in label_norm for token in annual_tokens):
            score += 100
        if any(token in label_norm for token in negative_tokens):
            score -= 80
        if label_norm.endswith("年度報告") or label_norm.endswith("年報"):
            score += 30
        return score

    # Deduplicate by URL
    seen: set[str] = set()
    unique: list[tuple[str, str, str | None]] = []
    for url, label, dt in candidate_urls:
        if url not in seen:
            seen.add(url)
            unique.append((url, label, dt))

    # Pick best by quality score, newest wins ties
    unique.sort(key=lambda x: (_quality_score(x[1]), x[2] or ""), reverse=True)
    return unique[0][0]


def run_annual_by_year_mode(args: argparse.Namespace) -> dict:
    """Search HKEX Disclosure title search API for annual reports by year.

    Supports full historical search (not limited to 7 days).
    """
    stock_codes = sorted(parse_stock_codes(args.stock_codes))
    if not stock_codes:
        raise ValueError("--stock-codes is required for annual-by-year mode")

    current_year = date.today().year
    years_range = list(range(current_year - 1, current_year - args.years - 1, -1))

    rows: list[dict] = []
    for stock_code in stock_codes:
        stock = stock_code.zfill(5)
        for year_val in years_range:
            try:
                url = find_annual_report_url(
                    stock_code=stock,
                    year=year_val,
                    timeout=args.timeout,
                )
                if not url:
                    rows.append({
                        "stockCode": stock,
                        "reportType": "annual",
                        "year": year_val,
                        "status": "missing",
                        "error": f"No annual report URL found for {year_val}",
                    })
                    print(f"[MISS] {stock} {year_val} no annual report found")
                    continue

                rows.append({
                    "stockCode": stock,
                    "reportType": "annual",
                    "year": year_val,
                    "status": "found",
                    "url": url,
                    "title": f"{year_val} annual report",
                    "date": str(year_val),
                    "company": stock,
                })
                print(f"[FOUND] {stock} {year_val} -> {url}")
            except Exception as exc:
                rows.append({
                    "stockCode": stock,
                    "reportType": "annual",
                    "year": year_val,
                    "status": "failed",
                    "error": str(exc),
                })
                print(f"[ERR] {stock} {year_val} | {exc}")

    found = sum(1 for r in rows if r.get("status") == "found")
    missing = sum(1 for r in rows if r.get("status") == "missing")
    failed = sum(1 for r in rows if r.get("status") == "failed")

    return {
        "mode": "annual-by-year",
        "stockCodes": stock_codes,
        "years": years_range,
        "count": len(rows),
        "items": rows,
        "totals": {
            "found": found,
            "missing": missing,
            "failed": failed,
        },
    }


# ── Main ──────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch HKEX notices — feed mode (recent 7d) or annual-by-year mode (full history via title search)"
    )
    parser.add_argument(
        "--mode",
        choices=["feed", "annual-by-year"],
        default="feed",
        help="'feed' = JSON feed (recent 7 days only); 'annual-by-year' = HKEX Disclosure title search (full history)",
    )

    # Shared args
    parser.add_argument("--stock-codes", default="", help="Comma-separated stock codes, e.g. 00700,09988")
    parser.add_argument("--timeout", type=int, default=25)
    parser.add_argument("--output-json", required=True)

    # Feed mode args
    parser.add_argument("--board", choices=["sehk", "gem"], default="sehk")
    parser.add_argument("--window", choices=["latest", "7days"], default="latest")
    parser.add_argument("--lang", choices=["c", "e"], default="c")
    parser.add_argument("--pages", type=int, default=3)
    parser.add_argument(
        "--report-types",
        default="annual,interim,quarterly,results,esg,financial",
        help="Comma-separated: annual,interim,quarterly,results,esg,financial,all",
    )
    parser.add_argument("--pdf-only", choices=["true", "false"], default="true")
    parser.add_argument("--per-type-mode", choices=["latest", "all"], default="latest")

    # Annual-by-year mode args
    parser.add_argument("--years", type=int, default=3, help="Number of recent years to search (annual-by-year mode only)")

    args = parser.parse_args()

    if args.mode == "annual-by-year":
        if not args.stock_codes.strip():
            parser.error("--stock-codes is required for annual-by-year mode")
        output = run_annual_by_year_mode(args)
    else:
        output = run_feed_mode(args)

    out_path = Path(args.output_json)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved {output.get('count', 0)} items -> {out_path}")


if __name__ == "__main__":
    main()
