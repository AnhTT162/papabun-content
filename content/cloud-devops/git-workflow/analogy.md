Một phòng lưu trữ hồ sơ không bao giờ sửa giấy tờ đã nộp. Mỗi bản hồ sơ được đóng dấu một mã tính từ chính nội dung của nó; hai bản giống hệt nhau thì cùng mã, nên kho chỉ giữ một bản. Mỗi lần chốt sổ, thủ kho ghi một phiếu: "danh sách các hồ sơ lúc này, phiếu trước đó là số mấy, ai chốt, vì sao". Phiếu cũng được đóng mã theo nội dung, nên sửa một chữ trong phiếu cũ là ra một phiếu khác hẳn.

Các tổ làm việc không giữ bản sao cả kho. Mỗi tổ chỉ có một tấm thẻ ghi "phiếu mới nhất của tổ là số mấy". Chốt sổ thì viết phiếu mới và chuyển thẻ sang đó. Gộp việc của hai tổ thì viết một phiếu có hai phiếu trước.

Có tổ muốn sổ trông gọn, nên chép lại các phiếu của mình như thể viết sau phiếu mới nhất của tổ kia. Bản chép mang mã mới; phiếu cũ vẫn còn trong kho cho tới khi dọn. Ai đang cầm số phiếu cũ thì bỗng thấy hai lịch sử song song.

Git chạy đúng như vậy: hồ sơ là [[git-blob|blob]], danh sách là tree, phiếu là [[git-commit-object|commit]], mã là hash theo nội dung, tấm thẻ là [[git-ref|ref]] (nhánh), gộp hai tổ là [[git-merge|merge]], còn chép lại phiếu là [[git-rebase|rebase]].
