Đặt một tour Đà Lạt cho cả nhà: vé máy bay của hãng bay, phòng của khách sạn, xe đưa đón của nhà xe. Ba công ty, ba hệ thống, không có nút "đặt tất cả hoặc không đặt gì". Đại lý đặt từng thứ một. Máy bay và khách sạn xong, nhà xe báo hết xe: đại lý không thể "rollback", mà phải gọi huỷ phòng khách sạn (có thể mất phí) và huỷ vé máy bay, tức là làm thêm các bước **bù trừ**.

Đại lý cẩn thận còn làm hai việc. Mỗi lần đặt xong một thứ, họ ghi ngay vào sổ "việc cần báo khách" trước khi gọi điện, để lỡ mất điện giữa chừng thì sáng mai vẫn nhớ phải báo. Và cuối tuần họ ngồi đối chiếu sổ của mình với hoá đơn của hãng bay và khách sạn, tìm chỗ lệch: phòng đã huỷ mà vẫn bị tính tiền, vé có trên hệ thống hãng mà không có trong sổ.

Đại lý vụng về thì gọi điện báo khách "đã đặt xong" trước, rồi mới ghi sổ; tối đó máy tính hỏng, sổ không có gì, nhưng khách đã nhận tin.

Mỗi service với database riêng giống mỗi công ty: không có transaction chung, chỉ có [[eventual-consistency|eventual consistency]]. Ghi sổ rồi mới gọi là [[outbox|outbox]], gọi trước rồi mới ghi là lỗi [[dual-write|dual write]], chuỗi bước kèm bù trừ là [[saga|saga]], và đối chiếu cuối tuần là [[reconciliation|reconciliation]].
