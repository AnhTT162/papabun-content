## Quick

Cloud là thuê hạ tầng tính tiền theo lượng dùng, tạo và xoá bằng API. **Càng lên cao (IaaS → PaaS → SaaS) bạn càng giao nhiều việc cho nhà cung cấp, nhưng cấu hình, dữ liệu và quyền truy cập luôn là việc của bạn.** Hệ thống chịu được mất một **Availability Zone** phải chạy trên ít nhất hai AZ.

## Interview

Cloud theo định nghĩa của NIST là tài nguyên dùng chung, tự lấy khi cần qua API, co giãn nhanh và tính tiền theo lượng dùng. Khác biệt thực tế với data center tự vận hành: tạo một máy mất vài phút thay vì vài tuần mua sắm, và trả tiền theo giờ thay vì đầu tư trước.

Có ba mô hình dịch vụ. [[iaas|IaaS]] như EC2: nhà cung cấp lo phần cứng và ảo hoá, tôi lo hệ điều hành, vá lỗi, runtime và ứng dụng. [[paas|PaaS]] và dịch vụ managed như RDS, Elastic Beanstalk: tôi chỉ lo code, cấu hình và dữ liệu. [[saas|SaaS]] như email doanh nghiệp: tôi chỉ quản lý người dùng và dữ liệu. Ranh giới đó chính là [[shared-responsibility-model|shared responsibility model]]: AWS chịu "security *of* the cloud", tôi chịu "security *in* the cloud". Nhiều sự cố bảo mật trên cloud là lỗi cấu hình phía khách hàng: bucket S3 để public, security group mở 0.0.0.0/0, access key lộ trên Git.

Về địa lý, một [[cloud-region|region]] là một vùng địa lý, gồm ít nhất ba [[availability-zone|AZ]]; mỗi AZ là một hay nhiều data center có điện, mạng, làm mát riêng, cách nhau nhiều km nhưng đủ gần để replication đồng bộ. Tôi chạy app trên hai, ba AZ sau [[load-balancer|load balancer]] và dùng database Multi-AZ; đó là mức mặc định cho production. Multi-region chỉ khi cần chịu mất cả region hoặc phục vụ người dùng ở xa, vì nó đắt và khó hơn nhiều.

Về tiền: trả cho thứ đã **cấp**, không phải thứ đã dùng. Máy chạy CPU 5% vẫn tính đủ giờ; volume vẫn tính khi máy đã dừng. Dữ liệu vào miễn phí, đi giữa AZ và ra Internet thì mất phí. Tải ổn định thì cam kết dài hạn để giảm giá, tải ngắn chịu được gián đoạn thì dùng spot.

Bẫy hay gặp: tưởng "lên cloud là tự HA" trong khi mọi thứ nằm một AZ, và quên [[service-quota|service quota]] tới đúng ngày cần scale.

## Deep

- **Định nghĩa NIST SP 800-145** (2011): năm đặc điểm (on-demand self-service, broad network access, resource pooling, rapid elasticity, measured service), ba mô hình dịch vụ (IaaS, PaaS, SaaS) và bốn mô hình triển khai (private, community, public, hybrid). Một "private cloud" chỉ là cụm máy ảo cấp bằng ticket, không có self-service và đo lường, thì chưa phải cloud theo nghĩa này.
- **Ranh giới thực tế mờ hơn ba tầng**:
  - Container managed (ECS/EKS trên EC2, hay Fargate) nằm giữa IaaS và PaaS: với EKS trên EC2 bạn vẫn vá node; Fargate thì không còn node để vá.
  - [[faas|FaaS]] (Lambda) giao cả việc scale và runtime cho nhà cung cấp; bạn lo code, quyền IAM và cấu hình. Chi tiết ở bài Serverless.
  - Dịch vụ managed như RDS: AWS vá hệ điều hành, cung cấp bản vá engine và áp dụng trong cửa sổ bảo trì bạn chọn (nâng major version thì bạn tự quyết), chạy backup tự động; bạn bật mã hoá, đặt security group, quản lý user database, và **tự thử restore**.
- **Shared controls**: AWS liệt kê các kiểm soát cả hai cùng làm nhưng ở hai tầng khác nhau: vá lỗi (AWS vá hạ tầng, bạn vá hệ điều hành khách và ứng dụng), quản lý cấu hình, đào tạo. Kiểm soát vật lý và môi trường thì bạn kế thừa hoàn toàn (inherited), dùng báo cáo kiểm toán của AWS làm bằng chứng khi audit.
- **Phạm vi của tài nguyên** quyết định cái gì sống sót khi một AZ hỏng:
  - Global: IAM, Route 53, CloudFront.
  - Regional: VPC, bucket S3 (tên bucket là duy nhất toàn cầu nhưng dữ liệu nằm trong một region), SQS, DynamoDB, Lambda, EFS, snapshot EBS. Load balancer (ALB/NLB) là tài nguyên regional nhưng chỉ có node ở các AZ bạn bật.
  - Zonal: subnet, instance EC2, volume EBS, [[nat-gateway|NAT gateway]] (chỉ một cái thì mất AZ đó là mọi subnet private mất đường ra Internet). Volume EBS chỉ gắn được vào instance **cùng AZ**; muốn mở máy ở AZ khác thì tạo volume mới từ snapshot.
