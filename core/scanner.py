"""扫描引擎：遍历目录收集文件元信息，支持进度回调。

设计目标：只读、不修改任何文件；对无权限/损坏文件静默跳过。
"""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class FileInfo:
    path: str
    size: int
    mtime: float
    ext: str

    def to_row(self, category: str = "") -> dict:
        return {
            "path": self.path,
            "size": self.size,
            "mtime": self.mtime,
            "ext": self.ext,
            "category": category,
        }


def scan(root: str, on_progress=None) -> list[FileInfo]:
    """遍历 root 收集 FileInfo。

    on_progress(count, sample_path) 每 500 个文件调用一次，用于 UI 进度展示。
    """
    results: list[FileInfo] = []
    count = 0
    for dirpath, dirnames, filenames in os.walk(root):
        # 跳过符号链接目录，避免循环遍历
        dirnames[:] = [d for d in dirnames if not os.path.islink(os.path.join(dirpath, d))]
        for fn in filenames:
            p = os.path.join(dirpath, fn)
            try:
                st = os.stat(p)
            except OSError:
                continue
            results.append(FileInfo(p, st.st_size, st.st_mtime, os.path.splitext(fn)[1].lower()))
            count += 1
            if on_progress is not None and count % 500 == 0:
                on_progress(count, p)
    return results
