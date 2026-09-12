"""报告导出层：扫描结果 / 清理清单导出为 CSV 或 TXT。"""
from __future__ import annotations

import csv


def export_csv(rows: list[dict], path: str) -> None:
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["path", "size_bytes", "mtime", "ext", "category"])
        for r in rows:
            w.writerow([r.get("path", ""), r.get("size", 0), r.get("mtime", ""), r.get("ext", ""), r.get("category", "")])


def export_txt(lines: list[str], path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
