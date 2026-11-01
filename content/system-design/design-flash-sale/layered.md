## Quick

[[flash-sale|Flash sale]] là vài nghìn món hàng hay vé gặp hàng triệu người bấm cùng một giây. **Thiết kế là một cái phễu: chặn càng sớm càng rẻ (CDN, [[waiting-room|phòng chờ]], rate limit, giới hạn mỗi người), trừ kho nguyên tử ở một chỗ thật nhanh làm cổng, tạo đơn bất đồng bộ phía sau, và để database chốt bằng cập nhật có điều kiện.** Bất biến duy nhất không được vi phạm: không bán vượt số đang có ([[oversell|oversell]]).

## Interview

Tôi hỏi trước: bao nhiêu món và bao nhiêu người dự kiến, mỗi người mua tối đa mấy món, có giữ hàng chờ thanh toán không và bao lâu, bán vé có chọn ghế không, có cần công bằng theo thứ tự đến không.

**Ước lượng**: 1.000 điện thoại, 2 triệu người, mỗi người bấm vài lần trong 10 giây đầu: hàng trăm nghìn request mỗi giây, 99,9% sẽ bị từ chối. Việc chính là từ chối thật rẻ.

**Phễu**: trang và đồng hồ đếm ngược nằm ở CDN, giờ mở bán lấy từ server. Phòng chờ cấp vị trí và cho vào theo tốc độ phần checkout chịu được, kèm [[admission-token|token vào cửa]] có chữ ký để gateway kiểm mà không gọi database. Rate limit theo tài khoản, thiết bị, IP.

**Trừ kho**: một [[lua-script|Lua script]] trong Redis kiểm còn hàng, kiểm người này chưa mua, trừ kho và ghi vào stream trong một bước. Lab Redis 6.2: kiểm bằng `GET` rồi `DECR` bán 1.023–1.033 trên 1.000 suất; Lua bán đúng 1.000 và không ai mua hai lần.

**Phía sau**: consumer đọc stream, tạo đơn `PENDING_PAYMENT` idempotent theo `(sale_id, user_id)`, giữ hàng có thời hạn ([[inventory-reservation|reservation]]), database trừ bằng `UPDATE ... WHERE left_qty > 0`. Redis là cổng, database là sự thật: Redis failover có thể mất lần trừ gần nhất.

**Database chịu bao nhiêu**: lab PostgreSQL 64 kết nối, một dòng đếm khoảng 4.000 lượt/s; chia 16 dòng con khoảng 29.000/s.

**Bẫy**: kiểm rồi mới trừ, nút bật theo đồng hồ máy khách, thanh toán trong cùng transaction với trừ kho, chung hạ tầng với luồng mua thường, autoscale phản ứng chậm hơn đợt tăng.

## Deep

- **Phễu bằng con số**: 2 triệu người × 3 lần bấm trong 10 giây là 600.000 request/s nếu không chặn gì. CDN nhận trang tĩnh; phòng chờ giữ người; gateway chỉ để vào người có token; Redis chỉ nhận lượt mua thật; database chỉ nhận vài nghìn đơn. Mỗi tầng phải biết "hết hàng" để trả lời ngay, không đẩy xuống tầng dưới.
- **Giờ mở bán**: nút bật theo đồng hồ máy khách thì người chỉnh giờ máy bấm sớm. Trang lấy giờ server (hoặc độ lệch so với server) và API mua kiểm giờ ở server. URL hay tham số mua chỉ được phát khi tới giờ, để script không gọi thẳng API từ trước.
- **Phòng chờ**:
  - Người vào trước giờ mở nhận vị trí ngẫu nhiên trong nhóm đầu (để chạy sớm 1 ms không thắng), người vào sau xếp theo thứ tự đến.
  - Tốc độ cho vào theo Little's law: checkout trung bình 3 phút, hệ chịu 3.000 phiên checkout cùng lúc thì cho vào khoảng 1.000 người mỗi phút.
  - Token vào cửa ký HMAC, chứa user id, sale id, hạn vài phút; gateway kiểm chữ ký và hạn, không cần tra kho. Token gắn với user để không chuyển nhượng.
  - Hết hàng thì báo cho cả hàng chờ ngay, không để họ chờ tới lượt mới biết.
