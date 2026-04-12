import argparse
import json
import re
import urllib.request
from pathlib import Path


SEC_TICKER_MAP_URL = "https://www.sec.gov/files/company_tickers.json"
SEC_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik10}.json"
SEC_BROWSE_URL = "https://www.sec.gov/edgar/browse/?CIK={cik}"


def build_headers(user_agent: str) -> dict:
    return {
        "User-Agent": user_agent,
        "Accept": "application/json",
    }


def get_json(url: str, headers: dict, timeout: int) -> dict:
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8", errors="ignore"))


def normalize_cik(raw: str) -> str:
    digits = re.sub(r"\D", "", raw or "")
    if not digits:
        return ""
    return str(int(digits))


def cik_to_10(cik: str) -> str:
    return str(int(cik)).zfill(10)


def load_ticker_map(headers: dict, timeout: int) -> list[dict]:
    raw = get_json(SEC_TICKER_MAP_URL, headers=headers, timeout=timeout)
    out: list[dict] = []
    for _, item in raw.items():
        out.append(
            {
                "cik": normalize_cik(str(item.get("cik_str", ""))),
                "ticker": str(item.get("ticker", "")).upper().strip(),
                "title": str(item.get("title", "")).strip(),
            }
        )
    return out


def resolve_company(query: str, headers: dict, timeout: int) -> dict:
    query = (query or "").strip()
    if not query:
        raise ValueError("query is empty")

    # Direct CIK input
    if re.fullmatch(r"\d{1,10}", query):
        cik = normalize_cik(query)
        return {"cik": cik, "ticker": "", "title": "", "match": "cik"}

    ticker_map = load_ticker_map(headers=headers, timeout=timeout)
    q_upper = query.upper()

    # Exact ticker match first
    for item in ticker_map:
        if item["ticker"] == q_upper:
            return {**item, "match": "ticker_exact"}

    # Exact company title match
    for item in ticker_map:
        if item["title"].upper() == q_upper:
            return {**item, "match": "title_exact"}

    # Fuzzy company title contains
    fuzzy = [x for x in ticker_map if q_upper in x["title"].upper()]
    if fuzzy:
        return {**fuzzy[0], "match": "title_fuzzy"}

    raise ValueError(
        "No SEC filer resolved from query: "
        f"{query}. This resolver currently matches SEC reporting issuers from company_tickers.json only. "
        "ADR or OTC symbols may be absent there, and some unsponsored ADRs do not have SEC periodic filings. "
        "Try the issuer legal name or CIK instead."
    )


def choose_forms(report_kind: str) -> list[str]:
    kind = (report_kind or "annual").strip().lower()
    if kind == "annual":
        return ["10-K", "20-F"]
    if kind == "quarterly":
        return ["10-Q"]
    if kind == "all":
        return ["10-K", "20-F", "10-Q", "6-K", "8-K"]
    # Custom form list, comma separated
    return [x.strip().upper() for x in report_kind.split(",") if x.strip()]


def sec_doc_links(cik: str, accession_number: str, primary_document: str) -> tuple[str, str]:
    cik_no_zero = str(int(cik))
    acc_no_dash = accession_number.replace("-", "")
    filing_index = f"https://www.sec.gov/Archives/edgar/data/{cik_no_zero}/{acc_no_dash}/"
    primary_doc = f"{filing_index}{primary_document}" if primary_document else filing_index
    return filing_index, primary_doc


def extract_recent_filings(submissions: dict, forms: list[str], years: int) -> list[dict]:
    recent = submissions.get("filings", {}).get("recent", {})
    form_list = recent.get("form", [])
    acc_list = recent.get("accessionNumber", [])
    filing_date_list = recent.get("filingDate", [])
    report_date_list = recent.get("reportDate", [])
    primary_doc_list = recent.get("primaryDocument", [])

    # Build a company-relative year window based on the newest matched filing year.
    matched_years: list[int] = []
    for i, form in enumerate(form_list):
        if form not in forms:
            continue
        filing_date = filing_date_list[i] if i < len(filing_date_list) else ""
        if filing_date and re.fullmatch(r"\d{4}-\d{2}-\d{2}", filing_date):
            matched_years.append(int(filing_date[:4]))

    max_year = max(matched_years) if matched_years else 0
    min_year = (max_year - years + 1) if (max_year and years > 0) else 0

    results: list[dict] = []
    for i, form in enumerate(form_list):
        if form not in forms:
            continue

        filing_date = filing_date_list[i] if i < len(filing_date_list) else ""
        filing_year = 0
        if filing_date and re.fullmatch(r"\d{4}-\d{2}-\d{2}", filing_date):
            filing_year = int(filing_date[:4])
        if min_year and filing_year and filing_year < min_year:
            continue

        accession = acc_list[i] if i < len(acc_list) else ""
        report_date = report_date_list[i] if i < len(report_date_list) else ""
        primary_document = primary_doc_list[i] if i < len(primary_doc_list) else ""

        filing_link, primary_link = sec_doc_links(
            cik=normalize_cik(str(submissions.get("cik", ""))),
            accession_number=accession,
            primary_document=primary_document,
        )

        results.append(
            {
                "form": form,
                "filingDate": filing_date,
                "reportDate": report_date,
                "accessionNumber": accession,
                "primaryDocument": primary_document,
                "filingLink": filing_link,
                "primaryDocumentLink": primary_link,
            }
        )

    results.sort(key=lambda x: x.get("filingDate", ""), reverse=True)
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch SEC EDGAR filings by ticker/name/CIK")
    parser.add_argument("--query", required=True, help="Ticker, company name, or CIK")
    parser.add_argument(
        "--report-kind",
        default="annual",
        help="annual | quarterly | all | custom form list, e.g. 10-K,20-F",
    )
    parser.add_argument("--years", type=int, default=3, help="Keep filings in the latest N filing years")
    parser.add_argument(
        "--user-agent",
        default="sec-edgar-skill/1.0 (contact: local-user@example.com)",
        help="SEC requires descriptive User-Agent",
    )
    parser.add_argument("--timeout", type=int, default=25)
    parser.add_argument("--output-json", required=True)
    args = parser.parse_args()

    headers = build_headers(args.user_agent)
    company = resolve_company(args.query, headers=headers, timeout=args.timeout)

    cik = normalize_cik(company.get("cik", ""))
    if not cik:
        raise ValueError("Resolved CIK is empty")

    cik10 = cik_to_10(cik)
    submissions_url = SEC_SUBMISSIONS_URL.format(cik10=cik10)
    submissions = get_json(submissions_url, headers=headers, timeout=args.timeout)

    forms = choose_forms(args.report_kind)
    filings = extract_recent_filings(submissions=submissions, forms=forms, years=args.years)

    output = {
        "query": args.query,
        "resolved": {
            "cik": cik,
            "ticker": company.get("ticker", ""),
            "title": submissions.get("name", "") or company.get("title", ""),
            "browseUrl": SEC_BROWSE_URL.format(cik=cik),
            "match": company.get("match", ""),
        },
        "reportKind": args.report_kind,
        "forms": forms,
        "years": args.years,
        "count": len(filings),
        "filings": filings,
    }

    out_path = Path(args.output_json)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved {len(filings)} filings -> {out_path}")


if __name__ == "__main__":
    main()