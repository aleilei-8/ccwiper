"""分类识别：把扫描到的文件归到 cache / temp / log / large / download / other。"""
from __future__ import annotations

import hashlib
import os
from collections import defaultdict

from .scanner import FileInfo

CACHE_MARKERS = {"cache", "temp", "tmp", "thumb", "__pycache__", "node_modules", ".cache", "thumbnails"}
TEMP_EXTS = {".tmp", ".temp", ".bak", ".old", ".part", ".crdownload"}
LOG_EXTS = {".log"}
DOWNLOAD_EXTS = {
    ".png", ".jpg", ".jpeg", ".gif", ".mp4", ".mov", ".mkv", ".zip", ".rar", ".7z",
    ".pdf", ".docx", ".xlsx", ".pptx", ".exe", ".msi", ".dmg", ".apk", ".iso",
}


def categorize(f: FileInfo) -> str:
    name = os.path.basename(f.path).lower()
    parent = os.path.basename(os.path.dirname(f.path)).lower()
    if f.ext in LOG_EXTS or name.endswith(".log"):
        return "log"
    if f.ext in TEMP_EXTS or parent in CACHE_MARKERS or any(m in parent for m in CACHE_MARKERS):
        return "temp"
    if f.size >= 1_000_000_000:
        return "large"
    if f.ext in DOWNLOAD_EXTS:
        return "download"
    return "other"


def find_duplicates(files: list[FileInfo]) -> list[list[str]]:
    """按内容 md5 查找重复文件，返回重复组列表（每组 >=2 个路径）。"""
    by_hash: dict[str, list[str]] = defaultdict(list)
    for f in files:
        if f.size == 0:
            continue
        try:
            h = hashlib.md5()
            with open(f.path, "rb") as fh:
                for chunk in iter(lambda: fh.read(1 << 20), b""):
                    h.update(chunk)
        except OSError:
            continue
        by_hash[h.hexdigest()].append(f.path)
    return [v for v in by_hash.values() if len(v) > 1]
