#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""
網頁檔案下載器 — 視窗版

貼上網址 → 搜尋 → 勾選檔案 → 下載。
抓檔案的邏輯沿用 downloader.py，只用 Python 內建模組。

用法:
    python gui.py
"""

import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, font, messagebox, ttk

import downloader as dl

CHECKED, UNCHECKED = "☑", "☐"
TIMEOUT = 60


class Cancelled(Exception):
    """使用者按了「停止」。"""


def default_folder():
    return Path.home() / "Downloads" / "網頁檔案下載器"


def open_in_file_manager(path):
    if sys.platform == "win32":
        os.startfile(path)
    elif sys.platform == "darwin":
        subprocess.run(["open", path], check=False)
    else:
        subprocess.run(["xdg-open", path], check=False)


class App:
    def __init__(self, root):
        self.root = root
        self.events = queue.Queue()  # 背景執行緒 → 畫面 的訊息
        self.stop_flag = threading.Event()
        self.busy = False
        self.closing = False  # 等下載停止後再關閉視窗
        self.closed = False
        self.links = {}  # 表格列 id → dl.FileLink

        # 高解析度螢幕（例如 150% 縮放）時，視窗與欄寬要跟著放大
        self.scale = max(1.0, root.winfo_fpixels("1i") / 96)
        root.title(f"網頁檔案下載器 {dl.__version__}")
        self._place_window(860, 600)
        root.minsize(self.px(560), self.px(400))
        root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.url_var = tk.StringVar()
        self.folder_var = tk.StringVar(value=str(default_folder()))
        self.images_var = tk.BooleanVar(value=False)
        self.deep_var = tk.BooleanVar(value=False)
        self.status_var = tk.StringVar(value="貼上網址，按「搜尋」找出網頁上的檔案。")
        self.count_var = tk.StringVar()

        self._setup_style()
        self._build()
        self.url_entry.focus_set()
        root.after(100, self._poll)

    # ---------- 畫面 ----------

    def px(self, n):
        return int(n * self.scale)

    def _place_window(self, width, height):
        """視窗置中，且不超過螢幕（扣掉工作列的高度）。"""
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        w = min(self.px(width), sw - self.px(40))
        h = min(self.px(height), sh - self.px(120))
        x = (sw - w) // 2
        y = max(0, (sh - self.px(80) - h) // 2)
        self.root.geometry(f"{w}x{h}+{x}+{y}")

    def _add_paste_menu(self, entry):
        """在輸入框按右鍵可以「貼上」，習慣用滑鼠的人比較方便。"""
        menu = tk.Menu(entry, tearoff=False)
        menu.add_command(label="貼上", command=lambda: entry.event_generate("<<Paste>>"))
        menu.add_command(label="全部選取", command=lambda: entry.select_range(0, "end"))
        menu.add_separator()
        menu.add_command(label="清除", command=lambda: entry.delete(0, "end"))

        def popup(event):
            entry.focus_set()
            menu.tk_popup(event.x_root, event.y_root)

        entry.bind("<Button-3>", popup)

    def _setup_style(self):
        for name in ("TkDefaultFont", "TkTextFont", "TkHeadingFont"):
            font.nametofont(name).configure(size=10)
        line = font.nametofont("TkDefaultFont").metrics("linespace")
        ttk.Style().configure("Treeview", rowheight=int(line * 1.7))

    def _build(self):
        pad = {"padx": 6, "pady": 4}

        top = ttk.Frame(self.root, padding=(10, 10, 10, 0))
        top.pack(fill="x")
        top.columnconfigure(1, weight=1)

        ttk.Label(top, text="網址").grid(row=0, column=0, sticky="w", **pad)
        self.url_entry = ttk.Entry(top, textvariable=self.url_var)
        self.url_entry.grid(row=0, column=1, sticky="ew", **pad)
        self.url_entry.bind("<Return>", lambda e: self.search())
        self._add_paste_menu(self.url_entry)
        self.search_btn = ttk.Button(top, text="搜尋", command=self.search)
        self.search_btn.grid(row=0, column=2, sticky="ew", **pad)

        ttk.Label(top, text="存到").grid(row=1, column=0, sticky="w", **pad)
        folder_entry = ttk.Entry(top, textvariable=self.folder_var)
        folder_entry.grid(row=1, column=1, sticky="ew", **pad)
        self._add_paste_menu(folder_entry)
        ttk.Button(top, text="選擇資料夾…", command=self.choose_folder).grid(row=1, column=2, sticky="ew", **pad)

        options = ttk.Frame(top)
        options.grid(row=2, column=1, sticky="w", **pad)
        ttk.Checkbutton(options, text="也找圖片檔", variable=self.images_var).pack(side="left")
        ttk.Checkbutton(
            options, text="也搜尋下一層頁面（例如「下載專區」裡的子頁面，較慢）", variable=self.deep_var
        ).pack(side="left", padx=(16, 0))

        mid = ttk.Frame(self.root, padding=(16, 6, 16, 0))
        mid.pack(fill="both", expand=True)

        bar = ttk.Frame(mid)
        bar.pack(fill="x", pady=(0, 6))
        self.all_btn = ttk.Button(bar, text="全選", command=lambda: self.check_all(True))
        self.all_btn.pack(side="left")
        self.none_btn = ttk.Button(bar, text="全不選", command=lambda: self.check_all(False))
        self.none_btn.pack(side="left", padx=6)
        ttk.Label(bar, textvariable=self.count_var).pack(side="left", padx=6)

        table = ttk.Frame(mid)
        table.pack(fill="both", expand=True)
        self.tree = ttk.Treeview(
            table, columns=("check", "name", "type", "status"), show="headings", selectmode="none"
        )
        for col, text, width, anchor, stretch in (
            ("check", "", 36, "center", False),
            ("name", "檔名", 440, "w", True),
            ("type", "類型", 76, "center", False),
            ("status", "狀態", 190, "w", False),
        ):
            self.tree.heading(col, text=text, anchor=anchor)
            self.tree.column(col, width=self.px(width), minwidth=self.px(min(width, 60)), anchor=anchor, stretch=stretch)
        scroll = ttk.Scrollbar(table, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        self.tree.bind("<Button-1>", self.on_click)

        bottom = ttk.Frame(self.root, padding=(16, 8, 16, 12))
        bottom.pack(fill="x")
        self.progress = ttk.Progressbar(bottom, mode="determinate")
        self.progress.pack(fill="x")
        ttk.Label(bottom, textvariable=self.status_var).pack(fill="x", pady=(6, 6))

        buttons = ttk.Frame(bottom)
        buttons.pack(fill="x")
        ttk.Button(buttons, text="打開資料夾", command=self.open_folder).pack(side="right")
        self.download_btn = ttk.Button(buttons, text="下載選取的檔案", command=self.start_download)
        self.download_btn.pack(side="right", padx=6)
        self.stop_btn = ttk.Button(buttons, text="停止", command=self.stop, state="disabled")
        self.stop_btn.pack(side="right")

    def set_busy(self, busy, downloading=False):
        self.busy = busy
        state = "disabled" if busy else "normal"
        for widget in (self.search_btn, self.download_btn, self.all_btn, self.none_btn):
            widget.configure(state=state)
        self.stop_btn.configure(state="normal" if downloading else "disabled")

    # ---------- 勾選 ----------

    def checked_items(self):
        return [i for i in self.tree.get_children() if self.tree.set(i, "check") == CHECKED]

    def update_count(self):
        total = len(self.tree.get_children())
        self.count_var.set(f"已選 {len(self.checked_items())} / 共 {total} 個檔案" if total else "")

    def on_click(self, event):
        item = self.tree.identify_row(event.y)
        if item and not self.busy:
            mark = UNCHECKED if self.tree.set(item, "check") == CHECKED else CHECKED
            self.tree.set(item, "check", mark)
            self.update_count()

    def check_all(self, value):
        for item in self.tree.get_children():
            self.tree.set(item, "check", CHECKED if value else UNCHECKED)
        self.update_count()

    # ---------- 動作 ----------

    def choose_folder(self):
        folder = filedialog.askdirectory(initialdir=self.folder_var.get() or str(Path.home()))
        if folder:
            self.folder_var.set(os.path.normpath(folder))

    def open_folder(self):
        folder = self.folder_var.get().strip()
        try:
            os.makedirs(folder, exist_ok=True)
            open_in_file_manager(folder)
        except OSError as e:
            messagebox.showerror("無法打開資料夾", str(e))

    def search(self):
        if self.busy:
            return
        url = dl.normalize_url(self.url_var.get())
        if not url:
            messagebox.showinfo("請輸入網址", "請先在「網址」欄貼上要下載的網頁網址。")
            return
        self.url_var.set(url)
        exts = dl.DEFAULT_EXTS | (dl.IMAGE_EXTS if self.images_var.get() else set())

        self.tree.delete(*self.tree.get_children())
        self.links.clear()
        self.update_count()
        self.set_busy(True)
        self.status_var.set("正在讀取網頁…")
        self.progress.configure(mode="indeterminate")
        self.progress.start(12)

        deep = self.deep_var.get()

        def work():
            try:
                log = lambda message: self.events.put(("status", message))
                self.events.put(("found", dl.get_links(url, exts, TIMEOUT, deep=deep, log=log)))
            except dl.DownloadError as e:
                self.events.put(("search_error", str(e)))
            except Exception as e:
                self.events.put(("search_error", f"請確認網址是否正確、網路是否連線。\n\n{e}"))

        threading.Thread(target=work, daemon=True).start()

    def start_download(self):
        if self.busy:
            return
        items = self.checked_items()
        if not items:
            messagebox.showinfo("沒有選取檔案", "請先按「搜尋」，再勾選要下載的檔案。")
            return
        folder = self.folder_var.get().strip()
        try:
            os.makedirs(folder, exist_ok=True)
        except OSError as e:
            messagebox.showerror("無法建立資料夾", str(e))
            return

        risky = [self.links[item].name for item in items if dl.is_risky(self.links[item].name)]
        if risky and not self.confirm_risky(risky):
            return

        jobs = [(item, self.links[item]) for item in items]
        for item, _ in jobs:
            self.tree.set(item, "status", "等待中")
        self.stop_flag.clear()
        self.set_busy(True, downloading=True)
        self.progress.configure(mode="determinate", maximum=len(jobs), value=0)
        self.status_var.set(f"開始下載 {len(jobs)} 個檔案…")
        threading.Thread(target=self._download_worker, args=(jobs, folder), daemon=True).start()

    def confirm_risky(self, names):
        shown = "\n".join(f"• {name}" for name in names[:5])
        if len(names) > 5:
            shown += f"\n…等共 {len(names)} 個"
        return messagebox.askyesno(
            "可能有病毒風險",
            f"你選取了 {len(names)} 個執行檔或含巨集的檔案：\n\n{shown}\n\n"
            "這類檔案打開後可能讓電腦中毒。請確認網站來源可信，打開前先用防毒軟體掃描。\n\n"
            "確定要下載嗎？",
            icon="warning",
        )

    def _download_worker(self, jobs, folder):
        ok = 0
        for item, link in jobs:
            if self.stop_flag.is_set():
                break
            self.events.put(("file_progress", item, 0))
            last = [-1]

            def progress(done, total, item=item):
                if self.stop_flag.is_set():
                    raise Cancelled
                if total:
                    pct = done * 100 // total
                    if pct != last[0]:
                        last[0] = pct
                        self.events.put(("file_progress", item, pct))

            try:
                _, size = dl.download(link.url, folder, TIMEOUT, progress, link.name, link.referer)
                ok += 1
                self.events.put(("file_done", item, size))
            except Cancelled:
                self.events.put(("file_failed", item, "已停止"))
                break
            except Exception as e:
                self.events.put(("file_failed", item, f"失敗：{e}"))
        self.events.put(("all_done", ok, len(jobs), self.stop_flag.is_set()))

    def stop(self):
        self.stop_flag.set()
        self.stop_btn.configure(state="disabled")
        self.status_var.set("正在停止…")

    def on_close(self):
        if self.busy and self.stop_btn.instate(["!disabled"]):
            if not messagebox.askyesno("還在下載", "檔案還在下載中，確定要停止並關閉嗎？"):
                return
            # 等背景執行緒刪掉下載到一半的檔案再關閉
            self.closing = True
            self.stop()
            return
        self.close_window()

    def close_window(self):
        self.closed = True
        self.root.destroy()

    # ---------- 處理背景訊息 ----------

    def _poll(self):
        try:
            while not self.closed:
                self._handle(*self.events.get_nowait())
        except queue.Empty:
            pass
        if not self.closed:
            self.root.after(100, self._poll)

    def _handle(self, kind, *data):
        if kind == "found":
            links = data[0]
            self.progress.stop()
            self.progress.configure(mode="determinate", value=0)
            risky_count = 0
            for link in links:
                kind = dl.name_ext(link.name).upper() or "?"
                mark = CHECKED
                if dl.is_risky(link.name):  # 執行檔、含巨集的檔案預設不勾選
                    kind, mark = f"⚠ {kind}", UNCHECKED
                    risky_count += 1
                item = self.tree.insert("", "end", values=(mark, link.name, kind, ""))
                self.links[item] = link
            self.update_count()
            self.set_busy(False)
            if risky_count:
                self.status_var.set(
                    f"找到 {len(links)} 個檔案。其中 {risky_count} 個是執行檔或含巨集的檔案（⚠），"
                    "可能有病毒風險，已預設不勾選。"
                )
            elif links:
                self.status_var.set(f"找到 {len(links)} 個檔案。勾選要的檔案，再按「下載選取的檔案」。")
            else:
                self.status_var.set("這個網頁沒有找到可以下載的檔案。")

        elif kind == "status":
            self.status_var.set(data[0])

        elif kind == "search_error":
            self.progress.stop()
            self.progress.configure(mode="determinate", value=0)
            self.set_busy(False)
            self.status_var.set("無法讀取網頁。")
            messagebox.showerror("無法讀取網頁", data[0])

        elif kind == "file_progress":
            item, pct = data
            self.tree.set(item, "status", f"下載中 {pct}%")
            self.tree.see(item)

        elif kind == "file_done":
            item, size = data
            self.tree.set(item, "status", f"✔ 完成 {size / 1024:,.0f} KB")
            self.progress.configure(value=self.progress["value"] + 1)

        elif kind == "file_failed":
            item, message = data
            self.tree.set(item, "status", message)
            self.progress.configure(value=self.progress["value"] + 1)

        elif kind == "all_done":
            ok, total, stopped = data
            self.set_busy(False)
            failed = total - ok
            if stopped:
                text = f"已停止。成功下載 {ok} 個檔案。"
            elif failed:
                text = f"完成：成功 {ok} 個，失敗 {failed} 個。"
            else:
                text = f"全部完成！成功下載 {ok} 個檔案。"
            self.status_var.set(text)
            if self.closing:
                self.close_window()


def main():
    if sys.platform == "win32":
        try:  # 高解析度螢幕上避免字體模糊
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
