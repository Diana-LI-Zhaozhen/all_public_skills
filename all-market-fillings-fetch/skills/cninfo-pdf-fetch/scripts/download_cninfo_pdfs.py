import argparse
import json
import re
import urllib.request
from pathlib import Path


def to_safe_filename(name: str) -> str:
    if not name or not name.strip():
        return "unnamed"
    safe = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name.strip())
    safe = safe.rstrip(". ")
    return safe or "unnamed"


def download_file(url: str, target_path: Path, timeout: int) -> None:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
            )
        },
    )
    target_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = target_path.with_suffix(target_path.suffix + ".part")

    with urllib.request.urlopen(request, timeout=timeout) as response:
        data = response.read()
    temp_path.write_bytes(data)
    temp_path.replace(target_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Download CNInfo PDF files from normalized JSON items.")
    parser.add_argument("--items-json", required=True, help="Path to normalized download items JSON.")
    parser.add_argument("--output-dir", default="./downloads/cninfo", help="Directory to save PDFs.")
    parser.add_argument("--timeout", type=int, default=60, help="HTTP timeout in seconds per file.")
    args = parser.parse_args()

    items_path = Path(args.items_json)
    output_dir = Path(args.output_dir)

    if not items_path.exists():
        raise FileNotFoundError(f"Items JSON not found: {items_path}")

    items = json.loads(items_path.read_text(encoding="utf-8-sig"))
    if not isinstance(items, list):
        raise ValueError("Items JSON must be a list.")

    success_count = 0
    skip_count = 0
    fail_count = 0

    for item in items:
        try:
            if not isinstance(item, dict):
                fail_count += 1
                print("WARN: Skip non-object item.")
                continue

            url = str(item.get("url", "")).strip()
            company = to_safe_filename(str(item.get("company", "")))
            report_type = to_safe_filename(str(item.get("reportType", "")))
            title = to_safe_filename(str(item.get("title", "")))
            date = to_safe_filename(str(item.get("date", "")))

            if not url:
                fail_count += 1
                print("WARN: Skip item without URL.")
                continue

            company_dir = output_dir / company
            file_name = to_safe_filename(f"{date}_{company}_{report_type}_{title}.pdf")
            target_path = company_dir / file_name

            if target_path.exists():
                skip_count += 1
                print(f"Skip existing: {target_path}")
                continue

            download_file(url, target_path, timeout=args.timeout)
            success_count += 1
            print(f"Downloaded: {target_path}")
        except Exception as exc:
            fail_count += 1
            item_title = item.get("title") if isinstance(item, dict) else "unknown"
            print(f"WARN: Failed item: {item_title} | Error: {exc}")

    print(f"Done. Success={success_count} Skip={skip_count} Fail={fail_count}")


if __name__ == "__main__":
    main()
