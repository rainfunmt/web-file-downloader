#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""
網頁檔案下載器 (Web File Downloader)

給一個網址，自動抓出頁面中所有檔案連結並下載。
只用 Python 內建模組，不需要安裝任何套件。

用法:
    python downloader.py <網址>
    python downloader.py <網址> -o 存放資料夾
    python downloader.py <網址> -e pdf,zip       只下載指定副檔名
    python downloader.py <網址> --images         也下載頁面中的圖片
    python downloader.py <網址> --list           只列出檔案，不下載
    python downloader.py                         不帶參數會詢問網址
"""

import argparse
import os
import re
import ssl
import sys
from html.parser import HTMLParser
from urllib.parse import quote, unquote, urljoin, urlparse
from urllib.request import Request, urlopen

__version__ = "1.0.0"

# 預設視為「檔案」的副檔名
DEFAULT_EXTS = {
    "pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx", "odt", "ods", "odp",
    "txt", "csv", "json", "xml", "md", "rtf",
    "zip", "rar", "7z", "tar", "gz", "bz2", "xz",
    "mp3", "wav", "flac", "m4a", "ogg",
    "mp4", "mkv", "avi", "mov", "webm",
    "exe", "msi", "apk", "dmg", "iso",
}
IMAGE_EXTS = {"jpg", "jpeg", "png", "gif", "webp", "svg", "bmp", "ico"}

HEADERS = {"User-Agent": f"Mozilla/5.0 (compatible; web-file-downloader/{__version__})"}

# 仍會驗證憑證，只是關掉 Python 3.13 新增的嚴格檢查
# （許多台灣政府網站的憑證缺少 Subject Key Identifier，會被誤擋）
SSL_CTX = ssl.create_default_context()
SSL_CTX.verify_flags &= ~ssl.VERIFY_X509_STRICT


class LinkParser(HTMLParser):
    """收集 <a href> 與 <img src> 等連結。"""

    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "a" and attrs.get("href"):
            self.links.append(attrs["href"])
        elif tag in ("img", "source", "video", "audio", "embed") and attrs.get("src"):
            self.links.append(attrs["src"])


def get_ext(url):
    path = unquote(urlparse(url).path)
    _, ext = os.path.splitext(path)
    return ext.lstrip(".").lower()


def encode_url(url):
    """把網址中的中文、空白等字元轉成 %XX，已經編碼過的部分不會重複編碼。"""
    return quote(url, safe=":/?#[]@!$&'()*+,;=%~")


def safe_filename(name):
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name).strip(" .")
    return name or "download"


def unique_path(folder, name):
    base, ext = os.path.splitext(name)
    path = os.path.join(folder, name)
    i = 1
    while os.path.exists(path):
        path = os.path.join(folder, f"{base}({i}){ext}")
        i += 1
    return path


def open_url(url, timeout):
    return urlopen(Request(encode_url(url), headers=HEADERS), timeout=timeout, context=SSL_CTX)


def fetch_page(url, timeout):
    with open_url(url, timeout) as resp:
        charset = resp.headers.get_content_charset() or "utf-8"
        return resp.read().decode(charset, errors="replace")


def find_file_links(page_url, html, exts):
    parser = LinkParser()
    parser.feed(html)
    seen, result = set(), []
    for link in parser.links:
        full = urljoin(page_url, link.strip()).split("#")[0]
        if not full.startswith(("http://", "https://")):
            continue
        if get_ext(full) in exts and full not in seen:
            seen.add(full)
            result.append(full)
    return result


def download(url, folder, timeout):
    name = safe_filename(os.path.basename(unquote(urlparse(url).path)))
    path = unique_path(folder, name)
    part = path + ".part"
    done = 0
    try:
        with open_url(url, timeout) as resp, open(part, "wb") as f:
            total = int(resp.headers.get("Content-Length") or 0)
            while chunk := resp.read(64 * 1024):
                f.write(chunk)
                done += len(chunk)
                if total:
                    print(f"\r    {done * 100 // total:3d}%  {done / 1024:,.0f} KB", end="", flush=True)
        os.replace(part, path)
    except BaseException:
        # 下載失敗或被中斷時，不留下不完整的檔案
        if os.path.exists(part):
            os.remove(part)
        print(f"\r{' ' * 40}\r", end="")
        raise
    print(f"\r{' ' * 40}\r    完成  {done / 1024:,.0f} KB -> {path}")


def parse_args(argv=None):
    ap = argparse.ArgumentParser(
        prog="downloader.py",
        description="給一個網址，自動下載頁面中的檔案",
    )
    ap.add_argument("url", nargs="?", help="網頁網址（或直接是檔案網址）")
    ap.add_argument("-o", "--output", default="downloads", help="存放資料夾（預設 downloads）")
    ap.add_argument("-e", "--ext", help="只下載這些副檔名，逗號分隔，例如 pdf,zip")
    ap.add_argument("--images", action="store_true", help="也下載圖片")
    ap.add_argument("-l", "--list", action="store_true", help="只列出找到的檔案，不下載")
    ap.add_argument("-t", "--timeout", type=float, default=60, help="連線逾時秒數（預設 60）")
    ap.add_argument("-V", "--version", action="version", version=f"%(prog)s {__version__}")
    return ap.parse_args(argv)


def run(args):
    """執行下載，回傳結束代碼：0 全部成功，1 有失敗。"""
    url = args.url
    if not url:
        try:
            url = input("請輸入網址: ").strip()
        except EOFError:
            url = ""
        if not url:
            print("沒有輸入網址。", file=sys.stderr)
            return 2
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    if args.ext:
        exts = {e.strip().lstrip(".").lower() for e in args.ext.split(",") if e.strip()}
    else:
        exts = DEFAULT_EXTS | (IMAGE_EXTS if args.images else set())

    # 網址本身就是檔案 → 直接下載
    if get_ext(url) in exts:
        links = [url]
    else:
        print(f"讀取網頁: {url}")
        try:
            html = fetch_page(url, args.timeout)
        except Exception as e:
            print(f"無法讀取網頁: {e}", file=sys.stderr)
            return 1
        links = find_file_links(url, html, exts)
        if not links:
            print("這個頁面沒有找到符合的檔案連結。")
            return 0
        print(f"找到 {len(links)} 個檔案:\n")

    if args.list:
        for link in links:
            print(link)
        return 0

    os.makedirs(args.output, exist_ok=True)
    ok = 0
    for i, link in enumerate(links, 1):
        print(f"[{i}/{len(links)}] {link}")
        try:
            download(link, args.output, args.timeout)
            ok += 1
        except Exception as e:
            print(f"    失敗: {e}")

    print(f"\n完成！成功 {ok} / {len(links)} 個，存在 {os.path.abspath(args.output)}")
    return 0 if ok == len(links) else 1


def main(argv=None):
    # 避免主控台不支援某些字元時程式中斷
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="replace")
    try:
        return run(parse_args(argv))
    except KeyboardInterrupt:
        print("\n已取消。", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
