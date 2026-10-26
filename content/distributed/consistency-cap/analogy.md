Một hiệu vàng có hai chi nhánh, mỗi chi nhánh giữ một cuốn sổ ghi số vàng khách gửi. Cuối mỗi giao dịch, nhân viên gọi điện cho chi nhánh kia để cùng ghi. Một hôm đường điện thoại giữa hai nơi bị đứt. Một khách gửi 5 chỉ ở chi nhánh A, rồi chạy sang chi nhánh B đòi rút 5 chỉ.

Chi nhánh B có hai lựa chọn. Một là từ chối phục vụ cho tới khi liên lạc lại được với A: không sai sổ, nhưng khách phải chờ. Hai là phục vụ theo cuốn sổ đang có: khách được việc ngay, nhưng sổ B không có giao dịch 5 chỉ vừa gửi ở A, và hai cuốn sổ sẽ lệch nhau cho tới khi gọi lại được để đối chiếu.

Ngay cả ngày bình thường, điện thoại vẫn liên lạc được, hiệu vàng cũng phải chọn: chờ chi nhánh kia ghi xong mới trả lời khách (chậm hơn nhưng hai sổ luôn khớp), hay ghi sổ mình rồi trả lời ngay và báo chi nhánh kia sau (nhanh hơn nhưng có lúc lệch).

Lựa chọn lúc mất liên lạc là nội dung của [[cap-theorem|định lý CAP]]; lựa chọn giữa chậm và lệch trong ngày bình thường là phần bổ sung của [[pacelc|PACELC]]; còn "hai sổ luôn như một" là [[linearizability|linearizability]], mức nhất quán mạnh nhất.
