## Quick

[[rolling-deployment|Rolling]] thay dần từng instance, [[blue-green-deployment|blue-green]] dựng cả bản mới rồi chuyển traffic một lần, [[canary-release|canary]] cho một phần nhỏ traffic vào bản mới, so số liệu rồi tăng dần. **Chiến lược nào cũng chỉ rollback được khi database, API và message vẫn tương thích với bản cũ**; rolling và canary luôn có giai đoạn hai phiên bản cùng phục vụ; blue-green và recreate không chồng ở tầng phục vụ nhưng vẫn dùng chung dữ liệu.

## Interview

Ba chiến lược khác nhau ở chỗ hai phiên bản cùng tồn tại thế nào.

Rolling update là mặc định của Kubernetes và ECS: thay từng nhóm instance, không tốn thêm nhiều tài nguyên, nhưng rollout lâu có hai phiên bản phục vụ xen kẽ, và rollback cũng là một lần rolling ngược lại, mất vài phút.

Blue-green dựng toàn bộ bản mới (green) bên cạnh bản đang chạy (blue), kiểm tra trên green, rồi chuyển load balancer một lần. Rollback là chuyển lại, tính bằng giây. Giá: gấp đôi tài nguyên trong lúc chuyển, và database thường dùng chung nên vẫn phải tương thích hai phiên bản; chuyển một lần nghĩa là mọi người dùng gặp lỗi cùng lúc nếu green có vấn đề mà kiểm tra không bắt được.

Canary cho 1–5% traffic vào bản mới, so tỉ lệ lỗi, latency, chỉ số nghiệp vụ với bản cũ trong cùng khoảng thời gian, đạt thì tăng lên 25%, 50%, 100%, trượt thì quay về. Đây là cách tôi chọn cho service quan trọng: phạm vi ảnh hưởng nhỏ, phát hiện cả lỗi chỉ lộ ra với traffic thật. Cần tự động hoá phân tích (Argo Rollouts, Flagger, CodeDeploy) và đủ traffic để số liệu có nghĩa.

Phần khó nhất không nằm ở chiến lược mà ở tương thích. Schema đổi theo [[expand-contract|expand/contract]]: thêm trước, dùng sau, xoá ở bản sau nữa, để bản cũ vẫn chạy được trên schema mới. API chỉ thêm trường, không đổi nghĩa trường cũ; client đọc theo kiểu [[tolerant-reader|tolerant reader]]. Message trên Kafka hay queue phải đọc được bởi cả consumer cũ và mới, vì message ghi lúc canary sẽ được bản cũ đọc nếu rollback.

Bẫy hay gặp: rollback code sau khi migration đã xoá cột; canary 5% nhưng mỗi request của cùng người dùng rơi vào hai phiên bản khác nhau; và phân tích canary trên quá ít request nên "đạt" chỉ vì may.

## Deep

