## Quick

Buổi System Design 45–60 phút đi qua sáu bước: làm rõ yêu cầu, ước lượng, API và mô hình dữ liệu, thiết kế tổng (high-level), đi sâu (deep dive) vào một hai phần khó, rồi tổng kết điểm nghẽn và trade-off. Người phỏng vấn chấm **cách bạn dẫn dắt và lập luận**, không chấm việc vẽ giống một kiến trúc mẫu. **Mỗi quyết định phải truy về được một yêu cầu hoặc một con số, kèm cái giá phải trả.**

## Interview

Tôi chia 45 phút thành các bước và nói to từng bước để người phỏng vấn theo kịp.

**Yêu cầu (5 phút)**: tách [[functional-requirement|yêu cầu chức năng]] (người dùng làm được gì) khỏi [[non-functional-requirement|yêu cầu phi chức năng]] (quy mô, latency như [[percentile|p99]], [[availability]], nhất quán). Tôi chốt phạm vi: làm gì, không làm gì. Câu hỏi nào người phỏng vấn để tôi tự quyết thì tôi nêu giả định và ghi lên bảng.

**Ước lượng (3–5 phút)**: chỉ tính những con số làm đổi thiết kế: [[qps|QPS]] trung bình và đỉnh, [[read-write-ratio|tỉ lệ đọc/ghi]], dung lượng sau vài năm. Ví dụ 1 triệu bản ghi mới mỗi ngày là khoảng 12 ghi mỗi giây: một database thừa sức, không cần sharding.

**API và dữ liệu (5 phút)**: vài endpoint chính, entity chính và cách truy cập, từ đó chọn loại database.

**High-level (10 phút)**: bắt đầu từ thiết kế đơn giản nhất chạy được: client, load balancer, app stateless, database. Rồi thêm cache, queue, object storage ở chỗ con số đòi hỏi, nói rõ vì sao.

**Deep dive (15 phút)**: chọn một hai phần khó nhất của chính bài này, hoặc theo hướng người phỏng vấn gợi ý. Ở đây tôi so hai ba phương án, chọn một và nói giá của nó.

**Tổng kết (5 phút)**: điểm nghẽn tiếp theo khi tải tăng gấp 10, cái gì xảy ra khi một khối chết, cần theo dõi metric nào.

Bẫy hay gặp: lao vào vẽ ngay khi chưa hỏi yêu cầu, thuộc lòng kiến trúc mẫu, thêm Kafka hay [[microservices]] mà không có lý do, im lặng suy nghĩ quá lâu, và hết giờ khi chưa tới phần deep dive. Cách làm đúng: hỏi trước, chốt con số, vẽ đơn giản rồi mới phức tạp dần, và sau mỗi bước hỏi lại người phỏng vấn muốn đi sâu chỗ nào.

## Deep

