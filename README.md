# 網頁檔案下載器 Web File Downloader

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Python 3.8+](https://img.shields.io/badge/Python-3.8%2B-blue)
![Windows | macOS | Linux](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)

**貼上一個網址，自動找出網頁上所有可以下載的檔案，勾選後一次下載。**

適合用在政府機關的「書表下載」、學校的課程講義、考試的歷屆試題、公司的文件中心這類一頁有很多檔案的網站，不必再一個一個點。

---

## 目錄

- [功能特色](#功能特色)
- [下載與安裝](#下載與安裝)
- [使用方式](#使用方式)
- [支援的下載方式](#支援的下載方式)
- [安全須知](#安全須知)
- [常見問題](#常見問題)
- [限制](#限制)
- [開發者資訊](#開發者資訊)
- [授權](#授權)

---

## 功能特色

| | |
|---|---|
| 🖱️ **免安裝、好上手** | Windows 下載 `.exe` 雙擊就能用；有視窗介面，不用打指令 |
| 🔍 **找得到藏起來的檔案** | 除了一般連結，也能找出「下載」按鈕、沒有副檔名的下載點、雲端分享連結等 |
| 🀄 **中文友善** | 支援中文網址、中文檔名與 Big5 編碼的舊網站 |
| 🛡️ **下載更安全** | 檔案標記為「來自網路」；執行檔與含巨集的檔案會特別提醒 |
| 📁 **不覆蓋、不留殘檔** | 同名檔案自動加編號；下載失敗或中途停止，不留下不完整的檔案 |
| 📦 **零相依套件** | 只用 Python 標準函式庫，一個檔案就能執行 |

---

## 下載與安裝

### Windows（推薦）

1. 到 [Releases 頁面](https://github.com/rainfunmt/web-file-downloader/releases/latest) 下載 **`WebFileDownloader.exe`**
2. 放在任何資料夾，雙擊打開即可，不需要安裝

> **第一次打開出現「Windows 已保護您的電腦」？**
> 這是因為程式沒有付費購買數位簽章，不代表有病毒。按 **其他資訊** → **仍要執行** 即可。
> Releases 頁面附有檔案的 SHA-256 指紋，可以用來確認下載的 exe 沒有被修改過。

### 用 Python 執行（Windows / macOS / Linux）

需要 Python 3.8 以上，不需要 `pip install` 任何套件。

```bash
git clone https://github.com/rainfunmt/web-file-downloader.git
cd web-file-downloader
```

---

## 使用方式

### 視窗版

用 exe，或執行：

```bash
python gui.py
```

1. 在 **網址** 欄貼上網頁網址（`Ctrl + V`，或按右鍵 →「貼上」），按 **搜尋**
2. 清單會列出找到的檔案。點一下那一列就能勾選或取消
3. 按 **下載選取的檔案**
4. 下載完成後按 **打開資料夾** 查看

| 選項 | 說明 |
|---|---|
| **存到** | 檔案存放位置，預設是「下載\網頁檔案下載器」，可按「選擇資料夾…」更改 |
| **也找圖片檔** | 連網頁上的圖片也列出來 |
| **也搜尋下一層頁面** | 找不到想要的檔案時勾選，會再打開網頁中看起來像「下載」的子頁面（較慢） |
| **停止** | 中途取消下載，下載到一半的檔案會自動刪除 |

### 指令版

```bash
python downloader.py                        # 執行後再貼上網址
python downloader.py https://example.com/   # 直接指定網址
```

檔案預設存到目前資料夾下的 `downloads/`。

| 參數 | 說明 |
|---|---|
| `url` | 網頁網址，也可以直接是檔案網址；省略時會詢問 |
| `-o`, `--output 資料夾` | 存放資料夾（預設 `downloads`） |
| `-e`, `--ext pdf,zip` | 只下載指定的副檔名，以逗號分隔 |
| `--images` | 連網頁上的圖片也一起下載 |
| `-d`, `--deep` | 也搜尋看起來像「下載」的下一層頁面（最多 30 頁） |
| `--include-risky` | 也下載執行檔與含巨集的檔案（預設略過） |
| `-l`, `--list` | 只列出找到的檔案，不下載 |
| `-t`, `--timeout 秒數` | 連線逾時秒數（預設 60） |
| `-V`, `--version` | 顯示版本 |
| `-h`, `--help` | 顯示說明 |

範例：

```bash
# 先看看網頁上有哪些檔案
python downloader.py https://example.com/resources --list

# 只下載 PDF，存到 docs 資料夾
python downloader.py https://example.com/resources -e pdf -o docs

# 連下一層頁面一起找
python downloader.py https://example.com/forms --deep
```

執行畫面：

```
讀取網頁: https://example.com/resources
正在確認 1 個沒有副檔名的下載連結…
找到 3 個檔案:

[1/3] 指南.pdf
    完成  5,115 KB -> downloads\指南.pdf
[2/3] 申報表.odt
    完成  82 KB -> downloads\申報表.odt
[3/3] missing.docx
    失敗: 找不到這個網址（HTTP 404），請確認網址是否正確。

完成！成功 2 / 3 個，存在 C:\...\downloads
```

結束代碼：`0` 全部成功（或沒有找到檔案）、`1` 有檔案失敗或無法讀取網頁、`2` 沒有輸入網址、`130` 按 Ctrl+C 取消。

---

## 支援的下載方式

網站提供檔案下載的方式有很多種，本程式支援以下幾種：

| # | 下載方式 | 例子 | 支援 |
|---|---|---|---|
| 1 | 一般檔案連結 | `<a href="report.pdf">` | ✅ |
| 2 | 媒體與嵌入標籤 | `<img>`、`<video>`、`<audio>`、`<iframe src="x.pdf">`、`<object>` | ✅ |
| 3 | HTML5 `download` 屬性 | `<a href="/get?id=1" download="報告.pdf">` | ✅ 使用指定的檔名 |
| 4 | 沒有副檔名的下載點 | `/Files/6010`、`download.php?id=5`、`GetFile.ashx?id=3` | ✅ 向伺服器詢問檔名與類型 |
| 5 | JavaScript 按鈕 | `onclick="window.open('/a.pdf')"`、`data-url="/a.pdf"` | ✅ |
| 6 | 網頁內嵌資料 | React、Next.js 等網站藏在 `<script>` 或 JSON 裡的檔案網址 | ✅ |
| 7 | 雲端分享連結 | Google 雲端硬碟、Google 文件／試算表／簡報、Dropbox | ✅ 限公開分享的單一檔案 |
| 8 | 下一層頁面 | 列表頁 →「書表下載」子頁面 → 附件 | ✅ 需開啟「也搜尋下一層頁面」 |
| 9 | 轉址 | HTTP 302 轉址、`<meta http-equiv="refresh">` | ✅ |
| 10 | 防盜連 | 檢查 Referer、Cookie | ✅ 自動帶上 |
| 11 | 表單送出才下載 | `<form method="post">`、ASP.NET `__doPostBack` | ❌ |
| 12 | 載入後才由 JavaScript 取得 | 「載入更多」、無限捲動、要先點選分頁 | ❌ 需要真正的瀏覽器 |
| 13 | 需要登入或驗證碼 | 會員專區、圖形驗證碼 | ❌ |
| 14 | 防機器人保護 | Cloudflare「Just a moment...」檢查頁 | ❌ 會顯示說明，請改用瀏覽器 |

第 4、7 類的連結看不出檔案類型，程式會先向伺服器詢問（只讀回應標頭，不下載內容），確認是檔案才列出來。

### 預設會找的檔案類型

| 類別 | 副檔名 |
|---|---|
| 文件 | pdf、doc、docx、xls、xlsx、ppt、pptx、odt、ods、odp、txt、csv、json、xml、md、rtf |
| 含巨集的文件 ⚠ | docm、xlsm、pptm |
| 壓縮檔 | zip、rar、7z、tar、gz、bz2、xz |
| 音訊 | mp3、wav、flac、m4a、ogg |
| 影片 | mp4、mkv、avi、mov、webm |
| 安裝檔 ⚠ | exe、msi、apk、dmg、iso |
| 圖片（需開啟「也找圖片檔」或 `--images`） | jpg、jpeg、png、gif、webp、svg、bmp、ico |

---

## 安全須知

從網路下載的檔案可能含有病毒。本程式提供以下保護，但最重要的還是**只下載你信任的網站的檔案**。

- **標記為「來自網路」**：下載的檔案會和用瀏覽器下載的一樣被 Windows 標記。Word、Excel 會用「受保護的檢視」開啟，執行檔會出現 SmartScreen 警告。請不要隨意關閉這些保護。（僅限 Windows；FAT32 隨身碟等不支援標記的磁碟會略過）
- **高風險檔案會特別提醒**：執行檔、安裝檔、指令檔與含巨集的 Office 檔會標示 ⚠。
  - 視窗版：預設不勾選，勾選後下載前會再提醒一次
  - 指令版：預設略過，確定需要時加上 `--include-risky`，或用 `-e exe` 明確指定
- **壓縮檔要小心**：zip、rar 裡可能藏有執行檔，解壓縮後一樣要留意。
- **保持防毒軟體開啟**：Windows Defender 等防毒軟體會即時掃描新下載的檔案。

---

## 常見問題

**Q：按了搜尋，卻顯示「沒有找到可以下載的檔案」？**
勾選「也搜尋下一層頁面」（指令版加 `--deep`）再試一次。如果還是找不到，可能是[不支援的下載方式](#支援的下載方式)（第 11～14 類）。

**Q：出現「這個網站啟用了 Cloudflare 防機器人保護」？**
代表網站不允許程式自動讀取，本程式不會嘗試繞過。請改用瀏覽器開啟網頁，手動下載。

**Q：可以下載我 Google 雲端硬碟裡的私人檔案嗎？**
不行，本程式不會讀取你在瀏覽器中的登入資料。想一次下載雲端硬碟裡的很多檔案，可以在 Google 雲端硬碟網頁選取檔案或資料夾後按右鍵 →「下載」，Google 會自動壓縮成 zip。

**Q：為什麼有些檔案預設沒有勾選？**
標示 ⚠ 的是執行檔或含巨集的檔案，可能有病毒風險。確認網站可信、真的需要時再勾選。

**Q：下載的 Word 檔打開時是「受保護的檢視」？**
這是正常的安全保護，和用瀏覽器下載的檔案一樣。確認內容沒問題後，按「啟用編輯」即可。

---

## 限制

- 不支援上表第 11～14 類的下載方式。網站用防機器人保護擋下程式，代表網站不希望被自動下載，本程式不會嘗試繞過。
- 「搜尋下一層頁面」只會打開同一個網站上、看起來像「下載」的頁面，最多 30 頁，不會無限往下爬。
- 少數網站會把網頁偽裝成檔案（例如要求先登入）。遇到時會顯示「伺服器回傳的是網頁，不是檔案」，不會存下錯誤的內容。
- Google 雲端硬碟的大型檔案需要先在網頁上確認病毒掃描，這類檔案無法直接下載；公開分享的資料夾也還不支援。

---

## 開發者資訊

### 專案結構

| 檔案 | 說明 |
|---|---|
| `downloader.py` | 核心邏輯與指令版 |
| `gui.py` | 視窗版（tkinter），沿用 `downloader.py` 的功能 |
| `build_exe.bat` | 打包成 Windows `.exe` 的腳本 |

### 自己打包 exe

在 Windows 上雙擊 `build_exe.bat`（或在命令列執行），完成後檔案在 `dist\WebFileDownloader.exe`。
腳本會自動建立虛擬環境並安裝 [PyInstaller](https://pyinstaller.org/)。

### 在其他程式中使用

```python
import downloader

links = downloader.get_links("https://example.com/", downloader.DEFAULT_EXTS, timeout=60)
for link in links:
    path, size = downloader.download(link.url, "downloads", 60, name=link.name, referer=link.referer)
    print(path, size)
```

---

## 使用須知

請只下載你有權取得的內容，並遵守網站的使用條款與著作權規定。大量下載前，請留意不要對網站造成過重負擔。

## 授權

本專案以 [MIT License](LICENSE) 授權，可自由使用、修改與散布。

Copyright (c) 2026 rainfunmt
