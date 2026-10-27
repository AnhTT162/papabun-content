## Quick

Capacity planning trả lời câu hỏi: cần bao nhiêu tài nguyên để **giữ [[slo|SLO]] ở đỉnh tải dự báo, kể cả khi mất một zone**. Số instance = tải đỉnh / (capacity đo được của một instance × mức utilization mục tiêu), rồi kiểm tra lại với dự phòng [[n-plus-1|N+1]]. **[[autoscaling|Autoscaling]] không thay thế capacity planning**: nó phản ứng theo phút và không mở rộng được database hay dependency phía sau. Autoscale theo tài nguyên bão hoà trước: CPU cho service CPU-bound, số request đang xử lý hay lag của queue cho service chờ I/O.

## Interview

**Bốn bước**:
1. *Dự báo tải đỉnh*, không phải trung bình: trung bình × hệ số đỉnh trong ngày, cộng tăng trưởng và sự kiện đã biết (campaign, ngày lương, cuối tháng).
2. *Đo capacity một instance* bằng load test (bài Load & performance testing): tăng arrival rate tới khi p99 vượt SLO. Trần là điểm đó, không phải điểm CPU 100%.
3. *Chọn mức utilization mục tiêu* để chừa [[headroom|headroom]]: với hàng đợi M/M/1, p99 ≈ `4,6 × S / (1 − ρ)`, service 10ms có p99 khoảng 92ms ở 50% tải, 230ms ở 80%, 460ms ở 90%. Thường lên kế hoạch ở 50–65% trần; 3 AZ thì không quá 2/3. (ρ tính trên throughput bão hoà, còn trần ở đây là điểm p99 chạm SLO, nên hai con số không trùng nhau.)
4. *Tính số instance và kiểm tra khi hỏng*: chạy trên 3 AZ thì mất một AZ, hai AZ còn lại gánh gấp 1,5 lần mà vẫn phải dưới trần.

Ví dụ: một pod giữ được SLO tới 400 req/s, kế hoạch 60% là 240 req/s. Đỉnh 7.200 req/s cần 30 pod (10 pod mỗi AZ); mất một AZ còn 20 pod, mỗi pod 360 req/s, vẫn dưới 400 nhưng p99 sát SLO: chấp nhận được khi sự cố, không phải mức thường ngày.

**Autoscale**: [[hpa|HPA]] của Kubernetes tính `ceil(số pod × giá trị hiện tại / mục tiêu)`, với CPU tính theo phần trăm `requests`. Ba bẫy:
- Service chờ database hay HTTP thì CPU không tăng dù đã quá tải: scale theo số request đang xử lý mỗi pod, hoặc theo lag của queue ([[keda|KEDA]]).
- Phản ứng chậm: chu kỳ metric, khởi động JVM, [[jit|JIT]] chưa nóng, thêm node mất vài phút. Đỉnh biết trước thì scale trước theo lịch.
- Thêm pod không thêm database: 30 pod × pool 20 là 600 connection, vượt `max_connections` 500 của database (bài Connection pool).

**Khi tải vượt kế hoạch**: [[rate-limiting|rate limit]] theo tenant, [[load-shedding|load shedding]] phần không quan trọng, hàng chờ ảo, thay vì để mọi người cùng chậm.

## Deep

