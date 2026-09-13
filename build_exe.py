#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
build_exe.py — 一键将 CCWiper 打包为免安装 exe (PyInstaller --onefile --windowed)
用法：在项目根目录运行  python build_exe.py
依赖：customtkinter（见 requirements.txt），pyinstaller（本脚本自动安装）
产物：dist/CCWiper.exe  （可直接发给别人双击运行，无需 Python 环境）
安全说明：本工具只归档不删除，纯本地运行，exe 内不含任何网络上传逻辑。
"""
import os
import sys
import subprocess

# ===== 项目参数 =====
APP_NAME = "CCWiper"
ENTRY = "main.py"
DATA_DIRS = ["core", "config"]   # 需随 exe 打包的资源目录（config 含安全规则 default_rules.json）
HIDDEN_IMPORTS = ["customtkinter", "darkdetect"]
# ====================

HERE = os.path.dirname(os.path.abspath(__file__))
SEP = os.pathsep  # Windows 用 ';'


def ensure_pyinstaller():
    try:
        import PyInstaller  # noqa
        return
    except ImportError:
        print("→ 未检测到 PyInstaller，正在自动安装…")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])


def main():
    ensure_pyinstaller()
    os.chdir(HERE)

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name", APP_NAME,
        "--onefile",
        "--windowed",
        "--noconfirm",
        "--clean",
        "--log-level", "WARN",
    ]
    for imp in HIDDEN_IMPORTS:
        cmd += ["--hidden-import", imp]
    # CustomTkinter 自带图片资源，需一并收集，否则打包后界面缺图标
    cmd += ["--collect-data", "customtkinter"]
    cmd += ["--collect-submodules", "customtkinter"]
    for d in DATA_DIRS:
        if os.path.isdir(os.path.join(HERE, d)):
            cmd += ["--add-data", f"{d}{SEP}{d}"]
    cmd.append(ENTRY)

    print(f"→ 开始打包 {APP_NAME}（首次约 1-3 分钟）…")
    subprocess.check_call(cmd)
    out = os.path.join(HERE, "dist", APP_NAME + ".exe")
    print(f"\n✅ 构建完成：{out}")
    print("   说明：--onefile 单文件 exe，首次启动会解压到临时目录稍慢（1-2 秒），之后正常。")


if __name__ == "__main__":
    main()
