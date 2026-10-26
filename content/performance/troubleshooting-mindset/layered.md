## Quick

Điều tra sự cố có hai mục tiêu tách bạch: **khôi phục dịch vụ trước ([[mitigation|cầm máu]]), tìm nguyên nhân gốc sau**. Trong lúc cầm máu vẫn phải giữ hiện trường (thread dump, heap dump, metric) trước khi restart. Tìm nguyên nhân bằng vòng lặp: khoanh [[blast-radius|phạm vi]] → hỏi "gần đây đổi gì" → đặt giả thuyết → kiểm chứng bằng bằng chứng, không bằng cảm giác.

## Interview

**1. Cầm máu trước**: người dùng không cần biết vì sao, họ cần dịch vụ chạy lại. Cách cầm máu theo thứ tự hay dùng:
- rollback bản deploy hoặc thay đổi cấu hình vừa làm;
- tắt tính năng bằng [[feature-flag|feature flag]];
- chuyển sang hệ dự phòng (provider khác, region khác);
- scale thêm (chỉ khi nút cổ chai nằm trong chính service mình, nếu không sẽ đẩy thêm tải vào dependency đang yếu), hoặc chặn bớt tải (load shedding).

Rollback rẻ và an toàn thì làm ngay khi thời điểm khớp, kể cả khi chưa chắc deploy là thủ phạm. Ngoại lệ: deploy có migration không đảo ngược được.

**2. Giữ hiện trường**: restart xoá mất trạng thái lỗi. Trước khi restart, chụp vài [[thread-dump|thread dump]] (cách nhau vài giây), [[heap-dump|heap dump]] nếu nghi bộ nhớ, ghi lại thời điểm và ảnh chụp dashboard. Có nhiều pod thì giữ một pod lỗi để điều tra (rút khỏi load balancer), restart các pod còn lại.

**3. Khoanh vùng**: lỗi ở endpoint nào, pod nào, zone nào, nhóm người dùng nào, bắt đầu lúc mấy giờ. So sánh cái hỏng với cái còn chạy: pod lỗi và pod khoẻ khác nhau ở đâu.

**4. Hỏi "đổi gì gần đây"**: phần lớn sự cố đến từ thay đổi: deploy, cấu hình, feature flag, hạ tầng, dữ liệu, lưu lượng, hoặc thay đổi ở phía dependency. Đặt dòng thời gian thay đổi cạnh thời điểm bắt đầu lỗi.

**5. Giả thuyết và bằng chứng**: mỗi giả thuyết phải chỉ ra được một số liệu xác nhận hoặc bác bỏ nó. Đổi một thứ mỗi lần. Thời điểm trùng nhau chưa phải bằng chứng nhân quả.

**Bẫy**: đọc log từ đầu không mục tiêu, bật debug log toàn hệ thống trên production, sửa lỗi thẳng trên production khi chưa hiểu, im lặng không báo cho ai. Sự cố lớn cần một người điều phối và cập nhật trạng thái đều đặn (vai trò trong sự cố: bài Alerting, on-call & postmortem).

## Deep

- **Thứ tự chỉ số khi mới vào**: [[red-method|RED]] của service bị báo (bài Phương pháp phân tích hiệu năng) để biết triệu chứng; rồi RED của từng dependency mà nó gọi; rồi USE của tài nguyên. Lỗi xuất hiện đồng loạt ở nhiều service thường do một dependency chung (database, DNS, mạng, provider).
- **Lỗi ở người gọi hay người bị gọi**: service A báo timeout tới B. Xem metric phía B: B cũng thấy chậm thì lỗi ở B hoặc sau B; B thấy nhanh thì thời gian mất ở giữa (mạng, LB, connection pool của A, GC của A).
- **Thu bằng chứng JVM nhanh**: `jcmd <pid> Thread.print` cho thread dump; `jcmd <pid> GC.heap_dump /tmp/heap.hprof` cho heap dump (dừng ứng dụng vài giây tới vài chục giây với heap lớn, và file có thể chứa dữ liệu cá nhân). Chi tiết ở bài Bộ công cụ chẩn đoán JVM; ca CPU 100% ở bài Ứng dụng Java CPU 100%.
- **Bằng chứng trong Kubernetes**: `kubectl logs --previous` cho log của container trước khi restart, `kubectl describe pod` cho lý do dừng (`OOMKilled`, exit code). Bật sẵn `-XX:+HeapDumpOnOutOfMemoryError` và JFR chạy liên tục, vì lúc sự cố xảy ra thường đã quá muộn để bật. `jcmd` cần chạy trong container (image distroless thường không có), file dump nằm trong filesystem của container nên phải `kubectl cp` ra trước khi pod bị xoá. `GC.heap_dump` mặc định chạy full GC và chỉ giữ object còn sống. Đừng mở `/actuator/heapdump` ra ngoài: ai gọi được là tải được toàn bộ bộ nhớ.
- **Một phần pod lỗi**: có thể do pod nằm trên node xấu, zone khác, phiên bản khác (deploy dở), cache cục bộ khác nhau, hoặc nhận request "độc" của một khách hàng. Gom lỗi theo `pod`, `node`, `zone`, `version` trước khi kết luận.
- **Thu hẹp bằng phân đôi**: nhiều thay đổi cùng lên một bản thì rollback từng nửa, hoặc dùng `git bisect` với test tái hiện. Tương tự với cấu hình: bật/tắt từng flag.
- **Tái hiện**: tái hiện được lỗi ở môi trường khác là nửa chặng đường. Không tái hiện được thì thêm metric và log có mục tiêu cho lần sau, thay vì đoán.
- **Ghi dòng thời gian ngay lúc xảy ra**: mỗi hành động kèm giờ phút (14:31 rollback v3.8, lỗi không giảm). Dòng thời gian là nguyên liệu cho postmortem và giúp người mới vào không làm lại việc đã làm.
- **[[runbook|Runbook]]**: sự cố quen thuộc (provider chậm, đầy đĩa, replica lag) nên có runbook ghi sẵn cách cầm máu và lệnh cần chạy; lúc 3 giờ sáng không ai nghĩ tốt.
- **Sau sự cố**: [[postmortem]] không đổ lỗi tìm vì sao hệ thống cho phép lỗi xảy ra và vì sao phát hiện muộn, kèm hành động có người chịu trách nhiệm và hạn (bài Alerting, on-call & postmortem). "5 why" dễ dừng ở một nguyên nhân duy nhất; sự cố thật thường có nhiều yếu tố góp phần.
- **Đo chất lượng xử lý**: thời gian phát hiện (từ lúc lỗi tới lúc có alert) và thời gian khôi phục thường quan trọng hơn thời gian tìm nguyên nhân gốc. Muốn giảm, cần alert theo triệu chứng người dùng và đường rollback nhanh.