- **Trừ kho trong Redis** (lab Redis 6.2.6, 1.000 suất, 20.000 người mỗi người bấm 3 lần, 64 kết nối):
  - `GET` rồi `DECR`: bán 1.023 và 1.033 ở hai lần chạy, kho về -23 và -33; 26 người được mua hai lần. Hai request cùng đọc "còn 1" rồi cùng trừ ([[check-then-act|check-then-act]]).
  - `DECR`, âm thì `INCR` trả lại: đúng 1.000 nhưng 24–25 người vẫn mua hai lần vì không kiểm người mua; khi hết hàng mỗi lượt tốn hai lệnh (khoảng 113.000–126.000 lượt/s so với 177.000–182.000 của Lua). Kho âm tạm thời còn làm người khác bị từ chối oan khi có hàng trả lại cùng lúc.
  - Lua gộp `SISMEMBER`, `GET`, `DECR`, `SADD`, `XADD`: đúng 1.000, không ai mua hai lần, stream có đúng 1.000 bản ghi để tạo đơn. Script chạy nguyên tử nên phải ngắn (bài Redis cho lock, rate limit, leaderboard). Trên Redis Cluster mọi key script đụng tới phải cùng hash slot, không thì lỗi `CROSSSLOT`: đặt tên `{sale:7}:stock`, `{sale:7}:buyers`, `{sale:7}:orders`, nên cả một đợt sale nằm trên một shard.
  - Một SKU là một key, tức một shard và một lõi CPU: trần cỡ 180.000 lượt/s trong lab. Khi về 0, app server giữ cờ "hết hàng" trong bộ nhớ (nhận qua Pub/Sub hay đọc lại mỗi giây) để thôi gọi Redis.
- **Redis không phải sự thật**: sao chép bất đồng bộ, failover có thể mất các lần trừ cuối nên kho trên replica cao hơn thực tế. Vì vậy database vẫn trừ có điều kiện và từ chối khi hết; người đã qua cổng Redis mà database từ chối thì nhận thông báo hết hàng (và hoàn tiền nếu đã trả). Đối chiếu số bán ở Redis và database sau đợt sale; cảnh báo nếu database bán quá số món.
- **Database chốt** (lab PostgreSQL 17.6 bản x86 trên M4, 20.000 suất, 64 kết nối, mỗi lượt `UPDATE` + `INSERT`; số tuyệt đối chỉ để so tương đối trong cùng lab, và khác con số 5.200 ở bài Thiết kế đơn hàng & tồn kho vì khác bản build và số kết nối):
  - Một dòng đếm `UPDATE stock SET left_qty = left_qty - 1 WHERE ... AND left_qty > 0`: khoảng 3.900–4.100 lượt/s, mọi transaction xếp hàng trên khoá của một dòng ([[hot-row|dòng nóng]], bài Thiết kế đơn hàng & tồn kho).
  - Chia kho thành 16 [[sharded-counter|dòng con]], mỗi lượt chọn ngẫu nhiên: khoảng 28.000–29.000/s. Nhưng nếu dòng được chọn hết mà không thử dòng khác thì 887–1.768 lượt bị từ chối khi kho còn hàng; thử lần lượt các dòng còn lại thì về 0, tốc độ gần như không đổi.
  - Mỗi suất một dòng, lấy bằng `FOR UPDATE SKIP LOCKED`: khoảng 13.000–14.000/s, đúng 20.000 dòng có người mua. Hợp với vé có ghế, vì mỗi ghế vốn là một dòng.
  - Không gọi thanh toán hay dịch vụ khác khi đang giữ khoá dòng kho.
