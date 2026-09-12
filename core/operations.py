"""归档操作层。

唯一对外提供的文件变动动作是「移动到归档目录」，不提供任何删除接口。
每次移动都会写入操作日志（operations.jsonl），供一键撤销使用。
"""
from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path

LOG_PATH = Path.home() / ".ccwiper" / "operations.jsonl"
DEFAULT_ARCHIVE_ROOT = str(Path.home() / ".ccwiper" / "archive")


def ensure_log() -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not LOG_PATH.exists():
        LOG_PATH.write_text("", encoding="utf-8")


def archive_file(src: str, archive_root: str | None = None) -> dict:
    """把 src 移动到归档目录（保留原盘剩余路径结构），并记录操作日志。

    返回操作记录 dict。失败抛出 OSError，调用方负责提示用户。
    """
    src_p = Path(src)
    if not src_p.exists():
        raise FileNotFoundError(src)
    archive_root = archive_root or DEFAULT_ARCHIVE_ROOT
    # 去掉盘符锚点（Windows: C:\\ -> 相对路径），保留其余目录结构
    anchor = src_p.anchor or ""
    rel = src_p.relative_to(anchor) if anchor else src_p.name
    dest = Path(archive_root) / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src_p), str(dest))

    rec = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "src": str(src_p),
        "dest": str(dest),
        "action": "archive",
    }
    ensure_log()
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return rec


def archive_many(items: list[str], archive_root: str | None = None) -> list[dict]:
    """批量归档，遇到单个失败不中断，返回成功记录列表。"""
    done = []
    for it in items:
        try:
            done.append(archive_file(it, archive_root))
        except OSError:
            continue
    return done
