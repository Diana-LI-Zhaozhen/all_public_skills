# HKEX Scripts

## 脚本
- fetch_hkex_notices.py
- build_download_items_json.py
- download_hkex_pdfs.py

## 工作流
1. 先抓取：`fetch_hkex_notices.py` 输出 stage-1 JSON。
2. 可选归一化：`build_download_items_json.py` 转为下载 items JSON。
3. 批量下载：`download_hkex_pdfs.py` 下载 PDF。

## 示例

```powershell
python .github/skills/hkex-pdf-downloader/scripts/fetch_hkex_notices.py \
  --stock-codes 00700,09988 \
  --report-types annual,results \
  --pages 3 \
  --per-type-mode latest \
  --output-json tmp/hkex-stage1.json
```

```powershell
python .github/skills/hkex-pdf-downloader/scripts/build_download_items_json.py \
  --input-json tmp/hkex-stage1.json \
  --output-json tmp/hkex-items.json
```

```powershell
python .github/skills/hkex-pdf-downloader/scripts/download_hkex_pdfs.py \
  --items-json tmp/hkex-items.json \
  --output-dir downloads/hkex
```