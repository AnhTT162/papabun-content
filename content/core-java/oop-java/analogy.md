Tổng đài giao hàng chỉ nói một câu với mọi tài xế: "Giao đơn này". Tài xế xe máy luồn hẻm, tài xế xe tải đi đường lớn, tài xế drone bay thẳng. Tổng đài không cần biết ai lái gì; **cách giao do người nhận lệnh quyết định**, lúc nhận lệnh.

Nhưng tổng đài chọn **câu lệnh nào** dựa trên tờ danh sách đang cầm. Nếu danh sách chỉ ghi "tài xế", tổng đài chỉ dùng được các lệnh chung cho mọi tài xế, dù người thật là tài xế drone.

Trong Java, việc chọn cài đặt lúc chạy theo kiểu thật của object là [[dynamic-dispatch]], nền của [[polymorphism|đa hình]]. Còn việc chọn chữ ký method nào (overload) thì compiler làm sẵn theo kiểu khai báo của biến.