- **Người phỏng vấn chấm gì**: (1) đi giải bài toán có hướng hay không (hỏi đúng, chia nhỏ, ưu tiên); (2) thiết kế có chạy và đáp ứng yêu cầu không; (3) hiểu sâu các khối mình dùng tới mức nào; (4) giao tiếp: nói rõ, nghe gợi ý, đổi hướng khi có thông tin mới. Không có đáp án duy nhất; hai thiết kế khác nhau đều đạt nếu cùng lập luận chặt.
- **Câu hỏi làm rõ nên có sẵn**: ai dùng, bao nhiêu người dùng hoạt động mỗi ngày ([[dau|DAU]]), mỗi người làm gì bao nhiêu lần; đọc hay ghi nhiều hơn; latency mong muốn (p99 dưới bao nhiêu); dữ liệu sai lệch vài giây có chấp nhận được không ([[eventual-consistency|nhất quán cuối cùng]] hay phải mạnh); giữ dữ liệu bao lâu; một vùng hay nhiều vùng; có ràng buộc chi phí, bảo mật, pháp lý không. Không cần hỏi hết; hỏi những câu mà câu trả lời đổi được thiết kế.
- **Yêu cầu phi chức năng phải có số**: "nhanh" và "luôn sẵn sàng" không đo được. Availability 99,9% cho phép khoảng 43 phút ngừng mỗi tháng (8,76 giờ mỗi năm), 99,99% chỉ khoảng 4,3 phút mỗi tháng. Mỗi số 9 thêm vào thường kéo theo nhiều [[availability-zone|AZ]], failover tự động, deploy không downtime, tức chi phí và độ phức tạp tăng rõ. Viết thành câu như "p99 đọc dưới 200 ms, 99,9%, chấp nhận trễ 5 giây cho bộ đếm lượt xem".
- **Ước lượng để ra quyết định, không để khoe phép tính**: 1 ngày ≈ 86.400 giây; làm tròn 10⁵ cho nhanh cũng được, kết quả cùng bậc. Ví dụ dịch vụ chia sẻ đoạn text (kiểu pastebin), giả định phần lớn paste giữ không hạn: 1 triệu paste mới mỗi ngày ≈ 12 ghi/giây, đọc gấp 10 ≈ 120/giây, đỉnh gấp 3 ≈ 350 đọc/giây; paste trung bình 10 KB → 10 GB/ngày, khoảng 3,65 TB/năm. Kết luận rút ra: tải thấp nên một database là đủ, cache để dành tới khi lượt đọc hay latency đòi hỏi; nội dung nên ra object storage còn database chỉ giữ metadata (khoảng 200 byte mỗi paste, 73 GB/năm). Nếu paste hết hạn sau 30 ngày thì dung lượng ổn định chỉ khoảng 300 GB: một yêu cầu về thời hạn đổi hẳn kết luận. Nói kết luận thành lời; con số không dẫn tới quyết định nào thì bỏ. Cách ước lượng chi tiết ở bài Ước lượng nhanh.
- **API**: viết vài dòng như `POST /pastes` → `{id}`, `GET /pastes/{id}`. Ghi rõ phân trang cho API trả danh sách, [[idempotency-key|idempotency key]] cho API ghi có thể bị retry, và xác thực ở đâu. Không cần đầy đủ như tài liệu; xem bài Thiết kế REST API.
- **Mô hình dữ liệu đi từ access pattern**: liệt kê query chính ("lấy paste theo id", "liệt kê paste của một user theo thời gian") rồi mới chọn bảng, khoá và index. Query nào chạy nhiều nhất quyết định khoá chính và shard key nếu cần. Xem bài NoSQL: chọn loại nào.
- **High-level đi từ đơn giản**: vẽ một bản chạy được với một database trước, rồi thêm khối khi một con số hay yêu cầu đòi hỏi. Ghi lên mũi tên là gọi đồng bộ hay bất đồng bộ, ghi lên mỗi khối nó giữ dữ liệu gì. Danh sách các khối và việc của từng khối ở bài Các khối xây dựng.
- **Chọn phần để deep dive**: chọn chỗ khó riêng của bài, không phải phần chung ai cũng có. Rút gọn link: sinh mã ngắn không trùng. News feed: fan-out khi ghi hay khi đọc, người dùng nổi tiếng. Chat: thứ tự tin nhắn, đồng bộ nhiều thiết bị. Thanh toán: idempotency và đối soát. Người phỏng vấn thường kéo vào phần họ quan tâm; đi theo họ, đừng giành lại kịch bản.
- **Nói trade-off theo mẫu**: "Tôi chọn X vì yêu cầu Y. Giá là Z. Nếu yêu cầu đổi thành W, tôi sẽ chuyển sang V." Ví dụ: "Tôi dùng cache-aside với TTL 5 phút vì trang sản phẩm đọc gấp 100 lần ghi; giá là giá hiển thị có thể cũ tới 5 phút; nếu giá phải luôn đúng thì xoá cache khi cập nhật và đọc giá từ database ở bước thanh toán."
- **Tổng kết bằng lỗi và tăng trưởng**: khi tải gấp 10 thì khối nào nghẽn trước; khi cache, database primary hay một AZ chết thì người dùng thấy gì; metric và cảnh báo chính ([[slo|SLO]], độ dài queue, [[replica-lag|replica lag]]). Đây thường là chỗ phân biệt senior với mid.
- **Quản lý thời gian**: nhìn đồng hồ ở mốc 15, 25 và 40 phút. Hết phút 25 mà chưa có sơ đồ tổng chạy được là đang chậm: rút gọn ước lượng và API, đừng hy sinh deep dive. Phần nào chưa kịp làm thì nói ngắn sẽ làm thế nào ("phần analytics tôi sẽ đẩy event qua Kafka vào kho riêng, có thể đi sâu nếu anh muốn") thay vì bỏ qua im lặng.
- **Kỳ vọng theo cấp**: mid được kỳ vọng ra thiết kế chạy được và hiểu các khối mình dùng. Senior chủ động dẫn dắt, tự tìm điểm nghẽn và cách hỏng, đi sâu được ít nhất một khối tới mức cơ chế bên trong. Solution Architect còn được hỏi về chi phí, bảo mật, vận hành, cách chuyển từ hệ cũ sang và cách chia việc cho các team.
- **Bẫy hay gặp**: thuộc lòng một kiến trúc mẫu rồi kể ra bất kể đề bài; [[premature-scaling|scale sớm]] (sharding, microservices, multi-region cho 50 ghi mỗi giây); tính con số rồi không dùng; dùng từ khoá mà không giải thích được cơ chế ("dùng consistent hashing" nhưng không biết nó giải quyết gì); bỏ qua gợi ý của người phỏng vấn; không nhắc gì tới lỗi, giám sát hay bảo mật.
- **Phỏng vấn online**: dùng công cụ vẽ quen tay (Excalidraw, draw.io), viết yêu cầu và con số thành danh sách ở góc bảng để nhìn lại khi chọn phương án. Hỏi trước người phỏng vấn muốn bạn vẽ hay chỉ nói.
