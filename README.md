# 網頁檔案下載器 Web File Downloader

給一個網址，自動找出網頁上所有的檔案（PDF、Word、ZIP、影音……），勾選後一次下載。

- **免安裝**：Windows 使用者下載 `.exe` 雙擊就能用，不需要安裝 Python
- **支援多種下載方式**：一般連結、「下載」按鈕、沒有副檔名的下載點、雲端分享連結…（見[支援的下載方式](#支援的下載方式)）
- **中文友善**：支援中文網址與中文檔名，包含 Big5 網頁與伺服器指定的中文檔名
- **安全下載**：同名檔案自動加編號、不覆蓋；下載失敗或中途停止，不留下殘缺檔案
- **相容台灣政府網站**：可處理部分政府網站憑證在 Python 3.13 被誤擋的問題（仍會驗證憑證）

## 快速開始（Windows）

1. 到 [Releases 頁面](https://github.com/rainfunmt/web-file-downloader/releases/latest) 下載 **`WebFileDownloader.exe`**
2. 雙擊打開
3. 在「網址」欄貼上網頁網址（`Ctrl + V` 或按右鍵 →「貼上」），按 **搜尋**
4. 勾選要的檔案，按 **下載選取的檔案**
5. 下載完按 **打開資料夾** 查看檔案

檔案預設存到 `下載\網頁檔案下載器`，可以按「選擇資料夾…」更改。

找不到想要的檔案時，勾選 **也搜尋下一層頁面** 再搜尋一次（例如「書表下載專區」這類要再點進子頁面的網站）。

> **第一次打開出現「Windows 已保護您的電腦」？**
> 這是因為程式沒有付費購買數位簽章，不代表有病毒。按 **其他資訊** → **仍要執行** 即可。
> 如果不放心，可以直接閱讀本專案的原始碼，或改用下面的 Python 版本。

## 用 Python 執行

需要 Python 3.8 以上（Windows / macOS / Linux 皆可），只用標準函式庫，不需要 `pip install`。

```bash
git clone https://github.com/rainfunmt/web-file-downloader.git
cd web-file-downloader
```

### 視窗版

```bash
python gui.py
```

### 指令版

最簡單的用法：執行後貼上網址。

```bash
python downloader.py
```

或直接把網址寫在指令後面：

```bash
python downloader.py https://example.com/resources
```

檔案預設會存到目前資料夾下的 `downloads/`。

| 參數 | 說明 |
|---|---|
| `url` | 網頁網址；也可以直接是檔案網址。省略時會詢問 |
| `-o`, `--output 資料夾` | 存放資料夾（預設 `downloads`） |
| `-e`, `--ext pdf,zip` | 只下載指定副檔名，逗號分隔 |
| `--images` | 連網頁上的圖片也一起下載 |
| `-d`, `--deep` | 也搜尋看起來像「下載」的下一層頁面（最多 30 頁，較慢） |
| `--include-risky` | 也下載執行檔與含巨集的檔案（預設略過，見[安全須知](#安全須知)） |
| `-l`, `--list` | 只列出找到的檔案，不下載 |
| `-t`, `--timeout 秒數` | 連線逾時秒數（預設 60） |
| `-V`, `--version` | 顯示版本 |
| `-h`, `--help` | 顯示說明 |

```bash
# 先看看網頁上有哪些檔案
python downloader.py https://example.com/resources --list

# 只下載 PDF，存到 docs 資料夾
python downloader.py https://example.com/resources -e pdf -o docs

# 直接下載單一檔案
python downloader.py https://example.com/files/report.pdf
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
    失敗: HTTP Error 404: Not Found

完成！成功 2 / 3 個，存在 C:\...\downloads
```

結束代碼：`0` 全部成功（或沒有找到檔案）、`1` 有檔案失敗或無法讀取網頁、`2` 沒有輸入網址、`130` 按 Ctrl+C 取消。

## 預設會找的檔案類型

| 類別 | 副檔名 |
|---|---|
| 文件 | pdf, doc, docx, xls, xlsx, ppt, pptx, odt, ods, odp, txt, csv, json, xml, md, rtf |
| 壓縮檔 | zip, rar, 7z, tar, gz, bz2, xz |
| 音訊 | mp3, wav, flac, m4a, ogg |
| 影片 | mp4, mkv, avi, mov, webm |
| 安裝檔 | exe, msi, apk, dmg, iso |
| 圖片（勾「也找圖片檔」或加 `--images`） | jpg, jpeg, png, gif, webp, svg, bmp, ico |

## 支援的下載方式

| # | 網站常見的下載方式 | 例子 | 支援 |
|---|---|---|---|
| 1 | 一般檔案連結 | `<a href="report.pdf">` | ✔ |
| 2 | 媒體與嵌入標籤 | `<img>`、`<video>`、`<audio>`、`<source>`、`<embed>`、`<iframe src="x.pdf">`、`<object>` | ✔ |
| 3 | HTML5 `download` 屬性 | `<a href="/get?id=1" download="報告.pdf">` | ✔ 使用指定的檔名 |
| 4 | 沒有副檔名的下載點 | `/Files/6010`、`download.php?id=5`、`GetFile.ashx?id=3` | ✔ 向伺服器詢問檔名與類型 |
| 5 | JavaScript 按鈕 | `onclick="window.open('/a.pdf')"`、`data-url="/a.pdf"` | ✔ |
| 6 | 網頁內嵌資料 | React / Next.js 等網站藏在 `<script>` 或 JSON 裡的檔案網址 | ✔ |
| 7 | 雲端分享連結 | Google 雲端硬碟、Google 文件／試算表／簡報（匯出成 docx / xlsx / pptx）、Dropbox | ✔ 大型檔案需確認病毒掃描的不支援 |
| 8 | 下一層頁面 | 列表頁 →「書表下載」子頁面 → 附件 | ✔ 勾「也搜尋下一層頁面」或加 `--deep` |
| 9 | 轉址 | HTTP 302 轉址、`<meta http-equiv="refresh">` | ✔ |
| 10 | 防盜連 | 檢查 Referer、Cookie、User-Agent | ✔ 自動帶上 |
| 11 | 表單送出下載 | `<form method="post">`、ASP.NET `__doPostBack` | ✘ |
| 12 | 載入後才由 JavaScript 取得 | 按「載入更多」、無限捲動、需要先點選分頁 | ✘ 需要真的瀏覽器 |
| 13 | 需要登入或驗證碼 | 會員專區、圖形驗證碼 | ✘ |
| 14 | 防機器人保護 | Cloudflare「Just a moment...」檢查頁 | ✘ 會清楚提示，請改用瀏覽器手動下載 |

第 4、7 類連結沒有副檔名，程式會先向伺服器詢問（只看回應標頭，不下載內容），確認是檔案才列出來。

## 限制

- 第 11～14 類的下載方式不支援（見上表）。網站用防機器人保護擋下程式，代表網站不希望被自動下載，本程式不會嘗試繞過。
- `--deep` 只會打開同一個網站上、看起來像「下載」的頁面，最多 30 頁，不會無限往下爬。
- 少數網站會把網頁假裝成檔案（例如要求先登入）；遇到時該檔案會顯示「伺服器回傳的是網頁，不是檔案」，不會存下錯誤的內容。

## 自己打包 .exe

在 Windows 上雙擊 `build_exe.bat`（或在命令列執行它），完成後檔案在 `dist\WebFileDownloader.exe`。
腳本會自動建立虛擬環境並安裝 [PyInstaller](https://pyinstaller.org/)。

## 專案結構

| 檔案 | 說明 |
|---|---|
| `downloader.py` | 核心邏輯與指令版 |
| `gui.py` | 視窗版（tkinter），沿用 `downloader.py` 的功能 |
| `build_exe.bat` | 打包成 Windows `.exe` 的腳本 |

## 安全須知

從網路下載的檔案可能含有病毒。本程式做了以下保護，但最重要的還是**只下載你信任的網站的檔案**：

- **標記為「來自網路」**：下載的檔案會像用瀏覽器下載一樣被 Windows 標記，Word / Excel 會用「受保護的檢視」開啟，執行檔會出現 SmartScreen 警告。請不要隨意關閉這些保護。（僅限 Windows；FAT32 隨身碟等不支援標記的磁碟會略過）
- **高風險檔案預設不下載**：執行檔、安裝檔、含巨集的 Office 檔（exe、msi、apk、dmg、iso、bat、js、docm、xlsm、pptm…）會標示 ⚠。
  - 視窗版：預設不勾選；勾選後下載前會再提醒一次。
  - 指令版：預設略過；確定需要時加上 `--include-risky`，或用 `-e exe` 明確指定類型。
- **壓縮檔要小心**：zip、rar 裡可能藏有執行檔，解壓縮後一樣要留意。
- **保持防毒軟體開啟**：Windows Defender 等防毒軟體會即時掃描新下載的檔案。

## 使用須知

請只下載你有權取得的內容，並遵守網站的使用條款與著作權規定。大量下載前，請留意不要對網站造成過重負擔。

## 授權

本專案以 [MIT License](LICENSE) 授權，可自由使用、修改與散布。
