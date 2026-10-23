# 網頁檔案下載器 Web File Downloader

給一個網址，自動找出網頁上所有的檔案連結（PDF、Word、ZIP、影音……）並一次下載。

- **免安裝套件**：只用 Python 標準函式庫，一個檔案就能執行
- **中文友善**：支援中文網址與中文檔名
- **安全下載**：同名檔案自動加編號、不覆蓋；下載失敗不留下殘缺檔案
- **抓得到「下載」按鈕**：除了一般連結，也會從網頁內嵌的資料中找出按鈕背後的檔案網址
- **相容台灣政府網站**：可處理部分政府網站憑證在 Python 3.13 被誤擋的問題（仍會驗證憑證）

## 需求

- Python 3.8 以上（Windows / macOS / Linux 皆可）

## 安裝

下載 `downloader.py` 即可，不需要 `pip install`。

```bash
git clone https://github.com/rainfunmt/web-file-downloader.git
cd web-file-downloader
```

## 使用方式

最簡單的用法：執行後貼上網址。

```bash
python downloader.py
```

或直接把網址寫在指令後面：

```bash
python downloader.py https://example.com/resources
```

檔案預設會存到目前資料夾下的 `downloads/`。

### 參數

| 參數 | 說明 |
|---|---|
| `url` | 網頁網址；也可以直接是檔案網址。省略時會詢問 |
| `-o`, `--output 資料夾` | 存放資料夾（預設 `downloads`） |
| `-e`, `--ext pdf,zip` | 只下載指定副檔名，逗號分隔 |
| `--images` | 連網頁上的圖片也一起下載 |
| `-l`, `--list` | 只列出找到的檔案，不下載 |
| `-t`, `--timeout 秒數` | 連線逾時秒數（預設 60） |
| `-V`, `--version` | 顯示版本 |
| `-h`, `--help` | 顯示說明 |

### 範例

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
找到 3 個檔案:

[1/3] https://example.com/files/指南.pdf
    完成  5,115 KB -> downloads\指南.pdf
[2/3] https://example.com/files/data.zip
    完成  1,024 KB -> downloads\data.zip
[3/3] https://example.com/files/missing.docx
    失敗: HTTP Error 404: Not Found

完成！成功 2 / 3 個，存在 C:\...\downloads
```

### 預設會下載的檔案類型

| 類別 | 副檔名 |
|---|---|
| 文件 | pdf, doc, docx, xls, xlsx, ppt, pptx, odt, ods, odp, txt, csv, json, xml, md, rtf |
| 壓縮檔 | zip, rar, 7z, tar, gz, bz2, xz |
| 音訊 | mp3, wav, flac, m4a, ogg |
| 影片 | mp4, mkv, avi, mov, webm |
| 安裝檔 | exe, msi, apk, dmg, iso |
| 圖片（需加 `--images`） | jpg, jpeg, png, gif, webp, svg, bmp, ico |

### 結束代碼

| 代碼 | 意義 |
|---|---|
| `0` | 全部成功（或沒有找到檔案） |
| `1` | 有檔案下載失敗，或無法讀取網頁 |
| `2` | 沒有輸入網址 |
| `130` | 使用者按 Ctrl+C 取消 |

## 限制

- 只會讀取網頁第一次載入時的內容（含內嵌資料）；之後才由 JavaScript 向伺服器另外要的連結（例如按「載入更多」）抓不到。
- 不支援需要登入才能看到的網頁。
- 只抓單一頁面，不會自動往下爬其他頁面。
- 以網址的副檔名判斷是不是檔案；沒有副檔名的下載連結（例如 `download?id=123`）不會被抓到。

## 使用須知

請只下載你有權取得的內容，並遵守網站的使用條款與著作權規定。大量下載前，請留意不要對網站造成過重負擔。

## 授權

本專案以 [MIT License](LICENSE) 授權，可自由使用、修改與散布。
