# papabun-content

Nội dung bài học cho app iOS PapaBun (repo app: `AnhTT162/papabun-app`, private). Repo này **public**.

## Lệnh
- `scripts/validate`: kiểm tra toàn bộ nội dung. Phải sạch lỗi trước khi commit.
- `scripts/build [--version X]`: biên dịch ra `dist/` (không commit).
- `scripts/new-topic <track>/<id> --title "..." --level mid --blocks analogy,layered`: tạo khung topic.
- `python3 -m unittest discover -s scripts/tests`: test của scripts. Chạy khi sửa `scripts/` hoặc `schema/`.
- Scripts chỉ dùng thư viện chuẩn Python 3.9. Không thêm dependency.

## Soạn nội dung
Dùng skill `/papabun:write-topic` để viết bài mới và agent `content-reviewer` để kiểm tra trước khi commit.
Cài plugin một lần mỗi máy: `claude plugin marketplace add AnhTT162/papabun-content` rồi `claude plugin install papabun@papabun`.

## Quy tắc bắt buộc
- Repo public: **không bao giờ** đưa tên công ty, khách hàng, code, URL nội bộ, số liệu thật của dự án công ty vào đây.
  Hồ sơ dự án thật (skill `/papabun:project-profile`) lưu ngoài repo này.
- Không đổi `id` của topic, flashcard, câu quiz, thuật ngữ đã phát hành (tiến độ học trong app gắn với id).
- Không tự tạo tag hay Release: tag `v*` là phát hành cho người dùng, chỉ chủ repo quyết định.
- Thay đổi schema phải giữ tương thích với app đã phát hành; định dạng mới cần tăng `minAppVersion` của topic.
