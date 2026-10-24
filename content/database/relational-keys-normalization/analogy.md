Một lớp học quản lý học sinh bằng một cuốn sổ duy nhất. Mỗi lần học sinh nộp bài, cô giáo chép lại cả họ tên, ngày sinh, địa chỉ và số điện thoại phụ huynh. Đến khi phụ huynh đổi số điện thoại, cô phải sửa ở 40 trang, sót một trang là sổ có hai số khác nhau cho cùng một người. Hai bạn trùng tên "Nguyễn Văn An" thì không biết bài nào của ai.

Cách làm đúng là tách thành **sổ học sinh** (mỗi bạn một dòng, có **mã học sinh** không bao giờ trùng) và **sổ nộp bài** (chỉ ghi mã học sinh, tên bài, điểm). Đổi số điện thoại thì sửa đúng một chỗ, và sổ nộp bài không thể ghi một mã học sinh không tồn tại.

Đó là [[normalization|chuẩn hoá]]: mỗi sự thật chỉ lưu ở một nơi. Mã học sinh là [[primary-key|primary key]], còn mã học sinh trong sổ nộp bài là [[foreign-key|foreign key]]. Các quy tắc như "không trùng", "không bỏ trống", "điểm từ 0 đến 10" là [[constraint|ràng buộc]] do chính database canh giữ.
