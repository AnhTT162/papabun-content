## Quick

High availability (HA) giữ dịch vụ chạy khi **một phần** hạ tầng hỏng (một máy, một [[availability-zone|AZ]]) bằng dư thừa và tự chuyển; disaster recovery (DR) đưa dịch vụ trở lại sau sự cố **lớn** (mất [[cloud-region|region]], xoá nhầm dữ liệu, ransomware). Hai con số quyết định thiết kế: [[rpo-rto|RPO]] (được mất bao nhiêu dữ liệu) và RTO (được ngừng bao lâu). **Mỗi bậc RPO/RTO thấp hơn tốn thêm tiền và độ phức tạp, và chỉ những gì đã diễn tập mới tính là có.**

## Interview

Tôi bắt đầu từ nghiệp vụ: mỗi hệ thống được phép mất bao nhiêu phút dữ liệu và ngừng bao lâu, và mất đó tốn bao nhiêu tiền. Thanh toán có thể cần RPO vài giây và RTO vài phút; báo cáo nội bộ chấp nhận RPO 24 giờ, RTO một ngày.

HA trong một region là mặc định: chạy qua ít nhất hai, ba AZ, database Multi-AZ ([[failover|failover]] tự động), đủ capacity để mất một AZ vẫn chịu tải ([[static-stability|static stability]], bài Độ tin cậy & SRE).

DR có bốn mức theo whitepaper của AWS. [[backup-and-restore|Backup và restore]]: chép backup sang region hoặc tài khoản khác, khi cần thì dựng lại từ IaC; rẻ nhất, RTO tính bằng giờ. [[pilot-light|Pilot light]]: dữ liệu luôn được sao chép, hạ tầng lõi có sẵn nhưng app tắt; RTO hàng chục phút. [[warm-standby|Warm standby]]: một bản thu nhỏ chạy sẵn; RTO vài phút. Multi-site active-active: cả hai region phục vụ, RTO gần 0 nhưng phải giải quyết ghi ở hai nơi (bài Multi-region & active-active).

RPO đến từ cách sao chép: đồng bộ (Multi-AZ) thì gần 0 trong region; bất đồng bộ qua region (Aurora Global Database, S3 Cross-Region Replication, DynamoDB global tables) thì mất phần lag lúc sự cố. Backup định kỳ thì RPO là khoảng giữa hai lần backup.

Ba điều tôi luôn nhắc. Một, sao chép không phải backup: xoá nhầm hay ransomware cũng được sao chép ngay; cần backup bất biến ở tài khoản riêng. Hai, failover trong region thì tự động, nhưng failover giữa region do người có quyền quyết định theo tín hiệu đã thống nhất, rồi chạy bằng runbook đã chuẩn bị, không phụ thuộc tạo mới tài nguyên hay control plane của region đang hỏng. Ba, diễn tập định kỳ, đo RTO thật, kể cả chuyển về.

Bẫy hay gặp: quên quota, image, secret, chứng chỉ ở region dự phòng; DNS TTL và cache của client làm chuyển traffic chậm hơn tính toán.

## Deep

- **RPO và RTO đo gì**: RPO là khoảng thời gian dữ liệu có thể mất tính ngược từ lúc sự cố; RTO tính từ lúc sự cố tới lúc dịch vụ chạy lại với người dùng, gồm phát hiện, quyết định, thực thi, kiểm tra. Ghi theo từng hệ thống và từng loại sự cố (mất AZ, mất region, hỏng dữ liệu): mất AZ có thể RTO 2 phút nhưng hỏng dữ liệu là vài giờ.
- **Availability của chuỗi** và ngân sách số 9 ở bài NFR & quality attribute.
- **Bốn mức DR và chi phí tương đối** (AWS, *Disaster Recovery of Workloads on AWS*; hệ số chi phí là minh hoạ, so với chạy một region):
  - Backup và restore (RTO giờ, RPO theo chu kỳ backup): trả lưu trữ backup và truyền dữ liệu giữa region, gần như không có compute chờ; cỡ 1,05–1,1 lần.
  - Pilot light (hàng chục phút): thêm database replica chạy thường trực, phí truyền dữ liệu sao chép liên tục; app không chạy; cỡ 1,2–1,4 lần. AWS Elastic Disaster Recovery làm kiểu này cho server.
  - Warm standby (vài phút): thêm một bản app nhỏ chạy thường trực; cỡ 1,4–1,7 lần.
  - Multi-site active-active (gần như tức thì): gần gấp đôi hạ tầng, cộng chi phí phát triển cho ghi hai nơi; 2 lần trở lên.
  - Giá truyền dữ liệu giữa region và cách ước tính ở bài Ước tính chi phí & FinOps.
