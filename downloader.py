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
    python downloader.py <網址> --deep           也搜尋下一層頁面
    python downloader.py <網址> --list           只列出檔案，不下載
    python downloader.py                         不帶參數會詢問網址

支援的下載方式:
    1. 一般檔案連結            <a href="report.pdf">
    2. 媒體與嵌入標籤          <img> <video> <audio> <source> <embed> <iframe> <object>
    3. HTML5 download 屬性     <a href="/get?id=1" download="報告.pdf">
    4. 沒有副檔名的下載點      /Files/6010、download.php?id=5（向伺服器詢問檔名與類型）
    5. JavaScript 按鈕         onclick="window.open('/a.pdf')"、data-url="/a.pdf"
    6. 網頁內嵌資料            <script> 或 JSON 裡的檔案網址
    7. 雲端分享連結            Google 雲端硬碟 / 文件 / 試算表 / 簡報、Dropbox
    8. 下一層頁面（--deep）    列表頁 → 「下載」子頁面 → 附件
    9. 防盜連                  自動帶上 Referer、保留 Cookie、使用瀏覽器 User-Agent
"""

import argparse
import mimetypes
import os
import re
import ssl
import sys
from concurrent.futures import ThreadPoolExecutor
from html import unescape
from html.parser import HTMLParser
from http.cookiejar import CookieJar
from typing import NamedTuple
from urllib.error import HTTPError
from urllib.parse import parse_qs, quote, unquote, urljoin, urlparse
from urllib.request import HTTPCookieProcessor, HTTPSHandler, Request, build_opener

__version__ = "1.4.0"

# 預設視為「檔案」的副檔名
DEFAULT_EXTS = {
    "pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx", "odt", "ods", "odp",
    "docm", "xlsm", "pptm",
    "txt", "csv", "json", "xml", "md", "rtf",
    "zip", "rar", "7z", "tar", "gz", "bz2", "xz",
    "mp3", "wav", "flac", "m4a", "ogg",
    "mp4", "mkv", "avi", "mov", "webm",
    "exe", "msi", "apk", "dmg", "iso",
}
IMAGE_EXTS = {"jpg", "jpeg", "png", "gif", "webp", "svg", "bmp", "ico"}

# 執行檔、安裝檔、含巨集的 Office 檔：打開後可能讓電腦中毒，預設不下載
RISKY_EXTS = {
    "exe", "msi", "msix", "appx", "apk", "dmg", "iso", "img", "bat", "cmd", "com", "scr",
    "ps1", "vbs", "vbe", "js", "jse", "wsf", "hta", "jar", "lnk", "reg", "cpl",
    "docm", "dotm", "xlsm", "xltm", "xlam", "pptm", "potm", "ppsm",
}

# 網址結尾是這些的通常是動態程式，可能其實是下載點（例如 download.php?id=5）
DYNAMIC_EXTS = {"", "php", "asp", "aspx", "ashx", "axd", "jsp", "jspx", "do", "action", "cgi"}
# 一般網頁；--deep 時會打開看起來像「下載」的頁面
PAGE_EXTS = DYNAMIC_EXTS | {"html", "htm", "shtml", "xhtml"}

# 連結文字或屬性出現這些字，代表很可能是「下載」
DOWNLOAD_WORDS = re.compile(r"下載|下载|附件|download|attach", re.IGNORECASE)
# 網址路徑像下載點，例如 /Files/6010、download.php?id=5、GetFile.ashx
DOWNLOAD_PATH = re.compile(r"download|attach|getfile|fileget|/files?/|/dl/", re.IGNORECASE)

MAX_PROBES = 300    # 最多詢問幾個沒有副檔名的連結
MAX_SUBPAGES = 30   # --deep 最多打開幾個下一層頁面

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
        f"Chrome/130.0 Safari/537.36 web-file-downloader/{__version__}"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
}

# 仍會驗證憑證，只是關掉 Python 3.13 新增的嚴格檢查
# （許多台灣政府網站的憑證缺少 Subject Key Identifier，會被誤擋）
SSL_CTX = ssl.create_default_context()
SSL_CTX.verify_flags &= ~ssl.VERIFY_X509_STRICT

# 共用的連線器：會保留網站給的 Cookie（有些網站要先看過網頁才允許下載）
OPENER = build_opener(HTTPSHandler(context=SSL_CTX), HTTPCookieProcessor(CookieJar()))


class FileLink(NamedTuple):
    url: str
    name: str          # 存檔用的檔名
    referer: str = ""  # 在哪個網頁找到的（有些網站會檢查）


class DownloadError(Exception):
    """可以直接顯示給使用者看的錯誤。"""


def explain_http_error(err):
    """把常見的 HTTP 錯誤轉成看得懂的說明；不是常見情況就回傳原本的錯誤。"""
    server = (err.headers.get("Server") or "").lower() if err.headers else ""
    challenged = err.headers.get("cf-mitigated") if err.headers else None
    if err.code in (403, 503) and ("cloudflare" in server or challenged):
        return DownloadError(
            "這個網站啟用了 Cloudflare 防機器人保護，不允許程式自動讀取。\n"
            "請改用瀏覽器開啟網頁，手動下載檔案。"
        )
    if err.code == 403:
        return DownloadError("網站拒絕存取（HTTP 403）。可能需要登入，或網站不允許程式自動下載。")
    if err.code == 404:
        return DownloadError("找不到這個網址（HTTP 404），請確認網址是否正確。")
    if err.code == 429:
        return DownloadError("連線太頻繁，被網站暫時限制（HTTP 429），請稍後再試。")
    return err


class LinkParser(HTMLParser):
    """
    收集網頁中的連結:
      links       [網址, 看起來像下載?, download 屬性的檔名]
      attr_texts  其他屬性（onclick、data-*、meta content…）的內容，之後再從中找檔案網址
    """

    SRC_TAGS = {"img", "source", "video", "audio", "embed", "iframe", "track"}
    SKIP_ATTRS = {"class", "style", "id", "title", "alt", "href", "src", "name", "lang",
                  "dir", "role", "type", "width", "height", "rel", "target", "charset", "download"}

    def __init__(self):
        super().__init__()
        self.links = []
        self.attr_texts = []
        self._anchor = None  # 目前所在 <a> 在 links 中的位置

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        hint_attrs = " ".join(d.get(k) or "" for k in ("class", "title", "aria-label", "alt"))
        if tag == "a" and d.get("href"):
            hint = "download" in d or bool(DOWNLOAD_WORDS.search(hint_attrs))
            self.links.append([d["href"], hint, (d.get("download") or "").strip()])
            self._anchor = len(self.links) - 1
        elif tag in self.SRC_TAGS and d.get("src"):
            self.links.append([d["src"], False, ""])
        elif tag == "object" and d.get("data"):
            self.links.append([d["data"], False, ""])
        # <a> 裡的圖示，例如 <img alt="下載">
        if tag != "a" and self._anchor is not None and DOWNLOAD_WORDS.search(hint_attrs):
            self.links[self._anchor][1] = True
        for key, value in d.items():
            if value and key not in self.SKIP_ATTRS:
                self.attr_texts.append(value)

    def handle_endtag(self, tag):
        if tag == "a":
            self._anchor = None

    def handle_data(self, data):
        if self._anchor is not None and DOWNLOAD_WORDS.search(data):
            self.links[self._anchor][1] = True


# ---------- 網址與檔名 ----------

def get_ext(url):
    path = unquote(urlparse(url).path)
    _, ext = os.path.splitext(path)
    return ext.lstrip(".").lower()


def name_ext(name):
    return os.path.splitext(name)[1].lstrip(".").lower()


def is_risky(name):
    return name_ext(name) in RISKY_EXTS


def url_filename(url):
    return unquote(os.path.basename(urlparse(url).path))


def encode_url(url):
    """把網址中的中文、空白等字元轉成 %XX，已經編碼過的部分不會重複編碼。"""
    return quote(url, safe=":/?#[]@!$&'()*+,;=%~")


def normalize_url(url):
    url = url.strip()
    if url and not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url


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


def cloud_direct_url(url):
    """把 Google 雲端硬碟 / 文件 / Dropbox 的分享連結轉成直接下載網址；不是的話回傳 None。"""
    p = urlparse(url)
    host = p.netloc.lower()
    if host == "drive.google.com":
        m = re.search(r"/file/d/([\w-]+)", p.path)
        file_id = m.group(1) if m else parse_qs(p.query).get("id", [None])[0]
        if file_id:
            return f"https://drive.google.com/uc?export=download&id={file_id}"
    elif host == "docs.google.com":
        m = re.match(r"/(document|spreadsheets|presentation)/d/([\w-]+)", p.path)
        if m:
            kind, file_id = m.groups()
            export = {"document": "export?format=docx",
                      "spreadsheets": "export?format=xlsx",
                      "presentation": "export/pptx"}[kind]
            return f"https://docs.google.com/{kind}/d/{file_id}/{export}"
    elif host.endswith("dropbox.com") and p.path.startswith(("/s/", "/scl/")):
        if re.search(r"[?&]dl=0", url):
            return re.sub(r"([?&])dl=0", r"\1dl=1", url)
        if not re.search(r"[?&]dl=1", url):
            return url + ("&" if p.query else "?") + "dl=1"
        return url
    return None


# ---------- 連線 ----------

def open_url(url, timeout, referer="", method="GET"):
    headers = dict(HEADERS)
    if referer:
        headers["Referer"] = encode_url(referer)
    return OPENER.open(Request(encode_url(url), headers=headers, method=method), timeout=timeout)


def content_type(resp):
    return (resp.headers.get("Content-Type") or "").split(";")[0].strip().lower()


def is_html(resp):
    return content_type(resp) in ("text/html", "application/xhtml+xml")


def is_file_response(resp):
    disposition = (resp.headers.get("Content-Disposition") or "").lower()
    if "attachment" in disposition or "filename" in disposition:
        return True
    return bool(content_type(resp)) and not is_html(resp)


def parse_content_disposition(value):
    """從 Content-Disposition 標頭取出檔名，處理各種中文編碼寫法。"""
    if not value:
        return ""
    m = re.search(r"filename\*\s*=\s*([\w-]*)'[^']*'([^;]+)", value, re.IGNORECASE)
    if m:
        try:
            return unquote(m.group(2).strip().strip('"'), encoding=m.group(1) or "utf-8", errors="replace")
        except LookupError:
            return unquote(m.group(2).strip().strip('"'))
    m = (re.search(r'filename\s*=\s*"([^"]*)"', value, re.IGNORECASE)
         or re.search(r"filename\s*=\s*([^;]+)", value, re.IGNORECASE))
    if not m:
        return ""
    name = m.group(1).strip()
    if re.search(r"%[0-9A-Fa-f]{2}", name):
        return unquote(name)
    # http.client 以 latin-1 解讀標頭，UTF-8 或 Big5 的中文檔名要轉回來
    try:
        raw = name.encode("latin-1")
    except UnicodeEncodeError:
        return name
    for encoding in ("utf-8", "cp950"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            pass
    return name


def filename_from_response(resp, url):
    """優先用伺服器給的檔名，其次用網址；沒有副檔名時依檔案類型補上。"""
    name = parse_content_disposition(resp.headers.get("Content-Disposition"))
    name = os.path.basename(name.replace("\\", "/"))
    if not name:
        name = url_filename(url)
    if not name_ext(name):
        ctype = content_type(resp)
        ext = mimetypes.guess_extension(ctype) if ctype and ctype != "application/octet-stream" else None
        if ext:
            name = (name or "download") + ext
    return name or "download"


def read_html(resp):
    data = resp.read()
    charset = resp.headers.get_content_charset()
    if not charset:  # 有些台灣網站是 Big5，只寫在 <meta> 裡
        m = re.search(rb"""<meta[^>]+charset\s*=\s*["']?([\w-]+)""", data[:4096], re.IGNORECASE)
        charset = m.group(1).decode("ascii") if m else "utf-8"
    try:
        return data.decode(charset, errors="replace")
    except LookupError:
        return data.decode("utf-8", errors="replace")


