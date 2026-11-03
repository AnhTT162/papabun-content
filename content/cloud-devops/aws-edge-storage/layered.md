## Quick

[[route-53|Route 53]] quyết định người dùng được trả IP nào (theo trọng số, latency, vị trí, sức khoẻ), [[amazon-cloudfront|CloudFront]] đưa nội dung và kết nối TLS tới gần người dùng, còn lưu trữ chọn theo **kiểu truy cập**: [[amazon-ebs|EBS]] là ổ đĩa khối của một máy trong một AZ, [[amazon-efs|EFS]] là thư mục dùng chung qua NFS nhiều AZ, [[amazon-s3|S3]] là kho object qua HTTP gần như vô hạn. **Chọn sai kiểu truy cập thì không tuning nào cứu được.**

## Interview

Đường vào của một hệ thống trên AWS thường là Route 53 rồi CloudFront rồi ALB hoặc S3.

Route 53 là DNS có [[routing-policy|routing policy]]: simple; weighted để chia phần trăm traffic khi chuyển hệ thống; latency để trả region có độ trễ thấp nhất với mạng của người dùng; failover kèm health check để chuyển sang site dự phòng; geolocation khi cần chặn hay phân vùng theo quốc gia. Tôi dùng [[alias-record|alias record]] để trỏ tên miền gốc vào CloudFront hay ALB, vì CNAME không đặt được ở apex và alias tới tài nguyên AWS không tính phí truy vấn. Nhớ rằng mọi chuyển hướng bằng DNS đều chậm theo TTL và cache phía client.

CloudFront đặt cache và điểm kết thúc TLS ở [[edge-location|edge]]. Tôi chia behavior theo path: `/static/*` cache dài từ S3 qua origin access control để bucket không public; `/api/*` không cache nhưng vẫn đi qua CloudFront để bắt tay TLS gần người dùng, giữ kết nối sẵn về origin, gắn WAF. Cache key chỉ gồm những header, query, cookie thật sự làm nội dung khác đi; thêm thừa là hit ratio rơi.

Lưu trữ: database tự chạy, Elasticsearch, Kafka cần EBS: latency thấp, chọn được IOPS, nhưng chỉ gắn vào một máy trong một AZ, nên HA phải nhờ replication của chính phần mềm. Nhiều pod cần đọc ghi chung một thư mục (CMS cũ, file dùng chung) thì EFS, chịu được mất một AZ, nhưng mỗi thao tác là một round trip mạng nên rất chậm với nhiều file nhỏ. File của người dùng, ảnh, báo cáo, backup, log lưu lâu thì S3 ([[object-storage|object storage]]): bền, rẻ, đọc ghi qua HTTP, nhất quán mạnh ngay sau khi ghi.

Bẫy hay gặp: chứng chỉ cho CloudFront phải nằm ở ACM `us-east-1`; volume tạo từ snapshot đọc lần đầu rất chậm; dùng EFS làm chỗ ghi log hay build artifact nhỏ li ti; và coi S3 như filesystem để rename hay append.

## Deep

- **Routing policy của Route 53** (8 loại): simple, failover, geolocation, geoproximity (theo vị trí tài nguyên, có hệ số kéo vùng), latency (theo số đo latency giữa mạng người dùng và region của AWS, không đo thời gian thực), IP-based (theo dải IP nguồn bạn khai báo), multivalue answer (tối đa 8 bản ghi khoẻ), weighted. Policy lồng nhau được: latency giữa hai region, trong mỗi region weighted giữa hai phiên bản.
- **Health check**:
  - Health checker ở nhiều nơi trên Internet gọi endpoint mỗi 30 giây (hoặc 10 giây, tính thêm phí), nên endpoint nhận nhiều request kiểm hơn chu kỳ đó. Endpoint chỉ có trong VPC private thì checker không gọi tới được: dùng health check theo CloudWatch alarm.
  - Alias tới ALB bật "evaluate target health" thì Route 53 dựa vào sức khoẻ target của ALB.
  - Failover thực tế = thời gian phát hiện (chu kỳ × ngưỡng) + TTL + cache của resolver và client (JVM cache 30 giây, bài DNS & CDN). Đặt TTL ngắn cho bản ghi dùng để failover.
