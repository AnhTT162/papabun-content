---
name: write-topic
description: Soạn một bài học (topic) mới hoặc viết lại bài cũ cho app PapaBun trong repo papabun-content, đúng định dạng, đúng kỹ thuật, rồi kiểm tra và review. Dùng khi người dùng muốn thêm bài, viết nội dung cho một chủ đề Java/Spring/Database/System Design/Solution Architect..., hoặc nhắc tới papabun-content.
---

# Soạn bài học PapaBun

Người học: Java engineer nhiều năm kinh nghiệm muốn vá lỗ hổng kiến thức, ôn phỏng vấn và lên Solution Architect.
Viết cho người đã đi làm: không giải thích vòng vo, nhưng **không bỏ qua kiến thức cơ bản** và **mọi thuật ngữ tiếng Anh đều có giải thích**.

## 0. Chuẩn bị
1. Làm việc trong bản clone của `AnhTT162/papabun-content`. Nếu chưa ở đó, hỏi người dùng đường dẫn hoặc clone về.
2. Đọc `docs/CURRICULUM.md` (danh sách bài, thứ tự viết, **tiêu chuẩn chuyên sâu**), `README.md`, `tracks.json`, `glossary.json` và liệt kê `content/` để biết topic và thuật ngữ đã có. Không viết trùng topic.
   Người dùng không nêu bài cụ thể thì đề xuất bài ⬜ tiếp theo theo thứ tự trong curriculum.
3. Tạo nhánh `topic/<id>` nếu đang ở máy khác máy chính hoặc người dùng muốn PR.

## 1. Chốt phạm vi với người dùng (một câu hỏi, có đề xuất sẵn)
- Track, `id` (kebab-case, tiếng Anh), tiêu đề, level, thời lượng (10–20 phút). Bài có trong curriculum thì dùng `id` và trọng tâm ghi ở đó; bài chưa có thì thêm dòng mới vào curriculum.
- Phạm vi phải đạt **tiêu chuẩn chuyên sâu** (mục 1 của curriculum): cơ chế bên trong, khác biệt giữa các hệ/phiên bản, bẫy production, trade-off, câu hỏi nối tiếp. Chủ đề quá rộng thì tách bài.
- Chọn block theo loại topic:

| Loại topic | Block |
|---|---|
| Nền tảng (HTTP, TCP, Big-O) | analogy + layered + diagram |
| Cơ chế bên trong (HashMap, GC) | simulation + layered + breakLab |
| Khái niệm trừu tượng (IoC, CAP, AuthN/AuthZ) | analogy + layered |
| Lỗi hay gặp (N+1, race condition) | breakLab + layered |
| Troubleshooting & Performance | troubleshoot + layered |
| Pattern phân tán (Saga, Outbox) | scenario + diagram + layered |
| Kiến trúc / SA | scenario + diagram |
| Kiến thức ngắn | layered |

`layered` gần như luôn có.

## 2. Nghiên cứu từ nguồn chính thức
Ưu tiên: Javadoc/JLS/JEP (docs.oracle.com, openjdk.org), Spring docs, tài liệu chính thức của PostgreSQL/MySQL/Redis/Kafka, OWASP, AWS docs, RFC.
Ghi 1–3 nguồn vào `references` của `topic.json`. Ghi rõ phiên bản Java khi hành vi phụ thuộc phiên bản.
Không chắc thì nói rõ với người dùng, không bịa.

## 3. Tạo khung và viết
```bash
scripts/new-topic <track>/<id> --title "..." --level <level> --minutes <n> --blocks <danh sách>
```
Thay **mọi** chữ TODO. Quy tắc theo block:

- **analogy.md**: 2–4 đoạn ngắn, ví dụ đời thường quen với người Việt. Câu cuối nối sang khái niệm kỹ thuật bằng thuật ngữ `[[...]]`.
- **layered.md**: đúng 3 heading `## Quick`, `## Interview`, `## Deep`.
  - Quick: 1–3 câu, nêu bản chất và quy tắc quan trọng nhất (in đậm).
  - Interview: câu trả lời mẫu nói được trong ~2 phút (200–350 từ): định nghĩa → cơ chế → khi nào dùng / bẫy hay gặp → cách làm đúng.
  - Deep: gạch đầu dòng, mỗi ý một edge case, chi tiết bên trong JDK/framework, hoặc lưu ý hiệu năng.