def fetch_page(url, timeout):
    with open_url(url, timeout) as resp:
        return read_html(resp)


def probe(url, timeout, referer=""):
    """詢問伺服器這個網址是不是檔案；是的話回傳 FileLink，否則回傳 None。"""
    for method in ("HEAD", "GET"):  # 有些伺服器不接受 HEAD，改用 GET（只看標頭，不讀內容）
        try:
            with open_url(url, timeout, referer, method) as resp:
                if is_file_response(resp):
                    return FileLink(url, filename_from_response(resp, url), referer)
                return None
        except HTTPError as e:
            if method == "HEAD" and e.code in (403, 405, 501):
                continue
            return None
        except Exception:
            return None
    return None


# ---------- 從網頁找檔案 ----------

def _ext_pattern(exts):
    return "|".join(sorted(map(re.escape, exts), key=len, reverse=True))


def find_urls_in_text(text, exts):
    """
    找出藏在 <script> 或 JSON 資料裡的檔案網址（完整網址，或引號中以 / 開頭的路徑）。
    有些網站的「下載」是 <button>，網址只存在給 JavaScript 用的資料中。
    """
    if not exts:
        return []
    text = text.replace("\\/", "/").replace("\\u002F", "/").replace("\\u002f", "/")
    e = _ext_pattern(exts)
    absolute = rf"""https?://[^\s"'<>\\]+?\.(?:{e})(?![\w])(?:\?[^\s"'<>\\#]*)?"""
    relative = rf"""(?<=["'])\.{{0,2}}/[^\s"'<>\\]+?\.(?:{e})(?:\?[^\s"'<>\\#]*)?(?=\\?["'])"""
    return [unescape(m.group(0)) for m in re.finditer(f"{absolute}|{relative}", text, re.IGNORECASE)]


