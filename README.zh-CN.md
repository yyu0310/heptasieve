# HeptaSieve

**隐私优先、AI 安全、把 Heptabase 持续同步成结构化 Markdown 的本地工具。**

由你决定 AI agent 到底能看到哪些卡片，其余一律进不了它的视野。

[English](README.md) · [繁體中文](README.zh-TW.md) · 简体中文 · [日本語](README.ja.md)

> 非官方工具，与 Heptabase 无任何隶属或背书关系。目前仅支持 macOS。

---

## 为什么打造这个工具

一开始的目标很单纯：把 Heptabase 接上 Claude Code，让 AI agent 读我的笔记。

官方路径是 Heptabase 自家的 [CLI](https://github.com/heptameta/heptabase-cli-skills)（在 app 内 Settings、AI Features、CLI 开启），它是 **fail-open**：一旦授权，agent 就能读你整个知识库。第三方工具如 `heptabase-mcp` server 也是同样机制。如果你的知识库每张卡片都能公开，这没问题；但只要你像多数人一样，把机密卡片和想给 AI 用的卡片放在一起，这条路就行不通。

真正的洞察是：隐私墙不在 Heptabase 内部，而在「AI 能读到什么」这个边界上。所以这类工具的价值不是「同步笔记」，而是 **把机密卡片留在 AI 碰不到的地方，只把其余卡片导出成 AI 可读的 Markdown。**

这就是 sieve（筛）：只有你放行的卡片才通过。

## 它做什么

HeptaSieve 直接读你本地的 Heptabase 数据库，把选定的卡片写成 Markdown 文件，放到你指定的位置。`launchd` 每 15 分钟跑一次，让 Markdown 与笔记保持同步。AI agent 永远只读导出的 Markdown 文件夹，不碰数据库。

- **直读 live 本地数据库。** Heptabase 在 2025 年底停止提供本地备份，直读 live DB 因此成为持续本地同步的可靠路径。
- **结构保真转换。** 表格、bullet／todo／toggle 列表、嵌套 section、视频，都是从 Heptabase 的 ProseMirror schema 逆向出来，转成干净 Markdown。
- **任意目的地路由。** 每张白板都能落到自己的文件夹，包含用绝对路径把某张白板直接放进另一个项目。

## fail-closed 隐私模型

一张卡片只有命中以下两个明确白名单之一才会导出，默认什么都不读。

| 来源 | 规则 |
|---|---|
| **`whitelist_whiteboards`** | 你点名的白板。只读每张白板『桌面上』的卡片，不钻子白板。要读子白板就把它的名字也加进来。 |
| **`card_map`** | `标题 -> 精准路径` 覆写层。这些标题一律同步，路径优先。 |
| **`blacklist_whiteboards`** | 这些白板上的卡片会在『读内容之前』先被扣除。黑名单优先于白名单，所以误放在两张白板上的卡片仍会被挡下。 |
| **未点名的子白板** | 卡片移进子白板后 `whiteboard_id` 会变，桌面扫描就扫不到。靠结构排除，不靠你记得设规则。 |

一句话的保证：每个会碰到卡片标题或内容的查询，都被限制在白名单白板 id 或 `card_map` 标题内。非白名单卡片的标题与内容根本不会被读进内存。

由此导出两个设计原则：**结构排除优于减法排除**（查询碰不到的卡片，比读进来再过滤掉更安全），以及 **最好的通知是不需要通知**（系统设计成根本没有「我是不是漏放了那张卡？」这个问题要回答）。

## 与其他方案的对照

| | HeptaSieve | 官方 Heptabase CLI | 其他导出工具 |
|---|---|---|---|
| 隐私模型 | fail-closed 白名单 | fail-open（整个知识库） | 全量导出 |
| 持续本地同步 | 是（`launchd`，15 分钟） | 按需读取 | 一次性导出 |
| 直读 live 本地 DB | 是 | 视情况 | 常需备份文件 |
| 结构保真 Markdown | 表格、列表、section、视频 | 视情况 | 视情况 |
| 各白板独立目的地路由 | 是，含绝对路径 | 否 | 否 |

这不是 Heptabase 的全面替代品；「比官方好」只在三个切面成立：隐私可控、持续本地同步、结构保真。受众刻意很窄：在意 AI 看到什么、重度使用 Heptabase 的 macOS 用户。如果这就是你，这工具正是为你的情境而生。

## 安装

需求：macOS、Python 3.9+、已安装 Heptabase 桌面 app。

```bash
git clone https://github.com/yyu0310/heptasieve.git
cd heptasieve
cp config.example.json config.json
```

接着编辑 `config.json`（每个字段都有 inline 注释说明）：

1. 确认 `db_path` 指向你的本地 `hepta.db`。
2. 设置 `base_output_dir` 与 `board_output_dir` 为你要写出 Markdown 的位置。
3. 在 `whitelist_whiteboards` 列出要导出的白板。
4. 在 `card_map` 加入需要精准路径覆写的标题。

先跑预览（不写入任何文件）：

```bash
python3 heptabase_sync.py --dry
```

计划看起来正确后，正式执行：

```bash
python3 heptabase_sync.py
```

### 每 15 分钟自动同步

```bash
cp com.example.heptasieve.plist ~/Library/LaunchAgents/
# 编辑刚复制的文件：填入绝对路径，并确认你的 python3 路径
launchctl load ~/Library/LaunchAgents/com.example.heptasieve.plist
```

## 搭配 AI agent 使用

HeptaSieve 附带 agent 可读的文档，你可以用对话让 AI coding agent 帮你设置，而不必手动照步骤操作：

- [`AGENTS.md`](AGENTS.md) 与 [`CLAUDE.md`](CLAUDE.md)：agent 该如何理解与设置这个工具。
- [`llms.txt`](llms.txt)：给 LLM 的文档索引。
- [`skills/setup-heptasieve/`](skills/setup-heptasieve/)：一个 Claude Code skill，一句话带你走完整套设置。

让你的 agent 指向导出的 Markdown 文件夹，永远不要指向 `hepta.db`。这个切分正是整个工具的重点。

## 运作原理

架构细节见 [`ARCHITECTURE.md`](ARCHITECTURE.md)：数据流、`build_plan` 里的 fail-closed 顺序、读到哪些数据库表，以及修改程序时必须守住的隐私不变量。

## 限制与诚实披露

- **schema 脆弱。** 这依赖 Heptabase 内部数据库结构，官方改版可能让它失效。它本质上就是非官方工具。
- **直读 live DB 非官方认可。** 实务上运作良好且为只读，但你该知道这不是受支持的集成方式。
- **仅支持 macOS。** 目前的路径与 `launchd` 设置都以 macOS 为前提。

## 授权

[MIT](LICENSE)。
