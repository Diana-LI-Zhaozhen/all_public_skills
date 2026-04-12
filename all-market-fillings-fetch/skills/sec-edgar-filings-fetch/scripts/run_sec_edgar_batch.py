import argparse
import json
from datetime import datetime
from pathlib import Path

from download_sec_edgar_docs import main as download_main
from fetch_sec_edgar_filings import (
    SEC_BROWSE_URL,
    SEC_SUBMISSIONS_URL,
    build_headers,
    choose_forms,
    cik_to_10,
    extract_recent_filings,
    get_json,
    normalize_cik,
    resolve_company,
)


def parse_companies(companies_arg: str, companies_json: str) -> list[str]:
    if companies_json:
        path = Path(companies_json)
        if not path.exists():
            raise FileNotFoundError(f"Companies JSON not found: {path}")
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
        if not isinstance(payload, list):
            raise ValueError("Companies JSON must be a string list")
        return [str(x).strip() for x in payload if str(x).strip()]

    if companies_arg:
        return [x.strip() for x in companies_arg.split(",") if x.strip()]

    raise ValueError("Provide --companies or --companies-json")


def fetch_to_json(
    query: str,
    report_kind: str,
    years: int,
    timeout: int,
    user_agent: str,
    output_json: Path,
) -> dict:
    headers = build_headers(user_agent)
    company = resolve_company(query, headers=headers, timeout=timeout)

    cik = normalize_cik(company.get("cik", ""))
    if not cik:
        raise ValueError(f"Resolved empty CIK for query: {query}")

    cik10 = cik_to_10(cik)
    submissions = get_json(SEC_SUBMISSIONS_URL.format(cik10=cik10), headers=headers, timeout=timeout)
    forms = choose_forms(report_kind)
    filings = extract_recent_filings(submissions=submissions, forms=forms, years=years)

    result = {
        "query": query,
        "resolved": {
            "cik": cik,
            "ticker": company.get("ticker", ""),
            "title": submissions.get("name", "") or company.get("title", ""),
            "browseUrl": SEC_BROWSE_URL.format(cik=cik),
            "match": company.get("match", ""),
        },
        "reportKind": report_kind,
        "forms": forms,
        "years": years,
        "count": len(filings),
        "filings": filings,
    }

    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def run_download(input_json: Path, output_dir: str, timeout: int, user_agent: str, summary_json: Path) -> None:
    import sys

    old_argv = sys.argv
    try:
        sys.argv = [
            "download_sec_edgar_docs.py",
            "--input-json",
            str(input_json),
            "--output-dir",
            output_dir,
            "--timeout",
            str(timeout),
            "--user-agent",
            user_agent,
            "--summary-json",
            str(summary_json),
        ]
        download_main()
    finally:
        sys.argv = old_argv


def safe_slug(text: str) -> str:
    keep = []
    for ch in text:
        if ch.isalnum() or ch in ["-", "_"]:
            keep.append(ch)
        else:
            keep.append("-")
    slug = "".join(keep).strip("-")
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug or "company"


def main() -> None:
    parser = argparse.ArgumentParser(description="One-click SEC EDGAR batch: fetch + download + summary")
    parser.add_argument("--companies", default="", help="Comma-separated query list, e.g. Berkshire Hathaway,BABA")
    parser.add_argument("--companies-json", default="", help="Optional JSON file with company queries")
    parser.add_argument("--report-kind", default="annual", help="annual | quarterly | all | custom form list")
    parser.add_argument("--years", type=int, default=3)
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument(
        "--user-agent",
        default="sec-edgar-skill/1.0 (contact: local-user@example.com)",
        help="SEC requires descriptive User-Agent",
    )
    parser.add_argument("--fetch-output-dir", default="tmp/sec-edgar/fetch")
    parser.add_argument("--download-output-dir", default="downloads/sec-edgar")
    parser.add_argument("--download-summary-dir", default="tmp/sec-edgar/download-summaries")
    parser.add_argument("--batch-summary-json", default="tmp/sec-edgar/batch-summary.json")
    args = parser.parse_args()

    companies = parse_companies(args.companies, args.companies_json)

    fetch_dir = Path(args.fetch_output_dir)
    dsum_dir = Path(args.download_summary_dir)
    bsum_path = Path(args.batch_summary_json)
    fetch_dir.mkdir(parents=True, exist_ok=True)
    dsum_dir.mkdir(parents=True, exist_ok=True)
    bsum_path.parent.mkdir(parents=True, exist_ok=True)

    rows = []
    for company in companies:
        slug = safe_slug(company)
        fetch_json = fetch_dir / f"{slug}-{args.report_kind}-{args.years}y.json"
        dsum_json = dsum_dir / f"{slug}-{args.report_kind}-{args.years}y-download-summary.json"

        try:
            fetch_result = fetch_to_json(
                query=company,
                report_kind=args.report_kind,
                years=args.years,
                timeout=args.timeout,
                user_agent=args.user_agent,
                output_json=fetch_json,
            )
            run_download(
                input_json=fetch_json,
                output_dir=args.download_output_dir,
                timeout=args.timeout,
                user_agent=args.user_agent,
                summary_json=dsum_json,
            )
            download_summary = json.loads(dsum_json.read_text(encoding="utf-8-sig"))

            rows.append(
                {
                    "query": company,
                    "status": "success",
                    "fetchJson": str(fetch_json),
                    "downloadSummaryJson": str(dsum_json),
                    "resolved": fetch_result.get("resolved", {}),
                    "filingsCount": fetch_result.get("count", 0),
                    "downloadTotals": download_summary.get("totals", {}),
                }
            )
        except Exception as exc:
            rows.append(
                {
                    "query": company,
                    "status": "failed",
                    "error": str(exc),
                    "fetchJson": str(fetch_json),
                    "downloadSummaryJson": str(dsum_json),
                }
            )

    ok = sum(1 for x in rows if x.get("status") == "success")
    fail = len(rows) - ok
    summary = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "reportKind": args.report_kind,
        "years": args.years,
        "companies": companies,
        "totals": {"requested": len(rows), "success": ok, "failed": fail},
        "rows": rows,
    }

    bsum_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Batch done. Requested={len(rows)} Success={ok} Failed={fail}")
    print(f"Batch summary: {bsum_path}")


if __name__ == "__main__":
    main()