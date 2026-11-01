## Quick

Ứng dụng gọi xe có hai đường nóng: **cập nhật vị trí** (hàng trăm nghìn tài xế gửi vị trí vài giây một lần, dữ liệu sống ngắn, giữ trong bộ nhớ) và **ghép cặp** (tìm tài xế gần qua [[geospatial-index|chỉ mục không gian]], xếp theo thời gian tới đón, gửi đề nghị và khoá tài xế). **Vị trí là dữ liệu tạm có thể dựng lại sau vài giây; chuyến đi là dữ liệu bền phải qua máy trạng thái.** Tách hai loại này là quyết định gốc.

## Interview

Tôi hỏi trước: bao nhiêu tài xế online lúc đỉnh, bao lâu gửi vị trí một lần, bao nhiêu yêu cầu đặt xe mỗi phút, khách có thấy xe chạy trên bản đồ không, có [[surge-pricing|giá động]] không.

**Ước lượng**: 300.000 tài xế online, mỗi 4 giây một vị trí: 75.000 lần ghi mỗi giây. Không ghi vào bảng SQL; giữ vị trí mới nhất trong bộ nhớ theo thành phố, lịch sử đẩy qua Kafka.

**Chỉ mục**: [[geohash|geohash]] chia mặt đất thành ô, mã chung tiền tố thì gần nhau, nhưng hai điểm cạnh nhau ở hai bên mép ô có thể khác mã từ rất sớm (lab: cách 10 m mà chỉ chung 4 ký tự; hai bên xích đạo thì khác ngay ký tự đầu), nên luôn phải tìm cả ô lân cận. [[quadtree|Quadtree]] chia nhỏ ô theo mật độ. [[h3-index|H3]] dùng lục giác, sáu ô kề cách tâm đều nhau, hợp để tính cung cầu theo vùng. Redis GEO lưu vị trí trong [[sorted-set|sorted set]] với điểm là geohash 52 bit.

**Ghép cặp**: lấy ứng viên theo khoảng cách đường chim bay, tính [[eta|ETA]] theo đường đi thật, gửi đề nghị cho một tài xế với hạn 15 giây, khoá tài xế bằng [[conditional-update|chuyển trạng thái có điều kiện]] để không bị ghép hai chuyến. [[batch-matching|Ghép theo lô]] vài giây một lần thay vì ai đến trước lấy xe gần nhất: mô phỏng cho quãng đón ngắn hơn 13–19%.

**Chuyến đi**: [[state-machine|máy trạng thái]] bền trong database, event qua [[outbox|outbox]], thanh toán khi kết thúc.

**Bẫy**: ghi mỗi lần gửi vị trí vào database, tìm bán kính lớn ở trung tâm đông xe, không xử lý tài xế mất kết nối, gửi một đề nghị cho nhiều tài xế mà không khoá.

## Deep

- **Đường vị trí**:
  - App tài xế gửi qua kết nối lâu dài ([[websocket|WebSocket]] hay gRPC stream, bài gRPC, WebSocket, SSE & long polling) hoặc HTTP theo lô; server gom rồi ghi vào kho vị trí của thành phố.
  - Kho vị trí chỉ giữ bản mới nhất mỗi tài xế. Mất nó thì sau một chu kỳ gửi (4 giây) mọi tài xế đã tự điền lại: không cần nhân bản đồng bộ hay backup.
  - Lịch sử vị trí của chuyến đi (tính tiền, tranh chấp, huấn luyện ETA) đi qua Kafka vào kho rẻ; 75.000 điểm/s × khoảng 50 byte là khoảng 3,75 MB/s.
  - Shard theo thành phố hay vùng: tìm xe không bao giờ cần dữ liệu thành phố khác.
