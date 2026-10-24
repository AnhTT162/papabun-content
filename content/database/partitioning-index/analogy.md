Kho lưu trữ hồ sơ của một bệnh viện không để mọi hồ sơ trong một phòng. Mỗi năm một phòng riêng: tìm hồ sơ khám tháng 3/2025 thì chỉ vào phòng 2025, và hết hạn lưu trữ thì dọn nguyên phòng 2015 trong một buổi, thay vì lục từng tủ rút từng tờ.

Mỗi phòng có **sổ tra cứu riêng** theo tên bệnh nhân. Nhân viên biết năm khám thì tra một cuốn sổ là xong. Nhưng khi bệnh nhân chỉ nhớ mã hồ sơ mà không nhớ năm, nhân viên phải mở sổ của từng phòng một. Bệnh viện có thể làm thêm một **sổ tổng ở quầy** cho mọi năm: tra một lần là ra, nhưng mỗi lần dọn một phòng thì phải gạch bỏ hàng nghìn dòng trong sổ tổng.

Chia một bảng lớn thành nhiều phần như vậy gọi là [[partitioning]]. Sổ của từng phòng là [[local-index|local index]], sổ tổng là [[global-index|global index]], và việc chỉ vào đúng phòng cần tìm là [[partition-pruning|partition pruning]].
