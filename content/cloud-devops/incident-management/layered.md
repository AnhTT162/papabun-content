## Quick

Hệ thống phát hiện, phản ứng và học từ sự cố gồm ba phần: **alert gọi người chỉ khi người dùng đang hoặc sắp bị ảnh hưởng và có việc cần làm ngay**; khi có sự cố thì một [[incident-commander|incident commander]] điều phối, ưu tiên [[mitigation|cầm máu]] trước khi tìm nguyên nhân; sau sự cố có [[postmortem|postmortem]] không đổ lỗi với việc phòng ngừa có người chịu trách nhiệm. Đo bằng thời gian phát hiện và thời gian khôi phục, không bằng số người bị khiển trách.

## Interview

Tôi thiết kế alert theo triệu chứng người dùng thấy, gắn với [[slo|SLO]]: tỉ lệ request lỗi, latency vượt ngưỡng, hàng đợi trễ quá hạn. Cách tính theo [[burn-rate|burn rate]] nhiều cửa sổ (bài Metrics, tracing & SLO) cho cân bằng giữa phát hiện nhanh và ít báo động giả. CPU cao, pod restart, disk 80% là nguyên nhân có thể có: để trên dashboard hoặc tạo ticket, không gọi người lúc 3 giờ sáng. Mỗi alert gọi người phải có [[runbook|runbook]] và phải dẫn tới một hành động; alert mà người trực thường bỏ qua thì sửa hoặc xoá, vì [[alert-fatigue|alert fatigue]] làm alert thật cũng bị bỏ qua.

[[on-call|On-call]] cần người trực chính, người trực phụ và đường escalation rõ ràng. Theo sách SRE của Google, tối đa khoảng hai sự cố mỗi ca 12 giờ, vì mỗi sự cố cùng việc theo sau tốn khoảng 6 giờ; nhiều hơn là dấu hiệu hệ thống cần sửa, không phải cần người chịu đựng.

Khi có sự cố, việc đầu tiên là phân [[incident-severity|mức độ]] và vai trò: incident commander điều phối và ra quyết định, người xử lý thao tác trên hệ thống, người liên lạc cập nhật stakeholder và trang trạng thái theo nhịp cố định. Ưu tiên cầm máu: rollback bản vừa deploy, tắt feature flag, chuyển sang region hay hệ dự phòng, bớt tải. Hỏi "cái gì vừa thay đổi" trước, vì phần lớn sự cố đến từ thay đổi.

Sau sự cố, postmortem trả lời vì sao hệ thống cho phép lỗi xảy ra, vì sao phát hiện muộn, vì sao khôi phục chậm; không hỏi ai có lỗi. Kết quả là vài việc phòng ngừa cụ thể, có người phụ trách và hạn, được theo dõi tới khi xong. Postmortem không có việc nào được làm xong thì chỉ là tài liệu.

Bẫy hay gặp: alert theo nguyên nhân, quá nhiều kênh không ai đọc, mọi người cùng nhảy vào debug mà không ai điều phối, và postmortem kết luận "lỗi do con người".

## Deep

- **Burn rate 14,4 là gì**: tốc độ đốt 2% [[error-budget|error budget]] 30 ngày trong một giờ; ngưỡng và cửa sổ đầy đủ ở bài Metrics, tracing & SLO.
- **Chất lượng alert** (SRE Workbook): precision (tỉ lệ alert ứng với sự kiện thật), recall (tỉ lệ sự kiện thật được báo), thời gian phát hiện, thời gian alert tự tắt sau khi hết lỗi. Cửa sổ ngắn thì nhanh nhưng nhiễu, cửa sổ dài thì chắc nhưng chậm; burn rate nhiều cửa sổ là cách giữ cả bốn ở mức chấp nhận được.
- **Gọi người hay tạo ticket**:
  - Gọi người: người dùng đang bị ảnh hưởng hoặc budget đang cháy nhanh, và cần hành động trong vài phút.
  - Ticket: cần xử lý trong ngày làm việc (budget cháy chậm, chứng chỉ hết hạn sau 14 ngày, đĩa sẽ đầy trong 5 ngày).
  - Dashboard: mọi thứ còn lại. Không gửi alert vào kênh chat mà không ai có trách nhiệm đọc.
