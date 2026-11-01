## Quick

Hệ thống metric và log là một hệ ghi nhiều, đọc ít: metric tốn theo **số [[active-series|series đang hoạt động]]** (bộ nhớ) và số sample mỗi giây, log tốn theo **lưu lượng request** (byte mỗi giây). **Kiểm soát [[metric-cardinality|cardinality]] của metric và khối lượng log ngay từ nguồn quan trọng hơn chọn database.** Phần còn lại là ghép các khối quen thuộc: thu ở gần nguồn, đệm trước khi ghi, dữ liệu mới trong bộ nhớ, dữ liệu cũ nén trên [[object-storage|object storage]].

## Interview

Tôi hỏi trước: bao nhiêu pod và service, chu kỳ scrape, mỗi pod bao nhiêu series, bao nhiêu request mỗi giây và mỗi request ghi mấy dòng log, giữ bao lâu, có nhiều team hay khách hàng (tenant) dùng chung không.

**Ước lượng**: 6.000 pod × 1.500 series là 9 triệu series; scrape 15 giây là 600.000 sample mỗi giây. Tài liệu Prometheus cho trung bình 1–2 byte mỗi sample sau nén, nhưng tuỳ dữ liệu (lab: series không đổi 0,4 byte, counter nguyên 2,2, gauge số thực 7,2), nên tôi ước 1,5–3 byte: 80–160 GB mỗi ngày. Log: 30.000 request/s × 6 dòng × 260 byte là 47 MB/s, khoảng 4 TB mỗi ngày trước khi nén.

**Metric**: Prometheus mỗi cluster scrape gần nguồn, đẩy về kho trung tâm (Mimir, Thanos, VictoriaMetrics) qua [[remote-write|remote write]]. Kho trung tâm chia series theo hash ring, nhân bản 3 bản, ghi đủ 2 bản là thành công; dữ liệu 2 giờ gần nhất trong bộ nhớ của ingester, cũ hơn thì thành block trên object storage. Query frontend chia query dài theo ngày và cache kết quả.

**Log**: agent trên node đọc stdout, có buffer đĩa, đẩy vào Kafka để chịu đỉnh; ingester ghi chunk nén. [[loki|Loki]] chỉ đánh index nhãn nên rẻ; Elasticsearch đánh index mọi từ nên tìm nhanh nhưng tốn gấp nhiều lần.

**[[downsampling|Downsampling]]**: giữ tổng, số đếm, min, max theo 5 phút và 1 giờ để xem khoảng dài nhanh. Nó không tự giảm chi phí (Thanos ghi thêm block); tiết kiệm đến từ việc rút ngắn thời gian giữ dữ liệu gốc.

**Bẫy**: nhãn `user_id` hay URL thô làm nổ series, lấy trung bình của p99 khi downsample, log DEBUG bật trên production, và hệ giám sát chết cùng lúc với hệ được giám sát.

## Deep

- **Ba con số định cỡ** (tài liệu Prometheus): đĩa = thời gian giữ × sample mỗi giây × byte mỗi sample. Bộ nhớ theo số series đang hoạt động, không theo số sample. CPU của query theo số series và số sample bị quét.
- **Bên trong [[time-series-database|TSDB]] của Prometheus**:
  - Series là tên metric cộng tập nhãn; sample là cặp (thời điểm mili giây, số `float64`). Index ngược từ cặp nhãn tới danh sách series, như [[inverted-index|inverted index]] của search engine.
  - Sample mới vào head block trong bộ nhớ và [[wal|WAL]]; mỗi 2 giờ cắt thành block bất biến trên đĩa; block được gộp dần tới 10% thời gian giữ hoặc 31 ngày. Mặc định giữ 15 ngày.
  - Sample đến sai thứ tự bị từ chối, trừ khi đặt `out_of_order_time_window` trong khối `storage.tsdb` (từ Prometheus 2.39; Mimir có giới hạn cùng tên theo tenant).
- **Nén XOR** ([[gorilla-compression|kiểu Gorilla]], lab Java cài theo XOR chunk của Prometheus, 120 sample mỗi chunk, 120.000 sample):
  - Thời điểm lưu chênh lệch của chênh lệch: scrape đều đặn thì 1 bit mỗi sample. Giá trị lưu XOR với giá trị trước: không đổi thì 1 bit.
  - Byte mỗi sample khi thời điểm đều tuyệt đối: `up` không đổi 0,40; counter tăng theo số nguyên 2,19; tổng thời gian `_sum` 6,05; gauge số thực đủ độ chính xác 7,17; gauge làm tròn 2 chữ số 5,80.
  - Thời điểm lệch ±20 ms: mọi loại tăng thêm khoảng 1,8 byte (16 bit cho chênh lệch thời điểm). Từ 2.30, Prometheus căn thời điểm scrape lệch rất ít (mặc định dưới 2 ms) về đúng lịch để giữ chênh lệch bằng 0.
  - Trung bình 1–2 byte của tài liệu có được vì rất nhiều series gần như không đổi giữa hai lần scrape: `up`, counter lỗi đứng ở 0, bucket cao của histogram. Hệ nhiều gauge số thực tốn hơn; khi ước lượng nên dùng một khoảng.
