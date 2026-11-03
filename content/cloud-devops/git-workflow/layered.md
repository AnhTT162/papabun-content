## Quick

Git là kho object đặt tên theo hash nội dung (blob, tree, commit), còn nhánh chỉ là một con trỏ tới commit. **Merge giữ nguyên commit cũ và thêm commit nối; rebase tạo commit mới có hash mới**, nên đừng rebase nhánh người khác đã dựa vào. Với service deploy liên tục, quy trình nhánh tốt nhất là trunk-based: nhánh sống ngắn, merge vào main mỗi ngày.

## Interview

Bên trong, Git lưu bốn loại object, mỗi object đặt tên bằng hash của nội dung. [[git-blob|Blob]] là nội dung file, [[git-tree|tree]] là danh sách tên file trỏ tới blob và tree con, [[git-commit-object|commit]] trỏ tới một tree (ảnh chụp toàn bộ project), các commit cha, tác giả và message. Annotated tag là loại thứ tư. Git lưu ảnh chụp chứ không lưu diff; file không đổi thì dùng lại blob cũ. Vì hash của commit gồm cả hash của cha, đổi một commit cũ là đổi toàn bộ chuỗi sau nó.

Nhánh là một [[git-ref|ref]]: file chứa hash của commit mới nhất; `HEAD` trỏ tới nhánh đang đứng. Commit mới chỉ là tạo object rồi dời con trỏ. Giữa thư mục làm việc và commit có staging area (index): `git add` ghi blob và đưa nó vào index, `git commit` dựng tree từ index.

[[git-merge|Merge]] tìm [[merge-base|merge base]] (tổ tiên chung gần nhất) rồi gộp ba chiều; nếu nhánh đích chưa đi tiếp thì chỉ [[fast-forward-merge|fast-forward]] con trỏ. [[git-rebase|Rebase]] áp lại từng commit của tôi lên đầu nhánh kia, tạo commit mới. Lịch sử thẳng và dễ đọc hơn, nhưng ai đã kéo commit cũ sẽ có hai bản song song. Quy tắc của tôi: rebase nhánh riêng trước khi mở pull request, không rebase nhánh dùng chung; buộc phải đẩy đè thì dùng `--force-with-lease`. Lỡ tay thì [[git-reflog|reflog]] còn giữ vị trí cũ.

Về quy trình, [[git-flow|Git Flow]] (develop, release, hotfix) hợp với phần mềm phát hành theo phiên bản và phải duy trì nhiều bản song song. Với service deploy liên tục, tôi chọn [[trunk-based-development|trunk-based]]: nhánh feature sống một hai ngày, CI chạy trên mọi pull request, tính năng chưa xong nằm sau [[feature-flag|feature flag]] thay vì nằm trên nhánh dài. Nhánh dài là nguồn của merge conflict lớn và lỗi tích hợp phát hiện muộn.

Khi cần tìm commit gây lỗi, [[git-bisect|`git bisect run`]] với một test tái hiện tìm được trong khoảng log₂(n) lần chạy: 100 commit thì khoảng 7 lần.

## Deep

- **Hash theo nội dung**: blob là SHA-1 của `blob <độ dài>\0<nội dung>`, nên `git hash-object` cho cùng kết quả với `printf 'blob 6\0hello\n' | shasum`. Thêm một file trùng nội dung file cũ rồi commit chỉ tạo hai object mới (tree, commit), không tạo blob mới (đã thử trên Git 2.54).
- **Ảnh chụp và packfile**: object rời được nén zlib; `git gc` gom vào packfile và lúc đó mới nén delta giữa các phiên bản gần giống nhau. Vì vậy "Git lưu ảnh chụp" không có nghĩa repo phình theo số commit × kích thước project. File nhị phân lớn thì delta kém: dùng Git LFS.
- **SHA-1 và SHA-256**: sau vụ va chạm SHAttered (2017), Git dùng SHA-1 có phát hiện va chạm (từ 2.13). Repo mới có thể tạo với `--object-format=sha256`, nhưng nhiều dịch vụ hosting còn chưa hỗ trợ đầy đủ. Git 2.54 vẫn mặc định SHA-1 và đã cảnh báo tên nhánh mặc định sẽ đổi thành `main` ở Git 3.0; kế hoạch của Git 3.0 cũng đổi định dạng object mặc định của repo mới sang SHA-256.
- **Commit bất biến**: commit chứa tree, cha, author (người viết, ngày viết), committer (người tạo commit này, ngày tạo). `--amend`, rebase, cherry-pick giữ author nhưng tạo commit mới với cha mới hoặc committer date mới, nên hash đổi (rebase một nhánh đã nằm sẵn trên base thì không có gì để làm, hash giữ nguyên) (đã thử: rebase một commit đổi `6579ee0` thành `cfc6d59`).
- **Merge**:
  - Fast-forward khi nhánh đích là tổ tiên của nhánh nguồn; `--no-ff` ép tạo merge commit để giữ ranh giới của feature.
  - Chiến lược mặc định là `ort` từ Git 2.34; `recursive` chỉ còn là tên gọi khác của `ort` từ 2.50. Khi có nhiều merge base (criss-cross merge), `ort` gộp các base thành một tree ảo làm gốc so sánh.
  - Conflict nội dung xảy ra khi hai bên sửa cùng vùng so với merge base; hai bên sửa giống hệt nhau thì không conflict. Còn conflict ở mức file: một bên xoá hoặc đổi tên file mà bên kia sửa, hai bên cùng thêm một file khác nội dung.
  - `git pull` là `fetch` rồi `merge`; `pull --rebase` (hoặc `pull.rebase=true`) thay merge bằng rebase để không sinh merge commit vô nghĩa trên nhánh riêng.
