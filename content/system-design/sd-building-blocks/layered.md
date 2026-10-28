## Quick

Mỗi khối giải một bài toán: [[load-balancer|load balancer]] chia tải và bỏ qua instance hỏng, [[cache]] giảm lượt đọc tốn kém, [[cdn|CDN]] đưa nội dung tĩnh tới gần người dùng, [[message-queue|queue]] tách việc chậm khỏi request và hấp thụ đỉnh, database giữ dữ liệu có cấu trúc, [[object-storage|object storage]] giữ file lớn, search engine tìm theo nội dung. **Database (và object storage, với file) là [[source-of-truth|nguồn sự thật]]; cache, CDN, search là bản sao phải dựng lại được. Mỗi khối thêm vào phải trả lời được "nó giải bài toán gì" và "giá là gì".**

## Interview

Tôi đi theo đường của một request và chỉ thêm khối khi có lý do.

**App server [[stateless|stateless]] sau load balancer**: session và file không nằm trên máy app, nên LB gửi request tới instance nào cũng được, và [[horizontal-scaling|scale ngang]] chỉ là thêm instance. LB kiểm [[health-check|health check]] để rút instance hỏng.

**Database** là nguồn sự thật. Mặc định chọn relational vì có transaction và query linh hoạt; chọn NoSQL khi [[access-pattern|access pattern]] rõ và quy mô vượt một máy. Đọc nhiều thì thêm [[read-replica|read replica]] (giá: [[replica-lag|replica lag]]); ghi vượt một máy thì [[sharding]].

**Cache** đặt trước database cho dữ liệu đọc nhiều, ít đổi. Hit ratio 95% nghĩa là database chỉ nhận 1/20 lượt đọc. Giá: dữ liệu cũ trong [[ttl|TTL]], và khi cache sập, toàn bộ tải dồn về database.

**CDN** cho ảnh, JS, CSS và response public: trả từ [[edge-location|edge]] gần người dùng, giảm latency và băng thông của origin.

**Queue** cho việc không cần làm ngay (gửi mail, tạo thumbnail): request trả về nhanh, worker xử lý theo sức mình, đỉnh tải thành backlog thay vì lỗi. Giá: xử lý bất đồng bộ, message có thể đến hai lần nên consumer phải [[idempotent-consumer|idempotent]].

**Object storage** cho file: client upload thẳng bằng [[presigned-url|presigned URL]], database chỉ giữ key và metadata.

**Search** cho tìm theo nội dung và xếp hạng; dữ liệu đồng bộ từ database qua [[cdc|CDC]].

Bẫy hay gặp khi phỏng vấn: vẽ đủ mọi khối ngay từ đầu mà không gắn với yêu cầu nào. Mỗi khối là một thứ phải vận hành, một chỗ có thể hỏng và một bản sao có thể lệch.

## Deep