def find_urls_in_attr(value, exts):
    """從 onclick、data-url 等屬性找出檔案網址，相對路徑也算。"""
    if not exts:
        return []
    e = _ext_pattern(exts)
    value = value.strip()
    if re.fullmatch(rf"""[^\s"'<>()]+\.(?:{e})(?:\?\S*)?""", value, re.IGNORECASE):
        return [value]
    quoted = rf"""(?<=["'])[^\s"'<>\\()=]+?\.(?:{e})(?:\?[^\s"'<>\\#]*)?(?=["'])"""
    # meta refresh：content="0; url=file.pdf"
    refresh = rf"""(?<=url=)[^\s"'<>;]+?\.(?:{e})(?![\w])"""
    found = find_urls_in_text(value, exts)
    found += [m.group(0) for m in re.finditer(f"{quoted}|{refresh}", value, re.IGNORECASE)]
    return found


class PageScan(NamedTuple):
    entries: list   # [("file", FileLink) 或 ("probe", 網址)]，依網頁中的順序
    subpages: list  # 看起來像「下載」的一般網頁（--deep 時會打開）


def scan_page(page_url, html, exts):
    parser = LinkParser()
    parser.feed(html)
    candidates = [tuple(link) for link in parser.links]
    candidates += [(u, False, "") for u in find_urls_in_text(html, exts)]
    for text in parser.attr_texts:
        candidates += [(u, False, "") for u in find_urls_in_attr(text, exts)]

    host = urlparse(page_url).netloc.lower()
    entries, subpages = [], []
    seen = {unquote(page_url.split("#")[0])}
    for href, hint, name in candidates:
        full = urljoin(page_url, href.strip()).split("#")[0]
        if not full.startswith(("http://", "https://")):
            continue
        key = unquote(full)  # 同一個網址可能一個有編碼、一個沒有
        if key in seen:
            continue
        seen.add(key)

        ext = get_ext(full)
        parts = urlparse(full)
        same_host = parts.netloc.lower() == host
        cloud = cloud_direct_url(full)
        if cloud:
            entries.append(("probe", cloud))
        elif name and name_ext(name) in exts:
            entries.append(("file", FileLink(full, name, page_url)))
        elif ext in exts:
            entries.append(("file", FileLink(full, url_filename(full), page_url)))
        elif ext in DYNAMIC_EXTS and (hint or DOWNLOAD_PATH.search(f"{parts.path}?{parts.query}")):
            entries.append(("probe", full))
            if hint and same_host:
                subpages.append(full)
        elif hint and same_host and ext in PAGE_EXTS:
            subpages.append(full)
    return PageScan(entries, subpages)


