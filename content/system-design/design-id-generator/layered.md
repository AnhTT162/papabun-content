## Quick

Bộ sinh ID phân tán phải cho ID **duy nhất mà không cần phối hợp qua mạng ở mỗi lần sinh**. Ba họ chính: **[[segment-allocation|cấp theo khối]] từ database** (ID nhỏ, đơn giản, nhưng không theo thời gian giữa các instance), **[[snowflake-id|Snowflake]]** (64 bit, gần tăng theo thời gian, cần [[worker-id|worker id]] không trùng và đồng hồ không lùi) và **[[uuid-v7|UUID v7]]** (128 bit, không cần phối hợp). ID theo thời gian chỉ **gần có thứ tự** ([[k-sorted]]); cần thứ tự chặt thì cấp số trong phạm vi một thực thể.

## Interview

Tôi hỏi trước: ID có phải vừa cột `bigint` không, có cần sắp xếp theo thời gian không, bao nhiêu ID mỗi giây, có lộ ra cho khách hàng không, và có nhiều region không. Giả định: 64 bit, gần theo thời gian để phân trang và lưu trữ, đỉnh 50.000 ID/giây, vài trăm pod.

**Phương án**:
- **Auto-increment một database**: đơn giản nhưng mỗi ID một round-trip và database là [[single-point-of-failure|SPOF]].
- **Cấp theo khối**: mỗi instance `UPDATE id_alloc SET max_id = max_id + step` lấy một khối 100.000 số rồi cấp trong bộ nhớ, nạp trước khối sau khi dùng 10%. Database chỉ bị gọi vài lần mỗi phút. Nhược điểm: instance A cấp 1–100.000, B cấp 100.001–200.000, nên ID không theo thời gian giữa các instance.
- **Snowflake**: 41 bit mili giây, 10 bit worker, 12 bit sequence, sinh hoàn toàn cục bộ, khoảng 70 năm và 4.096 ID mỗi mili giây mỗi worker.
- **UUID v7**: không cần phối hợp gì, nhưng 128 bit không vừa `bigint`.

Tôi chọn Snowflake. Phần khó không phải ghép bit mà là hai thứ:

**Worker id**: không lấy `hash(hostname) % 1024`: 50 pod có xác suất trùng 70%. Pod khởi động xin một worker id còn trống qua [[lease]] trong database hoặc etcd, gia hạn định kỳ, và **ngừng sinh** nếu không gia hạn được trước khi lease hết hạn.

**Đồng hồ**: lùi vài mili giây thì chờ; lùi nhiều thì ngừng sinh và cảnh báo. Lưu mốc thời gian cuối cùng của mỗi worker id cùng lease, để pod mới nhận lại worker id đó chờ đồng hồ vượt mốc rồi mới sinh.

**Thứ tự**: một worker tăng dần, nhưng giữa các worker chỉ đúng trong phạm vi [[clock-skew|clock skew]]. Cần thứ tự chặt, như tin nhắn trong một cuộc chat, thì cấp sequence theo cuộc chat.

Bẫy hay gặp: phân trang "lấy ID lớn hơn X" bỏ sót dòng có ID nhỏ commit muộn, lộ số đơn mỗi ngày qua ID, và ID 64 bit bị JavaScript làm tròn.

## Deep

