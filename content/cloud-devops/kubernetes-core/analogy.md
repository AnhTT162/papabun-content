Một chuỗi bếp trung tâm nấu cơm hộp cho văn phòng. Giám đốc không chỉ đạo từng đầu bếp; chị chỉ ghi lên bảng: "ca trưa cần 3 tổ nấu món gà, công thức bản 7". Mỗi khi bảng được sửa hay ngoài bếp có chuyện, quản lý ca so lại bảng với thực tế: thiếu một tổ thì gọi thêm, dư thì cho về, công thức đổi sang bản 8 thì thay dần từng tổ để bếp không lúc nào dừng.

Điều phối viên xếp mỗi tổ vào một gian bếp còn đủ chỗ và đủ bếp. Ở mỗi gian có một trưởng gian nhận lệnh và trông các tổ trong gian mình. Mỗi tổ gồm vài người làm chung một bàn, dùng chung một bộ dao thớt: họ vào ca và tan ca cùng nhau.

Khách văn phòng không gọi thẳng cho tổ nào, vì tổ có thể đổi người, đổi gian bất cứ lúc nào. Họ gọi một số tổng đài cố định "món gà", tổng đài chuyển tới tổ đang sẵn sàng. Lễ tân ở cổng xem đơn ghi "món gà" hay "món chay" để chuyển đúng tổng đài.

Kubernetes chạy đúng như vậy: tấm bảng là API server lưu trạng thái mong muốn, quản lý ca là controller của [[kubernetes-deployment|Deployment]], điều phối viên là scheduler, trưởng gian là [[kubelet|kubelet]], tổ nấu là [[kubernetes-pod|Pod]], số tổng đài là [[kubernetes-service|Service]], lễ tân ở cổng là [[ingress|Ingress]].