- **Rebase**:
  - Áp lại từng commit, nên conflict có thể phải giải nhiều lần, mỗi commit một lần. `git rerere` nhớ cách giải để dùng lại.
  - `git rebase -i` để gộp (squash/fixup), sửa message, bỏ commit trước khi mở pull request; `git commit --fixup` cộng `--autosquash` làm việc này gọn hơn.
  - `--onto` chuyển một dải commit sang gốc khác, ví dụ tách nhánh B khỏi nhánh A chưa merge.
  - Mặc định rebase bỏ merge commit và làm phẳng lịch sử; cần giữ thì dùng `--rebase-merges`.
- **Đẩy đè an toàn**: `--force-with-lease` chỉ đè nếu nhánh trên remote vẫn trùng ref theo dõi ở máy bạn. IDE hay chạy `git fetch` nền làm ref theo dõi được cập nhật, lease vẫn qua dù bạn chưa từng thấy commit mới; thêm `--force-if-includes` (Git 2.30) để kiểm, qua reflog local, rằng commit trên remote đã từng nằm trong lịch sử của bạn. Tuỳ chọn này chỉ có tác dụng khi `--force-with-lease` không kèm giá trị kỳ vọng cụ thể.
- **[[squash-merge|Squash merge]]** (nút "Squash and merge"): main nhận một commit mới chứa toàn bộ thay đổi, không có quan hệ cha với các commit của nhánh. Git không biết nhánh đã được gộp: `git branch -d` báo "not fully merged" (đã thử). Tiếp tục làm trên chính nhánh đó rồi mở pull request mới thì conflict lặp lại; tạo nhánh mới từ main.
- **Revert trên nhánh chung, không reset**: `git revert` tạo commit đảo ngược, an toàn khi người khác đã kéo. Revert một merge commit cần `-m 1` (giữ cha thứ nhất). Bẫy: sau khi revert merge của nhánh X, merge X lần nữa **không** mang thay đổi cũ quay lại, vì các commit đó đã nằm trong lịch sử; phải revert chính commit revert.
- **Reflog**: ghi mọi lần `HEAD` và nhánh di chuyển, chỉ ở máy local. Rebase hỏng thì `git reflog` tìm vị trí trước đó rồi `git reset --hard HEAD@{n}` (ngay sau rebase hay reset thì `ORIG_HEAD` cũng trỏ về vị trí cũ). `--hard` xoá luôn thay đổi chưa commit trong thư mục làm việc; `--soft` chỉ dời nhánh, `--mixed` (mặc định) dời nhánh và đặt lại index. Mặc định mục reflog giữ 90 ngày, mục trỏ tới commit không còn được nhánh nào giữ thì 30 ngày.
- **`git bisect run`**: script trả 0 là good, 1–127 (trừ 125) là bad, 125 là bỏ qua commit không build được, từ 128 trở lên thì dừng. Đã thử: 100 commit, lỗi ở commit 73, bisect tìm đúng sau 7 lần chạy. Cần test ổn định; test flaky làm bisect chỉ sai chỗ (bài Test chập chờn).
- **Git Flow** (Vincent Driessen, 2010): `main` chỉ chứa bản đã phát hành, `develop` để tích hợp, nhánh `feature/*`, `release/*`, `hotfix/*`. Năm 2020 chính tác giả viết thêm ghi chú: với web app deploy liên tục thì nên dùng quy trình đơn giản hơn. Hợp với thư viện, app mobile, phần mềm cài tại khách hàng cần vá nhiều phiên bản cùng lúc.
- **GitHub flow**: một nhánh `main` luôn deploy được, nhánh feature, pull request, merge rồi deploy. Gần trunk-based, khác ở chỗ nhánh có thể sống lâu hơn.
- **Trunk-based development**:
  - Mọi người tích hợp vào trunk ít nhất mỗi ngày; nhánh feature sống ngắn hay commit thẳng (team nhỏ, có pair programming).
  - Tính năng dở dang ẩn sau feature flag; thay đổi lớn dùng [[branch-by-abstraction|branch by abstraction]] thay vì nhánh dài.
  - Cần nền: CI nhanh và tin được, review nhanh, test tự động đủ. Thiếu những thứ này mà ép trunk-based thì main hỏng liên tục.
  - Cần nhánh phát hành (app mobile chờ duyệt) thì cắt `release/x.y` từ trunk, sửa lỗi trên trunk rồi [[cherry-pick|cherry-pick]] (`-x` để ghi nguồn) sang nhánh phát hành, không làm ngược lại.
  - Nghiên cứu DORA (*Accelerate*, 2018) thấy trunk-based đi cùng hiệu quả giao hàng cao: ít hơn ba nhánh hoạt động, merge vào trunk ít nhất mỗi ngày, không có giai đoạn đóng băng code.
- **Bảo vệ nhánh**: chặn đẩy thẳng vào main, bắt buộc check CI và review, `CODEOWNERS` cho phần nhạy cảm. Nhiều pull request cùng xanh nhưng hỏng khi gộp chung: [[merge-queue|merge queue]] chạy CI trên kết quả gộp trước khi vào main. Pipeline đầy đủ ở bài CI/CD pipeline.
- **Lỡ commit secret**: xoá trong commit sau không đủ vì lịch sử còn; viết lại lịch sử (`git filter-repo`) cũng không đủ khi đã đẩy lên, vì bản clone, fork và cache vẫn giữ. Việc đầu tiên là thu hồi và xoay secret (bài Quản lý secret).
