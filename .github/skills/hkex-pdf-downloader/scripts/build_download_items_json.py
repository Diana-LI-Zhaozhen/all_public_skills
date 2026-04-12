import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Build normalized HKEX download items JSON from stage-1 output")
    parser.add_argument("--input-json", required=True)
    parser.add_argument("--output-json", required=True)
    args = parser.parse_args()

    in_path = Path(args.input_json)
    if not in_path.exists():
        raise FileNotFoundError(f"Input JSON not found: {in_path}")

    payload = json.loads(in_path.read_text(encoding="utf-8-sig"))
    raw_items = payload.get("items") if isinstance(payload, dict) else payload
    if not isinstance(raw_items, list):
        raise ValueError("Input JSON must be a stage-1 object with items list or a list")

    out_items = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        out_items.append(
            {
                "company": str(item.get("company") or "").strip(),
                "stockCode": str(item.get("stockCode") or "").strip(),
                "reportType": str(item.get("reportType") or "").strip(),
                "title": str(item.get("title") or "").strip(),
                "date": str(item.get("date") or "").strip(),
                "url": str(item.get("url") or "").strip(),
            }
        )

    out_path = Path(args.output_json)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_items, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved {len(out_items)} items -> {out_path}")


if __name__ == "__main__":
    main()