- **Geohash** (lab Java, vĩ độ 10,78):
  - Xen kẽ bit kinh độ và vĩ độ rồi mã hoá base32. Kích thước ô (cao bắc–nam × rộng đông–tây): 5 ký tự 4,9 × 4,8 km; 6 ký tự 607 m × 1,2 km; 7 ký tự khoảng 150 × 150 m.
  - Hai điểm cách 10 m: `w3gv7fp` và `w3gvk40`, chỉ chung 4 ký tự. Tìm theo tiền tố mà không lấy ô lân cận sẽ bỏ sót xe ngay bên kia mép.
  - Mô phỏng 50.000 tài xế (30.000 dồn quanh 5 điểm nóng, 20.000 rải đều 40 × 40 km), tìm bán kính 2 km: ô 5 ký tự ở trung tâm quét 4 ô với 13.523 tài xế để lấy 5.034 trong bán kính; ô 6 ký tự quét 32 ô với 6.778. Ở ngoại ô: 1.195 và 324 quét để lấy 157. Ô nhỏ quét ít thừa hơn nhưng tốn nhiều lần tra ô hơn; ô cố định không hợp cả nơi đông lẫn nơi thưa.
- **Quadtree**: chia ô làm bốn khi quá số điểm cho phép, nên ô nhỏ ở nơi đông và lớn ở nơi thưa. Mô phỏng cùng 50.000 tài xế, tối đa 64 mỗi lá: 1.858 lá, sâu nhất 8 tầng. Giá: điểm di chuyển liên tục nên phải xoá/chèn hay dựng lại định kỳ; hợp làm cấu trúc trong bộ nhớ của một service theo thành phố.
- **H3** (Uber, lab h3-java 4.5.1):
  - Lục giác theo cấp độ: cấp 7 trung bình 5,16 km², cạnh 1,4 km; cấp 8 0,74 km², cạnh 531 m; cấp 9 0,105 km², cạnh 201 m.
  - Sáu ô kề của một ô cấp 8 có tâm cách 981–995 m, gần như bằng nhau; ô vuông thì ô chéo xa hơn √2 lần. Vòng k ô: 7, 19, 91 ô cho k = 1, 2, 5.
  - Giá của lục giác: mỗi cấp có 12 ô ngũ giác (chỉ 5 ô kề, nằm ở vị trí cố định, thường giữa biển), và 7 lục giác con không lồng khít trong ô cha, nên cộng số liệu từ cấp con lên cấp cha chỉ gần đúng.
  - Dùng để gom cung cầu theo vùng cho giá động, heatmap tài xế, và chia khu vực. S2 của Google (ô trên mặt cầu theo đường cong Hilbert) là lựa chọn tương tự.
- **Redis GEO** (lab Redis 6.2.6, 50.000 tài xế, 32 kết nối, không pipeline):
  - `GEOADD` lưu thành sorted set, điểm là geohash 52 bit (sai số dưới 1 m). Khoảng 112 byte mỗi tài xế: 50.000 tài xế 5,6 MB. `GEOADD` cập nhật khoảng 206.000–215.000 lần/s trên một instance.
  - `GEOSEARCH ... BYRADIUS 2 km ASC COUNT 10` ở điểm nóng: chỉ khoảng 1.800 lần/s. Khi có `COUNT` mà không có `ANY`, Redis duyệt mọi điểm trong các ô geohash bao quanh vùng tìm, giữ những điểm trong bán kính (khoảng 5.000 ở đây), sắp xếp rồi mới cắt 10. Bán kính 500 m: 11.000/s. `COUNT 10 ANY` (dừng khi đủ 10, không bảo đảm gần nhất): 67.000/s.
  - Bài học: tìm theo bán kính tăng dần (500 m, rồi 1 km, rồi 2 km) thay vì một bán kính lớn; ở nơi đông bán kính nhỏ đã đủ ứng viên.
  - Member trong sorted set không có TTL: tài xế tắt app vẫn nằm đó. Giữ `last_seen` ở một sorted set khác và job xoá tài xế im lặng quá 30 giây, hoặc lọc theo `last_seen` khi lấy ứng viên.
- **Từ ứng viên tới tài xế**:
  - Khoảng cách đường chim bay ([[haversine|haversine]]) chỉ để lọc. Xếp hạng theo ETA của routing engine trên mạng đường thật (một chiều, sông, cầu); tài xế cách 300 m bên kia sông có thể xa 4 km đường đi.
  - Lọc theo loại xe, trạng thái, đánh giá, tài xế sắp kết thúc chuyến gần đó.
  - GPS trong phố cao tầng lệch hàng chục mét: [[map-matching|map matching]] gắn điểm vào đoạn đường hợp lý; vận tốc bất khả thi giữa hai điểm là dấu hiệu GPS giả.
