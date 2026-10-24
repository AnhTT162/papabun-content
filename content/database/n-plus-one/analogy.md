Một shipper nhận danh sách 50 đơn cần giao. Thay vì lấy hết hàng ở kho một lần, anh ta cầm danh sách đi giao đơn thứ nhất, quay về kho lấy hàng đơn thứ hai, rồi lại quay về lấy hàng đơn thứ ba. Từng chuyến đều nhanh, nhưng 50 chuyến đi về làm cả ngày trôi qua. Kho không chậm, đường không tắc; cái sai là số chuyến.

Ứng dụng dùng [[orm|ORM]] cũng hay làm vậy. Một query lấy 50 đơn hàng, rồi code duyệt từng đơn và gọi `order.getCustomer().getName()`. Mỗi lần gọi như thế, ORM lặng lẽ chạy thêm một query để lấy khách hàng của đơn đó. Tổng cộng là 1 + 50 query thay vì 1 hoặc 2.

Đó là lỗi [[n-plus-one|N+1 query]]. Nó sinh ra từ [[lazy-loading|lazy loading]]: dữ liệu liên quan chỉ được tải khi code chạm tới nó. Từng query đều nhanh nên slow query log không bắt được, chỉ có số lượng query mới tố cáo nó.
