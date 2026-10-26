Một nhà hàng có ba khu. Nhân viên phục vụ nhận order và đưa món ra bàn. Bếp quyết định nấu thế nào: món này cần những gì, hết nguyên liệu thì báo đổi món. Thủ kho giữ nguyên liệu và chỉ biết nhập, xuất, kiểm kê.

Phục vụ không tự vào kho lấy thịt, và thủ kho không ra bàn tư vấn món. Khách cầm **thực đơn** có tên món và giá; bếp nhận **phiếu bếp** ghi số bàn và ghi chú "ít cay"; kho dùng **phiếu xuất** có mã lô và hạn dùng. Cùng là "một đĩa bò lúc lắc" nhưng mỗi khu ghi thông tin mình cần. Đưa phiếu xuất kho ra cho khách thì khách thấy cả giá nhập, còn để khách tự ghi vào phiếu bếp thì khách tự ghi luôn "miễn phí".

Nhà hàng nhỏ xếp người theo khu: tất cả phục vụ một chỗ, tất cả đầu bếp một chỗ. Nhà hàng lớn có nhiều quầy (phở, nướng, tráng miệng), mỗi quầy có đủ người nhận order, người nấu và kho riêng, và đổi thực đơn quầy phở không làm phiền quầy nướng.

Đó là [[layered-architecture|kiến trúc phân lớp]]: controller, service, repository, với [[dto|DTO]] riêng cho từng ranh giới. Xếp theo khu là package-by-layer, còn xếp theo quầy là [[package-by-feature|package-by-feature]].
