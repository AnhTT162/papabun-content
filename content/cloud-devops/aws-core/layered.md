## Quick

Một web app chuẩn trên AWS: [[vpc|VPC]] trải ít nhất hai AZ, [[application-load-balancer|ALB]] ở subnet public, app (EC2 trong Auto Scaling group, ECS hay EKS) ở subnet private, RDS Multi-AZ ở subnet riêng cho database. **Security group tham chiếu lẫn nhau theo tầng, app lấy quyền AWS qua [[iam-role|IAM role]] chứ không qua access key**, và mọi tầng đều sống sót khi mất một AZ.

## Interview

Tôi dựng từ mạng ra ngoài. VPC một dải CIDR đủ lớn, ví dụ `/16`, chia mỗi AZ ba subnet: public cho load balancer và NAT gateway, private cho app, private cho database. Subnet public có route `0.0.0.0/0` tới Internet gateway; subnet private đi ra ngoài qua [[nat-gateway|NAT gateway]], mỗi AZ một cái để mất một AZ không làm mất đường ra.

Phía vào là ALB: kết thúc TLS bằng chứng chỉ ACM, định tuyến theo host và path, kiểm health check rồi gửi tới target group. Cần TCP/UDP thuần, IP tĩnh, giữ IP client hay hàng triệu kết nối thì dùng [[network-load-balancer|NLB]].

App chạy trong [[auto-scaling-group|Auto Scaling group]] từ một launch template, trải đều các AZ, dùng health check của ELB để thay instance không phục vụ được. [[security-group|Security group]] chuỗi theo tầng: SG của ALB mở 443 cho Internet, SG của app chỉ nhận 8080 từ SG của ALB, SG của database chỉ nhận 5432 từ SG của app. Tham chiếu theo SG ID thay vì CIDR nên scale bao nhiêu instance cũng đúng.

Database là RDS PostgreSQL Multi-AZ: standby đồng bộ ở AZ khác, failover tự động bằng cách đổi DNS. Backup tự động cho phép khôi phục về một thời điểm bất kỳ trong thời gian giữ, tối đa 35 ngày. Password nằm trong Secrets Manager, có xoay vòng.

Quyền: instance có IAM role qua [[instance-profile|instance profile]]; SDK tự lấy credential tạm thời từ metadata service, nên không có access key nào trong cấu hình hay image. Bật [[imdsv2|IMDSv2]] bắt buộc để chặn tấn công SSRF đọc credential.

Bẫy tôi hay gặp: CloudWatch mặc định không có metric bộ nhớ của EC2; deregistration delay mặc định 300 giây làm mỗi lần deploy chậm 5 phút; keep-alive của app ngắn hơn idle timeout 60 giây của ALB gây lỗi 502 lác đác; và NAT gateway chỉ đặt ở một AZ.

## Deep

- **VPC và subnet**: subnet thuộc đúng một AZ. AWS giữ 5 địa chỉ mỗi subnet (4 đầu, 1 cuối), nên `/24` còn 251. Với EKS dùng VPC CNI, mỗi pod lấy một IP của subnet: subnet `/24` hết IP rất nhanh. CIDR, route và NAT ở bài Mạng máy tính cơ bản; PrivateLink, Transit Gateway, VPN ở bài Network trên cloud.
- **Security group và NACL**: SG stateful (cho vào thì tự cho chiều trả về), chỉ có luật allow, gắn vào ENI. NACL stateless, gắn vào subnet, có deny, phải mở cả dải port tạm cho chiều về. Thường chỉ dùng SG; NACL để chặn thô một dải IP.
- **ALB** (mặc định theo tài liệu ELB):
  - Health check: mỗi 30 giây, timeout 5 giây, 2 lần thất bại liên tiếp thì rút target, 5 lần thành công liên tiếp mới đưa lại. Instance hỏng có thể nhận request thêm khoảng một phút trước khi bị rút.
  - [[deregistration-delay|Deregistration delay]] 300 giây: target đang rút vẫn được chờ cho request dở hoàn tất. App tắt êm trong 30 giây thì giảm còn 30–60 giây cho deploy nhanh hơn (bài Graceful shutdown & vòng đời process).
  - Idle timeout 60 giây: keep-alive của Tomcat phải dài hơn, nếu không app đóng kết nối mà ALB vẫn gửi request vào, ra 502 lác đác (bài Tuning server & HTTP client).
  - Cross-zone load balancing luôn bật ở mức load balancer: chia đều cho mọi target bất kể AZ. Slow start cho target mới (JVM chưa warm-up) nhận tải tăng dần.
