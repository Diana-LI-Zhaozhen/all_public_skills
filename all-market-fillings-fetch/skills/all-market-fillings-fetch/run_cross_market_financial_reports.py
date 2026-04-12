import argparse
import json
import subprocess
import sys
from datetime import date
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse


def run_cmd(cmd: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=True, capture_output=True, text=True, cwd=str(cwd) if cwd else None)


def to_safe_filename(name: str) -> str:
    text = (name or "").strip()
    if not text:
        return "unnamed"
    out = []
    for ch in text:
        if ch in '<>:"/\\|?*' or ord(ch) < 32:
            out.append("_")
        else:
            out.append(ch)
    safe = "".join(out).rstrip(". ")
    return safe or "unnamed"


def build_hkex_target_path(download_root: Path, item: dict) -> Path:
    company = to_safe_filename(str(item.get("company") or ""))
    stock_code = to_safe_filename(str(item.get("stockCode") or ""))
    report_type = to_safe_filename(str(item.get("reportType") or ""))
    title = to_safe_filename(str(item.get("title") or ""))
    date = to_safe_filename(str(item.get("date") or ""))
    file_name = to_safe_filename(f"{date}_{stock_code}_{company}_{report_type}_{title}.pdf")
    return download_root / stock_code / file_name


def build_hkex_repo_annual_target_path(download_root: Path, stock_code: str, year: int, url: str) -> Path:
    suffix = Path(urlparse(url).path).suffix or ".pdf"
    safe_code = to_safe_filename(stock_code.zfill(5))
    file_name = f"{safe_code}_{year}_annual_report{suffix}"
    return download_root / safe_code / file_name


def build_cninfo_target_path(download_root: Path, item: dict) -> Path:
    company = to_safe_filename(str(item.get("company") or ""))
    report_type = to_safe_filename(str(item.get("reportType") or ""))
    title = to_safe_filename(str(item.get("title") or ""))
    date = to_safe_filename(str(item.get("date") or ""))
    file_name = to_safe_filename(f"{date}_{company}_{report_type}_{title}.pdf")
    return download_root / company / file_name


def collect_hkex_files(summary: dict, download_root: Path) -> list[dict]:
    files: list[dict] = []
    for row in summary.get("rows", []):
        if not isinstance(row, dict):
            continue
        if row.get("status") not in {"downloaded", "skipped"}:
            continue
        target = Path(str(row.get("filePath") or ""))
        files.append(
            {
                "market": "HKEX",
                "stockCode": str(row.get("stockCode") or ""),
                "reportType": "annual",
                "title": str(row.get("title") or ""),
                "date": str(row.get("date") or row.get("year") or ""),
                "url": str(row.get("url") or ""),
                "filePath": str(target),
                "exists": target.exists(),
                "status": str(row.get("status") or ""),
                "year": int(row.get("year") or 0),
            }
        )
    return files


def run_hkex_repo_annuals(
    python_executable: str,
    repo_root: Path,
    stock_codes: list[str],
    years: int,
    timeout: int,
    download_root: Path,
) -> dict:
    download_root_abs = download_root.resolve()
    current_year = date.today().year
    report_years = list(range(current_year - 1, current_year - years - 1, -1))
    rows: list[dict] = []

    for stock_code in stock_codes:
        stock = stock_code.strip().zfill(5)
        for year in report_years:
            resolve_cmd = [
                python_executable,
                "-m",
                "src.hkex_financial_monitor.cli",
                "annual-url",
                "--stock",
                stock,
                "--year",
                str(year),
                "--timeout-seconds",
                str(timeout),
            ]
            try:
                resolved = run_cmd(resolve_cmd, cwd=repo_root)
                stdout_lines = [line.strip() for line in resolved.stdout.splitlines() if line.strip()]
                url = next((line for line in reversed(stdout_lines) if line.startswith("http://") or line.startswith("https://")), "")
                if not url:
                    rows.append(
                        {
                            "stockCode": stock,
                            "year": year,
                            "status": "missing",
                            "error": "annual-url returned no URL",
                        }
                    )
                    continue

                target = build_hkex_repo_annual_target_path(download_root=download_root_abs, stock_code=stock, year=year, url=url)
                download_cmd = [
                    python_executable,
                    "-c",
                    (
                        "from pathlib import Path; "
                        "from src.hkex_financial_monitor.downloader import download_url, build_annual_target_path; "
                        f"url = {url!r}; "
                        f"target = build_annual_target_path(Path({str(download_root_abs)!r}), {stock!r}, {year}, url); "
                        f"download_url(url, target, timeout_seconds={timeout}); "
                        "print(target)"
                    ),
                ]
                downloaded = run_cmd(download_cmd, cwd=repo_root)
                target_lines = [line.strip() for line in downloaded.stdout.splitlines() if line.strip()]
                target_path = target_lines[-1] if target_lines else str(target)
                rows.append(
                    {
                        "stockCode": stock,
                        "year": year,
                        "status": "downloaded" if Path(target_path).exists() else "missing",
                        "url": url,
                        "filePath": target_path,
                        "title": f"{year} annual report",
                        "date": str(year),
                    }
                )
            except subprocess.CalledProcessError as exc:
                stderr = (exc.stderr or "").strip()
                stdout = (exc.stdout or "").strip()
                message = stderr or stdout or str(exc)
                status = "missing" if "No annual report URL found" in message else "failed"
                rows.append(
                    {
                        "stockCode": stock,
                        "year": year,
                        "status": status,
                        "error": message,
                    }
                )

    downloaded = sum(1 for row in rows if row.get("status") == "downloaded")
    missing = sum(1 for row in rows if row.get("status") == "missing")
    failed = sum(1 for row in rows if row.get("status") == "failed")
    return {
        "repoRoot": str(repo_root),
        "downloadRoot": str(download_root_abs),
        "years": report_years,
        "rows": rows,
        "totals": {
            "requested": len(rows),
            "downloaded": downloaded,
            "missing": missing,
            "failed": failed,
        },
    }