- **Rolling update chi tiết**: Kubernetes theo `maxSurge`/`maxUnavailable` (bài Kubernetes cơ bản), chỉ tiến khi pod mới Ready; readiness probe sai thì rolling update đẩy bản lỗi đi hết. ECS có `minimumHealthyPercent`/`maximumPercent` và circuit breaker tự rollback khi task không ổn định; Kubernetes thì không tự rollback, quá `progressDeadlineSeconds` chỉ đánh dấu `ProgressDeadlineExceeded`.
- **Recreate**: tắt hết bản cũ rồi mới chạy bản mới; có downtime nhưng không bao giờ có hai phiên bản cùng lúc. Hợp khi không thể tương thích (job đơn lẻ, ứng dụng nội bộ có cửa sổ bảo trì).
- **Blue-green trên AWS và Kubernetes**: chuyển listener của ALB giữa hai target group, hoặc đổi selector của Service sang Deployment mới; CodeDeploy làm việc này cho ECS kèm bước kiểm thử trước khi chuyển. Chuyển bằng DNS chậm và không đều vì TTL và cache của client (bài Route 53, CloudFront & lưu trữ trên AWS). Giữ blue một thời gian rồi mới xoá. Bẫy: consumer Kafka hay job định kỳ của green chạy ngay khi green lên, trước khi chuyển traffic, nên xử lý song song với blue; pool kết nối database gấp đôi; green có cache nguội.
- **Canary**:
  - Chia traffic bằng trọng số target group của ALB, Ingress/Gateway API hỗ trợ trọng số, hoặc service mesh. Chia theo số pod (1 pod mới trên 20) thô: cân bằng tải theo kết nối (keep-alive, HTTP/2, gRPC) làm tỉ lệ request lệch so với tỉ lệ pod.
  - Phân tích so canary với baseline cùng thời điểm, không so với hôm qua (Kayenta khuyên deploy một bản cũ mới tinh làm baseline, để JIT và cache nguội của canary không tạo chênh lệch giả): lưu lượng, cache, tải nền khác nhau theo giờ. Cần ngưỡng thống kê và số request tối thiểu; Kayenta, Argo Rollouts AnalysisTemplate, Flagger làm việc này theo metric Prometheus hay CloudWatch.
  - Dính phiên bản theo người dùng (header, cookie, hash user id) để một người không nhảy qua lại giữa hai phiên bản trong cùng phiên làm việc.
  - Lỗi theo thời gian (rò rỉ bộ nhớ, cache đầy dần, job đêm) có thể không lộ ra trong 30 phút canary; giữ bản cũ đủ lâu sau khi promote để quay lại nhanh.
- **Shadow traffic**: nhân bản request thật sang bản mới nhưng bỏ response; kiểm hiệu năng và lỗi mà người dùng không bị ảnh hưởng. Chỉ an toàn với request không có hiệu ứng phụ, hoặc khi bản shadow ghi vào chỗ riêng.
- **Canary khác A/B test**: canary trả lời "bản mới có hỏng không" theo chỉ số kỹ thuật; A/B test trả lời "tính năng nào tốt hơn" theo chỉ số sản phẩm, cần thời gian và cỡ mẫu khác hẳn. [[feature-flag|Feature flag]] phục vụ cả hai (bài CI/CD pipeline).
- **Tương thích khi deploy**: hai chiều đều cần: bản mới đọc được dữ liệu cũ (backward), và bản cũ đọc được dữ liệu bản mới đã ghi (forward), vế sau là điều kiện để rollback.
  - Database: thay đổi phá vỡ (đổi tên cột, đổi kiểu, thêm `NOT NULL` không có mặc định) tách thành nhiều bản theo expand/contract; mỗi migration phải chạy được với code đang chạy và code sắp lên (bài Migration không downtime).
  - API: thêm trường tuỳ chọn, endpoint mới; không xoá hay đổi nghĩa trường trong cùng bản; bản cũ của client mobile có thể sống nhiều tháng (bài Thiết kế REST API).
  - Message và event: schema tương thích hai chiều trong cửa sổ deploy; consumer bỏ qua trường lạ (bài Thiết kế event & schema evolution).
  - Cache và session: bản mới ghi định dạng mới vào Redis thì bản cũ đọc lỗi khi rollback; thêm phiên bản vào key hoặc đọc được cả hai định dạng.
- **Rollback hay sửa tiến**: rollback khi bản trước đã biết là tốt và mọi thứ vẫn tương thích; sửa tiến khi rollback nguy hiểm hơn (dữ liệu đã chuyển định dạng, migration không đảo được). Quyết định trước khi deploy, ghi trong kế hoạch phát hành, không quyết lúc đang cháy.
- **Chọn chiến lược**:
  - Service nội bộ ít rủi ro: rolling với readiness probe đúng và tự rollback.
  - Service quan trọng có traffic lớn: canary có phân tích tự động.
  - Thay đổi lớn về hạ tầng, cần kiểm tra toàn bộ trước khi mở, hay cần rollback tức thì: blue-green.
  - Service ít traffic: canary không có đủ số liệu; dùng blue-green với smoke test, hoặc rolling cộng feature flag.
