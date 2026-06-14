# HeptaSieve

**隱私優先、AI 安全、把 Heptabase 持續同步成結構化 Markdown 的本地工具。**

由你決定 AI agent 到底看得到哪些卡片，其餘一律進不了它的視野。

[English](README.md) · 繁體中文 · [简体中文](README.zh-CN.md) · [日本語](README.ja.md)

> 非官方工具，與 Heptabase 無任何隸屬或背書關係。目前僅支援 macOS。

---

## 為什麼打造這個工具

一開始的目標很單純：把 Heptabase 接上 Claude Code，讓 AI agent 讀我的筆記。

官方路徑（Heptabase MCP server 與社群 CLI）都是 **fail-open**：一旦授權，agent 就能讀你整個知識庫。如果你的知識庫每張卡片都能公開，這沒問題；但只要你像多數人一樣，把機密卡片和想給 AI 用的卡片放在一起，這條路就行不通。

真正的洞察是：隱私牆不在 Heptabase 內部，而在「AI 讀得到什麼」這個邊界上。所以這類工具的價值不是「同步筆記」，而是 **把機密卡片留在 AI 碰不到的地方，只把其餘卡片匯出成 AI 可讀的 Markdown。**

這就是 sieve（篩）：只有你放行的卡片才通過。

## 它做什麼

HeptaSieve 直接讀你本地的 Heptabase 資料庫，把選定的卡片寫成 Markdown 檔，放到你指定的位置。`launchd` 每 15 分鐘跑一次，讓 Markdown 與筆記保持同步。AI agent 永遠只讀匯出的 Markdown 資料夾，不碰資料庫。

- **直讀 live 本地資料庫。** Heptabase 在 2025 年底停止提供本地備份，直讀 live DB 因此成為持續本地同步的可靠路徑。
- **結構保真轉換。** 表格、bullet／todo／toggle 清單、巢狀 section、影片，都是從 Heptabase 的 ProseMirror schema 逆向出來，轉成乾淨 Markdown。
- **任意目的地路由。** 每張白板都能落到自己的資料夾，包含用絕對路徑把某張白板直接放進另一個專案。

## fail-closed 隱私模型

一張卡片只有命中以下兩個明確白名單之一才會匯出，預設什麼都不讀。

| 來源 | 規則 |
|---|---|
| **`whitelist_whiteboards`** | 你點名的白板。只讀每張白板『桌面上』的卡片，不鑽子白板。要讀子白板就把它的名字也加進來。 |
| **`card_map`** | `標題 -> 精準路徑` 覆寫層。這些標題一律同步，路徑優先。 |
| **`blacklist_whiteboards`** | 這些白板上的卡片會在『讀內容之前』先被扣除。黑名單優先於白名單，所以誤放在兩張白板上的卡片仍會被擋下。 |
| **未點名的子白板** | 卡片移進子白板後 `whiteboard_id` 會變，桌面掃描就掃不到。靠結構排除，不靠你記得設規則。 |

一句話的保證：每個會碰到卡片標題或內容的查詢，都被限制在白名單白板 id 或 `card_map` 標題內。非白名單卡片的標題與內容根本不會被讀進記憶體。

由此導出兩個設計原則：**結構排除優於減法排除**（查詢碰不到的卡片，比讀進來再過濾掉更安全），以及 **最好的通知是不需要通知**（系統設計成根本沒有「我是不是漏放了那張卡？」這個問題要回答）。

## 與其他方案的對照

| | HeptaSieve | 官方 Heptabase MCP / CLI | 其他匯出工具 |
|---|---|---|---|
| 隱私模型 | fail-closed 白名單 | fail-open（整個知識庫） | 全量匯出 |
| 持續本地同步 | 是（`launchd`，15 分鐘） | 依需求讀取 | 一次性匯出 |
| 直讀 live 本地 DB | 是 | 視情況 | 常需備份檔 |
| 結構保真 Markdown | 表格、清單、section、影片 | 視情況 | 視情況 |
| 各白板獨立目的地路由 | 是，含絕對路徑 | 否 | 否 |

這不是 Heptabase 的全面替代品；「比官方好」只在三個切面成立：隱私可控、持續本地同步、結構保真。受眾刻意很窄：在意 AI 看到什麼、重度使用 Heptabase 的 macOS 使用者。如果這就是你，這工具正是為你的情境而生。

## 安裝

需求：macOS、Python 3.9+、已安裝 Heptabase 桌面 app。

```bash
git clone https://github.com/yyu0310/heptasieve.git
cd heptasieve
cp config.example.json config.json
```

接著編輯 `config.json`（每個欄位都有 inline 註解說明）：

1. 確認 `db_path` 指向你的本地 `hepta.db`。
2. 設定 `base_output_dir` 與 `board_output_dir` 為你要寫出 Markdown 的位置。
3. 在 `whitelist_whiteboards` 列出要匯出的白板。
4. 在 `card_map` 加入需要精準路徑覆寫的標題。

先跑預覽（不寫入任何檔案）：

```bash
python3 heptabase_sync.py --dry
```

計畫看起來正確後，正式執行：

```bash
python3 heptabase_sync.py
```

### 每 15 分鐘自動同步

```bash
cp com.example.heptasieve.plist ~/Library/LaunchAgents/
# 編輯剛複製的檔案：填入絕對路徑，並確認你的 python3 路徑
launchctl load ~/Library/LaunchAgents/com.example.heptasieve.plist
```

## 搭配 AI agent 使用

HeptaSieve 附帶 agent 可讀的文件，你可以用對話讓 AI coding agent 幫你設定，而不必手動照步驟操作：

- [`AGENTS.md`](AGENTS.md) 與 [`CLAUDE.md`](CLAUDE.md)：agent 該如何理解與設定這個工具。
- [`llms.txt`](llms.txt)：給 LLM 的文件索引。
- [`skills/setup-heptasieve/`](skills/setup-heptasieve/)：一個 Claude Code skill，一句話帶你走完整套設定。

讓你的 agent 指向匯出的 Markdown 資料夾，永遠不要指向 `hepta.db`。這個切分正是整個工具的重點。

## 運作原理

架構細節見 [`ARCHITECTURE.md`](ARCHITECTURE.md)：資料流、`build_plan` 裡的 fail-closed 順序、讀到哪些資料庫表，以及修改程式時必須守住的隱私不變量。

## 限制與誠實揭露

- **schema 脆弱。** 這依賴 Heptabase 內部資料庫結構，官方改版可能讓它失效。它本質上就是非官方工具。
- **直讀 live DB 非官方認可。** 實務上運作良好且為唯讀，但你該知道這不是受支援的整合方式。
- **僅支援 macOS。** 目前的路徑與 `launchd` 設定都以 macOS 為前提。

## 授權

[MIT](LICENSE)。