def collect_cninfo_files(items: list[dict], download_root: Path) -> list[dict]:
    files: list[dict] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        target = build_cninfo_target_path(download_root=download_root, item=item)
        files.append(
            {
                "market": "CNINFO",
                "stockCode": str(item.get("stockCode") or ""),
                "reportType": str(item.get("reportType") or ""),
                "title": str(item.get("title") or ""),
                "date": str(item.get("date") or ""),
                "url": str(item.get("url") or ""),
                "filePath": str(target),
                "exists": target.exists(),
            }
        )
    return files


def collect_sec_files(summary: dict) -> list[dict]:
    files: list[dict] = []
    for row in summary.get("rows", []):
        if not isinstance(row, dict) or row.get("status") != "success":
            continue
        dsum = row.get("downloadSummaryJson")
        if not dsum:
            continue
        path = Path(str(dsum))
        if not path.exists():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8-sig"))
        except Exception:
            continue

        details = payload.get("details", [])
        if not isinstance(details, list):
            continue

        for detail in details:
            if not isinstance(detail, dict):
                continue
            status = str(detail.get("status") or "")
            if status not in {"downloaded", "skipped", "failed"}:
                continue
            files.append(
                {
                    "market": "SEC",
                    "query": str(row.get("query") or ""),
                    "ticker": str((row.get("resolved") or {}).get("ticker") or ""),
                    "company": str((row.get("resolved") or {}).get("title") or ""),
                    "form": str(detail.get("form") or ""),
                    "filingDate": str(detail.get("filingDate") or ""),
                    "url": str(detail.get("url") or ""),
                    "filePath": str(detail.get("filePath") or ""),
                    "status": status,
                }
            )
    return files


def market_ok_hkex(files: list[dict]) -> bool:
    return any(bool(x.get("exists")) for x in files)


def market_ok_cninfo(files: list[dict]) -> bool:
    return any(bool(x.get("exists")) for x in files)


