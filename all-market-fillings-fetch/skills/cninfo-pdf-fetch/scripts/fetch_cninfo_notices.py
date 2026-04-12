import argparse
import collections
import json
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


API_URL = "http://www.cninfo.com.cn/new/hisAnnouncement/query"
PDF_BASE_URL = "https://static.cninfo.com.cn/"

DEFAULT_HEADERS = {
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Referer": "http://www.cninfo.com.cn/new/commonUrl/pageOfSearch?url=disclosure/list/search",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "X-Requested-With": "XMLHttpRequest",
}

EXCLUDE_KEYWORDS = ["摘要", "英文版", "更正", "提示性公告"]


def parse_report_types(text: str) -> set[str]:
    requested = {x.strip() for x in text.split(",") if x.strip()}
    mapped: set[str] = set()
    for item in requested:
        if item in {"annual", "year", "yearly", "年报"}:
            mapped.add("annual")
        elif item in {"semi_annual", "semi", "half", "半年报"}:
            mapped.add("semi_annual")
        elif item in {"quarterly", "季度", "季度报告"}:
            mapped.update({"q1", "q3"})
        elif item in {"q1", "一季报"}:
            mapped.add("q1")
        elif item in {"q3", "三季报"}:
            mapped.add("q3")
    if not mapped:
        mapped = {"annual", "semi_annual", "q1", "q3"}
    return mapped


def classify_report_type(title: str) -> str | None:
    # Match only formal periodic report titles and avoid generic notices.
    if re.search(r"(第一季度报告|一季度报告|1季度报告)", title):
        return "q1"
    if re.search(r"(第三季度报告|三季度报告|3季度报告)", title):
        return "q3"
    if re.search(r"(半年度报告|半年报)", title):
        return "semi_annual"
    if re.search(r"(年度报告|年报)", title):
        return "annual"
    return None


def contains_excluded(title: str) -> bool:
    extra_excluded = ["业绩说明会", "问询函", "回复", "提示"]
    return any(k in title for k in EXCLUDE_KEYWORDS + extra_excluded)


def to_date_str(ts_or_date: str) -> tuple[str, datetime | None]:
    if not ts_or_date:
        return "", None
    text = str(ts_or_date).strip()
    if re.fullmatch(r"\d{13}", text):
        dt = datetime.fromtimestamp(int(text) / 1000, tz=timezone.utc)
        return dt.strftime("%Y-%m-%d"), dt
    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S"):
        try:
            dt = datetime.strptime(text, fmt)
            return dt.strftime("%Y-%m-%d"), dt
        except ValueError:
            continue
    return text, None


def in_time_scope(date_dt: datetime | None, mode: str, year: int | None, range_years: int | None) -> bool:
    if mode == "latest":
        return True
    if date_dt is None:
        return False
    if mode == "year":
        return year is not None and date_dt.year == year
    if mode == "range":
        if not range_years:
            return True
        now_year = datetime.now().year
        return date_dt.year >= now_year - range_years + 1
    return True