- **NLB**: L4, có security group (từ 2023) nên chuỗi SG áp dụng được, mỗi AZ một IP tĩnh (gắn được Elastic IP), giữ IP client với target kiểu instance; cross-zone mặc định **tắt** (bật thì tính phí truyền giữa AZ); idle timeout TCP 350 giây, chỉnh được 60–6000. Dùng cho gRPC/TCP thuần cần IP tĩnh để đối tác whitelist, cho PrivateLink, hoặc đặt trước ALB khi cần cả hai.
- **EC2**:
  - Tên loại: `m7g.large` là họ m (cân đối CPU/RAM), thế hệ 7, `g` là Graviton (ARM), cỡ large. `c` thiên CPU, `r` thiên RAM. Graviton thường rẻ hơn cùng cỡ; image phải build cho arm64 (bài Docker & container).
  - Họ T là burstable: tích credit khi rảnh, dùng khi bận. T2 mặc định bị hạ về baseline khi hết credit; T3/T4g mặc định unlimited nên không chậm nhưng tính thêm tiền. Không hợp cho tải đều cao.
  - CloudWatch mặc định có CPU, mạng, đĩa theo chu kỳ 5 phút (detailed monitoring 1 phút, tính phí); **không** có bộ nhớ và dung lượng đĩa: cần CloudWatch agent.
  - Instance store mất dữ liệu khi dừng máy; EBS thì còn. Volume gp3 kèm sẵn 3.000 IOPS và 125 MiB/s.
- **Auto Scaling group**: launch template ghi AMI, loại máy, user data, IAM role; health check kiểu `ELB` (không chỉ trạng thái EC2) để thay instance app chết mà máy còn chạy. Instance refresh để thay dần khi đổi AMI. Scale theo target tracking (CPU 50%, số request mỗi target), thời gian khởi động JVM là độ trễ phải tính (bài Capacity planning & autoscaling).
- **RDS**:
  - Multi-AZ DB instance: standby không đọc được, failover 60–120 giây. Multi-AZ DB cluster có hai standby đọc được và failover thường dưới 35 giây. Read replica bất đồng bộ cho đọc, có độ trễ; bản sao ở region khác dùng cho DR.
  - Backup tự động giữ 1–35 ngày, khôi phục về thời điểm bất kỳ tạo ra **instance mới** với endpoint mới, không ghi đè instance đang chạy. Snapshot thủ công giữ tới khi xoá.
  - Parameter group thay `postgresql.conf`; một số tham số cần reboot. Nâng minor version trong cửa sổ bảo trì có thể làm database ngắt vài phút.
  - Nhiều app instance mỗi cái pool 20 kết nối dễ chạm `max_connections`; RDS Proxy gom kết nối và giảm thời gian failover cảm nhận được, hợp với Lambda (bài Dịch vụ managed của AWS).
- **IAM cho app**:
  - Instance profile gắn role vào EC2; SDK lấy credential tạm thời (hết hạn sau vài giờ, tự làm mới) từ metadata service `169.254.169.254`. Trên EKS dùng EKS Pod Identity hoặc IRSA để mỗi pod một role, không dùng chung role của node.
  - IMDSv2 yêu cầu token lấy bằng `PUT`; bật bắt buộc để lỗ hổng SSRF chỉ gửi được `GET` không đọc được credential. Hop limit mặc định 1 chặn container chạy bridge network trên EC2 đọc metadata; Docker trên EC2 cần đặt hop limit 2.
  - Policy theo [[least-privilege|least privilege]]: app đọc đúng bucket và secret cần đọc. Thứ tự đánh giá policy, phân tách tài khoản ở bài Bảo mật trên cloud & IAM.
- **Chọn nơi chạy app**: EC2 + ASG kiểm soát nhiều nhất, phải vá AMI; ECS trên Fargate không có máy để vá, tính theo vCPU/GB mỗi giây; EKS khi đã có nền tảng Kubernetes và nhiều team. App Runner, Elastic Beanstalk cho đội rất nhỏ. Chi phí và khi nào serverless ở bài Ước tính chi phí & FinOps và bài Serverless.
