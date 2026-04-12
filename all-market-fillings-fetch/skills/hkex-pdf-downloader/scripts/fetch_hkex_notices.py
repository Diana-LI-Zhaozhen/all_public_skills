import argparse
import json
import re
import urllib.request
from pathlib import Path


HKEX_BASE = "https://www1.hkexnews.hk"


def build_feed_url(page: int, board: str, window: str, lang: str) -> str:
    board_part = "sehk" if board.lower() == "sehk" else "gem"
    window_part = "1" if window.lower() == "latest" else "7"
    lang_part = "e" if lang.lower().startswith("e") else "c"
    filename = f"lci{board_part}{window_part}relsd{lang_part}_{page}.json"
    return f"{HKEX_BASE}/ncms/json/eds/{filename}"


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


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch HKEX notices and filter report-like PDFs")
    parser.add_argument("--stock-codes", default="", help="Comma-separated stock codes, e.g. 00700,09988")
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
    parser.add_argument("--timeout", type=int, default=25)
    parser.add_argument("--output-json", required=True)
    args = parser.parse_args()

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

    # Keep newest first based on feed order; per-type latest returns one per stock+type.
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

    output = {
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

    out_path = Path(args.output_json)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved {len(final_rows)} items -> {out_path}")


if __name__ == "__main__":
    main()