- **Giữ hàng có thời hạn**: người qua cổng có 5–10 phút để trả tiền; quá hạn thì job nhả hàng và cộng lại vào Redis. Hàng nhả ra mở lại cho hàng chờ. Thứ tự thời hạn (phiên thanh toán < deadline của đơn < TTL reservation) và luồng nhả hàng ở bài Thiết kế đơn hàng & tồn kho; thanh toán ở bài Thiết kế hệ thống thanh toán.
- **Tạo đơn bất đồng bộ**: Lua ghi vào stream; consumer tạo đơn với unique `(sale_id, user_id)` nên đọc lại stream không tạo đơn trùng. Ràng buộc này cũng là chính sách: người để quá hạn thanh toán không mua lại được trong đợt đó; muốn cho mua lại thì dùng unique riêng phần `WHERE status <> 'EXPIRED'`.
  - Client chỉ nhận "đang xử lý" rồi hỏi trạng thái hay nhận push. Failover có thể mất cả bản ghi stream lẫn tên trong tập người mua, khi đó server không còn dấu vết nào: client quá khoảng 30 giây không thấy đơn thì báo thất bại và cho bấm lại (tập người mua đã mất nên bấm lại được).
  - Muốn chắc hơn: gọi `WAIT 1 <ms>` sau `EVALSHA` để chờ một replica nhận rồi mới trả lời, đổi lại thêm độ trễ mỗi lượt; hoặc ghi thẳng outbox trong database nếu tải chịu được.
- **Bán vé có chọn ghế**:
  - Giữ một ghế cụ thể: `UPDATE seat SET held_by = :u, hold_until = now() + interval '10 minutes' WHERE id = :seat AND status = 'AVAILABLE' AND (held_by IS NULL OR hold_until < now())`; 0 dòng là ghế vừa bị người khác giữ hoặc đã bán. Thanh toán xong thì đặt `status = 'SOLD'`; thiếu điều kiện `status` thì ghế đã bán có `hold_until` đã qua sẽ bị người khác giữ lại.
  - Ghế đẹp bị tranh nhau, nên sơ đồ ghế hiển thị là bản cache vài giây và luôn có thể đã cũ; giao diện phải xử lý "ghế vừa hết".
  - Sự kiện cực đông thường bỏ chọn ghế ở vòng đầu và cấp "ghế tốt nhất còn lại" bằng `SKIP LOCKED` theo hạng vé, để không ai tranh đúng một dòng.
- **Cô lập**: sale chạy trên deployment và pool kết nối riêng ([[bulkhead|bulkhead]]), để luồng mua thường không chết theo. Tắt tính năng phụ (gợi ý, đánh giá) trong giờ sale.
- **Scale trước, không chờ autoscale**: HPA cần vài chục giây tới vài phút để thêm pod, đợt tăng thì tới trong một giây. Scale theo lịch trước giờ mở, báo trước cho đội vận hành load balancer và CDN (bài Capacity planning). Load test bằng mô hình mở với đúng hình dạng đợt tăng (bài Load & performance testing).
- **Bot và công bằng**: giới hạn mỗi tài khoản và thiết bị, xác minh số điện thoại trước ngày sale, chặn tài khoản mới tạo, kiểm hành vi ở phòng chờ. Không có cách kỹ thuật nào chặn hết; giới hạn số lượng mỗi người là phòng tuyến cuối.
- **Đổi luật nghiệp vụ**: đăng ký trước rồi bốc thăm, hay bán theo đợt nhỏ trong nhiều khung giờ, xoá luôn đỉnh tải và cuộc đua bot. Câu trả lời cấp architect nên nêu phương án này cùng giá của nó (mất cảm giác "săn", thêm một bước).
- **Giám sát trong giờ sale**: số đã bán ở Redis và database, số reservation sắp hết hạn, độ dài hàng chờ và tốc độ cho vào, tỉ lệ từ chối theo lý do (hết hàng, rate limit, token hết hạn), p99 của API mua. Cảnh báo "database bán quá số món" phải bằng 0 tuyệt đối.
