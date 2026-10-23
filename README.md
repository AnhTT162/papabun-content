# papabun-content

Nội dung bài học cho app **PapaBun**. Repo này public để app tải bài mới qua GitHub Releases mà không cần cập nhật app.

## Thêm một bài học

```bash
scripts/new-topic concurrency/deadlock --title "Deadlock" --level mid --blocks analogy,simulation,layered,breakLab
# ...viết nội dung, thay hết chữ TODO...
scripts/validate
scripts/build          # tùy chọn: xem trước trên Simulator (xem bên dưới)
git add . && git commit -m "Add deadlock topic" && git push
git tag v2026.10.24 && git push origin v2026.10.24   # phát hành
```

Khi có tag `v*`, GitHub Actions build và tạo Release. App kiểm tra
`https://github.com/AnhTT162/papabun-content/releases/latest/download/manifest.json` và chỉ tải file đã thay đổi.

### Xem trước trên Simulator trước khi phát hành
1. `scripts/build` (ghi vào `dist/`, thư mục này không commit).
2. Chạy app bản Debug từ Xcode. Scheme đã trỏ biến môi trường `PAPABUN_LOCAL_CONTENT` tới `../papabun-content/dist`.
3. Trong app: tab Học → biểu tượng ⚙︎ → Nguồn nội dung → **Thư mục local**.

## Cấu trúc

```
schema/                    # JSON Schema: nguồn sự thật cho định dạng, cũng cho VS Code gợi ý
tracks.json                # 15 track và thứ tự
glossary.json              # thuật ngữ dùng chung
project-questions.json     # câu hỏi mẫu theo công nghệ cho "Dự án của tôi"
content/<track>/<topic>/
  topic.json               # metadata + danh sách block
  analogy.md, layered.md   # block Markdown
  lab.json, scenario.json, troubleshoot.json, diagram.json, simulation.json
  flashcards.json, quiz.json   # tùy chọn
  images/                  # ảnh dùng trong Markdown: ![mô tả](images/ten.png)
scripts/                   # new-topic, validate, build (chỉ cần Python 3.9+, không cần cài thêm gì)
```

## Viết nội dung
- **Thuật ngữ**: `[[bucket]]` hoặc `[[hash-code|hashCode]]` để đổi chữ hiển thị. Thuật ngữ phải có trong `glossary.json`.
- **layered.md** cần đúng 3 heading theo thứ tự: `## Quick`, `## Interview`, `## Deep`.
- **callout** viết thẳng trong `topic.json`: `{ "type": "callout", "style": "tip|warning|interview", "markdown": "..." }`.
- **code**: `{ "type": "code", "file": "Example.java", "caption": "..." }`, ngôn ngữ lấy từ đuôi file.
- Mỗi topic nên có `references` trỏ tới nguồn chính thức để kiểm chứng.

## `scripts/validate` kiểm tra gì
Schema của mọi file; id trùng; id topic trùng tên thư mục và track; prerequisites, thuật ngữ, ảnh tồn tại;
đáp án quiz/lab hợp lệ; sơ đồ troubleshoot đi tới được mọi bước và có kết luận; diagram tham chiếu đúng node/edge;
và **còn chữ TODO thì báo lỗi**.

## Định dạng phát hành (`dist/`)
- `manifest.json`: `contentVersion`, danh sách file kèm `sha256`, `size`, `kind`, và `minAppVersion` cho topic.
- `topic-<id>.json`: topic đã gộp, Markdown và JSON của mọi block nằm sẵn bên trong, kèm `flashcards` và `quiz`.
- `img-<topic>-<tên>.png`: ảnh, đường dẫn trong Markdown được viết lại tương ứng.

## Quy tắc
- Không đổi `id` của topic, thẻ, câu quiz, thuật ngữ sau khi đã phát hành: tiến độ học trong app gắn với `id`.
- Tăng `minAppVersion` của topic khi topic dùng tính năng chỉ app mới hiểu.
- Không đưa thông tin cá nhân hoặc dự án công ty vào repo này.