- **Cardinality**:
  - Số series của một metric là tích số giá trị của mọi nhãn. Histogram cổ điển nhân thêm số bucket cộng `_sum` và `_count`: timer của Micrometer khi bật percentile histogram khoảng 70 series mỗi tổ hợp nhãn (bài Micrometer & tracing).
  - Ví dụ: 20 URI × 4 mã trạng thái × 70 bucket là 5.600 series mỗi pod. Thêm nhãn `customer_id` với 5.000 khách là 28 triệu series mỗi pod nếu mỗi pod gặp mọi khách.
  - Chặn ở nhiều tầng: `sample_limit` và `label_limit` đặt trong job scrape, áp cho từng target, tính sau `metric_relabel_configs` (vượt thì cả lần scrape bị bỏ và `up` về 0; alert theo `prometheus_target_scrapes_exceeded_sample_limit_total`); [[relabeling|relabel]] để bỏ metric; giới hạn series theo tenant ở kho trung tâm. Tìm thủ phạm: `/api/v1/status/tsdb` của Prometheus, API cardinality của Mimir (`/api/v1/cardinality/label_names`).
  - Bỏ nhãn bằng relabel chỉ an toàn khi nhãn đó không phân biệt series. Bỏ `request_id` thì nhiều series trùng tập nhãn trong một lần scrape, sample bị loại như bản trùng chứ không được cộng. Muốn gộp thì sửa ở code (route template thay URL thô) hoặc dùng recording rule `sum without (...)`.
  - [[native-histogram|Native histogram]] lưu cả phân bố trong một series với bucket theo hàm mũ, thay cho hàng chục series bucket. Stable từ Prometheus 3.8, nhưng phải bật `scrape_native_histograms` khi scrape và `send_native_histograms` cho remote write; client phải xuất kiểu này (client_java 1.x), histogram cổ điển không tự chuyển.
- **Remote write**:
  - Prometheus đọc WAL rồi gửi theo lô, nén snappy, chia nhiều shard song song, tự retry. Tài liệu Prometheus: kho trung tâm sập dưới khoảng 2 giờ thì gửi bù không mất; lâu hơn thì WAL bị compact và phần chưa gửi mất.
  - Chế độ agent: chỉ scrape và remote write, không query, không chạy rule hay alert, tốn ít bộ nhớ hơn. WAL chỉ bị cắt khi đã gửi xong (tới `--storage.agent.retention.max-time`), nên chịu sự cố kho trung tâm lâu hơn; đổi lại recording rule và alert phải chuyển lên kho trung tâm.
  - Thanos có hai kiểu: sidecar tải block 2 giờ lên object storage (không cần remote write, nhưng dữ liệu mới nằm ở Prometheus), hoặc Receive nhận remote write như Mimir.
- **Ghi ở kho trung tâm** (Mimir):
  - Distributor kiểm nhãn, áp giới hạn theo tenant (vượt tốc độ ghi thì HTTP 429 và Prometheus retry; vượt số series thì series mới bị từ chối bằng lỗi 4xx và mất), chia series bằng hash ring ([[consistent-hashing|consistent hashing]]) và ghi [[replication-factor|3 bản]], cần [[quorum|quorum]] 2 bản. Mất 2 ingester cùng lúc có thể mất cả đọc lẫn ghi; chia bản sao theo zone.
  - Prometheus chạy cặp HA để không mất số khi một con chết. Hai con gửi trùng, distributor giữ một nguồn và bỏ nguồn kia theo nhãn cluster và replica ([[replica-dedup|khử trùng lặp]]).
  - Mimir 3.0 đưa kiến trúc ingest storage làm hướng chính (kiến trúc cổ điển vẫn được hỗ trợ): Kafka nằm giữa distributor và ingester, ghi thành công khi Kafka commit, ingester chỉ đọc để phục vụ query, nên ingester chết không chặn ghi.
  - Ingester tải block lên object storage mỗi 2 giờ; compactor gộp block và bỏ bản trùng do nhân bản. Compactor của Mimir không giảm độ phân giải.
- **Đọc**: query frontend chia query 30 ngày thành 30 query một ngày chạy song song và cache kết quả theo ngày đã xong; store gateway chỉ tải phần index cần từ object storage. Đặt giới hạn số series và số chunk mỗi query, nếu không một dashboard có thể làm sập querier.
- **Downsampling** (Thanos, lab Java):
  - Compactor tạo bản 5 phút cho dữ liệu cũ hơn 40 giờ và bản 1 giờ cho dữ liệu cũ hơn 10 ngày. Mỗi điểm lưu `count`, `sum`, `min`, `max` và `counter`; mỗi độ phân giải có retention riêng.
  - Tài liệu Thanos nói rõ mục tiêu là query khoảng dài nhanh, không phải tiết kiệm chỗ: giữ cả ba độ phân giải có thể tốn tới khoảng 3 lần.
  - p99 nền 120 ms, spike 3 phút lên 2.400 ms: trung bình 5 phút còn 1.489 ms, trung bình 1 giờ chỉ 234 ms; `max` vẫn giữ 2.498. Nhìn trung bình là mất sự cố.
  - Counter có pod restart giữa giờ: lấy cuối trừ đầu ra 178.500 request thay vì 360.000. Phải tính có xử lý reset như `rate()`, vì vậy bản downsample giữ riêng aggregate `counter`.
