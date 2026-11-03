## Quick

Dịch vụ managed là trả tiền để giao việc vận hành (vá, HA, backup, scale) cho nhà cung cấp. Đổi lại bạn nhận **giới hạn cứng, throttling, giá theo lượng dùng và API riêng khó mang đi**. Chọn dịch vụ theo kiểu tương tác (giao việc, phát sự kiện, luồng có thể đọc lại, tra theo khoá) và **đọc quota trước khi thiết kế**, không phải sau sự cố.

## Interview

Tôi chọn theo bài toán, không theo tên dịch vụ.

Giao việc cho worker, mỗi việc xử lý một lần, retry và DLQ: [[amazon-sqs|SQS]]. Standard gần như không giới hạn throughput, at-least-once; FIFO giữ thứ tự theo message group. Ngữ nghĩa [[visibility-timeout|visibility timeout]] và [[dead-letter-queue|DLQ]] ở bài Messaging cơ bản.

Một sự kiện cần tới nhiều bên ([[fan-out|fan-out]]): [[amazon-sns|SNS]] đẩy tới nhiều subscriber, thường là mỗi bên một queue SQS để bên chậm không kéo bên khác. Cần định tuyến theo nội dung sự kiện, nhiều tài khoản, lưu trữ và phát lại: [[amazon-eventbridge|EventBridge]]; bus kiểu rule (Classic) có quota invocation theo region, ở Singapore 2.250 mỗi giây, vượt thì sự kiện tới đích bị trễ.

Luồng sự kiện lớn cần thứ tự theo khoá và đọc lại từ một thời điểm: Kinesis Data Streams hoặc MSK (Kafka managed). MSK giữ giao thức Kafka nên dễ mang đi, nhưng bạn vẫn tự lo số partition, cỡ broker.

Dữ liệu tra theo khoá ở quy mô lớn, latency ổn định: [[amazon-dynamodb|DynamoDB]]. Thiết kế từ access pattern trước; chế độ on-demand là mặc định và chịu được gấp đôi đỉnh trước đó, vượt nhanh hơn thì bị throttle. Cache: ElastiCache với Valkey hay Redis, bản serverless khi không muốn định cỡ node.

Lambda làm keo nối: đọc SQS, xử lý file mới trên S3. Chi tiết cold start, giới hạn ở bài Serverless.

Managed hay tự chạy trên EC2/Kubernetes? Tôi tính tổng chi phí ([[tco|TCO]]): hoá đơn cộng công vận hành (người trực, vá, nâng cấp, diễn tập failover). Với đội nhỏ, managed gần như luôn thắng. Tự chạy hợp lý khi quy mô đủ lớn để công vận hành rẻ hơn phần chênh hoá đơn, cần tính năng hay phiên bản dịch vụ managed không có, hoặc phải chạy được trên nhiều cloud.

Bẫy hay gặp: không xử lý `ThrottlingException`; key nóng trên DynamoDB bị giới hạn mỗi partition dù bảng còn dư; Lambda đọc SQS scale lên hàng trăm instance và làm cạn connection của database.

## Deep

- **SQS**:
  - Message tối đa 1 MiB; lớn hơn thì dùng Extended Client Library: payload lên S3, queue chỉ giữ con trỏ. Trễ tối đa 15 phút (đặt theo từng message với queue standard; FIFO chỉ đặt được ở mức queue).
  - Standard: at-least-once, thứ tự cố gắng; consumer phải idempotent (bài Idempotency). FIFO: thứ tự trong `MessageGroupId`, khử trùng lúc gửi trong 5 phút, throughput thấp hơn standard nhiều; một message lỗi chặn cả group.
  - Long polling (`WaitTimeSeconds` 20) giảm request rỗng, vì SQS tính tiền theo request.
- **SNS và EventBridge**:
  - SNS: push tới SQS, Lambda, HTTP, email, SMS; filter policy theo thuộc tính message hoặc theo nội dung JSON của body để mỗi subscriber chỉ nhận loại sự kiện cần. Fan-out SNS → nhiều SQS là mẫu chuẩn (bài Messaging cơ bản).
  - EventBridge (bus kiểu rule, tài liệu gọi là Custom Event Bus - Classic): rule lọc theo nội dung JSON với nhiều toán tử, gửi tới hơn 20 loại đích, chuyển giữa tài khoản, archive và replay, schema registry. Quota khác nhau theo region: Singapore 2.250 invocation và 1.200 request `PutEvents` mỗi giây, us-east-1 18.750 và 10.000; tăng được qua Service Quotas. `PutEvents` tính theo request (một request gộp nhiều sự kiện), vượt thì bị throttle và producer phải retry; invocation (một sự kiện khớp rule gửi tới một đích) vượt quota thì vẫn được gửi nhưng bị trễ, nên hàng đợi trễ dồn lên. Phù hợp sự kiện nghiệp vụ tần suất vừa.
  - EventBridge có thêm loại Custom Event Bus mới với mô hình subscriber và quota tới 500.000 sự kiện mỗi giây mỗi bus; kiểm loại bus trước khi dùng các con số trên.
