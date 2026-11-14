# Minecraft 生存指南 LLM Wiki × 教學 HTML 簡報

**直接用瀏覽器打開 `site/index.html` 即可瀏覽**（不需要網路、不需要安裝任何東西）。

## 繳交內容對照
| 作業要求 | 在哪裡 |
|---|---|
| 1. LLM Wiki 主題與簡短介紹 | `site/process.html` 第 1 節 |
| 2. LLM Wiki 連結或成果 | `site/index.html`（17 篇指南、29 種生物、53 種物品，每個條目一個 HTML 頁，在 `site/wiki/`） |
| 3. 教學 HTML 簡報連結 | `site/slides.html`（43 頁，← → 翻頁，1–5 跳章節） |
| 4. loop / graph 流程圖與說明 | `site/process.html` 第 4 節 |
| 5. 一次實際執行的結果／檢查紀錄 | `site/process.html` 第 5 節；原始紀錄在 `runs/run_001.json`～`run_010.json` |
| 6. 反思 | `site/process.html` 第 6 節 |

## 資料夾
- `site/`：成果網站（Wiki＋簡報＋流程頁）
- `src/`：Wiki 資料（`data_*.py`）與建置流程（`build.py` = 前置檢查 → 生成 → 後置檢查）
- `runs/`：每次執行 build.py 自動留下的檢查紀錄

## 重新建置
```
python3 src/build.py site "這次改了什麼"
```
需要 Python 3（不需額外套件）。前置檢查有 error 時會停止且不產生頁面。

字型：俐方體 11 號（Cubic 11，免費授權，見 `site/assets/FONT_LICENSE.txt`）。鼠標、圖示、材質皆為原創像素圖。