- **Ghép theo lô** ([[batch-matching|batch matching]], mô phỏng 200 vòng, 40 khách trong vùng 5 × 5 km, khoảng cách thẳng):
  - Tham lam: mỗi khách đến lấy xe rảnh gần nhất. Lô: gom khách trong vài giây rồi giải bài toán gán tối ưu (Hungarian) cho tổng quãng đón nhỏ nhất.
  - 60 xe rảnh: quãng đón trung bình 498 m so với 434 m (ngắn hơn 12,8%). 44 xe rảnh (cung sát cầu): 785 m so với 632 m (19,4%); quãng xa nhất 4,99 km so với 3,46 km.
  - Lợi càng lớn khi xe khan. Giá: khách chờ thêm vài giây của cửa sổ lô, và bài toán gán chạy theo vùng nên cần chia vùng có chồng mép.
- **Gửi đề nghị và khoá tài xế** ([[driver-dispatch|dispatch]]):
  - Tài xế có trạng thái `AVAILABLE → OFFERED → ON_TRIP`. Gửi đề nghị là chuyển `AVAILABLE → OFFERED` có điều kiện (`UPDATE ... WHERE status = 'AVAILABLE'`, hay một Lua script trong Redis vừa kiểm tài xế đang rảnh vừa `SET offer:{driver} <ride> NX EX 15`, vì sau khi key hết hạn thì `SET NX` một mình lại thành công kể cả với tài xế đang chở khách); không được thì lấy ứng viên kế.
  - Hạn 15 giây; từ chối hay quá hạn thì về `AVAILABLE` và thử người kế. Chấp nhận thì kiểm `offer:{driver}` vẫn là chuyến này (so rồi xoá, bằng Lua), rồi trong **một transaction database**: `UPDATE trip SET status = 'MATCHED', driver_id = :d WHERE id = :t AND status = 'REQUESTED'` và `UPDATE driver SET status = 'ON_TRIP' WHERE id = :d AND status <> 'ON_TRIP'`; một câu trả 0 dòng thì rollback. Điều kiện trên chuyến bảo đảm mỗi chuyến một tài xế; điều kiện trên tài xế (hay unique riêng phần `trip(driver_id) WHERE status IN ('MATCHED', 'DRIVER_ARRIVED', 'IN_PROGRESS')`) bảo đảm mỗi tài xế một chuyến, kể cả khi khoá trong Redis mất vì failover hay tài xế bấm nhận sau khi đề nghị đã hết hạn.
  - Gửi cùng lúc cho nhiều tài xế, ai nhận trước thắng: nhanh hơn, nhưng tài xế thua thấy đề nghị biến mất và mỗi tài xế bị khoá cho nhiều chuyến cùng lúc.
- **Chuyến đi**: `REQUESTED → MATCHED → DRIVER_ARRIVED → IN_PROGRESS → COMPLETED`, cộng `CANCELLED` ở các bước đầu. Lưu trong database quan hệ, mọi chuyển trạng thái có điều kiện, event sang thanh toán và thông báo qua outbox. Yêu cầu đặt xe có [[idempotency-key|idempotency key]]: mạng chập chờn bấm hai lần không thành hai chuyến. Thanh toán và giữ tiền trước ở bài Thiết kế hệ thống thanh toán.
- **Khách xem xe chạy**: server đẩy vị trí tài xế của chuyến qua WebSocket mỗi 1–2 giây, lấy từ luồng vị trí; không để app khách hỏi liên tục.
- **[[surge-pricing|Giá động]]**: đếm yêu cầu và tài xế rảnh theo ô H3 trong cửa sổ vài phút, làm mượt theo thời gian và giữa ô kề để giá không nhảy giữa hai con phố; giá báo cho khách phải được giữ cố định trong một khoảng ngắn để họ đặt.
- **Lỗi và sự cố**: kho vị trí mất thì tự đầy lại sau một chu kỳ; service ghép cặp chết thì yêu cầu đang chờ phải còn trong database để service khác nhận; tài xế mất mạng giữa chuyến thì app lưu điểm GPS và gửi bù khi có mạng. Mỗi thành phố một cụm độc lập để sự cố một nơi không lan ra cả nước.