- **Giảm nhiễu bằng công cụ**: gom alert cùng nguyên nhân (grouping), bỏ trùng (dedup), ức chế alert phụ khi alert gốc đang bật (inhibition, ví dụ cluster sập thì không gửi thêm từng service), tắt có thời hạn khi bảo trì (silence). Alertmanager và các dịch vụ on-call đều có các cơ chế này.
- **Đo alert**: số lần gọi mỗi ca, tỉ lệ alert dẫn tới hành động, tỉ lệ alert tự tắt trước khi có người nhìn. Họp định kỳ xem lại các alert ồn nhất và sửa nguồn gốc.
- **On-call bền vững** (sách SRE của Google):
  - Kỹ sư dành tối đa 25% thời gian cho on-call; với trực chính và trực phụ theo tuần, một đội một địa điểm cần ít nhất 8 người, đội hai địa điểm mỗi nơi ít nhất 6.
  - Thời gian phản hồi thường 5 phút cho dịch vụ trực tiếp với người dùng, 30 phút cho dịch vụ ít gấp hơn.
  - Đội phát triển trực cùng hoặc trực cho service của mình (you build it, you run it) để người viết code cảm nhận được chi phí vận hành.
  - Bàn giao ca có ghi chú: sự cố còn mở, thay đổi rủi ro sắp tới.
- **Mức độ sự cố**: định nghĩa theo ảnh hưởng, không theo cảm giác. Ví dụ SEV1 là chức năng chính ngừng với nhiều người dùng hoặc mất dữ liệu, SEV2 là suy giảm rõ hay một phần người dùng không dùng được, SEV3 là ảnh hưởng nhỏ có cách vòng. Mức độ quyết định ai được gọi, nhịp cập nhật, có cần postmortem hay không. Nâng mức sớm rồi hạ xuống rẻ hơn để sự cố lớn chạy theo quy trình của sự cố nhỏ.
- **Vai trò khi có sự cố** (theo chương Managing Incidents, dựa trên Incident Command System):
  - Incident commander: giữ bức tranh chung, giao việc, quyết định; thường không tự gõ lệnh.
  - Operations: người duy nhất thao tác lên hệ thống, tránh nhiều người cùng đổi.
  - Communications: cập nhật stakeholder, trang trạng thái, định kỳ (ví dụ mỗi 30 phút với SEV1) kể cả khi chưa có gì mới.
  - Planning: theo dõi việc dài hạn, ticket, bàn giao, những gì đã đổi khỏi trạng thái bình thường để sau này hoàn tác.
  - Đội nhỏ thì một người kiêm nhiều vai, nhưng vai incident commander và người gõ lệnh nên tách nhau.
- **Cầm máu trước**: mitigation khôi phục dịch vụ khi chưa biết nguyên nhân: rollback, tắt flag, chuyển traffic, scale, chặn khách hàng gây tải. Thu thập bằng chứng nhanh trước khi rollback xoá dấu vết (thread dump, heap dump, log). Cách điều tra có hệ thống và ghi dòng thời gian ở bài Quy trình điều tra sự cố.
- **Postmortem không đổ lỗi**:
  - Khi nào viết: theo ngưỡng khách quan đặt trước (sự cố gọi người, mất dữ liệu, cần can thiệp tay, vượt ngưỡng budget; chính sách error budget ở bài Độ tin cậy & SRE) hoặc khi có người đề nghị.
  - Nội dung: tóm tắt, ảnh hưởng (bao nhiêu người, bao lâu, bao nhiêu budget), dòng thời gian, nguyên nhân trực tiếp và các yếu tố góp phần, điều đã làm tốt, điều may mắn, việc phòng ngừa (phát hiện sớm hơn, giảm phạm vi ảnh hưởng, khôi phục nhanh hơn, ngăn tái diễn).
  - "Lỗi do con người" không phải kết luận: hỏi vì sao hệ thống cho phép một lệnh sai chạy trên prod không có xác nhận, vì sao không có kiểm tra tự động. Người viết lệnh sai thường là người hiểu chuyện nhất để sửa hệ thống.
  - "5 why" dễ dừng ở một chuỗi nguyên nhân; sự cố thật thường là nhiều yếu tố gặp nhau.
- **Đo**: thời gian phát hiện (từ lúc người dùng bị ảnh hưởng tới lúc có alert), thời gian khôi phục, số sự cố tái diễn cùng nguyên nhân, tỉ lệ việc phòng ngừa hoàn thành đúng hạn. MTTR trung bình dễ bị một sự cố dài kéo lệch; xem phân phối hoặc từng sự cố. DORA đo riêng thời gian khôi phục sau deploy lỗi (bài CI/CD pipeline).
- **Sự cố bảo mật** đi theo quy trình riêng có pháp chế và bảo mật tham gia, giữ bằng chứng, giới hạn người biết (bài Kiến trúc bảo mật).
