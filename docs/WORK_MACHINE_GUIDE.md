# Làm nội dung PapaBun trên máy công ty

Hướng dẫn dùng Claude Code trên một máy khác (máy công ty, tài khoản Claude khác) để:

- **A. Soạn bài học lý thuyết** và gửi về repo `AnhTT162/papabun-content` bằng Pull Request.
- **B. Làm hồ sơ dự án thật** từ code công ty để luyện kể dự án khi phỏng vấn. Hồ sơ chỉ nằm trên máy và điện thoại của bạn, không lên GitHub.

---

## 0. Đọc trước khi bắt đầu

| ✅ Được | ❌ Không được |
|---|---|
| Kiến thức chung: Java, Spring, DB, Kafka, System Design… | Tên công ty, khách hàng, sản phẩm nội bộ trong bài học |
| Bài học gửi lên repo public qua PR | Code, cấu hình, URL, hostname, số liệu thật của công ty lên repo public |
| Hồ sơ dự án lưu ở `~/PapaBun/projects/` | Commit hồ sơ dự án vào bất kỳ repo nào |

- **Chính sách công ty:** việc dùng AI trên code công ty và cài công cụ (Claude Code, plugin) phải đúng quy định của công ty. Hỏi trước nếu chưa rõ, và dùng tài khoản Claude được công ty cho phép.
- **Repo `papabun-content` là public:** mọi thứ push lên đó ai cũng đọc được.

---

## 1. Cài đặt (một lần mỗi máy)

### 1.1. Công cụ cần có
- Claude Code (đã đăng nhập tài khoản Claude dùng trên máy này)
- Git, Python 3.9 trở lên (`python3 --version`)
- GitHub CLI (`gh`) nếu muốn mở PR từ dòng lệnh

### 1.2. Quyền push lên repo nội dung
Chọn **một** trong hai cách:

**Cách 1: Thêm tài khoản GitHub trên máy công ty làm collaborator (đơn giản nhất)**
Trên máy cá nhân (đang đăng nhập AnhTT162), thay `<github-user>` bằng tài khoản dùng trên máy công ty:
```bash
gh api -X PUT repos/AnhTT162/papabun-content/collaborators/<github-user> -f permission=push
```
Trên máy công ty, mở email mời hoặc vào https://github.com/AnhTT162/papabun-content/invitations để chấp nhận.

**Cách 2: Fork**
Trên máy công ty: `gh repo fork AnhTT162/papabun-content --clone`, rồi mở PR từ fork về repo gốc.

### 1.3. Clone repo nội dung
```bash
mkdir -p ~/PapaBun && cd ~/PapaBun
git clone https://github.com/AnhTT162/papabun-content.git
cd papabun-content && scripts/validate
```
Dòng cuối phải là `✓ Hợp lệ: ...`.

### 1.4. Cài plugin PapaBun cho Claude Code
```bash
claude plugin marketplace add AnhTT162/papabun-content
claude plugin install papabun@papabun
claude plugin list
```
`claude plugin list` phải có `papabun@papabun` với trạng thái enabled. Plugin gồm:

| Thành phần | Dùng để |
|---|---|
| `/papabun:write-topic` | Soạn bài học mới đúng định dạng |
| agent `content-reviewer` | Review độc lập độ chính xác kỹ thuật |
| `/papabun:project-profile` | Tạo hồ sơ dự án thật |

**Cập nhật plugin** khi repo có phiên bản mới (sau đó mở lại phiên Claude):
```bash
claude plugin marketplace update papabun
claude plugin update papabun@papabun
```

---

## 2. Quy trình A: soạn bài học lý thuyết

```bash
cd ~/PapaBun/papabun-content
git switch main && git pull
git switch -c topic/<id-bai-hoc>        # ví dụ topic/transaction-isolation
claude
```

Trong Claude, gõ ví dụ:
```
/papabun:write-topic Viết bài "Transaction Isolation Level" cho track database, level mid
```

Claude sẽ:
1. Hỏi chốt phạm vi (id, level, các block). Trả lời hoặc đồng ý đề xuất.
2. Tra nguồn chính thức, viết các file, thêm thuật ngữ vào `glossary.json`.
3. Chạy `scripts/validate` cho đến khi sạch lỗi.
4. Gọi `content-reviewer` để review, sửa theo các điểm có căn cứ.
5. Tóm tắt và hỏi bạn trước khi commit.

Sau khi đồng ý commit, đẩy lên và mở PR:
```bash
git push -u origin HEAD
gh pr create --repo AnhTT162/papabun-content --fill
```