def resolve(entries, exts, timeout, referer="", log=None):
    """把需要詢問的網址一次問完（同時發出多個請求），依原本順序回傳檔案清單。"""
    probe_urls = [value for kind, value in entries if kind == "probe"][:MAX_PROBES]
    found = {}
    if probe_urls:
        if log:
            log(f"正在確認 {len(probe_urls)} 個沒有副檔名的下載連結…")
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = pool.map(lambda u: probe(u, min(timeout, 20), referer), probe_urls)
            found = {u: link for u, link in zip(probe_urls, results) if link}
    links = []
    for kind, value in entries:
        if kind == "file":
            links.append(value)
        elif value in found and name_ext(found[value].name) in exts:
            links.append(found[value])
    return links


def find_file_links(page_url, html, exts, timeout=60, log=None):
    return resolve(scan_page(page_url, html, exts).entries, exts, timeout, page_url, log)


def _links_in_subpage(url, exts, timeout, referer):
    try:
        with open_url(url, timeout, referer) as resp:
            if not is_html(resp):
                return []
            html = read_html(resp)
        return find_file_links(url, html, exts, timeout)
    except Exception:
        return []


def get_links(url, exts, timeout, deep=False, log=None):
    """
    回傳要下載的 FileLink 清單。
    網址本身就是檔案時直接回傳它；deep=True 時也會搜尋看起來像「下載」的下一層頁面。
    """
    if get_ext(url) in exts:
        return [FileLink(url, url_filename(url))]
    cloud = cloud_direct_url(url)
    if cloud:
        link = probe(cloud, timeout)
        return [link] if link else []

    try:
        with open_url(url, timeout) as resp:
            if is_file_response(resp):
                return [FileLink(url, filename_from_response(resp, url))]
            html = read_html(resp)
    except HTTPError as e:
        raise explain_http_error(e) from e

    scan = scan_page(url, html, exts)
    links = resolve(scan.entries, exts, timeout, url, log)

    if deep and scan.subpages:
        seen = {unquote(link.url) for link in links}
        pages = [p for p in scan.subpages if unquote(p) not in seen][:MAX_SUBPAGES]
        if log:
            log(f"正在搜尋 {len(pages)} 個下一層頁面…")
        with ThreadPoolExecutor(max_workers=4) as pool:
            for sub_links in pool.map(lambda p: _links_in_subpage(p, exts, timeout, url), pages):
                for link in sub_links:
                    if unquote(link.url) not in seen:
                        seen.add(unquote(link.url))
                        links.append(link)
    return links