def fetch_page(searchkey: str, page_num: int, page_size: int, timeout: int) -> dict:
    payload = {
        "pageNum": str(page_num),
        "pageSize": str(page_size),
        "column": "szse",
        "tabName": "fulltext",
        "plate": "",
        "stock": "",
        "searchkey": searchkey,
        "secid": "",
        "category": "",
        "trade": "",
        "seDate": "",
    }
    request = urllib.request.Request(
        API_URL,
        data=urllib.parse.urlencode(payload).encode("utf-8"),
        headers=DEFAULT_HEADERS,
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8", errors="ignore"))


def resolve_code_and_aliases(company_query: str, timeout: int) -> tuple[str | None, list[str]]:
    """Resolve a stable stock code from a name-like query and gather observed aliases.

    This uses announcement hits to infer the dominant secCode and related secName values.
    """
    if not company_query:
        return None, []

    counter: collections.Counter[str] = collections.Counter()
    code_to_names: dict[str, set[str]] = {}

    for page in range(1, 4):
        result = fetch_page(company_query, page_num=page, page_size=50, timeout=timeout)
        anns = result.get("announcements") or []
        if not anns:
            break

        for ann in anns:
            code = str(ann.get("secCode") or ann.get("seccode") or "").strip()
            name = str(ann.get("secName") or ann.get("secname") or "").strip()
            if not code:
                continue
            counter[code] += 1
            if code not in code_to_names:
                code_to_names[code] = set()
            if name:
                code_to_names[code].add(name)

        if not result.get("hasMore"):
            break

    if not counter:
        return None, []

    resolved_code, _ = counter.most_common(1)[0]
    aliases = sorted(code_to_names.get(resolved_code, set()))
    return resolved_code, aliases


def normalize_ann(ann: dict) -> dict:
    sec_name = str(ann.get("secName") or ann.get("secname") or "").strip()
    sec_code = str(ann.get("secCode") or ann.get("seccode") or "").strip()
    title = str(ann.get("announcementTitle") or ann.get("announcementtitle") or "").strip()
    adjunct = str(ann.get("adjunctUrl") or ann.get("adjuncturl") or "").strip()
    time_raw = str(ann.get("announcementTime") or ann.get("announcementtime") or "").strip()
    date_str, date_dt = to_date_str(time_raw)
    return {
        "secName": sec_name,
        "secCode": sec_code,
        "announcementTitle": title,
        "adjunctUrl": adjunct,
        "announcementTime": time_raw,
        "date": date_str,
        "date_dt": date_dt,
    }


def to_output_item(rec: dict, report_type: str) -> dict:
    return {
        "company": rec["secName"],
        "reportType": report_type,
        "title": rec["announcementTitle"],
        "date": rec["date"],
        "adjunctUrl": rec["adjunctUrl"],
        "url": f"{PDF_BASE_URL}{rec['adjunctUrl'].lstrip('/')}",
        "announcementTime": rec["announcementTime"],
    }


def report_keywords(report_type: str) -> list[str]:
    if report_type == "annual":
        return ["年度报告", "年报"]
    if report_type == "semi_annual":
        return ["半年度报告", "半年报"]
    if report_type == "q1":
        return ["第一季度报告", "一季度报告"]
    if report_type == "q3":
        return ["第三季度报告", "三季度报告"]
    return []


def title_matches_report_type_exact(title: str, report_type: str) -> bool:
    if report_type == "annual":
        if "半年度报告" in title or "半年报" in title:
            return False
        return "年度报告" in title or "年报" in title
    if report_type == "semi_annual":
        return "半年度报告" in title or "半年报" in title
    if report_type == "q1":
        return "第一季度报告" in title or "一季度报告" in title or "1季度报告" in title
    if report_type == "q3":
        return "第三季度报告" in title or "三季度报告" in title or "3季度报告" in title
    return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch and filter CNInfo notices for report PDFs.")
    parser.add_argument("--company-query", required=True, help="Company name or stock keyword, e.g. 贵州茅台")
    parser.add_argument(
        "--report-types",
        default="annual,semi_annual,q1,q3",
        help="Comma-separated: annual,semi_annual,q1,q3,quarterly",
    )
    parser.add_argument("--time-mode", choices=["latest", "year", "range"], default="latest")
    parser.add_argument("--year", type=int, default=None)
    parser.add_argument("--range-years", type=int, default=None)
    parser.add_argument("--page-size", type=int, default=30)
    parser.add_argument("--max-pages", type=int, default=5)
    parser.add_argument("--timeout", type=int, default=25)
    parser.add_argument("--stock-code", default=None, help="Optional exact stock code filter, e.g. 600750")
    parser.add_argument(
        "--company-aliases",
        default=None,
        help="Optional comma-separated company name aliases. Keep records when secName contains one alias.",
    )
    parser.add_argument(
        "--enable-precise-fallback",
        choices=["true", "false"],
        default="true",
        help="Enable alias+keyword fallback queries to improve recall for renamed companies.",
    )
    parser.add_argument(
        "--per-type-mode",
        choices=["latest", "all"],
        default="latest",
        help="latest: one newest file per type; all: keep all matched files per type",
    )
    parser.add_argument("--output-json", required=True, help="Output stage-1 JSON path")
    args = parser.parse_args()

    requested_types = parse_report_types(args.report_types)
    user_aliases = [x.strip() for x in (args.company_aliases or "").split(",") if x.strip()]
    resolved_code, resolved_aliases = resolve_code_and_aliases(args.company_query, timeout=args.timeout)
    effective_stock_code = args.stock_code or resolved_code

    # Expand query terms with resolved aliases and code to survive company renames.
    query_terms: list[str] = []
    for term in [args.company_query, effective_stock_code, *resolved_aliases, *user_aliases]:
        if term and term not in query_terms:
            query_terms.append(term)

    company_aliases = sorted({*resolved_aliases, *user_aliases})
    records: list[dict] = []

    for term in query_terms:
        for page in range(1, args.max_pages + 1):
            result = fetch_page(term, page, args.page_size, args.timeout)
            anns = result.get("announcements") or []
            if not anns:
                break
            for ann in anns:
                records.append(normalize_ann(ann))
            if not result.get("hasMore"):
                break

    selected_latest: dict[str, dict] = {}
    selected_all: list[dict] = []
    seen_urls: set[str] = set()

    for rec in records:
        if effective_stock_code and rec.get("secCode") != effective_stock_code:
            continue

        if company_aliases:
            sec_name = rec.get("secName") or ""
            if not any(alias in sec_name for alias in company_aliases):
                continue

        title = rec["announcementTitle"]
        if not title or contains_excluded(title):
            continue

        report_type = classify_report_type(title)
        if report_type is None or report_type not in requested_types:
            continue

        if not in_time_scope(rec["date_dt"], args.time_mode, args.year, args.range_years):
            continue

        if not rec["adjunctUrl"]:
            continue

        url = f"{PDF_BASE_URL}{rec['adjunctUrl'].lstrip('/')}"
        if args.per_type_mode == "all":
            if url in seen_urls:
                continue
            seen_urls.add(url)
            selected_all.append(
                {
                    "company": rec["secName"],
                    "reportType": report_type,
                    "title": rec["announcementTitle"],
                    "date": rec["date"],
                    "adjunctUrl": rec["adjunctUrl"],
                    "url": url,
                    "announcementTime": rec["announcementTime"],
                    "date_dt": rec["date_dt"],
                }
            )
            continue

        prev = selected_latest.get(report_type)
        if prev is None:
            selected_latest[report_type] = rec
            continue

        prev_dt = prev.get("date_dt")
        cur_dt = rec.get("date_dt")
        if prev_dt is None and cur_dt is not None:
            selected_latest[report_type] = rec
        elif prev_dt is not None and cur_dt is not None and cur_dt > prev_dt:
            selected_latest[report_type] = rec

    output_items = []
    if args.per_type_mode == "all":
        selected_all.sort(
            key=lambda x: (
                x["reportType"],
                x["date_dt"] or datetime.min.replace(tzinfo=timezone.utc),
            ),
            reverse=True,
        )
        for rec in selected_all:
            item = rec.copy()
            item.pop("date_dt", None)
            output_items.append(item)
    else:
        for report_type in sorted(selected_latest.keys()):
            rec = selected_latest[report_type]
            output_items.append(
                to_output_item(rec, report_type)
            )

    if args.enable_precise_fallback == "true":
        already_urls = {x["url"] for x in output_items}
        already_types = {x["reportType"] for x in output_items}

        fallback_aliases = company_aliases if company_aliases else [args.company_query]
        precise_terms: list[str] = []
        for alias in fallback_aliases:
            for rtype in sorted(requested_types):
                for kw in report_keywords(rtype):
                    term = f"{alias} {kw}".strip()
                    if term and term not in precise_terms:
                        precise_terms.append(term)

        for term in precise_terms:
            result = fetch_page(term, page_num=1, page_size=50, timeout=args.timeout)
            anns = result.get("announcements") or []
            for ann in anns:
                rec = normalize_ann(ann)

                if effective_stock_code and rec.get("secCode") != effective_stock_code:
                    continue
                if company_aliases:
                    sec_name = rec.get("secName") or ""
                    if not any(alias in sec_name for alias in company_aliases):
                        continue

                title = rec["announcementTitle"]
                if not title or contains_excluded(title):
                    continue

                rtype = classify_report_type(title)
                if rtype is None or rtype not in requested_types:
                    continue
                if not title_matches_report_type_exact(title, rtype):
                    continue
                if args.per_type_mode == "latest" and rtype in already_types:
                    continue

                if not in_time_scope(rec["date_dt"], args.time_mode, args.year, args.range_years):
                    continue
                if not rec["adjunctUrl"]:
                    continue

                item = to_output_item(rec, rtype)
                if item["url"] in already_urls:
                    continue
                output_items.append(item)
                already_urls.add(item["url"])
                already_types.add(rtype)

        output_items.sort(
            key=lambda x: (x["reportType"], x.get("date", ""), x.get("title", "")),
            reverse=True,
        )

    out_path = Path(args.output_json)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(output_items, ensure_ascii=False, indent=2), encoding="utf-8")

    matched_types = {x["reportType"] for x in output_items}
    missing = sorted(requested_types.difference(matched_types))
    print(
        json.dumps(
            {
                "company_query": args.company_query,
                "requested_types": sorted(requested_types),
                "matched_count": len(output_items),
                "missing_types": missing,
                "per_type_mode": args.per_type_mode,
                "company_aliases": company_aliases,
                "resolved_stock_code": resolved_code,
                "effective_stock_code": effective_stock_code,
                "query_terms": query_terms,
                "output_json": str(out_path),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
