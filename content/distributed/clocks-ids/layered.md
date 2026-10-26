## Quick

Đồng hồ của các máy không bao giờ khớp nhau tuyệt đối ([[clock-skew|clock skew]] từ vài mili giây tới hàng giây), và giờ hệ thống có thể nhảy lùi. Ba quy tắc: **đo khoảng thời gian bằng [[monotonic-clock|monotonic clock]]** (`System.nanoTime()`); **không dùng giờ hệ thống của các máy khác nhau để quyết định cái gì xảy ra trước**, mà dùng [[lamport-clock|logical clock]] hoặc một bên cấp số thứ tự; và **chọn kiểu ID theo yêu cầu** (sắp xếp được không, sinh ở đâu, có được lộ thông tin không): sequence của database, [[uuid-v7|UUID v7]] hay [[snowflake-id|Snowflake]].

## Interview

**Hai loại đồng hồ**: [[wall-clock|wall clock]] (`System.currentTimeMillis()`, `Instant.now()`) cho biết "bây giờ là mấy giờ", nhưng có thể nhảy tới hoặc lùi khi [[ntp|NTP]] chỉnh giờ. Monotonic clock (`System.nanoTime()`) chỉ tăng, dùng để đo timeout và độ trễ, nhưng giá trị chỉ có nghĩa trong một process, không so được giữa hai máy.

**Vì sao không dùng giờ máy để xếp thứ tự**: NTP trong một data center thường giữ lệch ở mức mili giây, nhưng khi NTP hỏng hay VM vừa được khôi phục thì lệch hàng giây. Hệ thống dùng [[last-write-wins|last-write-wins]] theo timestamp của máy sẽ **mất ghi một cách im lặng**: máy có đồng hồ nhanh luôn thắng, kể cả khi ghi trước.

**Logical clock**: Lamport clock là một bộ đếm; mỗi sự kiện tăng 1, gửi kèm message, bên nhận đặt `max(của mình, nhận được) + 1`. Đảm bảo: nếu a xảy ra trước b về nhân quả thì `L(a) < L(b)`. Chiều ngược lại không đúng, nên Lamport không phát hiện được hai lần ghi **đồng thời**. [[vector-clock|Vector clock]] (mỗi node một bộ đếm) phát hiện được, nên dùng để tìm xung đột cần gộp. [[hybrid-logical-clock|Hybrid logical clock]] ghép giờ vật lý với bộ đếm: gần giờ thật mà vẫn giữ thứ tự nhân quả (CockroachDB, MongoDB).

**Sinh ID**:
- Sequence/auto-increment: nhỏ, tăng dần, nhưng phải đi qua một database và lộ số lượng.
- [[uuid-v4|UUID v4]]: sinh ở đâu cũng được, nhưng ngẫu nhiên nên làm index B-tree phân mảnh.
- UUID v7: 48 bit thời gian rồi tới bit ngẫu nhiên, gần tăng dần, 128 bit.
- Snowflake: 64 bit gồm 41 bit mili giây, 10 bit worker, 12 bit sequence. Vừa `bigint`, tăng theo thời gian, nhưng phải cấp worker id không trùng và xử lý đồng hồ chạy lùi.

## Deep

- **Snowflake tối giản** (Java 21, đã chạy thử; đồng hồ truyền vào để test được):
  ```java
  synchronized long nextId() {
      long now = clock.getAsLong();
      if (now < lastMillis) {
          now = lastMillis;                 // đồng hồ lùi: dùng tiếp mốc cũ, không sinh trùng
      }
      if (now == lastMillis) {
          sequence = (sequence + 1) & MAX_SEQUENCE;
          if (sequence == 0) {              // hết 4096 id trong mili giây này: chờ sang mili giây sau
              while ((now = clock.getAsLong()) <= lastMillis) Thread.onSpinWait();
          }
      } else {
          sequence = 0;
      }
      lastMillis = now;
      return ((now - EPOCH) << 22) | (workerId << 12) | sequence;
  }
  ```
  41 bit mili giây đủ khoảng 69 năm tính từ `EPOCH` tự chọn. Đồng hồ lùi lâu (vài giây) thì "dùng tiếp mốc cũ" sẽ cạn sequence; nhiều nơi chọn báo lỗi và cảnh báo thay vì chờ.