- **Sao chép dữ liệu qua region**:
  - Aurora Global Database: chép bất đồng bộ ở tầng lưu trữ, RPO thường tính bằng giây, RTO cỡ vài phút. Switchover là chủ động, không mất dữ liệu; failover khi region chính hỏng có thể mất phần lag. Aurora không tự failover giữa region: người hay automation phải gọi. Theo dõi lag bằng metric của CloudWatch (`AuroraGlobalDBReplicationLag`, `AuroraGlobalDBRPOLag`) và cảnh báo theo lag đỉnh. `rds.global_db_rpo` (Aurora PostgreSQL) đặt trần RPO bằng cách làm chậm ghi, không đưa RPO về 0; RPO 0 xuyên region đòi ghi đồng bộ, trả bằng latency mỗi lần ghi.
  - RDS cross-region read replica: promote mất vài phút, có reboot.
  - S3 Cross-Region Replication: bất đồng bộ, versioning bắt buộc; object có trước khi bật replication không tự được chép (cần Batch Replication); delete marker chỉ được chép khi bật, còn xoá một version cụ thể thì không chép. Replication Time Control cam kết 99,9% object trong 15 phút, có metric và cảnh báo.
  - DynamoDB global tables: mặc định ghi được ở mọi region, eventual consistency, last-writer-wins; có chế độ multi-Region strong consistency (từ 2025) để RPO 0, đổi lại ghi chậm hơn (bài Thiết kế key-value store phân tán). Global tables cũng chép luôn ghi sai: vẫn cần PITR.
  - Kafka giữa region: MirrorMaker 2 phải dịch offset của consumer group; Cluster Linking giữ nguyên offset; với MSK có MSK Replicator (bài Multi-region & active-active).
- **Sao chép không phải backup**: lệnh `DELETE` thiếu `WHERE`, migration hỏng, ransomware mã hoá dữ liệu đều được chép sang trong vài giây. Cần backup point-in-time (bài Backup, restore & PITR) và bản sao bất biến (AWS Backup Vault Lock, S3 Object Lock) ở tài khoản tách biệt mà quyền của tài khoản prod không xoá được. Vault Lock chế độ compliance không gỡ được sau thời gian chờ: thử bằng governance mode trước.
- **Control plane và data plane khi failover**:
  - Data plane là phần phục vụ (trả lời DNS, nhận request, xác thực); control plane là phần thay đổi cấu hình (tạo tài nguyên, sửa IAM, sửa bản ghi DNS, promote database, đổi desired capacity). Control plane của IAM, Route 53, CloudFront đặt ở `us-east-1`, của Application Recovery Controller ở `us-west-2`.
  - Rủi ro không phải mọi thao tác control plane đều hỏng, mà là phụ thuộc vào control plane của chính region đang hỏng, của dịch vụ global đang có sự cố, hoặc bị nghẽn khi mọi khách hàng cùng failover. Thao tác control plane ở region còn sống (promote Aurora secondary, tăng ASG) là chấp nhận được nếu nằm trong runbook và đã diễn tập.
  - Cách an toàn nhất là chuẩn bị trước những gì không cần tạo mới: role, ASG, endpoint, chứng chỉ có sẵn; capacity chạy sẵn đủ cho tải tối thiểu chấp nhận được; chuyển traffic bằng thao tác data plane: health check của Route 53 hay routing control của Application Recovery Controller, bật tắt qua cluster endpoint của nó (lưu sẵn endpoint và credential, không phụ thuộc control plane ở `us-west-2`).
- **Tự động hay người quyết định**: trong region thì tự động (Multi-AZ, load balancer bỏ target hỏng, [[zonal-shift|zonal shift]]). Giữa region, failover sai làm mất dữ liệu chưa chép và kéo theo một lần chuyển về phức tạp, nên để người có quyền quyết định dựa trên nhiều tín hiệu, rồi automation chạy các bước. Health check của Route 53 hợp để tự chuyển phần không có trạng thái (trang tĩnh, API chỉ đọc).
- **Zonal shift** (Application Recovery Controller): rút traffic của load balancer khỏi một AZ đang có vấn đề kể cả khi health check vẫn xanh vì lỗi chập chờn; có thời hạn, và AZ còn lại phải đủ capacity. Zonal autoshift để AWS tự làm, kèm practice run định kỳ.
- **Thứ tự failover giữa region**: quyết định (ai, dựa trên tín hiệu nào); chặn ghi ở region cũ nếu còn với tới được (fencing), để khi nó sống lại không nhận ghi song song (split-brain); promote database ở region phụ; scale app; chuyển traffic; kiểm tra bằng giao dịch thật; thông báo.
- **Chuyển về (failback)**: sau failover, cluster cũ đã tách khỏi global database; phần dữ liệu chưa kịp chép ở region cũ phải được giữ lại để đối soát rồi mới xoá. Dựng lại sao chép từ region đang chạy về region cũ, rồi switchover có kế hoạch vào giờ thấp điểm. Failback cũng phải diễn tập.
- **Những thứ hay thiếu ở region dự phòng**: service quota, image (ECR replication) và AMI ID theo region, secret (Secrets Manager replica), chứng chỉ ACM (CloudFront dùng `us-east-1`), khoá KMS multi-Region, whitelist IP của đối tác cho NAT ở region phụ, pipeline CI/CD và Terraform state đặt ở region chính (khi region chính mất thì không deploy được), DNS cache phía client (JVM mặc định 30 giây, bài HTTP request đi qua những gì).
- **Diễn tập**:
  - Restore thử tự động (AWS Backup restore testing) và kiểm dữ liệu sau restore, theo lịch.
  - Game day failover trong môi trường riêng hoặc switchover chủ động trên prod vào giờ thấp điểm; tiêu chí đạt viết trước (RTO, RPO, không lỗi dữ liệu) và có đường quay lại.
  - Đo RTO theo từng phần: phát hiện, quyết định, thực thi, kiểm tra; phần quyết định thường dài nhất.
  - Mỗi lần diễn tập sinh danh sách việc có người phụ trách: bước tay nào cần tự động hoá, thiếu gì ở region phụ (bài Độ tin cậy & SRE).
- **Chọn mức**: so giá một giờ ngừng và một phút dữ liệu mất với chi phí tăng thêm ở trên; phần lớn hệ thống chỉ cần Multi-AZ cộng backup và restore có diễn tập.
