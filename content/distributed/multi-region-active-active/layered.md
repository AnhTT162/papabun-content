## Quick

Chạy hệ thống ở nhiều region để giảm độ trễ cho người dùng ở xa, sống sót khi mất cả một region, và giữ dữ liệu trong vùng pháp lý yêu cầu. [[active-passive|Active-passive]] (một region nhận ghi, region kia chờ) đơn giản; [[active-active|active-active]] (nhiều region cùng nhận ghi) buộc chọn giữa **ghi đồng bộ liên region** (chậm thêm 50–200 ms mỗi lần ghi) và **ghi bất đồng bộ** (nhanh nhưng có xung đột phải giải quyết). **Cách bền nhất là tránh xung đột: mỗi bản ghi có một [[home-region|home region]] duy nhất nhận ghi**, các region khác chỉ đọc bản sao.

## Interview

**Ba mô hình**:
1. Active-passive: region phụ nhận bản sao bất đồng bộ, chỉ được promote khi region chính chết. [[rpo-rto|RPO]] lớn hơn 0 (mất phần chưa kịp sao chép), RTO tính bằng phút.
2. Active-active cho đọc: mọi region phục vụ đọc từ replica cục bộ, ghi đi về một region chính. Phổ biến và dễ nhất.
3. Active-active cho ghi: mọi region nhận ghi. Khi hai region sửa cùng một bản ghi trước khi kịp sao chép cho nhau thì có xung đột.

**Giải quyết xung đột**: [[last-write-wins|last-write-wins]] (DynamoDB global tables mặc định, Cassandra) đơn giản nhưng âm thầm bỏ một lần ghi; [[crdt|CRDT]] gộp được không mất dữ liệu nhưng chỉ cho một số kiểu (bộ đếm, tập hợp); gộp theo nghiệp vụ (giỏ hàng lấy hợp hai bên) cần code riêng. Tốt nhất là **không để xung đột xảy ra**: chia dữ liệu theo người dùng hoặc tenant, mỗi phần có home region; ghi từ region khác được chuyển tiếp về đó. Hệ thống vẫn active-active, nhưng mỗi bản ghi chỉ có một nơi ghi.

**Dữ liệu cần nhất quán mạnh** (số dư, tồn kho, tên đăng nhập duy nhất) không chịu được LWW: đi qua một region duy nhất, hoặc dùng database [[consensus|consensus]] trải ba region (Spanner, CockroachDB, DynamoDB chế độ strong consistency) và chấp nhận mỗi lần ghi chờ RTT liên region.

**Định tuyến**: [[geodns|GeoDNS]] hoặc định tuyến theo độ trễ đưa người dùng tới region gần; [[anycast]] đưa vào mạng của nhà cung cấp ở điểm gần nhất. Health check tự rút region hỏng ra.

**Bẫy hay gặp**: người dùng ghi ở region A rồi đọc ở region B thấy dữ liệu cũ ([[read-your-writes|read-your-writes]] bị vỡ); unique constraint chỉ đúng trong một region; ID trùng nếu mỗi region tự đánh sequence; failover chưa bao giờ diễn tập; và chi phí: hạ tầng gấp đôi cộng phí truyền dữ liệu liên region tính theo GB.

## Deep

- **CRDT đơn giản nhất, G-Counter** (Java 21, đã chạy thử): mỗi region chỉ tăng phần của mình, gộp lấy `max` từng phần, giá trị là tổng. Gộp bao nhiêu lần, theo thứ tự nào cũng ra cùng kết quả.
  ```java
  record GCounter(Map<String, Long> counts) {
      GCounter increment(String region, long n) {
          var copy = new HashMap<>(counts);
          copy.merge(region, n, Long::sum);
          return new GCounter(copy);
      }
      GCounter merge(GCounter other) {
          var copy = new HashMap<>(counts);
          other.counts().forEach((region, n) -> copy.merge(region, n, Math::max));
          return new GCounter(copy);
      }
      long value() { return counts.values().stream().mapToLong(Long::longValue).sum(); }
  }
  ```
  Bộ đếm giảm được thì dùng PN-Counter (hai G-Counter, tăng và giảm). Tập hợp có xoá thì dùng OR-Set. Không có CRDT nào cho "số dư không được âm": ràng buộc toàn cục cần phối hợp.
