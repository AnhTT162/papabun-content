## Quick

Hệ thống chống gian lận là một **dịch vụ quyết định đồng bộ** đặt ở các điểm rủi ro (đăng ký, đăng nhập, thanh toán, rút tiền), trả `ALLOW`, `CHALLENGE`, `REVIEW` hoặc `BLOCK` trong vài chục ms. Nó ghép **rule** (chính sách cứng, đổi nhanh) với **model** (điểm rủi ro), đọc [[velocity-feature|velocity feature]] từ [[feature-store|feature store]], rồi học lại từ nhãn đến trễ hàng tháng. **Quy tắc quan trọng nhất: train đúng như lúc serve.** Ghi lại feature đã dùng tại thời điểm quyết định, và nhớ rằng giao dịch bị chặn không bao giờ có nhãn.

## Interview

Tôi hỏi trước: chống loại gian lận nào (thẻ bị đánh cắp, chiếm tài khoản, lạm dụng khuyến mãi, hoàn tiền giả), quyết định ở bước nào, quy mô lúc đỉnh, ngân sách latency trong luồng checkout, và chi phí của từng loại sai: chặn nhầm khách thật mất doanh thu, cho qua gian lận mất hàng cộng phí [[chargeback|chargeback]].

**Luồng đồng bộ**: Payment gọi Fraud trước khi authorize. Fraud đọc feature (tuổi tài khoản, số thẻ mới trên thiết bị trong 24 giờ, số lần thử của thẻ trong 10 phút), chạy rule, gọi model, rồi ra quyết định theo ngưỡng. `CHALLENGE` là [[three-d-secure|3-D Secure]] hay OTP; `REVIEW` vào hàng chờ cho người xem. Quyết định lưu theo id attempt cùng feature, phiên bản rule và model, để retry nhận đúng quyết định cũ.

**Luồng bất đồng bộ**: mọi event đi qua Kafka vào stream processor tính velocity và ghi vào kho online (Redis). Bản ghi quyết định cùng nhãn sau này (chargeback, kết quả review) thành dữ liệu train.

**Ngưỡng theo chi phí**: chặn khi xác suất gian lận × thiệt hại lớn hơn (1 − xác suất) × lợi nhuận mất đi. Lợi nhuận 10% thì ngưỡng khoảng 9%, không phải 50%. Fraud chỉ chiếm 0,1% nên accuracy vô nghĩa: đo [[precision-recall|precision và recall]], và dải `REVIEW` phải vừa sức đội review.

**Bẫy**: train và serve tính feature khác nhau ([[training-serving-skew|training-serving skew]]); join feature theo giá trị hiện tại thay vì [[point-in-time-correctness|tại thời điểm giao dịch]]; train trên tháng gần nhất khi chargeback chưa kịp về ([[label-delay|nhãn trễ]]); coi giao dịch bị chặn là gian lận; gọi model với timeout dài rồi chặn hết khi model chết; trả lý do từ chối cho client.

## Deep

- **Điểm quyết định và kết cục**:
  - Đăng ký (lạm dụng khuyến mãi, tài khoản ảo), đăng nhập ([[account-takeover|chiếm tài khoản]]), thêm thẻ ([[card-testing|card testing]]), thanh toán, đổi số điện thoại hay tài khoản nhận tiền, rút tiền. Mỗi điểm có feature, ngưỡng và kết cục riêng; một model cho tất cả thì tối ưu cho loại nhiều nhất.
  - `CHALLENGE` rẻ hơn `BLOCK`: khách thật qua được, kẻ gian thường bỏ. Giao dịch thẻ xác thực 3-D Secure thành công thường chuyển trách nhiệm chargeback loại gian lận sang ngân hàng phát hành (trừ giao dịch được miễn xác thực, và tuỳ mạng thẻ, khu vực); đổi lại một phần khách bỏ dở ở bước xác thực.
  - `REVIEW` với thẻ: authorize trước, giữ capture tới khi review xong (authorization có hạn, xem bài Thiết kế đơn hàng & tồn kho). Với ví hay QR tiền đã chuyển: giữ việc giao hàng hoặc giữ tiền của người bán.
