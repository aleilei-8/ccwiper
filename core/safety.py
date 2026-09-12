"""安全规则引擎。

核心原则（不可违反）：
1. 只做「归档移动」，绝不删除文件。
2. 系统关键目录与可执行/系统文件类型禁止任何操作。
3. 所有规则可从 config/default_rules.json 覆盖，缺省使用内置白名单。
"""
from __future__ import annotations

import json
import os
from pathlib import Path

DEFAULT_RULES = {
    "protected_dirs": [
        "C:\\Windows",
        "C:\\Program Files",
        "C:\\Program Files (x86)",
        "C:\\ProgramData",
        "C:\\$Recycle.Bin",
    ],
    "protected_exts": [
        ".exe", ".dll", ".sys", ".bat", ".cmd", ".msi",
        ".com", ".scr", ".drv", ".lnk", ".ini",
    ],
    "large_file_threshold": 1_000_000_000,
}

_RULES_CACHE: dict | None = None


def load_rules(path: str | None = None) -> dict:
    """加载安全规则；文件不存在或损坏时回退内置默认规则。"""
    global _RULES_CACHE
    if _RULES_CACHE is not None:
        return _RULES_CACHE
    rules = dict(DEFAULT_RULES)
    candidates = [
        path,
        os.path.join(os.path.dirname(__file__), "..", "config", "default_rules.json"),
    ]
    for c in candidates:
        if not c:
            continue
        try:
            with open(c, "r", encoding="utf-8") as f:
                data = json.load(f)
            rules.update({k: data[k] for k in DEFAULT_RULES if k in data})
            break
        except (OSError, ValueError):
            continue
    rules["protected_dirs"] = [
        os.path.normcase(os.path.abspath(d)) for d in rules["protected_dirs"]
    ]
    rules["protected_exts"] = {e.lower() for e in rules["protected_exts"]}
    _RULES_CACHE = rules
    return rules


def normalize(p: str) -> str:
    return os.path.normcase(os.path.abspath(p))


def is_protected_path(path: str) -> bool:
    rules = load_rules()
    np = normalize(path)
    for d in rules["protected_dirs"]:
        if np == d or np.startswith(d + os.sep):
            return True
    return False


def is_protected_ext(path: str) -> bool:
    return os.path.splitext(path)[1].lower() in load_rules()["protected_exts"]


def check_item(path: str) -> tuple[bool, str]:
    """返回 (是否允许操作, 原因)。允许返回 ('', '')。"""
    if is_protected_path(path):
        return False, "系统关键目录，受保护"
    if is_protected_ext(path):
        return False, "可执行/系统文件类型，禁止移动"
    return True, ""