- **Thuật toán HPA** (Kubernetes 1.37): chu kỳ mặc định 15 giây; bỏ qua nếu tỉ lệ nằm trong tolerance 10% (đặt riêng cho từng HPA bằng `behavior.scaleUp.tolerance` từ 1.33, stable từ 1.37). Mặc định scale up không có stabilization window, mỗi 15 giây thêm tối đa 100% hoặc 4 pod (lấy số lớn hơn); scale down dùng cửa sổ 300 giây. Pod chưa ready, hoặc mẫu CPU lấy trước lúc pod ready trong 5 phút đầu (`cpu-initialization-period`), bị để riêng và coi như 0% khi tính scale up, nên thực tế tăng chậm hơn công thức.
- **CPU bão hoà che mất độ lớn của đỉnh**: khi `requests` bằng `limits`, utilization không vượt 100%, nên mục tiêu 50% thì mỗi vòng HPA thấy tối đa gấp đôi, mục tiêu 80% chỉ thấy 1,25 lần. Mô phỏng tải tăng 6 lần trên 5 pod (trần 400 req/s, CPU 85% ở trần): mục tiêu 50% cần 3 vòng (5 → 10 → 20 → 31), mục tiêu 80% cần 5 vòng (5 → 7 → 9 → 12 → 15 → 19) và dừng ở 19 pod, mỗi pod khoảng 379 req/s, sát trần. Một vòng thực tế dài bằng thời gian pod mới ready và có metric, không phải 15 giây.
- **`requests`, `limits` và JVM**: utilization tính trên `requests`, nên pod có `limits` lớn hơn có thể báo trên 100%. JVM tính số CPU từ CPU limit (quota); từ JDK 19 (backport vào 17.0.5, 11.0.17) không còn dùng CPU shares, tức `requests`. Không đặt limit thì JVM thấy toàn bộ CPU của node và sinh số GC thread, kích thước `ForkJoinPool.commonPool()` theo đó; đặt limit quá thấp thì bị [[cpu-throttling|CPU throttling]] (bài JVM trong container).
- **Metric tốt hơn CPU cho service I/O-bound**: số request đang xử lý mỗi pod, mục tiêu tính bằng [[littles-law|Little's law]] (240 req/s × 0,1 giây = 24 request đồng thời). Không dùng latency làm metric scale chính: latency tăng vì database chậm thì thêm pod chỉ dồn thêm tải xuống database. Dùng latency để cảnh báo.
- **Scale theo queue**: KEDA đọc lag của consumer group hay độ dài queue rồi điều khiển HPA. Với Kafka, số consumer có việc bị chặn bởi số [[kafka-partition|partition]]; scaler Kafka của KEDA mặc định không vượt số partition (`allowIdleConsumers: false`).
- **Scale trước cho đỉnh biết trước**: nâng `minReplicas` theo lịch (KEDA cron scaler, hoặc CronJob sửa HPA), predictive scaling của AWS Auto Scaling. Ngoài Kubernetes, EC2 Auto Scaling có target tracking (giữ một metric quanh mục tiêu), step scaling, scheduled scaling và predictive scaling. Giữ chỗ trống trên node bằng pod giữ chỗ có priority thấp (overprovisioning): pod thật đẩy chúng ra ngay thay vì chờ [[cluster-autoscaler|Cluster Autoscaler]] hay Karpenter thêm node.
- **Trải đều giữa các AZ**: phép tính mất một AZ chỉ đúng khi pod chia đều. Dùng `topologySpreadConstraints` theo `topology.kubernetes.io/zone` với `maxSkew: 1`; scheduler chỉ cân bằng lúc đặt pod, không chuyển pod đang chạy, nên scale down có thể làm lệch lại. Cluster Autoscaler cần node group riêng cho từng AZ (hoặc dùng Karpenter) để thêm node đúng zone đang thiếu; PodDisruptionBudget giữ số pod tối thiểu khi drain node.
- **Pod mới làm tăng p99**: pod vừa ready nhận đủ phần tải khi JIT chưa nóng. Chạy warm-up trước khi readiness probe báo ready, hoặc dùng slow start ở load balancer (`slow_start` của ALB target group, `slow_start_config` của Envoy) để tăng dần lưu lượng vào pod mới.
- **Scale down cẩn thận hơn scale up**: metric dao động quanh mục tiêu gây scale lên xuống liên tục; giữ cửa sổ scale down dài, giới hạn số pod bỏ mỗi phút, và cần graceful shutdown để request đang chạy không bị cắt.
- **Ngân sách connection theo Little's law**: pod 240 req/s giữ connection trung bình 10ms chỉ dùng khoảng 2,4 connection, nên pool 8 là dư; 30 pod × 8 = 240, kể cả `maxSurge` 25% khi deploy (38 pod) là 304. Cache, bên thứ ba có rate limit, database primary không mở rộng theo số pod: đọc thì thêm cache hay replica, ghi thì phải nâng database hoặc shard.
- **Scale không tuyến tính**: tranh chấp lock và đồng bộ giữa các node làm throughput mỗi instance giảm khi cụm lớn lên ([[universal-scalability-law|Universal Scalability Law]]). Đo ở 2–3 kích thước cụm thay vì nhân kết quả của một pod.
- **Horizontal hay vertical**: VPA không nên chạy cùng HPA trên cùng metric CPU hay memory vì hai bên giành nhau điều khiển. Scale dọc hợp với database và hệ stateful nhưng có trần và thường phải khởi động lại.
- **Dự báo từ chỉ số kinh doanh**: đơn hàng mỗi ngày, người dùng hoạt động → request mỗi đơn → CPU, connection, dung lượng đĩa, số partition. Theo dõi xu hướng và cảnh báo khi dự báo chạm trần trong vài tuần tới, không chờ tới khi đầy.
- **Chi phí**: so `requests` với mức dùng thật (pod xin 2 CPU nhưng dùng 0,3 là trả tiền cho 85% không dùng). Phần tải nền dùng reserved hoặc savings plan; phần dao động dùng on-demand hay spot. Spot có thể bị thu hồi (AWS báo trước 2 phút), nên không đặt phần capacity bắt buộc cho SLO lên spot.
- **Một tenant ăn hết capacity**: hệ thống dùng chung cần quota và rate limit theo tenant (bài Database chậm trên production), nếu không kế hoạch tính theo tổng tải vẫn vỡ khi một khách hàng lớn chạy import.