- **AZ name khác AZ ID**: với các tài khoản tạo trước 11/2025 ở những region lâu đời, AWS ánh xạ tên AZ ngẫu nhiên theo từng tài khoản, nên `us-east-1a` của tài khoản này có thể là data center khác `us-east-1a` của tài khoản kia. Tài khoản tạo từ 11/2025 có cùng ánh xạ. Khi chia sẻ subnet hay đối chiếu vị trí giữa nhiều tài khoản (ví dụ đặt client cùng AZ với broker để tránh phí cross-AZ), dùng [[az-id|AZ ID]] như `use1-az1`.
- **Quy mô và khoảng cách**: AWS công bố 39 region và 124 AZ (11/2026); mỗi region ít nhất ba AZ, các AZ cách nhau nhiều km nhưng trong vòng 100 km. Đủ xa để một sự cố điện, lũ không đánh sập hai AZ, đủ gần để database ghi đồng bộ sang standby. Azure và Google Cloud cũng dùng khái niệm region và zone, nhưng không phải region Azure nào cũng có availability zone; kiểm tra trước khi chọn.
- **Chọn region**:
  - Latency tới người dùng: người dùng ở Việt Nam thường dùng Singapore (`ap-southeast-1`); gần đó còn có Jakarta, Malaysia, Bangkok. AWS chưa có region ở Việt Nam; có [[local-zone|Local Zone]] Hà Nội gắn với region Singapore, chỉ có một phần dịch vụ.
  - Quy định lưu trữ dữ liệu cá nhân (bài Dữ liệu cá nhân & tuân thủ).
  - Dịch vụ cần dùng đã có ở region đó chưa; dịch vụ mới thường ra ở `us-east-1` trước.
  - Giá khác nhau theo region, có khi chênh vài chục phần trăm cho cùng loại máy.
- **Mô hình tính tiền** (con số và cách tối ưu ở bài Ước tính chi phí & FinOps):
  - Trả theo tài nguyên đã cấp: EC2 Linux tính theo giây (tối thiểu 60 giây), volume EBS tính theo GB đã cấp. Instance đã dừng không tính giờ máy nhưng vẫn tính volume và Elastic IP (IPv4 public tự gán thì bị trả lại khi dừng).
  - Ba cách mua compute: on-demand (không cam kết), [[savings-plan|Savings Plans]] hay [[reserved-instance|reserved instance]] (cam kết 1–3 năm, giảm sâu), [[spot-instance|spot]] (rẻ nhất, bị thu hồi với thông báo 2 phút).
  - Truyền dữ liệu là khoản hay bất ngờ nhất: vào miễn phí, giữa AZ tính cả hai chiều, ra Internet và qua NAT gateway tính theo GB.
- **[[elasticity|Elasticity]] khác scalability**: scalability là chịu được tải lớn hơn khi thêm tài nguyên; elasticity là tự thêm và **bớt** theo tải để không trả tiền cho máy nhàn rỗi. Elasticity chỉ có khi app [[stateless|stateless]] và khởi động nhanh (bài Twelve-Factor App), cộng [[autoscaling|autoscaling]] để [[horizontal-scaling|scale ngang]].
- **[[service-quota|Service quota]]**: mỗi tài khoản có giới hạn theo region cho hầu hết tài nguyên (số vCPU on-demand, số Elastic IP, số VPC). Quota tính theo region, nên region DR cũng phải xin tăng trước, không đợi lúc failover. Một số quota tăng được qua Service Quotas, một số là giới hạn cứng.
- **Bẫy "lên cloud là tự HA"**: một instance EC2 hay một RDS Single-AZ hỏng AZ là ngừng. RDS Multi-AZ DB instance giữ một standby đồng bộ ở AZ khác (không nhận đọc); [[failover|failover]] đổi DNS endpoint, thường mất 60–120 giây. Multi-AZ DB cluster có hai standby đọc được và failover thường dưới 35 giây; Aurora có cơ chế riêng. App phải tự kết nối lại theo tên DNS, và JVM không được giữ IP cũ quá lâu: `networkaddress.cache.ttl` mặc định 30 giây khi không có security manager (bài HTTP request đi qua những gì). RPO/RTO và multi-region ở bài High availability & disaster recovery.
- **Lift-and-shift không tự rẻ hơn**: chuyển nguyên máy chủ chạy 24/7 lên EC2 cùng cỡ thường đắt hơn data center đã khấu hao. Lợi ích đến khi rightsizing, tắt môi trường dev ngoài giờ, dùng dịch vụ managed và co giãn theo tải (bài Migration & hiện đại hoá).
