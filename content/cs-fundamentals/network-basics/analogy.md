Gửi một bưu kiện từ văn phòng ở tầng 12 một toà nhà tới khách hàng ở tỉnh khác. Bưu kiện cần **địa chỉ toà nhà** (số nhà, phường, quận) và **số phòng** của người nhận. Địa chỉ cho bưu tá biết đưa tới toà nào, số phòng cho lễ tân biết giao cho ai trong toà.

Mã bưu chính gom cả một khu vào một con số: thấy mã của quận mình thì bưu tá tự giao, mã khác thì gửi lên bưu cục trung tâm. Toà nhà có quầy thư chung: thư gửi đi đều ghi địa chỉ của **quầy**, không ghi số phòng riêng, và quầy ghi sổ để thư trả lời quay về đúng phòng. Bảo vệ ở cổng chỉ cho bưu kiện vào các phòng nằm trong danh sách được phép.

Mạng máy tính chạy đúng như vậy: địa chỉ toà nhà là [[ip-address|địa chỉ IP]], số phòng là [[network-port|port]], mã bưu chính của một khu là [[cidr|CIDR]] của một [[subnet]], bưu cục trung tâm là router với [[route-table|route table]], quầy thư chung là [[nat|NAT]], bảo vệ ở cổng là firewall hay [[security-group|security group]].
