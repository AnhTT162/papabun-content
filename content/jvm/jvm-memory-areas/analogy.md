Một văn phòng kế toán có **kho hồ sơ chung**: ai cũng cất và lấy hồ sơ ở đó, định kỳ có người đi dọn hồ sơ không còn ai cần. Mỗi nhân viên lại có **một bàn riêng**: việc đang làm dở xếp chồng lên nhau, làm xong việc nào thì dọn việc đó khỏi bàn, không cần ai dọn hộ.

Ngoài ra còn **sổ quy trình** mô tả từng loại hồ sơ phải xử lý ra sao, **tờ ghi nhớ** cho các thao tác làm nhiều tới mức thuộc lòng, và một **kho thuê ngoài** để chứa hàng cồng kềnh mà kho chung không tiện giữ.

Mỗi chỗ đầy theo một kiểu khác nhau. Kho chung đầy thì không cất thêm được hồ sơ. Một nhân viên chồng việc quá cao trên bàn thì đổ, nhưng chỉ bàn đó đổ. Sổ quy trình phình mãi nếu cứ in thêm loại hồ sơ mới mà không bỏ loại cũ. Xây kho chung to hơn không giúp gì khi cái đầy là kho thuê ngoài.

Trong [[jvm|JVM]], kho chung là [[java-heap|heap]], bàn riêng là stack của mỗi thread với từng [[stack-frame|frame]], sổ quy trình là [[metaspace|metaspace]], tờ ghi nhớ là [[code-cache|code cache]], kho thuê ngoài là [[direct-buffer|direct memory]].