- **Ticket server** ([[ticket-server]], cách của Flickr): hai MySQL, một máy `auto_increment_increment = 2, auto_increment_offset = 1`, máy kia offset 2; mỗi ID là `REPLACE INTO Tickets64 (stub) VALUES ('a'); SELECT LAST_INSERT_ID();`. Một máy chết thì máy kia vẫn cấp. Giá: mỗi ID một round-trip, hai máy lệch nhịp nên ID không theo thời gian, và thêm máy thứ ba phải đổi bước của cả cụm.
- **Cấp theo khối chi tiết**: bảng `id_alloc(biz_tag, max_id, step)`; PostgreSQL: `UPDATE id_alloc SET max_id = max_id + step WHERE biz_tag = 'order' RETURNING max_id`, khối là `(max_id - step, max_id]`. Dòng bị khoá chỉ trong lúc UPDATE, nên hàng trăm instance tranh nhau vẫn ổn khi mỗi khối dùng được vài chục giây. Sequence của PostgreSQL với `INCREMENT BY 100000` làm cùng việc mà không khoá dòng (`nextval` không nằm trong transaction); Hibernate `pooled` với `allocationSize` cũng là cấp theo khối (bài Đồng hồ, thứ tự & sinh ID).
- **[[double-buffering|Đệm kép]]**: 5.000 ID/giây với khối 100.000 thì một khối dùng 20 giây. Nạp khối sau bằng thread nền khi khối hiện tại đã dùng 10%: database chết ngay sau lần nạp thì còn chạy được khoảng 38 giây (90% khối hiện tại cộng khối dự phòng), chết ngay sau khi chuyển khối thì khoảng 20 giây. Không nạp trước thì mỗi lần hết khối, request đứng chờ database, và database chết là cấp ID chết ngay khi khối cạn. Leaf của Meituan còn tự nhân đôi `step` khi một khối dùng hết dưới 15 phút, để số lần gọi database không tăng theo lưu lượng.
- **Khối làm mất thứ tự và để lỗ**: pod restart bỏ phần còn lại của khối; ID không cho biết cái nào tạo trước. Không sao với khoá chính, nhưng đừng dùng ID khối để sắp xếp theo thời gian.
- **Chọn số bit**: ba con số quyết định là tuổi thọ, số worker, tốc độ mỗi worker. 41 bit mili giây là 69,7 năm: epoch 2026-01-01 dùng tới tháng 9/2095; epoch của Twitter (11/2010) hết vào 7/2080. Tổng 41 + 10 + 12 = 63 bit để bit dấu luôn 0 (ID dương trong `long`). Sonyflake chọn 39 bit theo đơn vị 10 ms (174 năm), 16 bit máy, 8 bit sequence: 256 ID mỗi 10 ms, tức 25.600 ID/giây mỗi máy. Instagram dùng 41 bit mili giây, 13 bit shard logic, 10 bit sequence, sinh ngay trong PostgreSQL bằng hàm PL/pgSQL của từng shard, nên đọc ID là biết shard để định tuyến.
- **Nút thắt là ngân sách bit, không phải CPU**: generator `synchronized` một thread trên JDK 27 (máy M4) đạt khoảng 4,1 triệu ID/giây, đúng trần 4.096 mỗi mili giây; vượt trần thì nó chờ sang mili giây sau. Cần nhiều hơn thì thêm worker, không tối ưu code.
- **Worker id trùng là ID trùng**: `hash(tên pod) % 1024` theo [[birthday-paradox|nghịch lý ngày sinh]] có xác suất trùng 17% với 20 pod, 70% với 50 pod (mô phỏng 100.000 lần: 70,5%), 99,3% với 100 pod. Cách đúng: ordinal của [[statefulset|StatefulSet]] (`pod-0`, `pod-1`) nếu chấp nhận StatefulSet; hoặc lease trong bảng database, etcd hay ZooKeeper (node tuần tự ephemeral). Lease có vấn đề của bài Distributed lock & fencing token: process bị dừng (GC dài, VM bị treo) quá hạn lease, pod khác nhận cùng worker id, pod cũ tỉnh dậy vẫn sinh. Giảm rủi ro: ngừng sinh khi thời gian từ lần gia hạn thành công cuối (đo bằng [[monotonic-clock|monotonic clock]]) vượt khoảng an toàn ngắn hơn lease.
- **Kích thước pool worker id**: pod chết vẫn giữ worker id tới khi lease hết hạn. Rollout thay 400 pod trong vài phút với lease 5 phút cần tới 800 id nếu pod cũ không trả; pod tắt êm phải xoá lease của mình, và số bit worker phải dư cho phần pod chết bất thường.
- **Đồng hồ lùi sau restart**: generator chỉ nhớ `lastMillis` trong bộ nhớ. Máy restart với đồng hồ chậm hơn lúc trước, nhận lại đúng worker id cũ, là sinh lại các ID đã cấp. Leaf-snowflake ghi mốc thời gian lên ZooKeeper vài giây một lần và khi khởi động từ chối chạy nếu đồng hồ cục bộ nhỏ hơn mốc đó. Cách NTP chỉnh giờ (slew, step) ở bài Đồng hồ, thứ tự & sinh ID.
- **Thứ tự chỉ gần đúng** (đã chạy): worker A và B lệch đồng hồ 5 ms; đơn trên A tạo trước, đơn trên B tạo sau 2 ms lại có ID nhỏ hơn. Muốn thứ tự chặt trong một phạm vi thì cấp số trong phạm vi đó: `UPDATE conversations SET last_seq = last_seq + 1 WHERE id = ? RETURNING last_seq` cho tin nhắn của một cuộc chat, hay offset của một partition Kafka.
- **Phân trang theo ID bỏ sót dòng**: ID được cấp **trước** khi transaction commit. Job đồng bộ đọc `WHERE id > :last` thấy ID 1005 đã commit, ghi nhớ 1005, rồi transaction giữ ID 1003 mới commit: dòng 1003 không bao giờ được đọc. Đúng với mọi bộ sinh, kể cả sequence. Cách xử lý: chỉ đọc dòng cũ hơn vài giây so với hiện tại (chấp nhận trễ), hoặc đọc theo thứ tự commit qua CDC, [[outbox]] hay LSN.
- **Thư viện hay dịch vụ**: dịch vụ ID tập trung (gọi qua HTTP/gRPC) thêm một round-trip và thành điểm chết của mọi lệnh ghi, trừ khi client lấy ID theo lô. Thư viện nhúng trong mỗi service (Snowflake với lease, hoặc cấp theo khối) chỉ cần kho phối hợp lúc khởi động và lúc gia hạn.
- **Không lộ ID nội bộ**: Snowflake và khối đều lộ số lượng và thời điểm, và ID đoán được tiếp tay cho [[idor|IDOR]] nếu thiếu kiểm tra quyền. Mã hiện cho khách (mã đơn) là cột riêng: ngẫu nhiên có unique constraint, hoặc hoán vị [[feistel-cipher|Feistel]] của ID (bài Thiết kế URL shortener).
- **Nhiều region**: đưa mã region vào bit worker (Snowflake) hoặc vào bit cao của khối (mỗi region một dải riêng), để không region nào phải hỏi region khác khi cấp. Đừng để mỗi region tự đánh sequence từ 1 (bài Multi-region & active-active).
- **UUID v7 khi nào hợp hơn**: không cần `bigint`, client (app di động) phải tự sinh ID khi offline, hay không muốn vận hành lease. Giá: khoá và index gấp đôi kích thước, và JSON vẫn phải dùng chuỗi. ID 64 bit trong JavaScript cũng phải trả dạng chuỗi (bài Thiết kế REST API).