- **Alias record**: đặt được ở apex, trỏ tới CloudFront, ALB/NLB, S3 website, API Gateway, bản ghi khác trong zone; IP đích đổi thì Route 53 tự trả IP mới; TTL do tài nguyên đích quyết định, không chỉnh được. Không tính phí truy vấn alias tới tài nguyên AWS, khác với CNAME.
- **CloudFront**:
  - Mỗi distribution có nhiều cache behavior theo path pattern, mỗi behavior một origin, một cache policy (cái gì vào cache key, TTL) và origin request policy (cái gì gửi tới origin nhưng không vào cache key). Tách hai policy này là cách giữ hit ratio cao mà origin vẫn nhận header cần thiết.
  - [[origin-access-control|Origin access control]] (OAC) cho CloudFront ký request tới S3 bằng SigV4; bucket policy chỉ cho phép distribution đó. Origin access identity (OAI) là cách cũ, không nên dùng cho cấu hình mới.
  - Chứng chỉ TLS cho tên miền riêng phải ở ACM region `us-east-1`, bất kể origin ở đâu.
  - CloudFront Functions chạy JavaScript rất nhẹ ở viewer request/response (đổi URL, thêm header, chặn đơn giản); Lambda@Edge chạy nặng hơn, được ở cả origin request/response, gọi mạng được, đắt và chậm hơn.
  - Origin group: một origin chính và một origin dự phòng; origin chính trả lỗi hay không kết nối được thì CloudFront tự thử origin dự phòng (chỉ cho GET, HEAD, OPTIONS). Kèm custom error response để trả trang lỗi tĩnh từ S3. Với CDN đã có thì đây thường là cách failover gọn hơn DNS.
  - Cache key, TTL, purge, [[origin-shield|origin shield]], cache poisoning ở bài DNS & CDN; signed URL/cookie cho video ở bài Thiết kế lưu trữ file / video.
- **EBS**:
  - Zonal, gắn vào một instance (trừ io1/io2 multi-attach cho phần mềm cluster biết khoá). gp3 kèm sẵn 3.000 IOPS và 125 MiB/s, mua thêm IOPS và throughput tách khỏi dung lượng; io2 Block Express cho database cần IOPS cao và ổn định.
  - Instance cũng có giới hạn băng thông EBS theo loại máy: volume mua 16.000 IOPS gắn vào máy nhỏ vẫn bị máy chặn trước.
  - Snapshot tăng dần, lưu theo region; copy sang region khác để DR. Volume tạo từ snapshot tải block từ S3 khi đọc lần đầu, nên lần quét đầu chậm hẳn; khởi tạo trước (đọc hết volume) hoặc bật Fast Snapshot Restore trước khi đưa database vào phục vụ.
- **EFS**:
  - NFSv4, mount đồng thời từ nhiều instance, pod (Kubernetes `ReadWriteMany` qua EFS CSI driver), Lambda; dữ liệu nằm ở nhiều AZ (bản One Zone rẻ hơn, một AZ).
  - Throughput mode Elastic tự scale theo tải; mỗi thao tác metadata (mở, stat, tạo file) là một round trip mạng. Hàng nghìn file nhỏ (`npm install`, log ghi từng dòng, build Maven) chậm hơn ổ cục bộ rất nhiều lần.
  - Hợp với thư mục dùng chung cho ứng dụng cũ chưa sửa được sang S3, nội dung CMS, model ML đọc nhiều. Ứng dụng mới thì S3 thường tốt hơn.
- **S3**:
  - Nhất quán mạnh read-after-write cho PUT, DELETE và cả LIST, ở mọi region (từ 12/2020): ghi xong là đọc thấy ngay.
  - Không phải filesystem: không rename (phải copy rồi xoá, tốn thời gian với object lớn), không sửa giữa file, ghi đè cả object. Conditional write: `If-None-Match: *` để chỉ tạo khi chưa có, `If-Match` theo ETag để tránh ghi đè lên bản người khác vừa đổi.
  - Mỗi prefix chịu ít nhất 3.500 ghi và 5.500 đọc mỗi giây, và S3 tự chia prefix khi tải tăng dần; tăng đột ngột thì có thể nhận `503 Slow Down` một lúc. Chỉ khi tải rất lớn và tăng đột ngột mới đáng nghĩ tới việc rải khoá ra nhiều prefix, và cái giá là mất prefix có ý nghĩa cho `list` và lifecycle rule.
  - Object tối đa 5 TB, upload lớn dùng multipart, trình duyệt tải thẳng lên bằng [[presigned-url|presigned URL]] (bài Thiết kế lưu trữ file / video). [[storage-class|Storage class]] và lifecycle ở bài Ước tính chi phí & FinOps. Chặn public access ở mức tài khoản, mã hoá mặc định bật.
- **Chọn lưu trữ**:
  - Database, broker, search tự vận hành: EBS (hoặc dịch vụ managed để khỏi lo).
  - File dùng chung kiểu POSIX giữa nhiều máy: EFS (Windows/SMB hay HPC thì FSx).
  - File người dùng, artifact, backup, dữ liệu phân tích: S3.
  - Bộ nhớ đệm tạm cực nhanh, chấp nhận mất khi dừng máy: instance store (NVMe gắn liền máy).
