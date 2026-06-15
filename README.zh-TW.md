# Heptabase Local Sync Security

**隱私優先、AI 安全、把 Heptabase 持續同步成結構化 Markdown 的本地工具。**

由你決定 AI agent 到底看得到哪些卡片，其餘一律進不了它的視野。

[English](README.md) · 繁體中文 · [简体中文](README.zh-CN.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Tiếng Việt](README.vi.md) · [Español](README.es.md) · [Français](README.fr.md) · [Deutsch](README.de.md) · [العربية](README.ar.md) · [עברית](README.he.md) · [Русский](README.ru.md) · [Українська](README.uk.md)

> 非官方工具，與 Heptabase 無任何隸屬或背書關係。目前僅支援 macOS。

---

## 為什麼打造這個工具

一開始的目標很單純：把 Heptabase 接上 Claude Code，讓 AI agent 讀我的筆記。

官方路徑是 Heptabase 自家的 [CLI](https://github.com/heptameta/heptabase-cli-skills) 採 **fail-open** 機制，一旦授權，agent 就能讀你整個知識庫，第三方工具如 `heptabase-mcp` server 也是同樣機制。如果你的知識庫每張卡片都能公開就沒問題，但只要你像多數人一樣，把機密卡片和想給 AI 用的卡片放在一起，這就不可行。

問題的核心在於，隱私牆必須立在「AI 讀得到什麼」這條邊界上，而這條邊界落在 Heptabase 之外，在你怎麼把筆記餵給 AI 的那一層。所以這類工具真正要做的，是**把機密卡片留在 AI 碰不到的地方，只把其餘卡片匯出成 AI 可讀的 Markdown**。同步筆記只是簡單的那一半。

## 命名由來

名字拆成三段，各說一件事，`heptabase` 是資料來源，`local-sync` 說明它的機制，`security` 說明它的角色。

Security 同時帶著兩層含義。第一層是安全：工具守在 AI 和你的知識庫之間，用 fail-closed 機制決定哪些卡片能進 AI 的視野、哪些一律擋在外面，不用擔心資料外洩。第二層更像一個盡責的秘書：主動在背景把筆記整理好，按你設定的位置每 15 分鐘自動同步，讓你打開 AI 工具就直接有內容可用，不必再手動管這件事。

## 它做什麼

Heptabase Local Sync Security 中本地運作的 Python 程式直接讀你本地的 Heptabase 資料庫，把選定的卡片寫成 Markdown 檔，並放到你指定的位置。
`launchd` 每 15 分鐘跑一次，讓 Markdown 與筆記保持同步。AI agent 永遠只讀匯出的 Markdown 資料夾，不碰資料庫。

- **直讀 live 本地資料庫。** Heptabase 在 2025 年底停止提供[自動本地備份](https://support.heptabase.com/en/articles/11064116-how-does-auto-backup-work-in-heptabase)，直讀 live DB 因此成為持續本地同步的可靠路徑。
- **結構保真轉換。** 表格、bullet／todo／toggle 清單、巢狀 section、影片，都是從 Heptabase 的 ProseMirror schema 逆向出來，轉成乾淨 Markdown。
- **任意目的地路由。** 每張白板都能落到自己的資料夾，包含用絕對路徑把某張白板直接放進另一個專案，可以透過 AI Agent 協作，決定 python 要指向你本地的哪個位置。

## fail-closed 隱私模型

一張卡片只有命中以下兩個明確白名單之一才會匯出，預設什麼都不讀。

| 來源 | 規則 |
|---|---|
| **`whitelist_whiteboards`** | 你點名的白板。只讀每張白板『桌面上』的卡片，不鑽子白板。要讀子白板就把它的名字也加進來。 |
| **`card_map`** | `標題 -> 精準路徑` 覆寫層。這些標題一律同步，路徑優先。 |
| **`blacklist_whiteboards`** | 這些白板上的卡片會在『讀內容之前』先被扣除。黑名單優先於白名單，所以誤放在兩張白板上的卡片仍會被擋下。 |
| **未點名的子白板** | 卡片移進子白板後 `whiteboard_id` 會變，桌面掃描就掃不到。靠結構排除，不靠你記得設規則。 |

更重要的是，每個會碰到卡片標題或內容的查詢，都被限制在白名單白板 id 或 `card_map` 標題內。非白名單卡片的標題與內容根本不會被讀進記憶體。

由此導出兩個設計原則。**結構排除優於減法排除**，查詢碰不到的卡片比讀進來再過濾掉更安全。工具設計讓你從頭到尾不必擔心某張卡有沒有外洩，靠結構保證，不靠你事後去檢查。

## 與其他方案的對照

| | Heptabase Local Sync Security | 官方 Heptabase CLI | 其他匯出工具 |
|---|---|---|---|
| 隱私模型 | fail-closed 白名單 | fail-open（整個知識庫） | 全量匯出 |
| 持續本地同步 | 是（`launchd`，15 分鐘） | 依需求讀取 | 一次性匯出 |
| 直讀 live 本地 DB | 是 | 視情況 | 常需備份檔 |
| 結構保真 Markdown | 表格、清單、section、影片 | 視情況 | 視情況 |
| 各白板獨立目的地路由 | 是，含絕對路徑 | 否 | 否 |

這不是 Heptabase 的全面替代品。「比官方好」只在三個切面成立：隱私可控、持續本地同步、結構保真。受眾刻意很窄：在意 AI 看到什麼、重度使用 Heptabase 的 macOS 使用者。如果這就是你，這工具正是為你的情境而生。

## 安裝

需求：macOS、Python 3.9+、已安裝 Heptabase 桌面 app。

```bash
git clone https://github.com/yyu0310/heptabase-local-sync-security.git
cd heptabase-local-sync-security
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

這個工具附帶 agent 可讀的文件，你可以用對話讓 AI coding agent 幫你設定，而不必手動照步驟操作：

- [`AGENTS.md`](AGENTS.md) 與 [`CLAUDE.md`](CLAUDE.md) 告訴 agent 如何理解與設定這個工具。
- [`llms.txt`](llms.txt) 是給 LLM 的文件索引。
- [`skills/setup-heptasieve/`](skills/setup-heptasieve/) 是一個 Claude Code skill，一句話帶你走完整套設定。

讓你的 agent 指向匯出的 Markdown 資料夾，永遠不要指向 `hepta.db`。這個切分正是整個工具的重點。

### 情境一：Claude Code 專案助理

你在開發一套量化交易工具，Heptabase 裡有三張白板：`交易策略研究`、`系統設計筆記`、`個人財務記錄`。你只把前兩張加進 `whitelist_whiteboards`，工具每 15 分鐘把它們同步到 `/projects/trading/heptabase-export/`。接著在專案的 CLAUDE.md 裡加上這個資料夾路徑，讓 Claude Code 把它當作背景知識讀取。財務記錄那張白板從頭到尾不在白名單，Claude Code 連標題都碰不到。

### 情境二：跨工具的個人記憶層

不同 AI 工具之間沒有共同記憶，每次換工具都要從頭說明背景。把常用的參考筆記、工作脈絡、研究摘要同步成 Markdown，任何支援讀取本地資料夾的 AI 工具都能直接取用，幾秒內上手。哪些白板進白名單、哪些永遠不進，靠設定決定，不靠信任 AI 工具的判斷。

## 運作原理

架構細節見 [`ARCHITECTURE.md`](ARCHITECTURE.md)，包含資料流、`build_plan` 裡的 fail-closed 順序、讀到哪些資料庫表，以及修改程式時必須守住的隱私不變量。

## 限制與揭露

- **schema 脆弱。** 這依賴 Heptabase 內部資料庫結構，官方改版可能讓它失效。它本質上就是非官方工具。
- **直讀 live DB 非官方認可。** 實務上運作良好且為唯讀，但你該知道這不是受支援的整合方式。
- **僅支援 macOS。** 目前的路徑與 `launchd` 設定都以 macOS 為前提。

## 授權

[MIT](LICENSE)。
