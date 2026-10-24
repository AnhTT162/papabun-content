Một chi nhánh ngân hàng có 8 quầy giao dịch. Khách tới thì bốc số và ngồi chờ; quầy nào xong khách trước thì gọi số tiếp theo. Không ai mở thêm quầy mỗi khi có khách mới, vì dựng một quầy (bàn, máy tính, nhân viên được đào tạo) tốn kém hơn nhiều so với một lượt giao dịch.

Thêm quầy chỉ có ích tới một mức. Phía sau chỉ có hai nhân viên kho quỹ và một máy đếm tiền: mở 30 quầy thì 30 giao dịch viên cùng xếp hàng chờ kho quỹ, mỗi lượt còn chậm hơn trước. Điều làm cả chi nhánh tắc thường không phải số quầy, mà là khách ngồi lì ở quầy để gọi điện cho người nhà hỏi số tài khoản, trong khi hàng chờ phía sau dài ra.

Mỗi quầy là một connection tới database, số quầy là `maximumPoolSize`, ghế chờ là thời gian chờ `connectionTimeout`, kho quỹ là CPU và đĩa của database, còn người ngồi lì gọi điện là code gọi API bên ngoài khi đang giữ connection. Đó chính là [[connection-pool|connection pool]].
