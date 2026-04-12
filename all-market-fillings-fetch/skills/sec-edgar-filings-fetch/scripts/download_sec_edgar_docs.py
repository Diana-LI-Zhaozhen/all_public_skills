import argparse
import json
import re
import urllib.request
from pathlib import Path


def to_safe_filename(name: str) -> str:
    text = (name or "").strip()
    if not text:
        return "unnamed"
    safe = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", text)
    safe = safe.rstrip(". ")
    return safe or "unnamed"


def infer_extension(url: str, fallback: str = ".htm") -> str:
    lower = (url or "").lower()
    for ext in [".htm", ".html", ".xml", ".txt", ".pdf", ".xsd", ".xlsx"]:
        if lower.endswith(ext):
            return ext
    return fallback


def download_binary(url: str, target_path: Path, timeout: int, user_agent: str) -> None:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": user_agent,
            "Accept": "*/*",
        },
    )
    target_path.parent.mkdir(parents=True, exist_ok=True)
    temp = target_path.with_suffix(target_path.suffix + ".part")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = resp.read()
    temp.write_bytes(data)
    temp.replace(target_path)


def build_file_name(company: str, filing: dict) -> str:
    filing_date = to_safe_filename(str(filing.get("filingDate", "")))
    report_date = to_safe_filename(str(filing.get("reportDate", "")))
    form = to_safe_filename(str(filing.get("form", "")))
    accession = to_safe_filename(str(filing.get("accessionNumber", "")))
    primary = str(filing.get("primaryDocument", "")).strip()
    ext = Path(primary).suffix if primary else ""
    if not ext:
        ext = infer_extension(str(filing.get("primaryDocumentLink", "")))
    return f"{filing_date}_{company}_{form}_{report_date}_{accession}{ext}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Download SEC EDGAR primary documents from fetch output JSON")
    parser.add_argument("--input-json", required=True, help="Path to fetch_sec_edgar_filings.py output JSON")
    parser.add_argument("--output-dir", default="./downloads/sec-edgar", help="Root folder for downloaded docs")
    parser.add_argument("--timeout", type=int, default=60, help="HTTP timeout seconds per file")
    parser.add_argument(
        "--user-agent",
        default="sec-edgar-skill/1.0 (contact: local-user@example.com)",
        help="SEC requires descriptive User-Agent",
    )
    parser.add_argument(
        "--summary-json",
        default="",
        help="Optional path to save a download summary JSON",
    )
    args = parser.parse_args()

    input_path = Path(args.input_json)
    if not input_path.exists():
        raise FileNotFoundError(f"Input JSON not found: {input_path}")

    payload = json.loads(input_path.read_text(encoding="utf-8-sig"))
    filings = payload.get("filings", [])
    if not isinstance(filings, list):
        raise ValueError("Invalid input JSON: filings must be a list")

    company = to_safe_filename(str(payload.get("resolved", {}).get("title", "UNKNOWN")))
    ticker = to_safe_filename(str(payload.get("resolved", {}).get("ticker", "")))
    cik = to_safe_filename(str(payload.get("resolved", {}).get("cik", "")))

    company_folder_name = "_".join([x for x in [company, ticker, cik] if x])
    output_root = Path(args.output_dir) / company_folder_name

    success = 0
    skipped = 0
    failed = 0
    details: list[dict] = []

    for filing in filings:
        if not isinstance(filing, dict):
            failed += 1
            details.append({"status": "failed", "reason": "non-dict filing item"})
            continue

        url = str(filing.get("primaryDocumentLink", "")).strip()
        if not url:
            failed += 1
            details.append(
                {
                    "status": "failed",
                    "reason": "missing primaryDocumentLink",
                    "accessionNumber": filing.get("accessionNumber", ""),
                }
            )
            continue

        file_name = to_safe_filename(build_file_name(company=company, filing=filing))
        target_path = output_root / file_name

        if target_path.exists():
            skipped += 1
            details.append(
                {
                    "status": "skipped",
                    "filePath": str(target_path),
                    "url": url,
                    "form": filing.get("form", ""),
                    "filingDate": filing.get("filingDate", ""),
                }
            )
            print(f"Skip existing: {target_path}")
            continue

        try:
            download_binary(
                url=url,
                target_path=target_path,
                timeout=args.timeout,
                user_agent=args.user_agent,
            )
            success += 1
            details.append(
                {
                    "status": "downloaded",
                    "filePath": str(target_path),
                    "url": url,
                    "form": filing.get("form", ""),
                    "filingDate": filing.get("filingDate", ""),
                }
            )
            print(f"Downloaded: {target_path}")
        except Exception as exc:
            failed += 1
            details.append(
                {
                    "status": "failed",
                    "reason": str(exc),
                    "url": url,
                    "form": filing.get("form", ""),
                    "filingDate": filing.get("filingDate", ""),
                }
            )
            print(f"WARN: Failed: {url} | {exc}")

    summary = {
        "inputJson": str(input_path),
        "outputDir": str(output_root),
        "company": payload.get("resolved", {}),
        "totals": {
            "requested": len(filings),
            "downloaded": success,
            "skipped": skipped,
            "failed": failed,
        },
        "details": details,
    }

    summary_json = args.summary_json.strip()
    if summary_json:
        out = Path(summary_json)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Summary saved: {out}")

    print(
        "Done. "
        f"Requested={len(filings)} Downloaded={success} Skipped={skipped} Failed={failed}"
    )


if __name__ == "__main__":
    main()