- **[[recording-rule|Recording rule]]**: tính sẵn biểu thức hay dùng (`sum by (service) (rate(...[5m]))`) thành series mới. Bỏ nhãn `pod` giảm theo số pod mỗi service (15 pod là 15 lần); chỉ giữ lâu vài chục metric đã gộp thay vì mọi series mới giảm hàng trăm lần. Đây là đòn giảm chi phí lớn nhất cho dữ liệu lâu.
  - Retention của Mimir đặt theo tenant, không theo series. Muốn series gộp sống 13 tháng còn series gốc vài tuần thì ghi series gộp sang tenant riêng: recording rule chạy ở Prometheus mỗi cluster, remote write thứ hai với `write_relabel_configs` chỉ giữ series `service:...`. Thanos đặt retention theo độ phân giải, cũng không theo metric.
- **Đường log**:
  - Agent trên node (Fluent Bit, Vector, OpenTelemetry Collector) đọc stdout, buffer ra đĩa khi đích chậm, gắn nhãn Kubernetes. Trên Kubernetes, container runtime ghi stdout ra file trong `/var/log/pods` và kubelet xoay vòng (mặc định 10 MiB × 5 file); agent chỉ tail các file đó. Agent chậm hơn tốc độ xoay thì mất log chứ không chặn ứng dụng; ứng dụng bị chặn khi đĩa node bão hoà I/O, hoặc khi appender gửi log đồng bộ qua mạng (bài Logging trên production).
  - Kafka ở giữa chịu đỉnh và sự cố của kho log; một consumer (Grafana Alloy, Vector) đọc Kafka rồi đẩy vào Loki. Theo dõi lag để biết log đến trễ bao lâu. Chia partition theo tenant cộng hash, để tenant lớn không dồn vào một partition nóng.
  - Loki: stream là một tổ hợp nhãn; chunk mục tiêu khoảng 1 MB nén (5–10 MB log thô). Quá nhiều stream thì chunk nhỏ, flush sớm, index phình. Tenant rất lớn (trên 10 TB/ngày) nên giữ dưới 100.000 stream đang hoạt động. `trace_id`, `order_id` để trong nội dung hay structured metadata, không làm nhãn.
  - Nén: lab 200.000 dòng JSON 261 byte, gzip (mặc định `chunk_encoding` của Loki) nhỏ hơn 7,2 lần; trace id ngẫu nhiên là phần nén kém nhất. Tài liệu Loki khuyên snappy khi lưu lượng lớn: nhanh hơn nhưng nén kém hơn, nên ước dung lượng theo một khoảng.
  - Elasticsearch đánh index mọi trường và mọi từ, cộng replica: tìm `order_id` trong 90 ngày tức thì, nhưng chi phí đĩa và vận hành lớn hơn nhiều; hợp cho log bảo mật và audit cần tìm kiếm nhanh. Kho theo cột như ClickHouse hay Doris là lựa chọn ở giữa (bài OLAP).
- **Giảm khối lượng log**: bỏ log health check, [[log-sampling|lấy mẫu]] log INFO của request thành công nhưng giữ mọi WARN và ERROR, đổi sự kiện lặp lại thành metric đếm, giới hạn tốc độ theo tenant và stream ([[noisy-neighbor|noisy neighbor]]). Retention theo mức: DEBUG vài ngày, INFO vài tuần, audit theo yêu cầu pháp lý.
- **Đa tenant**: header tenant (`X-Scope-OrgID` ở Mimir và Loki) tách dữ liệu và giới hạn; một team bật nhãn sai chỉ chạm giới hạn của team đó. Mimir và Loki tin header này, nên nó phải do gateway có xác thực đặt; để agent tự đặt thì team này ghi được vào tenant của team khác.
- **Giám sát hệ giám sát**: đặt meta-monitoring ở cụm hoặc tài khoản khác; alert [[deadman-switch|dead man's switch]] luôn bật gửi tới dịch vụ bên ngoài, ngừng nhận là biết đường alert đã hỏng. Alertmanager chạy nhiều bản thành cụm; Prometheus phải gửi alert tới mọi bản, không qua load balancer, thì cụm mới khử trùng lặp thông báo được.
- **Metric, log hay trace**: đếm thì dùng metric, chi tiết lỗi dùng log, thời gian từng bước dùng trace; nối ba thứ bằng trace id và [[exemplar|exemplar]] (bài Metrics, tracing & SLO).
