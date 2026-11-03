Một khách sạn chia toà nhà thành nhiều phòng. Mọi phòng dùng chung móng, thang máy, đường điện nước của toà nhà, nhưng mỗi phòng có cửa riêng, số phòng riêng, tủ lạnh nhỏ riêng. Khách trong phòng thấy như căn hộ của mình: không thấy phòng bên, không biết hành lang có ai. Đồng hồ điện mỗi phòng có cầu dao: dùng quá định mức là ngắt.

Phòng được dọn theo một bộ chuẩn: lớp nội thất cố định của toà, lớp đồ của hạng phòng, lớp đồ riêng của gói khách đặt. Các lớp này in sẵn trong danh mục, phòng nào cùng hạng thì dùng lại. Khách được bày biện thêm trong thời gian ở, nhưng trả phòng là dọn sạch, phòng sau lại bắt đầu từ bộ chuẩn.

Phòng khách sạn khác một căn nhà riêng: nhà riêng có móng và đường điện riêng, còn phòng dùng chung hạ tầng của toà, nên toà có lỗi kết cấu thì mọi phòng cùng chịu.

Container chạy đúng như vậy: toà nhà là kernel của máy host, cửa riêng và số phòng riêng là [[linux-namespace|namespace]], cầu dao là [[cgroup|cgroup]], bộ chuẩn nhiều lớp là [[container-image|image]] gồm các [[image-layer|layer]], đồ bày thêm khi ở là lớp ghi được của container, còn nhà riêng là máy ảo.