def market_ok_sec(files: list[dict]) -> bool:
    return any(str(x.get("status")) in {"downloaded", "skipped"} for x in files)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run CNInfo + HKEX + SEC fetch & download, then write one cross-market summary"
    )
    parser.add_argument("--name", default="", help="Display name, e.g. Alibaba")

    parser.add_argument("--cninfo-company-query", default="", help="CNInfo company query, e.g. 贵州茅台")
    parser.add_argument("--cninfo-stock-code", default="", help="Optional CNInfo stock code, e.g. 600519")
    parser.add_argument("--cninfo-report-types", default="annual", help="annual,semi_annual,q1,q3,quarterly")

    parser.add_argument("--hkex-stocks", default="", help="Comma-separated HKEX stock codes, e.g. 09988")
    parser.add_argument("--hkex-report-types", default="annual", help="annual,interim,quarterly,results,esg,financial")
    parser.add_argument("--hkex-pages", type=int, default=3)
    parser.add_argument("--hkex-per-type-mode", choices=["latest", "all"], default="latest")
    parser.add_argument(
        "--hkex-repo-root",
        default="tmp/Claw/skills/hkex-pdf-downloader",
        help="Local path to the authoritative Claw HKEX repo skill root",
    )

    parser.add_argument("--sec-companies", default="", help="Comma-separated SEC queries, e.g. BABA,Alibaba Group")
    parser.add_argument("--sec-report-kind", default="annual", help="annual | quarterly | all | custom forms")

    parser.add_argument("--years", type=int, default=3)
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument(
        "--sec-user-agent",
        default="sec-edgar-skill/1.0 (contact: local-user@example.com)",
        help="SEC requests require descriptive User-Agent",
    )

    parser.add_argument("--tmp-root", default="tmp/cross-market")
    parser.add_argument("--cninfo-download-output-dir", default="downloads/cninfo")
    parser.add_argument("--hkex-download-output-dir", default="downloads/hkex")
    parser.add_argument("--sec-download-output-dir", default="downloads/sec-edgar")
    parser.add_argument("--summary-json", default="tmp/cross-market/batch-summary.json")
    args = parser.parse_args()

    if not args.cninfo_company_query.strip() and not args.hkex_stocks.strip() and not args.sec_companies.strip():
        raise ValueError(
            "At least one market is required: --cninfo-company-query or --hkex-stocks or --sec-companies"
        )

    script_dir = Path(__file__).resolve().parent
    skills_dir = script_dir.parent
    cninfo_fetch_script = skills_dir / "cninfo-pdf-fetch" / "scripts" / "fetch_cninfo_notices.py"
    cninfo_download_script = skills_dir / "cninfo-pdf-fetch" / "scripts" / "download_cninfo_pdfs.py"
    sec_batch_script = skills_dir / "sec-edgar-filings-fetch" / "scripts" / "run_sec_edgar_batch.py"

    tmp_root = Path(args.tmp_root)
    tmp_root.mkdir(parents=True, exist_ok=True)

    result = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "request": {
            "name": args.name,
            "years": args.years,
            "cninfoCompanyQuery": args.cninfo_company_query,
            "cninfoStockCode": args.cninfo_stock_code,
            "hkexStocks": [x.strip() for x in args.hkex_stocks.split(",") if x.strip()],
            "secCompanies": [x.strip() for x in args.sec_companies.split(",") if x.strip()],
        },
        "markets": {},
        "totals": {},
        "files": [],
    }

    cninfo_files: list[dict] = []
    if args.cninfo_company_query.strip():
        cninfo_stage1_json = tmp_root / "cninfo" / "stage1.json"
        cninfo_items_json = tmp_root / "cninfo" / "items.json"
        cninfo_cmd = [
            sys.executable,
            str(cninfo_fetch_script),
            "--company-query",
            args.cninfo_company_query,
            "--report-types",
            args.cninfo_report_types,
            "--time-mode",
            "range",
            "--range-years",
            str(args.years),
            "--per-type-mode",
            "all",
            "--timeout",
            str(args.timeout),
            "--output-json",
            str(cninfo_stage1_json),
        ]
        if args.cninfo_stock_code.strip():
            cninfo_cmd.extend(["--stock-code", args.cninfo_stock_code.strip()])

        try:
            run_cmd(cninfo_cmd)
            stage1 = json.loads(cninfo_stage1_json.read_text(encoding="utf-8-sig"))
            if isinstance(stage1, dict):
                items = stage1.get("items", [])
            elif isinstance(stage1, list):
                items = stage1
            else:
                items = []
            if not isinstance(items, list):
                items = []

            cninfo_items_json.parent.mkdir(parents=True, exist_ok=True)
            cninfo_items_json.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")

            cninfo_download_cmd = [
                sys.executable,
                str(cninfo_download_script),
                "--items-json",
                str(cninfo_items_json),
                "--output-dir",
                args.cninfo_download_output_dir,
                "--timeout",
                str(args.timeout),
            ]
            run_cmd(cninfo_download_cmd)

            cninfo_files = collect_cninfo_files(items=items, download_root=Path(args.cninfo_download_output_dir))
            ok = market_ok_cninfo(cninfo_files)
            result["markets"]["CNINFO"] = {
                "status": "success" if ok else "partial_or_empty",
                "summaryJson": str(cninfo_stage1_json),
                "itemsJson": str(cninfo_items_json),
                "requested": 1,
                "success": 1 if ok else 0,
                "failed": 0 if ok else 1,
                "filesFound": sum(1 for x in cninfo_files if x.get("exists")),
                "filesTotal": len(cninfo_files),
            }
        except Exception as exc:
            result["markets"]["CNINFO"] = {
                "status": "failed",
                "error": str(exc),
                "summaryJson": str(cninfo_stage1_json),
                "itemsJson": str(cninfo_items_json),
                "filesFound": 0,
                "filesTotal": 0,
            }

    hkex_files: list[dict] = []
    if args.hkex_stocks.strip():
        hkex_summary_json = tmp_root / "hkex" / "batch-summary.json"
        hkex_repo_root = Path(args.hkex_repo_root)

        try:
            if not hkex_repo_root.exists():
                raise FileNotFoundError(f"HKEX repo root not found: {hkex_repo_root}")
            if args.hkex_report_types.strip().lower() != "annual":
                raise ValueError("Current cross-market HKEX integration uses the Claw repo annual-url workflow and supports annual only")

            hkex_summary = run_hkex_repo_annuals(
                python_executable=sys.executable,
                repo_root=hkex_repo_root,
                stock_codes=[x.strip() for x in args.hkex_stocks.split(",") if x.strip()],
                years=args.years,
                timeout=args.timeout,
                download_root=Path(args.hkex_download_output_dir),
            )
            hkex_summary_json.parent.mkdir(parents=True, exist_ok=True)
            hkex_summary_json.write_text(json.dumps(hkex_summary, ensure_ascii=False, indent=2), encoding="utf-8")
            hkex_summary = json.loads(hkex_summary_json.read_text(encoding="utf-8-sig"))
            hkex_files = collect_hkex_files(summary=hkex_summary, download_root=Path(args.hkex_download_output_dir))
            ok = market_ok_hkex(hkex_files)
            result["markets"]["HKEX"] = {
                "status": "success" if ok else "partial_or_empty",
                "summaryJson": str(hkex_summary_json),
                "requested": hkex_summary.get("totals", {}).get("requested", 0),
                "success": hkex_summary.get("totals", {}).get("downloaded", 0),
                "failed": hkex_summary.get("totals", {}).get("failed", 0),
                "filesFound": sum(1 for x in hkex_files if x.get("exists")),
                "filesTotal": len(hkex_files),
                "repoRoot": str(hkex_repo_root),
            }
        except Exception as exc:
            result["markets"]["HKEX"] = {
                "status": "failed",
                "error": str(exc),
                "summaryJson": str(hkex_summary_json),
                "filesFound": 0,
                "filesTotal": 0,
            }

    sec_files: list[dict] = []
    if args.sec_companies.strip():
        sec_summary_json = tmp_root / "sec-edgar" / "batch-summary.json"
        sec_cmd = [
            sys.executable,
            str(sec_batch_script),
            "--companies",
            args.sec_companies,
            "--report-kind",
            args.sec_report_kind,
            "--years",
            str(args.years),
            "--timeout",
            str(args.timeout),
            "--user-agent",
            args.sec_user_agent,
            "--fetch-output-dir",
            str(tmp_root / "sec-edgar" / "fetch"),
            "--download-output-dir",
            args.sec_download_output_dir,
            "--download-summary-dir",
            str(tmp_root / "sec-edgar" / "download-summaries"),
            "--batch-summary-json",
            str(sec_summary_json),
        ]

        try:
            run_cmd(sec_cmd)
            sec_summary = json.loads(sec_summary_json.read_text(encoding="utf-8-sig"))
            sec_files = collect_sec_files(summary=sec_summary)
            ok = market_ok_sec(sec_files)
            result["markets"]["SEC"] = {
                "status": "success" if ok else "partial_or_empty",
                "summaryJson": str(sec_summary_json),
                "requested": 1,
                "success": sec_summary.get("totals", {}).get("success", 0),
                "failed": sec_summary.get("totals", {}).get("failed", 0),
                "filesFound": sum(1 for x in sec_files if x.get("status") in {"downloaded", "skipped"}),
                "filesTotal": len(sec_files),
            }
        except Exception as exc:
            result["markets"]["SEC"] = {
                "status": "failed",
                "error": str(exc),
                "summaryJson": str(sec_summary_json),
                "filesFound": 0,
                "filesTotal": 0,
            }

    result["files"] = cninfo_files + hkex_files + sec_files

    requested_markets = [name for name in ["CNINFO", "HKEX", "SEC"] if name in result["markets"]]
    fetched_markets = [
        name
        for name in requested_markets
        if str(result["markets"].get(name, {}).get("status")) == "success"
    ]

    result["totals"] = {
        "requestedMarkets": len(requested_markets),
        "fetchedMarkets": len(fetched_markets),
        "fetchedMarketNames": fetched_markets,
        "filesFound": sum(int(result["markets"][m].get("filesFound", 0)) for m in requested_markets),
    }

    summary_path = Path(args.summary_json)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    print(
        "执行结果："
        f"请求市场 {result['totals']['requestedMarkets']} 个，"
        f"成功获取 {result['totals']['fetchedMarkets']} 个，"
        f"识别到文件 {result['totals']['filesFound']} 个。"
    )
    for market in requested_markets:
        market_obj = result["markets"].get(market, {})
        print(
            f"- {market}: status={market_obj.get('status')} | "
            f"files={market_obj.get('filesFound', 0)}/{market_obj.get('filesTotal', 0)}"
        )

    print(f"Summary: {summary_path}")


if __name__ == "__main__":
    main()
