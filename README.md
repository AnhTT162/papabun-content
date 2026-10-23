# papabun-content

Nội dung bài học cho app **PapaBun**. Repo này public để app tải bài mới qua GitHub Releases mà không cần cập nhật app.

## Cấu trúc
```
tracks.json      # 15 track và thứ tự
glossary.json    # thuật ngữ dùng chung, tham chiếu trong bài bằng [[id]]
content/<track>/<topic>/   # mỗi topic một thư mục
schema/          # JSON Schema (Giai đoạn 1)
scripts/         # new-topic, validate, build (Giai đoạn 1)
```

## Quy tắc
- Không đổi `id` của topic, thẻ, thuật ngữ sau khi đã phát hành: tiến độ học trong app gắn với `id`.
- Không đưa thông tin cá nhân hoặc dự án công ty vào repo này.
