"""CCWiper 主界面（CustomTkinter）。

安全承诺：只做归档移动、绝不删除；操作前弹确认清单；支持一键撤销；全程本地处理不上传。
"""
from __future__ import annotations

import os
import threading
from pathlib import Path

import customtkinter as ctk

from core import scanner, classifier, safety, operations, undo, report

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

ARCHIVE_ROOT = str(Path.home() / ".ccwiper" / "archive")
CATEGORIES = ["全部", "cache", "temp", "log", "large", "download", "other", "受保护"]

_SIZE_UNITS = ["B", "KB", "MB", "GB", "TB", "PB"]


def fmt_size(n: float) -> str:
    x = float(n)
    for u in _SIZE_UNITS:
        if x < 1024:
            return f"{x:.1f} {u}"
        x /= 1024
    return f"{x:.1f} PB"


class App(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title("CCWiper · 开源 C 盘清理（只归档，不删除）")
        self.geometry("980x740")
        self.rows: list[dict] = []
        self.vars: dict[str, ctk.BooleanVar] = {}
        self._build_ui()

    # ---------- UI 构建 ----------
    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        # 顶部：路径 + 扫描
        top = ctk.CTkFrame(self)
        top.grid(row=0, column=0, padx=12, pady=(12, 6), sticky="ew")
        top.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(top, text="扫描路径：").grid(row=0, column=0, padx=8, pady=8)
        self.path_var = ctk.StringVar(value=str(Path.home()))
        self.path_entry = ctk.CTkEntry(top, textvariable=self.path_var)
        self.path_entry.grid(row=0, column=1, padx=8, pady=8, sticky="ew")
        ctk.CTkButton(top, text="浏览", width=70, command=self._pick_dir).grid(row=0, column=2, padx=6, pady=8)
        ctk.CTkButton(top, text="扫描所选", width=90, command=self._scan_selected).grid(row=0, column=3, padx=6, pady=8)
        ctk.CTkButton(top, text="扫描下载/桌面", width=130, fg_color="#2A8C5A", command=self._scan_quick).grid(row=0, column=4, padx=6, pady=8)

        # 进度
        prog = ctk.CTkFrame(self)
        prog.grid(row=1, column=0, padx=12, pady=(0, 6), sticky="ew")
        prog.grid_columnconfigure(0, weight=1)
        self.progress = ctk.CTkProgressBar(prog)
        self.progress.set(0)
        self.progress.grid(row=0, column=0, padx=8, pady=6, sticky="ew")
        self.status = ctk.CTkLabel(prog, text="就绪")
        self.status.grid(row=0, column=1, padx=8, pady=6)

        # 筛选
        filt = ctk.CTkFrame(self)
        filt.grid(row=2, column=0, padx=12, pady=(0, 6), sticky="ew")
        filt.grid_columnconfigure(3, weight=1)
        ctk.CTkLabel(filt, text="分类：").grid(row=0, column=0, padx=8, pady=6)
        self.cat_var = ctk.StringVar(value="全部")
        ctk.CTkComboBox(filt, values=CATEGORIES, variable=self.cat_var, width=120,
                        command=lambda _: self._render_rows()).grid(row=0, column=1, padx=6, pady=6)
        self.search_var = ctk.StringVar()
        self.search_var.trace_add("write", lambda *_: self._render_rows())
        ctk.CTkEntry(filt, textvariable=self.search_var, placeholder_text="搜索路径关键字…").grid(row=0, column=2, padx=6, pady=6, sticky="ew")
        ctk.CTkButton(filt, text="全选/取消", width=90, command=self._toggle_all).grid(row=0, column=3, padx=8, pady=6)

        # 列表
        self.list = ctk.CTkScrollableFrame(self, label_text="扫描结果（勾选后归档）")
        self.list.grid(row=3, column=0, padx=12, pady=(0, 6), sticky="nsew")

        # 底部操作
        bottom = ctk.CTkFrame(self)
        bottom.grid(row=4, column=0, padx=12, pady=(0, 12), sticky="ew")
        bottom.grid_columnconfigure(0, weight=1)
        self.summary = ctk.CTkLabel(bottom, text="未选择文件")
        self.summary.grid(row=0, column=0, padx=8, pady=8, sticky="w")
        ctk.CTkButton(bottom, text="归档选中", fg_color="#C0392B", width=110, command=self._archive).grid(row=0, column=1, padx=6, pady=8)
        ctk.CTkButton(bottom, text="一键撤销", width=90, command=self._do_undo).grid(row=0, column=2, padx=6, pady=8)
        ctk.CTkButton(bottom, text="导出 CSV", width=90, command=self._export).grid(row=0, column=3, padx=6, pady=8)

        self.safety_note = ctk.CTkLabel(
            self, text="安全承诺：本工具绝不删除文件，仅移动到归档目录；操作前有确认清单，可一键撤销；全程本地运行，不上传任何数据。",
            text_color="#2A8C5A", font=ctk.CTkFont(size=11))
        self.safety_note.grid(row=5, column=0, padx=12, pady=(0, 8), sticky="w")

    # ---------- 交互 ----------
    def _pick_dir(self) -> None:
        d = ctk.filedialog.askdirectory()
        if d:
            self.path_var.set(d)

    def _scan(self, roots: list[str]) -> None:
        self.status.configure(text="扫描中…")
        self.progress.set(0.02)
        self.rows = []

        def run() -> None:
            files: list[scanner.FileInfo] = []
            for r in roots:
                files.extend(scanner.scan(r, on_progress=self._on_progress))
            rows = []
            for f in files:
                cat = classifier.categorize(f)
                ok, reason = safety.check_item(f.path)
                rows.append(f.to_row(cat if ok else "受保护"))
                rows[-1]["allow"] = ok
                rows[-1]["reason"] = reason
            self.rows = rows
            self.after(0, self._after_scan)

        threading.Thread(target=run, daemon=True).start()

    def _on_progress(self, count: int, _sample: str) -> None:
        self.after(0, lambda: self.status.configure(text=f"已扫描 {count} 个文件…"))

    def _after_scan(self) -> None:
        self.progress.set(1)
        total = sum(r["size"] for r in self.rows)
        self.status.configure(text=f"完成：{len(self.rows)} 个文件，共 {fmt_size(total)}")
        self._render_rows()

    def _scan_selected(self) -> None:
        p = self.path_var.get()
        if p and os.path.isdir(p):
            self._scan([p])

    def _scan_quick(self) -> None:
        roots = [str(Path.home() / "Downloads"), str(Path.home() / "Desktop")]
        roots = [r for r in roots if os.path.isdir(r)]
        if roots:
            self._scan(roots)

    def _visible_rows(self) -> list[dict]:
        cat = self.cat_var.get()
        kw = self.search_var.get().lower()
        out = []
        for r in self.rows:
            if cat != "全部" and r["category"] != cat:
                continue
            if kw and kw not in r["path"].lower():
                continue
            out.append(r)
        return out

    def _render_rows(self) -> None:
        for w in self.list.winfo_children():
            w.destroy()
        self.vars.clear()
        for r in self._visible_rows():
            row = ctk.CTkFrame(self.list)
            row.pack(fill="x", padx=4, pady=2)
            var = ctk.BooleanVar(value=False)
            self.vars[r["path"]] = var
            cb = ctk.CTkCheckBox(row, text="", variable=var, width=20,
                                 command=self._update_summary)
            cb.pack(side="left", padx=(4, 8))
            # 受保护项禁用勾选
            if not r.get("allow", True):
                cb.configure(state="disabled")
            label = ctk.CTkLabel(row, text=f"{r['path']}", anchor="w")
            label.pack(side="left", fill="x", expand=True)
            tag = "受保护" if not r.get("allow", True) else r["category"]
            ctk.CTkLabel(row, text=f"{fmt_size(r['size'])} · {tag}", width=170, anchor="e").pack(side="right", padx=6)
        self._update_summary()

    def _selected_paths(self) -> list[str]:
        return [p for p, v in self.vars.items() if v.get()]

    def _update_summary(self) -> None:
        sel = self._selected_paths()
        size = sum(r["size"] for r in self.rows if r["path"] in sel)
        if not sel:
            self.summary.configure(text="未选择文件")
        else:
            self.summary.configure(text=f"已选 {len(sel)} 项 · 合计 {fmt_size(size)}")

    def _toggle_all(self) -> None:
        if self.vars and all(v.get() for v in self.vars.values()):
            for v in self.vars.values():
                v.set(False)
        else:
            for p, v in self.vars.items():
                if safety.check_item(p)[0]:
                    v.set(True)
        self._update_summary()

    def _archive(self) -> None:
        sel = self._selected_paths()
        if not sel:
            return
        # 二次安全校验（防御性）
        sel = [p for p in sel if safety.check_item(p)[0]]
        if not sel:
            return
        # 确认清单弹窗
        confirm = ctk.CTkToplevel(self)
        confirm.title("确认归档清单")
        confirm.geometry("760x460")
        confirm.transient(self)
        ctk.CTkLabel(confirm, text=f"以下 {len(sel)} 个文件将被移动到归档目录（不删除）：\n{ARCHIVE_ROOT}",
                     text_color="#C0392B", font=ctk.CTkFont(size=12, weight="bold")).pack(padx=12, pady=8, anchor="w")
        box = ctk.CTkScrollableFrame(confirm)
        box.pack(fill="both", expand=True, padx=12, pady=6)
        for p in sel:
            ctk.CTkLabel(box, text=f"{fmt_size(os.path.getsize(p)) if os.path.exists(p) else '?'} · {p}",
                         anchor="w").pack(anchor="w", padx=4, pady=1)
        bar = ctk.CTkFrame(confirm)
        bar.pack(fill="x", padx=12, pady=8)
        ctk.CTkButton(bar, text="取消", width=90, command=confirm.destroy).pack(side="right", padx=6)
        ctk.CTkButton(bar, text="确认归档", fg_color="#C0392B", width=110,
                      command=lambda: self._do_archive(sel, confirm)).pack(side="right", padx=6)

    def _do_archive(self, items: list[str], confirm) -> None:
        n = len(operations.archive_many(items, ARCHIVE_ROOT))
        confirm.destroy()
        self.status.configure(text=f"已归档 {n} 个文件到 {ARCHIVE_ROOT}")
        self.rows = [r for r in self.rows if r["path"] not in items]
        self._render_rows()

    def _do_undo(self) -> None:
        n = undo.undo_all()
        self.status.configure(text=f"已撤销 {n} 个归档操作" if n else "没有可撤销的操作")
        # 撤销后重新扫描当前路径以恢复列表
        self._scan_selected()

    def _export(self) -> None:
        from tkinter import filedialog as fd
        path = fd.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if path:
            report.export_csv(self.rows, path)
            self.status.configure(text=f"已导出 {len(self.rows)} 条到 {path}")


if __name__ == "__main__":
    App().mainloop()
