Một cửa hàng tạp hoá ghi sổ cái kho (sổ dày, mỗi mặt hàng một trang). Mỗi lần bán hàng mà lật sổ cái tìm đúng trang để sửa thì rất chậm, nhất là lúc đông khách.

Nên chủ cửa hàng làm khác: mỗi giao dịch được ghi ngay một dòng vào cuốn sổ nhật ký đặt trên quầy, chỉ việc viết nối tiếp ở dòng cuối. Ghi xong dòng nhật ký mới đưa hàng cho khách. Bảng tồn kho thì nhẩm trong đầu và trên tờ nháp. Cuối ngày, hoặc khi rảnh, mới chép các thay đổi vào sổ cái một lượt. Nếu mất tờ nháp (mất điện, quên), chỉ cần mở nhật ký từ lần chép gần nhất và chép lại.

Sổ cái là file dữ liệu chia thành các [[page]], tờ nháp là [[buffer-pool|buffer pool]] trong RAM, sổ nhật ký là [[wal|WAL]], "ghi xong mới đưa hàng" là [[fsync]] lúc commit, và lần chép vào sổ cái là [[checkpoint]].