- **Ngân sách latency**:
  - Checkout chừa cho Fraud khoảng 50–100 ms p99. 3.000 quyết định/s, mỗi quyết định 40 ms thì theo Little's law có 120 quyết định đang chạy cùng lúc: đọc feature theo lô (một `MGET` hay pipeline), model nạp sẵn trong bộ nhớ.
  - Model không trả lời kịp thì quyết định chỉ bằng rule, theo bậc số tiền: nhỏ thì cho qua, lớn thì `CHALLENGE` hoặc `REVIEW`. Không [[fail-open|fail open]] toàn bộ (kẻ gian chờ lúc model chết), cũng không chặn hết (một sự cố của model thành sự cố doanh thu). Đặt [[circuit-breaker|circuit breaker]] để không chờ timeout ở từng request.
  - Quyết định idempotent theo id attempt. Gọi lại mà chấm điểm lại thì velocity đã tăng, và kẻ gian thử lại tới khi gặp quyết định dễ hơn.
- **Rule và model**:
  - Rule cho chính sách cứng và phản ứng nhanh: blocklist thẻ, thiết bị, danh sách cấm vận, giới hạn velocity, chặn một đợt tấn công đang diễn ra trong vài phút.
  - Rule là dữ liệu có phiên bản (DSL hay bảng điều kiện), không phải `if` trong code checkout. Trước khi bật: chạy lại trên dữ liệu cũ để biết sẽ chặn bao nhiêu và trúng bao nhiêu, rồi chạy [[shadow-mode|shadow mode]] ghi quyết định giả định. Rule nào lâu không bắn hay chỉ trùng model thì gỡ, nếu không vài năm sau có hàng nghìn rule không ai dám xoá.
  - Model (thường là cây quyết định tăng cường) học tổ hợp mà rule không viết hết. Ra mắt model mới theo [[champion-challenger|champion/challenger]]: chấm song song, so trên cùng giao dịch, rồi chuyển một phần lưu lượng.
- **Velocity feature**:
  - Đếm theo khoá và cửa sổ: lần thử theo thẻ trong 10 phút, thẻ khác nhau theo thiết bị trong 24 giờ, tài khoản theo số điện thoại, tỉ lệ bị từ chối theo IP.
  - Cách đếm như thuật toán [[sliding-window|sliding window]] của bài Rate limiting: sorted set mỗi event một phần tử thì đúng nhưng bộ nhớ tăng theo số event; bucket theo phút (`HINCRBY` + `EXPIRE`) thì nhỏ nhưng lệch tối đa một bucket ở mép cửa sổ (đã chạy: 8 event, cửa sổ 60 phút đúng là 5, đếm 60 bucket phút ra 4). Đếm phần tử khác nhau với tập nhỏ (6 thẻ trên một thiết bị) thì một set nhỏ đã chính xác và rẻ; [[hyperloglog|HyperLogLog]] (sai khoảng 0,81%, bài Cấu trúc dữ liệu trong hệ thống lớn) chỉ đáng dùng khi khoá có rất nhiều phần tử, như số thẻ khác nhau theo IP hay BIN. HLL không xoá được phần tử, nên cửa sổ 24 giờ là 24 HLL theo giờ rồi `PFCOUNT` gộp cả 24 khoá.
  - Stream processor trễ vài giây. Một đợt card testing 50 lần thử trong 10 giây đi qua trước khi bộ đếm kịp tăng, nên vài bộ đếm nóng nhất (lần thử theo thẻ, IP, thiết bị) tăng đồng bộ ngay trong dịch vụ quyết định; feature nặng (trung bình 30 ngày, đồ thị) mới đi qua stream hay batch.
  - Tăng trước rồi đọc, hay đọc rồi mới tăng: chọn một và dùng giống hệt khi tính dữ liệu train. Lệch nhau một đơn vị đủ làm model học sai ngưỡng.
