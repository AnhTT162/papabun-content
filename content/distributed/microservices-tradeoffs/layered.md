## Quick

[[microservices|Microservices]] là kiến trúc chia hệ thống thành các service **deploy độc lập**, mỗi service gắn với một năng lực nghiệp vụ (thường là một [[bounded-context|bounded context]]), **sở hữu dữ liệu riêng** và do một đội chủ quản. Lợi ích chính là về **tổ chức**: nhiều đội release độc lập, scale và cô lập lỗi theo từng phần. Cái giá là toàn bộ độ phức tạp của hệ phân tán. **Chọn microservices khi vấn đề nằm ở việc nhiều đội phải phối hợp, không phải vì muốn code "sạch" hơn**; còn lại, [[modular-monolith|modular monolith]] thường là điểm xuất phát tốt hơn.

## Interview

**Lợi ích thật**:
- Đội release độc lập, không chờ lịch deploy chung.
- Scale riêng phần nóng (tìm kiếm, thanh toán mùa sale).
- Lỗi một service (nếu thiết kế đúng) không kéo sập cả hệ thống.
- Mỗi service chọn công nghệ hợp với nó (đổi lại, nhiều ngôn ngữ và framework làm tăng chi phí vận hành và tuyển người).

**Cái giá**:
- Lời gọi qua mạng có thể chậm hay lỗi; cần timeout, retry, [[circuit-breaker|circuit breaker]] (bài Resilience patterns).
- Không có transaction chung: [[outbox]], [[saga]], consumer idempotent, đối soát (bài Nhất quán dữ liệu giữa các service).
- Vận hành: mỗi service cần pipeline, giám sát, tracing, on-call; debug một request đi qua sáu service.
- Test end-to-end khó; cần contract test giữa các service.

**Chia thế nào**: theo năng lực nghiệp vụ và bounded context, khớp với đội ([[conways-law|Conway's law]]); cách tìm ranh giới ở bài DDD chiến lược. Góc nhìn phân tán thêm một tiêu chí đo được: **khả dụng nhân theo chuỗi gọi đồng bộ**. Một request đi qua 5 service, mỗi service 99,9%, thì chỉ còn khoảng 99,5%, và p99 của cả request xấu hơn p99 của từng service. Một service nên làm được phần lớn việc của nó mà không gọi đồng bộ sang service khác.

**Khi nào không nên**: đội nhỏ, nghiệp vụ chưa rõ, chưa có nền tảng vận hành; khi đó dùng modular monolith (bài Modular monolith).

**Dấu hiệu chia sai** ([[distributed-monolith|distributed monolith]]): các service phải deploy cùng nhau, dùng chung database, một tính năng sửa năm service, chuỗi gọi đồng bộ dài.

## Deep

- **Điều kiện tiên quyết**: tạo môi trường và deploy tự động trong vài phút, giám sát và cảnh báo cơ bản, log và tracing tập trung, đội làm chủ được service từ code tới production. Thiếu những thứ này, mỗi service mới làm vận hành tệ hơn.
- **Nền tảng nội bộ**: khi số service tăng, một đội platform cung cấp "đường mòn" chung (template service, pipeline, thư viện quan sát, cấu hình bảo mật) để mỗi đội không tự xây lại. Không có nó, mỗi service một kiểu và chi phí vận hành tăng theo số service.
- **Kích thước service**: không có số dòng code đúng. Quá nhỏ (nano-service) thì mỗi thao tác nghiệp vụ là năm lời gọi mạng; quá lớn thì quay lại vấn đề phối hợp. Thước đo hữu ích: một đội làm chủ được, deploy được một mình, và phần lớn thay đổi nghiệp vụ chỉ chạm một service.
- **Thư viện dùng chung**: thư viện hạ tầng giúp đồng nhất; thư viện model nghiệp vụ là shared kernel mất kiểm soát (bài DDD chiến lược).
- **Hợp đồng API giữa các đội**: thay đổi phải tương thích ngược (thêm trường tuỳ chọn, không đổi nghĩa trường cũ); thay đổi phá vỡ cần version mới chạy song song và thời gian deprecate có hẹn, kèm metric xem consumer nào còn gọi bản cũ.
- **Bảo mật giữa các service**: mỗi service xác thực bên gọi (mTLS hoặc token của service), và truyền danh tính người dùng (JWT đã xác minh) để service phía sau tự kiểm tra quyền thay vì tin mạng nội bộ. Service mesh làm mTLS bằng [[sidecar|sidecar]] mà không sửa code; với vài service, thư viện và chứng chỉ do nền tảng cấp là đủ (bài API gateway, BFF & service mesh).
- **Đo xem tách có đúng không**: theo dõi chỉ số DORA theo từng đội (tần suất deploy, lead time, tỉ lệ thay đổi gây lỗi). Tách đúng thì các chỉ số này cải thiện; tách sai thì số deploy phải phối hợp giữa nhiều đội tăng lên.
- **[[consumer-driven-contract|Consumer-driven contract test]]**: consumer mô tả request và response mong đợi; provider chạy bộ kiểm tra đó trong CI của mình (Pact, Spring Cloud Contract). Thay cho phần lớn test end-to-end giòn và chậm.
- **Dữ liệu và báo cáo**: mỗi service sở hữu database của mình; báo cáo cần dữ liệu nhiều nơi thì đổ về kho dữ liệu phân tích qua event hoặc CDC, không join trực tiếp vào database của service khác.
- **Chi phí hạ tầng**: mỗi service có tối thiểu vài instance cho khả dụng, sidecar, connection pool riêng tới database. Hai mươi service nhỏ thường tốn hơn đáng kể so với một ứng dụng xử lý cùng tải.
- **Đi ngược lại là bình thường**: gộp các service luôn deploy cùng nhau hay gọi nhau cho mọi thao tác về một service hoặc một modular monolith là quyết định kiến trúc hợp lệ, không phải thất bại. Nhiều nhóm đã làm vậy và giảm cả chi phí lẫn độ trễ.
- **Tách từ monolith**: bắt đầu với phần có lý do đo được, dùng [[strangler-fig|strangler fig]]; quy trình chi tiết ở bài Modular monolith.