- **DynamoDB global tables**: chế độ mặc định (MREC) sao chép bất đồng bộ, thường dưới một giây, xung đột giải bằng last writer wins theo từng item. Chế độ MRSC sao chép đồng bộ tới ít nhất một region khác trước khi trả lời, phải triển khai đúng ba region (ba bản sao, hoặc hai bản sao cộng một witness), và conditional write luôn kiểm tra trên bản mới nhất.
- **Aurora Global Database**: một region ghi, các region phụ chỉ đọc với độ trễ sao chép thường dưới một giây; write forwarding cho phép ứng dụng ở region phụ gửi ghi, Aurora chuyển về region chính. Đây là active-active cho đọc, không phải cho ghi.
- **Spanner, CockroachDB**: consensus trên từng range dữ liệu, có thể đặt leader của range gần người dùng sở hữu nó. CockroachDB có bảng `REGIONAL BY ROW` (mỗi dòng có home region), bảng `GLOBAL` (đọc nhanh mọi nơi, ghi chậm), và mục tiêu `SURVIVE REGION FAILURE` cần ít nhất ba region.
- **PostgreSQL hai chiều**: logical replication từ bản 16 có `origin = none` để không gửi vòng lại thay đổi vừa nhận. Không có phát hiện hay giải quyết xung đột: trùng khoá làm apply worker lỗi và thử lại liên tục (hoặc tự tắt subscription nếu đặt `disable_on_error`); hai bên cùng sửa một dòng gần như cùng lúc thì mỗi bên áp bản của bên kia, và hai node **lệch nhau âm thầm**, không lỗi nào. PostgreSQL 18 có đếm xung đột trong `pg_stat_subscription_stats` nhưng vẫn không tự giải. Muốn multi-master thật thì dùng sản phẩm chuyên dụng, và vẫn nên thiết kế tránh xung đột.
- **Cassandra**: `NetworkTopologyStrategy` đặt số bản sao cho từng data center; `LOCAL_QUORUM` chỉ chờ quorum trong region của mình (nhanh, xung đột giải bằng timestamp từng cột), `EACH_QUORUM` chờ quorum ở mọi region (chậm, mất một region là ghi lỗi).
- **Kafka giữa các region**: MirrorMaker 2 sao chép topic và đặt tiền tố tên cluster nguồn (`sg.orders` ở cluster Frankfurt) để không lặp vòng, và dịch offset của consumer group để consumer chuyển region tiếp tục được. Consumer phải [[idempotency|idempotent]] vì sau failover có thể đọc lại một phần.
- **Unique toàn cục** (email, username): ghi qua một region "toàn cục" duy nhất, hoặc bảng giữ chỗ trên database consensus; kiểm tra cục bộ ở mỗi region sẽ để lọt hai người cùng tên trong khoảng trễ sao chép. **ID**: UUID v7, hoặc Snowflake với bit worker gồm cả mã region (bài Đồng hồ, thứ tự & sinh ID).
- **Read-your-writes khi người dùng đổi region**: gắn người dùng vào home region (cookie hoặc token chứa region), hoặc kèm "phiên bản đã ghi" trong session và để region đọc chờ replica đuổi kịp phiên bản đó, nếu không thì chuyển đọc về home region.
- **Failover giữa region**: DNS TTL 60 giây nhưng client và JVM có thể cache lâu hơn (`networkaddress.cache.ttl`), nên anycast hoặc load balancer toàn cục chuyển nhanh hơn. Đừng để hai region tự promote khi chỉ mất đường nối giữa chúng: cần [[witness]] ở region thứ ba hoặc quyết định của con người, nếu không là [[split-brain|split brain]] cấp region. Failback khó hơn failover: các lần ghi chưa kịp sao chép khỏi region cũ phải đối soát bằng tay trước khi region đó nhận lại vai.
- **[[cell-based-architecture|Cell-based architecture]]**: chia người dùng thành nhiều cell độc lập (mỗi cell một bộ đầy đủ service và database), cell nằm trong một region. Lỗi hay đợt triển khai hỏng chỉ ảnh hưởng một cell; home region trở thành "home cell".
- **Chi phí và độ phức tạp**: mọi thay đổi schema, mọi cache, mọi job định kỳ phải nghĩ cho nhiều region (job chạy ở đâu, cache invalidation lan thế nào). Nhiều hệ thống chỉ cần multi-AZ trong một region cộng sao lưu sang region khác; multi-region active-active chỉ đáng khi yêu cầu độ trễ toàn cầu hoặc khả dụng khi mất cả region thật sự đến từ nghiệp vụ.