- **Training-serving skew và point-in-time**:
  - Feature tính bằng Java lúc serve và bằng SQL lúc train sẽ khác nhau ở múi giờ, `NULL`, biên cửa sổ. Cách chắc nhất: ghi feature đã dùng vào log quyết định và train trên chính log đó; làm cho một phần nhỏ cũng đủ để so hai đường (Rules of ML, Rule #29).
  - Feature mới chưa có trong log thì phải tính lại cho quá khứ bằng point-in-time join: với mỗi giao dịch, lấy giá trị feature có hiệu lực ngay trước thời điểm giao dịch. Join với bảng hiện tại là rò rỉ: "số chargeback của tài khoản" hôm nay đã gồm chargeback của chính giao dịch đang học, model offline đẹp, production vô dụng.
- **Nhãn**:
  - Chargeback về sau vài tuần, phần lớn trong 120 ngày, vài loại lâu hơn. Train trên 30 ngày gần nhất thì phần lớn gian lận còn mang nhãn sạch. Chỉ dùng giao dịch đã đủ "chín" (ví dụ cũ hơn 90 ngày), cộng tín hiệu sớm: kết quả review, khách báo mất tài khoản, báo cáo gian lận của ngân hàng phát hành (về trước chargeback).
  - Nhãn bẩn theo hai chiều: friendly fraud (khách thật nhận hàng rồi báo không mua) thành nhãn gian lận; gian lận mà chủ thẻ không phát hiện thì mang nhãn sạch mãi.
  - Giao dịch bị chặn không có nhãn: coi tất cả là gian lận thì model tự khẳng định chính nó; bỏ đi thì mất đúng vùng rủi ro nhất. Muốn đo recall thật phải ước lượng điều gì sẽ xảy ra với giao dịch đã chặn: cho một tỉ lệ nhỏ ngẫu nhiên giao dịch số tiền thấp lẽ ra bị chặn đi qua (nhóm đối chứng), rồi cân trọng số khi train và đo.
- **Ngưỡng và đo lường**:
  - Chặn khi `p × L > (1 − p) × M`, tức `p > M / (M + L)`, với `L` là thiệt hại khi cho qua gian lận (giá trị hàng cộng phí chargeback) và `M` là lợi nhuận mất khi chặn nhầm. Lợi nhuận 10%: ngưỡng khoảng 8,3% cho đơn 200.000 VND (phí chargeback cố định chiếm phần lớn hơn), khoảng 9,1% cho đơn 20 triệu (đã chạy). Công thức chỉ đúng khi điểm đã được hiệu chỉnh thành xác suất; điểm thô của model thì phải hiệu chỉnh trước.
  - Ngưỡng chi phí là ranh giới dưới của vùng không cho qua thẳng. Trên đó chia hai: từ ngưỡng chi phí tới một ngưỡng cao hơn (ví dụ 9–40%) là `CHALLENGE` hay `REVIEW`, khi đội review còn sức và còn giữ được capture hay giao hàng; trên ngưỡng cao thì `BLOCK`.
  - Mất cân bằng lớp: 1 triệu giao dịch, gian lận 0,1%, recall 80% với tỉ lệ chặn nhầm 0,5% cho 800 đúng và 4.995 nhầm, precision 13,8% (đã chạy). Model "cho qua tất cả" có accuracy 99,9%.
  - Theo dõi theo phân khúc (phương thức, quốc gia thẻ, người bán): tỉ lệ duyệt, tỉ lệ chặn, phân bố điểm. Tỉ lệ duyệt tụt đột ngột là cảnh báo đánh thức người trực; phân bố điểm trôi chậm ([[concept-drift|concept drift]]) là lý do train lại.
  - Với thẻ, tỉ lệ fraud và dispute trên giao dịch không xuất trình thẻ còn là ngưỡng của tổ chức thẻ. Theo các tài liệu tổng hợp về chương trình VAMP của Visa, ngưỡng "quá mức" cho người bán ở nhiều khu vực giảm còn khoảng 1,5% từ 4/2026 (chỉ áp khi vượt số ca tối thiểu mỗi tháng), kèm phí cho từng ca; con số và khu vực áp dụng cần xác nhận với acquirer.
- **Hàng chờ review**:
  - 12 người, mỗi người 40 ca/giờ, 8 giờ: 3.840 ca/ngày, khoảng 0,96% của một phân khúc 400.000 giao dịch/ngày như thẻ quốc tế (đã tính); với toàn bộ lưu lượng cỡ 3.000/s thì tỉ lệ đó chưa tới 0,005%, nên dải `REVIEW` phải rất hẹp hoặc chỉ áp cho phân khúc rủi ro. Dải điểm `REVIEW` phải chọn sao cho lưu lượng vào nhỏ hơn sức xử lý; vượt thì hàng chờ dài ra, authorization hết hạn, khách thật bỏ đi.
  - Ưu tiên theo thiệt hại kỳ vọng `p × số tiền`, không theo thứ tự đến. Người review cần lý do (rule đã bắn, feature đóng góp nhiều nhất) và lịch sử liên quan; quyết định của họ là nhãn nhanh nhất hệ thống có.
- **Vòng gian lận theo đồ thị**:
  - Tài khoản chia sẻ thiết bị, thẻ, số điện thoại, địa chỉ nhận hàng tạo thành đồ thị. Gom thành phần liên thông bằng union-find chạy batch (đã chạy: u1, u2 chung thiết bị; u2, u3 chung thẻ; u3, u5 chung IP: một vòng 4 tài khoản, u4 đứng riêng), rồi dùng kích thước vòng, số tài khoản bị chặn trong vòng làm feature.
  - Bỏ nút có bậc quá cao: IP của nhà mạng di động (dùng CGNAT, hàng nghìn khách chung một IP), Wi-Fi quán cà phê, địa chỉ kho của dịch vụ giao hàng. Giữ chúng thì cả nước thành một vòng.
  - [[device-fingerprint|Device fingerprint]] là tín hiệu mạnh nhưng giả được; kết hợp nhiều tín hiệu, đừng tin một.
- **Card testing và chiếm tài khoản**:
  - Card testing: kẻ gian thử hàng nghìn thẻ đánh cắp bằng giao dịch nhỏ để tìm thẻ còn sống. Dấu hiệu: tỉ lệ từ chối tăng vọt, nhiều thẻ trên một thiết bị hay IP, cùng BIN. Chặn ở trước Fraud: CAPTCHA, rate limit tạo khách hàng và thêm thẻ theo IP, giới hạn số thẻ mỗi tài khoản; một heuristic IP đơn lẻ không đủ (tài liệu card testing của Stripe).
  - Chiếm tài khoản: thiết bị mới, quốc gia IP mới, đổi mật khẩu rồi đổi tài khoản nhận tiền trong vài phút. Phản ứng bằng step-up MFA và giữ rút tiền 24 giờ; credential stuffing ở tầng đăng nhập thuộc bài Thiết kế rate limiter và AuthN & AuthZ cơ bản.
- **Đối đầu với kẻ gian**: trả cùng một thông báo từ chối chung, không lộ rule nào bắn; kẻ gian dò ngưỡng bằng cách tăng dần số tiền. Thêm rule nhanh khi đợt tấn công mới bắt đầu, vì model cần nhãn mới học được.
- **Dữ liệu cá nhân**: fingerprint, vị trí, danh bạ là dữ liệu cá nhân; chỉ thu cái dùng tới, có thời hạn lưu, ghi rõ mục đích chống gian lận (bài Dữ liệu cá nhân & tuân thủ). Khách bị chặn có đường khiếu nại, và lý do quyết định phải truy được từ log.
- **Tự xây hay mua**: PSP có sẵn dịch vụ chấm điểm học từ dữ liệu của nhiều merchant, mạnh với thẻ mà mình chưa từng thấy. Nó không thấy hành vi trong app của mình (khuyến mãi, đổi tài khoản nhận tiền, vòng tài khoản), nên thường dùng cả hai: điểm của PSP thành một feature.
