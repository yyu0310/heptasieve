# HeptaSieve

**Ưu tiên quyền riêng tư, an toàn với AI. Công cụ đồng bộ liên tục Heptabase sang Markdown có cấu trúc, chạy hoàn toàn trên máy tính của bạn.**

Bạn quyết định chính xác những thẻ nào AI agent được phép xem. Tất cả những thẻ còn lại đều nằm ngoài tầm với của nó.

[English](README.md) · [繁體中文](README.zh-TW.md) · [简体中文](README.zh-CN.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · Tiếng Việt · [Español](README.es.md) · [Français](README.fr.md) · [Deutsch](README.de.md) · [العربية](README.ar.md) · [עברית](README.he.md) · [Русский](README.ru.md) · [Українська](README.uk.md)

> Công cụ không chính thức. Không có liên kết hay chứng thực từ Heptabase. Hiện chỉ hỗ trợ macOS.

---

## Lý do ra đời

Tất cả bắt đầu từ một mục tiêu đơn giản: kết nối Heptabase với Claude Code để AI agent có thể đọc ghi chú của tôi.

Con đường chính thức là [CLI](https://github.com/heptameta/heptabase-cli-skills) của chính Heptabase, được bật trong ứng dụng tại Settings, AI Features, CLI. Đây là cơ chế **fail-open**: một khi bạn cấp quyền, agent có thể đọc toàn bộ cơ sở kiến thức. Các công cụ bên thứ ba như `heptabase-mcp` server cũng hoạt động theo cách tương tự. Nếu mọi thẻ trong kho kiến thức của bạn đều có thể chia sẻ, không thành vấn đề. Nhưng nếu bạn để thẻ bí mật cạnh những thẻ muốn dùng với AI, cơ chế này không phù hợp, và đó là trường hợp của hầu hết mọi người.

Điều then chốt: bức tường bảo mật phải đặt tại ranh giới "AI có thể đọc gì". Ranh giới đó nằm bên ngoài Heptabase, ở cách bạn đưa ghi chú cho agent. Vì thế, việc thực sự cần làm của một công cụ như thế này là **giữ các thẻ bí mật ở nơi AI không với tới được, và chỉ xuất những thẻ còn lại thành Markdown mà AI có thể đọc.** Đồng bộ ghi chú chỉ là nửa phần dễ.

Đó là cái sieve (rây). Chỉ những thẻ bạn cho phép mới đi qua.

## Tính năng

HeptaSieve đọc trực tiếp cơ sở dữ liệu Heptabase cục bộ của bạn và ghi các thẻ đã chọn dưới dạng file Markdown tại vị trí bạn chỉ định. `launchd` chạy nó 15 phút một lần để Markdown luôn đồng bộ với ghi chú. AI agent chỉ đọc thư mục Markdown đã xuất, không bao giờ chạm vào cơ sở dữ liệu.

- **Đọc trực tiếp cơ sở dữ liệu cục bộ đang hoạt động.** Heptabase ngừng cung cấp [bản sao lưu cục bộ tự động](https://support.heptabase.com/en/articles/11064116-how-does-auto-backup-work-in-heptabase) vào cuối năm 2025, nên đọc trực tiếp DB đang chạy là con đường đáng tin cậy để đồng bộ liên tục.
- **Chuyển đổi trung thực với cấu trúc.** Bảng, danh sách bullet / todo / toggle, các section lồng nhau và video được phân tích ngược từ schema ProseMirror của Heptabase và xuất ra Markdown sạch.
- **Định tuyến đến bất kỳ đích nào.** Mỗi whiteboard có thể lưu vào thư mục riêng, kể cả dùng đường dẫn tuyệt đối để đặt một board thẳng vào dự án khác.

## Mô hình bảo mật fail-closed

Một thẻ chỉ được xuất khi khớp với một trong hai danh sách cho phép tường minh. Mặc định không đọc gì cả.

| Nguồn | Quy tắc |
|---|---|
| **`whitelist_whiteboards`** | Các whiteboard bạn đặt tên. Chỉ đọc thẻ trên *bề mặt* của mỗi board. Sub-whiteboard không được theo dõi. Muốn bao gồm sub-whiteboard nào, thêm tên nó vào. |
| **`card_map`** | Lớp `tiêu đề -> đường dẫn chính xác`. Các tiêu đề này luôn được đồng bộ, và đường dẫn của chúng có độ ưu tiên cao hơn. |
| **`blacklist_whiteboards`** | Thẻ trên các board này bị loại trừ *trước khi* đọc nội dung. Blacklist thắng whitelist, nên thẻ đặt nhầm trên cả hai board vẫn bị chặn. |
| **Sub-whiteboard (chưa đặt tên)** | Chuyển thẻ vào sub-whiteboard sẽ thay đổi `whiteboard_id`, khiến quét bề mặt không thấy được. Bị loại bởi cấu trúc, không cần bạn nhớ cài quy tắc. |

Đảm bảo trong một câu: mọi truy vấn chạm đến tiêu đề hoặc nội dung thẻ đều bị giới hạn trong whiteboard id thuộc whitelist hoặc tiêu đề `card_map`. Tiêu đề và nội dung của thẻ không thuộc whitelist không bao giờ được đọc vào bộ nhớ.

Từ đây rút ra hai nguyên tắc thiết kế. **Loại trừ theo cấu trúc tốt hơn loại trừ theo phép trừ**: thẻ mà truy vấn không với tới an toàn hơn thẻ bị lọc sau khi đọc. **Thông báo tốt nhất là thông báo không cần thiết**: công cụ được xây dựng để bạn không bao giờ phải lo liệu một thẻ có bị rò rỉ không.

## So sánh

| | HeptaSieve | CLI Heptabase chính thức | Công cụ xuất khác |
|---|---|---|---|
| Mô hình bảo mật | Danh sách cho phép fail-closed | Fail-open (toàn bộ cơ sở kiến thức) | Xuất toàn bộ |
| Đồng bộ cục bộ liên tục | Có (`launchd`, 15 phút) | Đọc theo yêu cầu | Xuất một lần |
| Đọc DB cục bộ đang hoạt động | Có | Tùy trường hợp | Thường cần file backup |
| Markdown trung thực với cấu trúc | Bảng, danh sách, section, video | Tùy trường hợp | Tùy trường hợp |
| Định tuyến đích riêng theo board | Có, bao gồm đường dẫn tuyệt đối | Không | Không |

Đây không phải bản thay thế hoàn toàn cho Heptabase, và "tốt hơn chính thức" chỉ đúng ở ba điểm: quyền riêng tư có thể kiểm soát, đồng bộ cục bộ liên tục, và trung thực với cấu trúc. Đối tượng hướng đến có chủ đích hẹp: người dùng macOS sống trong Heptabase và quan tâm đến những gì AI có thể thấy. Nếu đó là bạn, công cụ này được tạo ra chính xác cho trường hợp của bạn.

## Cài đặt

Yêu cầu: macOS, Python 3.9+, đã cài ứng dụng desktop Heptabase.

```bash
git clone https://github.com/yyu0310/heptasieve.git
cd heptasieve
cp config.example.json config.json
```

Sau đó chỉnh sửa `config.json` (mỗi trường đều có chú thích inline giải thích):

1. Xác nhận `db_path` trỏ vào `hepta.db` cục bộ của bạn.
2. Đặt `base_output_dir` và `board_output_dir` là nơi bạn muốn ghi Markdown.
3. Liệt kê các whiteboard muốn xuất trong `whitelist_whiteboards`.
4. Thêm các tiêu đề cần ghi đè đường dẫn chính xác vào `card_map`.

Chạy thử trước, không ghi gì cả:

```bash
python3 heptabase_sync.py --dry
```

Khi kế hoạch có vẻ đúng, chạy thật:

```bash
python3 heptabase_sync.py
```

### Tự động đồng bộ mỗi 15 phút

```bash
cp com.example.heptasieve.plist ~/Library/LaunchAgents/
# chỉnh sửa file vừa sao chép: đặt đường dẫn tuyệt đối và xác nhận đường dẫn python3
launchctl load ~/Library/LaunchAgents/com.example.heptasieve.plist
```

## Dùng với AI agent

HeptaSieve đi kèm tài liệu mà agent có thể đọc để bạn thiết lập bằng cách trò chuyện với AI coding agent thay vì làm theo từng bước thủ công:

- [`AGENTS.md`](AGENTS.md) và [`CLAUDE.md`](CLAUDE.md): cách agent nên hiểu và cấu hình công cụ này.
- [`llms.txt`](llms.txt): chỉ mục tài liệu cho LLM.
- [`skills/setup-heptasieve/`](skills/setup-heptasieve/): một Claude Code skill hướng dẫn toàn bộ thiết lập chỉ trong một yêu cầu.

Hướng agent của bạn vào thư mục Markdown đã xuất, đừng bao giờ hướng vào `hepta.db`. Sự phân tách đó là toàn bộ điểm mấu chốt.

## Cách hoạt động

Xem [`ARCHITECTURE.md`](ARCHITECTURE.md) để biết chi tiết kiến trúc: luồng dữ liệu, thứ tự fail-closed bên trong `build_plan`, các bảng cơ sở dữ liệu mà nó đọc, và các bất biến bảo mật cần giữ khi sửa đổi code.

## Hạn chế và lưu ý thẳng thắn

- **Schema dễ vỡ.** Phụ thuộc vào cấu trúc cơ sở dữ liệu nội bộ của Heptabase. Bản cập nhật Heptabase có thể làm hỏng nó. Về bản chất đây là công cụ không chính thức.
- **Đọc DB đang hoạt động không được phê duyệt chính thức.** Trong thực tế nó hoạt động tốt và chỉ đọc, nhưng bạn cần biết đây không phải là tích hợp được hỗ trợ.
- **Chỉ macOS.** Đường dẫn và cấu hình `launchd` hiện tại giả định macOS.

## Giấy phép

[MIT](LICENSE).
