"""一键撤销层。

读取 operations.jsonl，把文件从归档目录搬回原始路径，并从日志移除对应记录。
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

from .operations import LOG_PATH


def list_operations() -> list[dict]:
    if not LOG_PATH.exists():
        return []
    out = []
    for line in LOG_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            out.append(json.loads(line))
    return out


def _write_back(ops: list[dict]) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    body = "".join(json.dumps(o, ensure_ascii=False) + "\n" for o in ops)
    LOG_PATH.write_text(body, encoding="utf-8")


def undo_last() -> dict | None:
    ops = list_operations()
    if not ops:
        return None
    last = ops[-1]
    src = Path(last["src"])
    dest = Path(last["dest"])
    if dest.exists():
        src.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(dest), str(src))
    _write_back(ops[:-1])
    return last


def undo_all() -> int:
    n = 0
    while undo_last() is not None:
        n += 1
    return n