- **Stateless là điều kiện để scale ngang**: session giữ trong bộ nhớ app thì phải dùng [[sticky-session|sticky session]], instance chết là mất session, và scale thêm máy không chia lại người dùng cũ. Đưa session vào Redis hoặc token, file vào object storage, job định kỳ ra khỏi app hoặc có khoá. [[vertical-scaling|Scale dọc]] (máy to hơn) vẫn là bước đầu hợp lý cho database, vì nó không đổi kiến trúc; trần của nó là máy lớn nhất mua được và một [[single-point-of-failure|điểm hỏng duy nhất]].
- **Load balancer cũng không được là điểm hỏng duy nhất**: LB managed của cloud chạy nhiều node qua nhiều [[availability-zone|AZ]], tự dựng thì cần cặp active-standby. L4/L7, thuật toán chia tải và connection draining ở bài Load balancing.
- **Cache: tính bằng hit ratio**: tải về database = tổng lượt đọc × (1 − hit ratio). Từ 95% xuống 90% nghe nhỏ nhưng tải database **gấp đôi** (5% thành 10%). Cache mất hết (restart Redis, đổi format key) thì database nhận 100%, gấp 20 lần lúc bình thường: phải tính database có chịu nổi không, hoặc có cơ chế làm ấm và giới hạn. Các tầng cache và chính sách eviction ở bài Cache là gì & cache ở đâu; stampede, hot key ở bài Stampede, penetration, avalanche, hot key.
- **CDN không chỉ cho file tĩnh** nhưng lợi nhất ở đó. Response cá nhân hoá (giỏ hàng, trang tài khoản) gần như không cache được ở edge; CDN vẫn giúp ở TLS gần người dùng và kết nối giữ sẵn về origin. Xoá cache (purge) chậm và có giới hạn, nên file tĩnh dùng tên có hash nội dung thay vì purge. Chi tiết ở bài DNS & CDN.
- **Queue không làm hệ thống xử lý nhanh hơn**: nó chỉ dời việc sang sau. Nếu tốc độ đến trung bình lớn hơn tốc độ xử lý, backlog tăng mãi; queue chỉ hấp thụ được **đỉnh ngắn**. Theo dõi độ dài queue và tuổi message cũ nhất ([[consumer-lag|consumer lag]]), không chỉ CPU của worker. Queue khác log kiểu Kafka (giữ message để đọc lại) thế nào ở bài Messaging cơ bản và Kiến trúc Kafka.
- **Các loại database theo access pattern**: relational (PostgreSQL, MySQL) cho dữ liệu nghiệp vụ có quan hệ và transaction; [[key-value-store|key-value]] cho đọc theo khoá với latency thấp; [[document-database|document]] cho aggregate đọc nguyên khối; [[wide-column-store|wide-column]] cho ghi rất lớn và đọc dải theo partition; [[time-series-database|time-series]] cho metric theo thời gian; [[graph-database|graph]] cho truy vấn nhiều bước quan hệ. Báo cáo phân tích trên hàng trăm triệu dòng thuộc về [[data-warehouse|data warehouse]] (lưu theo cột), đừng chạy trên primary của hệ [[oltp|OLTP]]. So sánh chi tiết ở bài NoSQL: chọn loại nào.
- **Read replica chỉ scale đọc**: mọi ghi vẫn vào primary. Đọc ngay sau ghi từ replica có thể không thấy dữ liệu vừa ghi ([[read-your-writes|read-your-writes]]); các luồng như "vừa đặt hàng xong, mở trang đơn" nên đọc từ primary. Ghi vượt một máy mới cần sharding, và đó là quyết định đắt: query và transaction xuyên shard trở nên khó. Xem bài Replication & high availability và bài Sharding.
- **Object storage không phải file system**: không gian tên phẳng theo key (dấu `/` chỉ là một phần của key), không sửa một phần object mà ghi đè cả object, đổi tên là copy rồi xoá. Đổi lại nó rẻ, gần như vô hạn và rất bền (S3 thiết kế cho độ bền 11 số 9). Với S3: một PUT tối đa 5 GB, file lớn hơn dùng [[multipart-upload|multipart upload]] (tới 50 TB); latency đọc object nhỏ khoảng 100–200 ms nên đặt CDN phía trước khi phục vụ người dùng. Từ 12/2020 S3 nhất quán mạnh read-after-write: đọc ngay sau khi ghi thấy bản mới.
- **Đừng lưu file trong database**: BLOB lớn làm phình backup, replication và buffer pool, và mỗi lượt tải file chiếm một connection. Mẫu chuẩn: database giữ key, kích thước, checksum, chủ sở hữu; file nằm ở object storage; client tải lên và tải về bằng presigned URL có thời hạn, file không đi qua app server. Presigned PUT không tự giới hạn loại file hay dung lượng: dùng presigned POST với policy giới hạn kích thước, hoặc kiểm tra (và quét virus) sau khi upload xong rồi mới đánh dấu file dùng được. Đặt lifecycle rule xoá multipart upload dở dang, nếu không chúng vẫn bị tính tiền.
- **Search engine không là database chính**: [[inverted-index|inverted index]] cho tìm full-text và xếp hạng, nhưng dữ liệu chỉ thấy được sau khoảng 1 giây ([[near-real-time|near real-time]]) và phải dựng lại được từ database. Dữ liệu vừa phải thì full-text search của PostgreSQL thường đủ. Xem bài Search engine & Elasticsearch.
- **Mỗi bản sao là một bài toán đồng bộ**: ghi database rồi ghi cache, search, queue trong cùng một request là [[dual-write|dual write]]; một bước lỗi là lệch vĩnh viễn. Dùng [[outbox|transactional outbox]] hoặc CDC để các bản sao đi theo database, xem bài Transactional outbox & CDC. Thêm khối nào cũng phải trả lời: khi nó chết thì sao, và khi nó lệch với database thì ai sửa.
- **Thứ tự hay dùng khi scale một hệ đọc nhiều**: tối ưu query và index → cache → read replica → CDN cho phần tĩnh → tách việc nặng sang queue → mới tới sharding. Con số cụ thể quyết định dừng ở bước nào; cách ước lượng ở bài Ước lượng nhanh, cách trình bày trong buổi phỏng vấn ở bài Khung trả lời System Design.