- **Kinesis Data Streams và MSK**: cả hai là log có thứ tự theo khoá, đọc lại được, nhiều consumer độc lập (bài Kiến trúc Kafka, bài Thiết kế distributed message queue). Kinesis là API riêng của AWS; chế độ provisioned tính theo shard (mỗi shard nhận 1 MB hoặc 1.000 bản ghi mỗi giây), chế độ on-demand tự scale; giữ dữ liệu mặc định 24 giờ, kéo dài tới 365 ngày có tính phí. MSK là Kafka thật: client Kafka, Kafka Connect, Kafka Streams dùng được ngay; MSK Serverless bớt việc định cỡ broker. Chi phí truyền dữ liệu giữa AZ của Kafka tự chạy ở bài Ước tính chi phí & FinOps.
- **DynamoDB**:
  - On-demand là chế độ mặc định và được khuyên dùng cho phần lớn workload. Bảng on-demand mới chịu ngay 4.000 ghi và 12.000 đọc mỗi giây; sau đó chịu ngay gấp đôi đỉnh trước đó, vượt gấp đôi trong vòng 30 phút thì có thể bị throttle. Biết trước đợt tăng lớn (mở bán) thì làm ấm bảng (warm throughput) trước.
  - Provisioned kèm auto scaling rẻ hơn cho tải đều; burst capacity giữ tới 300 giây năng lực chưa dùng cho các đợt tăng ngắn.
  - Đơn vị: 1 WCU là ghi 1 KB mỗi giây, 1 RCU là đọc nhất quán mạnh 4 KB mỗi giây (eventually consistent tốn một nửa). Mỗi partition tối đa 3.000 RCU và 1.000 WCU: key nóng bị throttle dù bảng dư. Adaptive capacity dời key nóng sang partition riêng nhưng không vượt được giới hạn đó; phải chia khoá (write sharding). Item tối đa 400 KB. Mô hình dữ liệu, GSI/LSI, single-table design ở bài NoSQL: chọn loại nào.
  - Có transaction nhiều item, TTL tự xoá, Streams cho CDC, point-in-time recovery tới 35 ngày, global tables cho nhiều region (bài Thiết kế key-value store phân tán).
- **ElastiCache**:
  - Engine Valkey, Redis OSS, Memcached. Node-based: tự chọn cỡ node, số shard, replica, Multi-AZ. Serverless: một endpoint, tự scale theo dữ liệu và request, tính theo GB và đơn vị xử lý; tiện cho tải khó đoán nhưng đắt hơn khi tải đều và lớn.
  - Failover (đưa replica lên primary và đổi DNS) thường mất vài chục giây; app phải chịu được và không dùng cache làm nguồn đúng duy nhất (bài Redis Sentinel & Cluster). MemoryDB khi cần bền dữ liệu hơn.
- **Lambda đọc SQS**: event source mapping bắt đầu 5 lời gọi đồng thời, thêm tối đa 300 mỗi phút, tới 1.250. Đặt maximum concurrency của mapping để không làm cạn connection database; đừng dùng reserved concurrency cho việc này: lời gọi bị throttle làm message quay lại queue, tăng số lần nhận và có thể rơi vào DLQ dù không lỗi. Queue FIFO thì mức song song còn bị giới hạn bởi số message group; đặt visibility timeout của queue ít nhất 6 lần timeout của function; bật `ReportBatchItemFailures` để chỉ message lỗi được giao lại thay vì cả batch.
- **Quota và throttling**: mọi API của AWS đều có giới hạn tốc độ. AWS SDK for Java v2 tự retry với backoff có jitter (số lần và thời gian chờ mặc định tuỳ chế độ retry và từng client, DynamoDB retry nhiều hơn); retry ở tầng app cộng thêm thì nhân số request lúc đã bị throttle (bài Timeout, retry, circuit breaker, bulkhead). Theo dõi metric throttle của từng dịch vụ và đặt cảnh báo trước khi chạm quota.
- **Managed hay tự vận hành**:
  - Bảng trách nhiệm: managed lo phần cứng, vá, HA, backup, nâng cấp minor; bạn vẫn lo mô hình dữ liệu, cấu hình, quyền IAM, mã hoá, giám sát và thử restore.
  - Chi phí so sánh phải gồm công người: một cụm Kafka hay Redis tự chạy cần người hiểu nó, trực đêm, nâng phiên bản. TCO và cách so sánh ở bài Build hay buy & chọn vendor.
  - Lock-in: dịch vụ giữ giao thức mở (MSK với Kafka, ElastiCache với Valkey/Redis, RDS với PostgreSQL) dễ chuyển đi; API riêng (DynamoDB, SQS, Kinesis, EventBridge) cần lớp adapter nếu tính chuyện rời đi. Đừng bọc mọi thứ trong abstraction "phòng khi đổi cloud" nếu không có kế hoạch thật: lớp đó che mất tính năng và vẫn rò rỉ ngữ nghĩa.
- **Test cục bộ**: LocalStack và DynamoDB Local qua Testcontainers giả lập API cho integration test, nhưng không giả lập đúng quota, throttling, IAM và hành vi khi lỗi; giữ một bộ test nhỏ chạy trên tài khoản AWS thật trong pipeline (bài Testcontainers).
