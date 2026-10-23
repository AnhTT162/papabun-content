---
name: project-profile
description: Tạo hoặc cập nhật hồ sơ một dự án thật (kiến trúc, tech stack, quyết định, vấn đề khó theo STAR, câu hỏi luyện tập) để nhập vào mục "Dự án của tôi" của app PapaBun. Chạy bên trong repo của dự án cần làm hồ sơ. Dùng khi người dùng muốn chuẩn bị kể về dự án đã làm khi phỏng vấn.
---

# Hồ sơ dự án cho PapaBun

Mục tiêu: giúp người dùng **hiểu thật rõ dự án mình đã làm** và kể lại mạch lạc khi phỏng vấn. Kết quả là một file JSON nhập vào app, theo `schema/project-profile.schema.json` của repo `AnhTT162/papabun-content`.

## Quy tắc bảo mật (đọc trước khi làm gì)
Code đang mở thường là tài sản của công ty.
1. Trước khi đọc code, nhắc người dùng một lần: việc dùng AI trên code công ty phải đúng chính sách của công ty, và nên dùng tài khoản Claude được công ty cho phép. Chỉ tiếp tục khi người dùng xác nhận.
2. **Không** ghi vào hồ sơ: tên công ty, tên khách hàng, tên nội bộ của service/repo, hostname, IP, URL nội bộ, credential, đoạn code, schema DB chi tiết, số liệu kinh doanh chính xác. Dùng mô tả chung ("một ngân hàng bán lẻ", "service xử lý thanh toán") và số làm tròn ("~2.000 request/giây").
3. **Không** đọc file chứa secret (`.env`, `*secret*`, `*credential*`, keystore, file `application-*.yml` có mật khẩu). Gặp giá trị nhạy cảm thì bỏ qua, không trích dẫn.
4. File kết quả ghi **ngoài** repo dự án và **không bao giờ** commit vào `papabun-content` (repo public) hay repo dự án.
5. Trước khi ghi file, cho người dùng xem toàn bộ nội dung để họ duyệt.

## Quy trình
1. **Khảo sát repo** (chỉ đọc): README, tài liệu kiến trúc, file build (`pom.xml`, `build.gradle*`), `docker-compose*`, manifest Kubernetes/Helm, cấu hình CI/CD, cấu trúc package, các module chính, cấu hình dependency (DB, cache, message broker, cloud SDK). Không cần đọc hết code.
2. **Phác thảo phần suy ra được từ code**: sản phẩm, kiến trúc (thành phần và luồng dữ liệu chính, viết Markdown), tech stack kèm vai trò của từng công nghệ trong dự án. Với mỗi công nghệ, gán `technologyId` nếu trùng id trong `project-questions.json` của papabun-content (tải từ `https://github.com/AnhTT162/papabun-content/releases/latest/download/project-questions.json` nếu có mạng; các id hiện có: kafka, redis, spring-boot).
3. **Hỏi người dùng phần code không trả lời được**, từng nhóm một, có gợi ý câu trả lời từ những gì đã thấy:
   - Vai trò của bạn, quy mô team, thời gian tham gia.
   - Quy mô hệ thống (ước lượng).
   - 2–4 quyết định kỹ thuật: chọn gì, cân nhắc những phương án nào, vì sao, đánh đổi gì.
   - 1–3 vấn đề khó nhất: kể theo STAR. Giúp người dùng làm rõ phần Action (bạn đã làm gì cụ thể) và Result (có số liệu nếu được).
   - Con số đáng nhớ, và nếu làm lại sẽ làm khác gì.
4. **Sinh 5–10 câu hỏi luyện tập** mà người phỏng vấn dễ hỏi về chính dự án này (ví dụ "Nếu traffic tăng 10 lần thì phần nào vỡ trước?"), mỗi câu kèm `answerNotes` là các ý chính dựa trên câu trả lời của người dùng. Ưu tiên câu xoáy vào quyết định và trade-off.
5. **Chỉ ra lỗ hổng**: liệt kê các chủ đề người dùng trả lời còn mơ hồ (ví dụ chưa giải thích được vì sao chọn isolation level) và gợi ý topic tương ứng để ôn trong PapaBun.
6. **Rà soát bảo mật** theo mục Quy tắc, cho người dùng duyệt, rồi ghi file:
   `~/PapaBun/projects/<id>.json` (tạo thư mục nếu chưa có). `id` là kebab-case mô tả chung, ví dụ `payment-platform`.
7. Hướng dẫn chuyển file sang iPhone (AirDrop, iCloud Drive hoặc email cho chính mình) rồi nhập trong app: tab Phỏng vấn → Dự án của tôi → Nhập. (Màn nhập có ở Giai đoạn 5 của app; trước đó cứ giữ file.)

## Cập nhật hồ sơ đã có
Nếu `~/PapaBun/projects/<id>.json` đã tồn tại, đọc nó, hỏi người dùng muốn bổ sung phần nào, giữ nguyên `id` và các `practiceQuestions[].id` cũ.