# ---------- 下載 ----------

def mark_from_internet(path, url, referer=""):
    """
    像瀏覽器一樣替檔案加上「來自網路」標記（Windows 的 Zone.Identifier），
    讓 Word / Excel 用「受保護的檢視」開啟、執行檔出現 SmartScreen 警告。
    """
    if sys.platform != "win32":
        return
    lines = ["[ZoneTransfer]", "ZoneId=3"]
    if referer:
        lines.append(f"ReferrerUrl={encode_url(referer)}")
    lines.append(f"HostUrl={encode_url(url)}")
    try:
        with open(path + ":Zone.Identifier", "w", encoding="ascii", errors="replace") as f:
            f.write("\n".join(lines) + "\n")
    except OSError:
        pass  # 例如 FAT32 隨身碟不支援，略過即可


def download(url, folder, timeout, progress=None, name=None, referer=""):
    """
    下載單一檔案，回傳 (存檔路徑, 位元組數)。
    progress(已下載, 總大小) 會在每個區塊後被呼叫；總大小未知時為 0。
    """
    part = None
    done = 0
    try:
        with open_url(url, timeout, referer) as resp:
            name = safe_filename(name or filename_from_response(resp, url))
            if is_html(resp) and name_ext(name) not in ("html", "htm"):
                raise DownloadError("伺服器回傳的是網頁，不是檔案（可能需要登入或在瀏覽器中確認）")
            path = unique_path(folder, name)
            part = path + ".part"
            total = int(resp.headers.get("Content-Length") or 0)
            with open(part, "wb") as f:
                while chunk := resp.read(64 * 1024):
                    f.write(chunk)
                    done += len(chunk)
                    if progress:
                        progress(done, total)
        os.replace(part, path)
        mark_from_internet(path, url, referer)
    except HTTPError as e:
        raise explain_http_error(e) from e
    except BaseException:
        # 下載失敗或被中斷時，不留下不完整的檔案
        if part and os.path.exists(part):
            os.remove(part)
        raise
    return path, done


