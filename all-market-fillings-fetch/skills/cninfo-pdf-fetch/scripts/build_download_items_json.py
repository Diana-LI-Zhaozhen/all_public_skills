import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path


def get_string_value(item: dict, candidate_keys: list[str]) -> str:
    for key in candidate_keys:
        value = item.get(key)
        if value is not None:
            text = str(value).strip()
            if text:
                return text
    return ""


def resolve_report_type(current_type: str, title: str) -> str:
    if current_type:
        return current_type

    patterns = [
        (r"(?i)q1|quarter\s*1|first\s*quarter|\u7b2c\u4e00\u5b63\u5ea6|\u4e00\u5b63", "q1"),
        (r"(?i)q3|quarter\s*3|third\s*quarter|\u7b2c\u4e09\u5b63\u5ea6|\u4e09\u5b63", "q3"),
        (r"(?i)semi|half\s*year|interim|\u534a\u5e74\u5ea6|\u534a\u5e74", "semi_annual"),
        (r"(?i)annual|year|\u5e74\u5ea6\u62a5\u544a|\u5e74\u62a5", "annual"),
    ]
    for pattern, report_type in patterns:
        if re.search(pattern, title):
            return report_type
    return "unknown"


def resolve_date(raw_date: str) -> str:
    if not raw_date:
        return ""
    digits = raw_date.strip()
    if re.fullmatch(r"\d{13}", digits):
        try:
            ms = int(digits)
            dt = datetime.fromtimestamp(ms / 1000, tz=timezone.utc)
            return dt.strftime("%Y-%m-%d")
        except (ValueError, OSError):
            return raw_date
    return raw_date


def normalize_items(source_data: object, pdf_base_url: str) -> list[dict]:
    if isinstance(source_data, list):
        input_items = source_data
    elif isinstance(source_data, dict) and isinstance(source_data.get("announcements"), list):
        input_items = source_data["announcements"]
    else:
        raise ValueError("Source JSON must be a list or an object containing an 'announcements' list.")

    seen_urls = set()
    output_items = []
    base = pdf_base_url.rstrip("/")

    for item in input_items:
        if not isinstance(item, dict):
            continue

        direct_url = get_string_value(item, ["url", "pdfUrl"])
        adjunct = get_string_value(item, ["adjunctUrl", "adjuncturl"])

        final_url = direct_url
        if not final_url and adjunct:
            final_url = f"{base}/{adjunct.lstrip('/')}"

        if not final_url or final_url in seen_urls:
            continue
        seen_urls.add(final_url)

        company = get_string_value(item, ["company", "secName", "secname", "orgName"])
        title = get_string_value(item, ["title", "announcementTitle", "announcementtitle"])
        date_raw = get_string_value(item, ["date", "announcementTime", "announcementtime"])
        report_type_raw = get_string_value(item, ["reportType", "report_type"])

        output_items.append(
            {
                "url": final_url,
                "company": company,
                "reportType": resolve_report_type(report_type_raw, title),
                "title": title,
                "date": resolve_date(date_raw),
            }
        )

    return output_items


def main() -> None:
    parser = argparse.ArgumentParser(description="Build normalized CNInfo download items JSON.")
    parser.add_argument("--source-json", required=True, help="Path to stage-1 raw JSON.")
    parser.add_argument("--output-json", required=True, help="Path to normalized output JSON.")
    parser.add_argument(
        "--pdf-base-url",
        default="https://static.cninfo.com.cn/",
        help="Base URL used when only adjunctUrl is present.",
    )
    args = parser.parse_args()

    source_path = Path(args.source_json)
    output_path = Path(args.output_json)

    if not source_path.exists():
        raise FileNotFoundError(f"Source JSON not found: {source_path}")

    source_data = json.loads(source_path.read_text(encoding="utf-8-sig"))
    output_items = normalize_items(source_data, args.pdf_base_url)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output_items, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Built {len(output_items)} download item(s): {output_path}")


if __name__ == "__main__":
    main()
