Một văn phòng có **bảng trắng chung** ghi các con số quan trọng. Mỗi nhân viên chép số từ bảng vào **sổ tay riêng** rồi làm việc trên sổ cho nhanh. Ghi gì mới thì ghi vào sổ trước, lúc nào tiện mới chép lên bảng. Vì thế chị kế toán sửa số trên sổ của mình, còn anh kho hàng vẫn nhìn con số cũ trong sổ của anh.

Phòng họp có **một chìa khoá**. Quy định: ai trả chìa khoá phải chép hết những gì mới ghi trong sổ lên bảng; ai nhận chìa khoá phải bỏ những gì đã chép trong sổ và đọc lại bảng. Người sau luôn thấy việc người trước đã làm, và trong phòng họp không ai chen vào được.

Có vài con số được dán thẳng lên bảng với nhãn **"không chép vào sổ"**: ai cũng phải đọc và ghi trực tiếp trên bảng. Nhưng việc "đọc số, cộng thêm 1, ghi lại" vẫn là ba động tác, và hai người vẫn có thể cùng đọc số 5 rồi cùng ghi 6.

Trong Java, quy tắc sổ tay và bảng là [[jmm|Java Memory Model]], chuyện thấy hay không thấy số mới là [[visibility]], chìa khoá phòng họp là `synchronized`, nhãn "không chép vào sổ" là `volatile`, còn ba động tác bị chen giữa là thiếu [[atomicity]].