# ---------- 指令版 ----------

CLEAR_LINE = f"\r{' ' * 40}\r"


def print_progress(done, total):
    if total:
        print(f"\r    {done * 100 // total:3d}%  {done / 1024:,.0f} KB", end="", flush=True)


def parse_args(argv=None):
    ap = argparse.ArgumentParser(
        prog="downloader.py",
        description="給一個網址，自動下載頁面中的檔案",
    )
    ap.add_argument("url", nargs="?", help="網頁網址（或直接是檔案網址）")
    ap.add_argument("-o", "--output", default="downloads", help="存放資料夾（預設 downloads）")
    ap.add_argument("-e", "--ext", help="只下載這些副檔名，逗號分隔，例如 pdf,zip")
    ap.add_argument("--images", action="store_true", help="也下載圖片")
    ap.add_argument("-d", "--deep", action="store_true", help="也搜尋看起來像「下載」的下一層頁面（較慢）")
    ap.add_argument("--include-risky", action="store_true",
                    help="也下載執行檔、安裝檔與含巨集的檔案（預設略過，可能有病毒風險）")
    ap.add_argument("-l", "--list", action="store_true", help="只列出找到的檔案，不下載")
    ap.add_argument("-t", "--timeout", type=float, default=60, help="連線逾時秒數（預設 60）")
    ap.add_argument("-V", "--version", action="version", version=f"%(prog)s {__version__}")
    return ap.parse_args(argv)


def run(args):
    """執行下載，回傳結束代碼：0 全部成功，1 有失敗。"""
    url = args.url
    if not url:
        try:
            url = input("請輸入網址: ")
        except EOFError:
            url = ""
    url = normalize_url(url)
    if not url:
        print("沒有輸入網址。", file=sys.stderr)
        return 2

    if args.ext:
        exts = {e.strip().lstrip(".").lower() for e in args.ext.split(",") if e.strip()}
    else:
        exts = DEFAULT_EXTS | (IMAGE_EXTS if args.images else set())

    is_page = get_ext(url) not in exts
    if is_page:
        print(f"讀取網頁: {url}")
    try:
        links = get_links(url, exts, args.timeout, deep=args.deep, log=print)
    except Exception as e:
        print(f"無法讀取網頁: {e}", file=sys.stderr)
        return 1
    if not links:
        print("這個頁面沒有找到符合的檔案連結。")
        return 0
    if is_page:
        print(f"找到 {len(links)} 個檔案:\n")

    if args.list:
        for link in links:
            print(("⚠ " if is_risky(link.name) else "") + link.name)
            print(f"    {link.url}")
        return 0

    # 指定了 -e 代表使用者明確要這些類型，就不再略過
    if not args.ext and not args.include_risky:
        risky = [link for link in links if is_risky(link.name)]
        if risky:
            links = [link for link in links if not is_risky(link.name)]
            print(f"⚠ 已略過 {len(risky)} 個執行檔或含巨集的檔案（可能有病毒風險）。")
            print("  確定來源可信、需要下載時，請加上 --include-risky。\n")
        if not links:
            return 0

    os.makedirs(args.output, exist_ok=True)
    ok = 0
    for i, link in enumerate(links, 1):
        print(f"[{i}/{len(links)}] {link.name}")
        try:
            path, size = download(link.url, args.output, args.timeout, print_progress, link.name, link.referer)
            print(f"{CLEAR_LINE}    完成  {size / 1024:,.0f} KB -> {path}")
            ok += 1
        except Exception as e:
            print(f"{CLEAR_LINE}    失敗: {e}")

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