**Trên máy cá nhân** (bước phát hành, chỉ làm ở đây):
1. Review PR trên GitHub, merge.
2. Phát hành bằng tag (thêm `.2`, `.3` nếu phát hành nhiều lần trong ngày):
   ```bash
   cd papabun-content && git switch main && git pull
   git tag v2026.10.25 && git push origin v2026.10.25
   ```
3. Mở app PapaBun, kéo xuống ở tab Học để tải bài mới.

**Mẹo viết nhiều bài:** mỗi bài một nhánh và một PR để review dễ hơn. Có thể yêu cầu Claude:
```
/papabun:write-topic Viết lần lượt 3 bài cho track database: index, execution plan, n-plus-one. Mỗi bài xong thì commit riêng.
```

---

## 3. Quy trình B: hồ sơ dự án thật

Chạy **bên trong repo dự án** trên máy công ty:
```bash
cd ~/work/<repo-du-an>
claude
```
```
/papabun:project-profile
```

Claude sẽ:
1. Nhắc về chính sách AI của công ty và chờ bạn xác nhận.
2. Chỉ đọc cấu trúc, file build, Docker/Kubernetes, CI/CD để phác thảo kiến trúc và tech stack. Không đọc file chứa secret.
3. Hỏi bạn phần code không trả lời được: vai trò, quy mô, quyết định và trade-off, vấn đề khó theo STAR, con số.
4. Sinh câu hỏi luyện tập kèm ý chính để tự chấm, và chỉ ra chủ đề bạn trả lời còn mơ hồ để ôn trong app.
5. Cho bạn duyệt toàn bộ nội dung, rồi ghi `~/PapaBun/projects/<id>.json`.

**Khi duyệt, kiểm tra kỹ:** không còn tên công ty/khách hàng, tên service nội bộ, URL, IP, đoạn code, số liệu kinh doanh chính xác. Thấy gì nhạy cảm thì yêu cầu Claude bỏ hoặc viết chung chung hơn.

**Đưa hồ sơ sang iPhone:** AirDrop, iCloud Drive hoặc email cho chính mình (nếu chính sách công ty cho phép), rồi trong PapaBun: Phỏng vấn → Dự án của tôi → Nhập. Màn nhập sẽ có ở Giai đoạn 5 của app; trước đó cứ giữ file.

**Không bao giờ:** `git add` file hồ sơ vào repo dự án hay `papabun-content`.

**Cập nhật hồ sơ sau này:** chạy lại `/papabun:project-profile` trong repo đó. Claude đọc file cũ và hỏi phần muốn bổ sung.

---

## 4. Prompt mẫu

| Mục đích | Prompt |
|---|---|
| Bài có lab | `/papabun:write-topic Bài "N+1 query trong JPA", track database, có breakLab` |
| Bài troubleshoot | `/papabun:write-topic Bài "Connection pool cạn", track performance, có troubleshoot` |
| Review lại bài đã có | `Dùng agent content-reviewer review content/core-java/equals-hashcode` |
| Bổ sung thuật ngữ | `Thêm vào glossary các thuật ngữ còn thiếu trong track concurrency, kèm giải thích tiếng Việt` |
| Luyện dự án | `/papabun:project-profile` rồi `Hỏi tôi 5 câu xoáy nhất về dự án này như người phỏng vấn, chấm từng câu` |

---

## 5. Xử lý sự cố

| Triệu chứng | Cách xử lý |
|---|---|
| `scripts/validate` báo lỗi | Đọc dòng `✗ file: lỗi`, nhờ Claude sửa. `còn chữ TODO` nghĩa là còn phần chưa viết |
| Không thấy `/papabun:...` | `claude plugin list`; nếu thiếu thì làm lại mục 1.4, rồi mở phiên Claude mới |
| `Permission denied` khi push | Chưa chấp nhận lời mời collaborator (Cách 1) hoặc đang push vào repo gốc thay vì fork (Cách 2) |
| Python quá cũ | Cần Python 3.9+. Kiểm tra `python3 --version` |
| Mạng công ty chặn GitHub | Không làm Quy trình A trên máy đó; Quy trình B vẫn làm được vì không cần push |

---

## 6. Checklist trước mỗi lần push

- [ ] `scripts/validate` sạch lỗi
- [ ] `content-reviewer` đã review, các điểm "Sai" đã sửa
- [ ] Không có tên công ty, khách hàng, dự án, URL nội bộ trong diff (`git diff main`)
- [ ] Không có file hồ sơ dự án trong commit
- [ ] Push lên nhánh `topic/...`, không push thẳng `main`, không tạo tag
