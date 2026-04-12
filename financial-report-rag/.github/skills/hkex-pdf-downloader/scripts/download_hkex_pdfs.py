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


def download_file(url: str, target_path: Path, timeout: int) -> None:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; hkex-pdf-downloader/1.0)",
            "Accept": "*/*",
        },
    )
    target_path.parent.mkdir(parents=True, exist_ok=True)
    temp = target_path.with_suffix(target_path.suffix + ".part")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = resp.read()
    temp.write_bytes(data)
    temp.replace(target_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Download HKEX PDFs from normalized items JSON")
    parser.add_argument("--items-json", required=True, help="Path to normalized items JSON")
    parser.add_argument("--output-dir", default="./downloads/hkex", help="Directory to save files")
    parser.add_argument("--timeout", type=int, default=60)
    args = parser.parse_args()

    items_path = Path(args.items_json)
    if not items_path.exists():
        raise FileNotFoundError(f"Items JSON not found: {items_path}")

    items = json.loads(items_path.read_text(encoding="utf-8-sig"))
    if not isinstance(items, list):
        raise ValueError("Items JSON must be a list")

    out_dir = Path(args.output_dir)
    success = 0
    skip = 0
    fail = 0

    for item in items:
        try:
            if not isinstance(item, dict):
                fail += 1
                print("WARN: Non-object item skipped")
                continue

            url = str(item.get("url") or "").strip()
            company = to_safe_filename(str(item.get("company") or ""))
            stock_code = to_safe_filename(str(item.get("stockCode") or ""))
            report_type = to_safe_filename(str(item.get("reportType") or ""))
            title = to_safe_filename(str(item.get("title") or ""))
            date = to_safe_filename(str(item.get("date") or ""))

            if not url:
                fail += 1
                print("WARN: Empty url item skipped")
                continue

            file_name = to_safe_filename(f"{date}_{stock_code}_{company}_{report_type}_{title}.pdf")
            target = out_dir / stock_code / file_name

            if target.exists() and target.stat().st_size > 0:
                skip += 1
                print(f"Skip existing: {target}")
                continue

            download_file(url=url, target_path=target, timeout=args.timeout)
            success += 1
            print(f"Downloaded: {target}")
        except Exception as exc:
            fail += 1
            print(f"WARN: Failed item download | {exc}")

    print(f"Done. Success={success} Skip={skip} Fail={fail}")


if __name__ == "__main__":
    main()