- **lab.json (breakLab)**: code lỗi chạy được, triệu chứng có output thật, 4 lựa chọn chẩn đoán với 1 đáp án đúng và các lựa chọn sai hợp lý, cách sửa có code.
- **scenario.json**: đề bài thực tế có ràng buộc (quy mô, SLA), 2–4 gợi ý từ rộng đến hẹp, lời giải, `tradeoffs` khi có nhiều phương án.
- **troubleshoot.json**: bước đầu là triệu chứng; mỗi bước có 3–4 lựa chọn với `quality` good/ok/poor và feedback giải thích vì sao; evidence là dữ liệu như thật (thread dump, log, metric) dùng `evidenceFormat: monospace`; kết thúc bằng step không có choices nêu nguyên nhân gốc và cách phòng ngừa.
- **simulation.json**: chọn engine theo nội dung, xem schema trong `schema/simulations/` và ví dụ chạy được trong `schema/simulations/examples/`.
  - `threadTimeline`: race condition, deadlock, `synchronized`, `volatile`/visibility (đặt `memoryModel: jmm`). Mỗi bước có dòng `code` Java ngắn. Có ít nhất một `schedules` dẫn tới kết cục đáng học (deadlock, sai giá trị) và `outcomes` giải thích; khai báo `expect` khi có giá trị đúng.
  - `stateMachine`: vòng đời, trạng thái (Thread lifecycle, Circuit Breaker, Saga). Toạ độ trạng thái theo cùng quy tắc với diagram; nhãn transition ≤ 20 ký tự; mỗi state có `note`.
  - `native:hashmap`: chỉ cho topic HashMap; `keys` nên có nhóm trùng hashCode (Aa/BB) để thấy collision và đủ key để vượt ngưỡng resize.
  - `instructions`: 1–2 câu nói người học cần thử gì.
- **diagram.json**: 3–7 node, mỗi step thêm 1–2 node/edge kèm caption một câu. Sơ đồ hiển thị trên khung ~340×300pt của điện thoại: tối đa 4 cột; app coi hai node chênh `y` < 0.35 là cùng hàng và thu nhỏ node theo cặp gần nhất, nên các node đó phải chênh `x` ≥ 0.32 (nên ≥ 0.6 để nhãn không bị cắt khi chữ lớn); node cùng cột phải chênh `y` ≥ 0.26 (`scripts/validate` kiểm tra). Bố cục an toàn: 2 cột `x` 0.1 và 0.85, các hàng `y` 0.05 / 0.5 / 0.95; nhãn node ngắn, tối đa ~2 dòng × 12 ký tự; nhãn edge tối đa 20 ký tự và chỉ hiện ở bước edge đó được nhấn mạnh (`highlight`, hoặc bước edge xuất hiện).
- **glossary.json**: `term` là tên ngắn (ví dụ `DNS`, `Keep-alive`); phần viết đầy đủ hoặc giải thích đưa vào `meaning`.
- **callout** (inline trong topic.json): `interview` cho câu hỏi nối tiếp hay gặp, `warning` cho bẫy, `tip` cho mẹo.
- **flashcards.json**: 5–10 thẻ, mặt trước là câu hỏi ngắn, mặt sau trả lời trong 1–2 câu. Mỗi thẻ chỉ một ý.
- **quiz.json**: 3–5 câu; có ít nhất 1 câu `output` nếu topic có code. Đáp án sai phải là hiểu lầm phổ biến, không phải đáp án vô lý. Giải thích vì sao đúng. App xáo thứ tự lựa chọn mỗi lần hiển thị (cả quiz lẫn chẩn đoán của lab), nên lời giải gọi lựa chọn theo nội dung, không theo vị trí ("đáp án thứ hai", "lựa chọn cuối"; `scripts/validate` báo lỗi), và độ dài các lựa chọn nên tương đương để đáp án đúng không lộ vì dài nhất.

### Văn phong
- Tiếng Việt, câu ngắn, giọng thẳng. Thuật ngữ giữ tiếng Anh.
- Lần đầu xuất hiện thuật ngữ trong mỗi file: bọc `[[id]]` hoặc `[[id|chữ hiển thị]]`. Thuật ngữ chưa có thì thêm vào `glossary.json`: `meaning` 1–2 câu tiếng Việt, `example` cụ thể, `related`, `topics`.
- Code Java hiện đại (17–21) trừ khi topic nói về phiên bản cũ. Tên biến có nghĩa, không dùng `foo`.
- Không nhắc tên công ty, dự án hay khách hàng thật.

## 4. Kiểm tra
```bash
scripts/validate
```
Sửa đến khi sạch lỗi. Validator báo lỗi nếu bài chưa có trong `docs/CURRICULUM.md` hoặc chưa đổi ⬜ thành ✅. Sau đó gọi agent **content-reviewer** với đường dẫn topic để review độc lập về độ chính xác kỹ thuật và chất lượng sư phạm. Sửa theo các phát hiện có căn cứ; với điểm không đồng ý thì nói lý do cho người dùng.

Nếu có repo app cạnh repo này, có thể xem trước: `scripts/build`, rồi chạy app trên Simulator với nguồn "Thư mục local".

## 5. Bàn giao
- Tóm tắt cho người dùng: các block, số flashcard/quiz, thuật ngữ mới, nguồn tham khảo, điểm reviewer đã nêu.
- Commit (hoặc mở PR nếu đang trên nhánh) khi người dùng đồng ý. **Không tạo tag**: phát hành là quyết định của chủ repo.