- **Cấp worker id** là phần khó nhất. Cấu hình tĩnh dễ trùng khi copy cấu hình; ordinal của Kubernetes StatefulSet (`pod-0`, `pod-1`) ổn định; cấp động qua [[lease]] trong etcd/ZooKeeper/Redis thì quay lại vấn đề của bài Distributed lock: process bị pause quá lease, node khác nhận cùng worker id, và hai máy sinh trùng ID.
- **JavaScript và số 64 bit**: `Number` chỉ chính xác tới 2^53. ID Snowflake vượt mốc này chỉ khoảng 25 ngày sau `EPOCH` (2^53 dịch phải 22 bit là 2^31 mili giây), nên trình duyệt làm tròn ID khi parse JSON. Trả ID dạng chuỗi trong JSON (Jackson: `@JsonSerialize(using = ToStringSerializer.class)`).
- **UUID v7 trong Java và database**: JDK 26 có `UUID.ofEpochMillis(long)`: 48 bit mili giây cộng 74 bit ngẫu nhiên, nên hai UUID trong cùng một mili giây **không** có thứ tự, và Javadoc để người gọi tự đảm bảo timestamp truyền vào không lùi. RFC 9562 cho phép dùng một phần bit làm bộ đếm để tăng dần cả trong một mili giây; thư viện như `uuid-creator` làm việc đó. PostgreSQL 18 có `uuidv7()` dùng thêm phần dưới mili giây. Lưu và so sánh trong MySQL: bài Mô hình hoá dữ liệu nâng cao.
- **[[ulid|ULID]]**: 48 bit mili giây cộng 80 bit ngẫu nhiên, viết thành 26 ký tự base32 sắp xếp được theo chữ. Cùng ý tưởng với UUID v7 nhưng không phải chuẩn RFC; dự án mới nên chọn UUID v7 để database và thư viện hỗ trợ sẵn.
- **Sequence có lỗ là bình thường**: sequence của PostgreSQL không quay lại khi transaction rollback; Hibernate `@SequenceGenerator` mặc định `allocationSize = 50` lấy trước 50 giá trị cho mỗi instance, nên mỗi instance cấp ID trong khối riêng của nó: ID không theo thứ tự thời gian tạo, và có lỗ khi restart. MySQL 8.0 mặc định `innodb_autoinc_lock_mode = 2` cũng có lỗ. Đừng dùng ID để đếm hay suy ra thứ tự commit.
- **ID tăng dần lộ thông tin**: đối thủ đặt hai đơn cách nhau một ngày là biết bạn bán bao nhiêu đơn; ID đoán được còn tiếp tay cho lỗi [[idor|IDOR]] nếu thiếu kiểm tra quyền. UUID v7 và Snowflake lộ thời điểm tạo.
- **NTP chỉnh giờ hai cách**: *slew* (chạy nhanh hoặc chậm đi chút ít cho tới khi khớp, giờ vẫn tăng) và *step* (nhảy thẳng, có thể lùi). ntpd mặc định step khi lệch quá 128 ms; chrony cấu hình bằng `makestep`. [[leap-second|Leap second]] thường được *smear* (rải 1 giây ra nhiều giờ) bởi Google và AWS; `java.time.Instant` không biểu diễn leap second.
- **Đồng hồ có cận sai số**: Google Spanner dùng [[truetime|TrueTime]] trả về khoảng `[earliest, latest]`, và **commit wait**: chờ hết độ bất định (vài mili giây) trước khi báo commit, nhờ đó thứ tự theo timestamp khớp thứ tự thật. AWS có ClockBound với ý tưởng tương tự. Không có cận sai số thì không suy ra thứ tự từ giờ được.
- **Vector clock có giá**: kích thước tăng theo số node (hoặc số client) ghi vào key; Dynamo cắt bớt khi quá dài, Riak dùng dotted version vector. Đó là lý do nhiều hệ chọn LWW cho đơn giản và chấp nhận mất ghi, hoặc dùng [[crdt|CRDT]] (bài Multi-region & active-active).
- **Thứ tự trong một luồng dữ liệu**: không cần đồng hồ khi đã có một bên xếp hàng duy nhất: offset của một partition Kafka, LSN của WAL, version của aggregate. Thiết kế để thứ tự quan trọng đi qua một nơi như vậy thay vì so timestamp.
