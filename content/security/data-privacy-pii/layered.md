## Quick

[[pii|Dữ liệu cá nhân]] là mọi thông tin giúp xác định một người cụ thể, kể cả khi phải ghép nhiều trường lại. Bảo vệ nó không phải một tính năng mà là kỷ luật trên cả vòng đời: **không thu cái không cần, biết mình đang giữ gì ở đâu, mã hoá và giới hạn người xem, ghi lại ai đã xem, và xoá được khi hết mục đích**. Chỗ hay rò nhất không phải database chính mà là bản sao: log, kho phân tích, backup, môi trường test.

## Interview

**Định nghĩa và phân loại**: định danh trực tiếp (họ tên kèm số điện thoại, số CCCD, email), định danh gián tiếp ([[quasi-identifier|quasi-identifier]] như ngày sinh, giới tính, mã bưu chính, ghép lại vẫn ra một người), và [[sensitive-personal-data|dữ liệu nhạy cảm]] (sức khoẻ, tài khoản ngân hàng, lịch sử giao dịch, ảnh CCCD, sinh trắc học, vị trí). Mức nhạy cảm quyết định mức bảo vệ.

**Nguyên tắc chung của** [[gdpr|GDPR]] **và luật Việt Nam**: có cơ sở pháp lý cho mỗi mục đích (đồng ý hoặc ngoại lệ luật cho phép), [[purpose-limitation|giới hạn mục đích]], [[data-minimization|tối thiểu hoá]], giữ có thời hạn, bảo mật, và chứng minh được mình tuân thủ. Ở Việt Nam, Luật Bảo vệ dữ liệu cá nhân 2025 và Nghị định 356/2025 thay Nghị định 13 từ 1/1/2026.

**Biện pháp kỹ thuật**:
- [[data-classification|Phân loại]] và kiểm kê: bảng nào, topic nào, bucket nào chứa gì, ai sở hữu.
- [[pseudonymization|Giả danh hoá]] hoặc [[tokenization|tokenization]] khi hệ thống khác chỉ cần khoá nối, không cần giá trị thật.
- [[encryption-at-rest|Mã hoá at rest]] và TLS cho mọi kết nối, thêm [[field-level-encryption|mã hoá theo trường]] cho dữ liệu nhạy cảm nhất.
- [[data-masking|Che dữ liệu]] khi hiển thị cho support và trong log.
- [[audit-log|Audit log]] truy cập: ai xem hồ sơ nào, lúc nào, vì lý do gì.
- [[data-retention|Thời hạn lưu]] và luồng xoá chạy tới mọi bản sao.

**Bẫy hay gặp**: che `toString()` của [[dto|DTO]] nhưng PostgreSQL vẫn đưa giá trị vào thông báo lỗi constraint, và handler log nguyên `getMessage()`. Băm số điện thoại bằng SHA-256 rồi gọi là ẩn danh: không gian số di động dạng `09xxxxxxxx` tối đa 100 triệu chuỗi, dò ngược hết trong khoảng một giây. Chép database production xuống staging cho dev test.

**Cách làm đúng**: xử lý như một yêu cầu kiến trúc từ đầu (privacy by design), không phải việc pháp chế làm lúc cuối.

## Deep

- **Khung pháp lý cần biết ở mức kỹ sư** (không thay tư vấn pháp lý):
  - Việt Nam: Luật Bảo vệ dữ liệu cá nhân số 91/2025/QH15 có hiệu lực 1/1/2026; Nghị định 356/2025/NĐ-CP hướng dẫn và thay Nghị định 13/2023. Mức phạt tối đa với tổ chức: mua bán dữ liệu cá nhân 10 lần khoản thu bất hợp pháp; vi phạm chuyển dữ liệu ra nước ngoài 5% doanh thu năm trước (hai mức này áp dụng khi cao hơn 3 tỷ đồng); vi phạm khác tới 3 tỷ đồng.
  - Nghị định 356 mở rộng nhóm nhạy cảm: thêm tình trạng sức khoẻ nói chung, thông tin tài khoản và thẻ ngân hàng, lịch sử giao dịch tài chính, ảnh CCCD, tên đăng nhập và mật khẩu tài khoản định danh điện tử, dữ liệu theo dõi hành vi trên mạng.
  - Đồng ý phải rõ ràng, lưu lại và kiểm chứng được nội dung và thời điểm; không được đặt sẵn ô đồng ý. Luật có ngoại lệ không cần đồng ý (thực hiện thoả thuận với chủ thể, nghĩa vụ pháp luật, tình huống khẩn cấp...).
  - Quyền của chủ thể (xem, sửa, xoá, rút đồng ý, phản đối) theo Nghị định 356: phản hồi trong 2 ngày làm việc; xoá trong 20 ngày, 30 ngày nếu phải phối hợp bên xử lý hay bên thứ ba, gia hạn một lần tối đa 20 ngày. GDPR: một tháng, gia hạn thêm tối đa hai tháng.
  - Vi phạm: báo Bộ Công an trong 72 giờ kể từ khi phát hiện, nếu có thể gây hại cho chủ thể. Rò dữ liệu vị trí hoặc sinh trắc học còn phải báo chủ thể trong 72 giờ. GDPR cũng là 72 giờ tới cơ quan giám sát (Điều 33), báo chủ thể khi rủi ro cao (Điều 34).
  - Lưu trên cloud đặt ở nước ngoài (ví dụ region Singapore) là chuyển dữ liệu ra nước ngoài theo luật Việt Nam: cần hồ sơ đánh giá tác động chuyển dữ liệu xuyên biên giới, trừ một số trường hợp như dữ liệu của chính người lao động. Hồ sơ [[dpia|DPIA]] và hồ sơ chuyển dữ liệu nay được Bộ Công an xem xét trước. Doanh nghiệp nhỏ và khởi nghiệp được miễn DPO và hai hồ sơ này 5 năm kể từ 1/1/2026, trừ khi xử lý dữ liệu nhạy cảm, kinh doanh dịch vụ xử lý dữ liệu, hoặc đã xử lý dữ liệu của từ 100.000 người trở lên.
  - GDPR áp dụng cả với công ty ở Việt Nam khi chào bán hàng cho người ở EU hoặc theo dõi hành vi của họ (Điều 3(2)). Phạt tới 20 triệu EUR hoặc 4% doanh thu toàn cầu. Các điều kỹ sư hay gặp: Điều 17 (quyền được xoá, có ngoại lệ khi luật bắt giữ), Điều 25 (bảo vệ dữ liệu từ thiết kế và mặc định), Điều 28 (hợp đồng với bên xử lý), Điều 32 (biện pháp bảo mật, nêu cả giả danh hoá và mã hoá).
  - [[data-controller|Bên kiểm soát]] quyết định mục đích và cách xử lý; [[data-processor|bên xử lý]] làm thay theo hợp đồng (nhà cung cấp SMS, dịch vụ log, cloud). Gửi dữ liệu cho bên xử lý cần hợp đồng ghi mục đích, loại dữ liệu, thời hạn và việc xoá.
- **Kiểm kê trước, bảo vệ sau**: không bảo vệ được thứ mình không biết đang giữ. Bản đồ dữ liệu ghi mỗi trường cá nhân nằm ở bảng, topic Kafka, index, bucket, kho phân tích, bên thứ ba nào, mục đích gì, giữ bao lâu. Gắn nhãn phân loại trong schema hoặc [[data-catalog|data catalog]]; quét tự động (Amazon Macie cho S3, công cụ phát hiện PII trong log) để bắt chỗ bị sót.
- **Tối thiểu hoá là biện pháp rẻ nhất**: không thu CCCD nếu chỉ cần xác nhận đủ 18 tuổi; lưu năm sinh thay vì ngày sinh khi đủ dùng; không gửi PII vào event mà chỉ gửi id (bài Thiết kế event & schema evolution); analytics nhận id giả danh thay vì số điện thoại.
- **Giả danh hoá không phải ẩn danh hoá**:
  - Dữ liệu giả danh vẫn nối ngược được về người (có bảng tra hay khoá), nên vẫn là dữ liệu cá nhân (GDPR Recital 26). Chỉ dữ liệu [[anonymization|ẩn danh]] thật sự, không còn cách hợp lý nào nhận lại người, mới ra khỏi phạm vi luật.
  - Đo trên JDK 27, MacBook 10 lõi: băm SHA-256 toàn bộ 100 triệu số dạng `09xxxxxxxx` mất 1,1 giây, tức hash số điện thoại không có khoá đảo ngược ngay. Muốn giả danh bằng hash thì dùng [[hmac|HMAC]] với khoá giữ trong [[kms|KMS]]; mất khoá là mất khả năng nối.
  - Quasi-identifier: nghiên cứu của Latanya Sweeney (2000) ước tính 87% người Mỹ được xác định duy nhất chỉ bằng mã ZIP 5 chữ số, giới tính và ngày sinh. Xuất dữ liệu "đã bỏ tên" mà còn ba cột này là chưa ẩn danh. Kỹ thuật như k-anonymity (làm thô dữ liệu cho tới khi mỗi tổ hợp có ít nhất k người) hay differential privacy (thêm nhiễu có kiểm soát vào kết quả thống kê) dành cho xuất bản dữ liệu, không phải việc làm hằng ngày.
- **Tokenization**: một vault giữ giá trị thật, các hệ thống khác chỉ thấy token ngẫu nhiên. Khác hash: không suy ngược được nếu không gọi vault, và xoá trong vault là mọi token mất nghĩa. Đổi lại vault thành dependency quan trọng nhất về availability và bảo mật. Bản thẻ thanh toán của ý này là [[card-tokenization|tokenization thẻ]] ở bài Thiết kế hệ thống thanh toán.
- **Mã hoá, mỗi lớp chặn một kiểu tấn công**:
  - At rest ở tầng đĩa (EBS, RDS, TDE): chống mất đĩa, lộ snapshot. Không chặn được ai có quyền SQL hay ứng dụng bị chiếm, vì database tự giải mã khi đọc.
  - In transit: TLS cả trong VPC, gồm kết nối tới database (`sslmode=verify-full` với pgjdbc), cache và broker (bài TLS & HTTPS).
  - Theo trường ở tầng ứng dụng với [[envelope-encryption|envelope encryption]] và KMS (bài Mật mã cho kỹ sư): DBA, bản dump, replica đọc chỉ thấy ciphertext. Giá phải trả: không `WHERE`, `ORDER BY`, `LIKE` được trên cột đó. Tìm chính xác thì thêm [[blind-index|blind index]] là HMAC của giá trị đã chuẩn hoá; khoá HMAC phải khác khoá mã hoá; blind index của trường ít giá trị (giới tính, tỉnh) lộ phân bố nên đừng làm.
  - Xoá theo người bằng [[crypto-shredding|crypto-shredding]] khi dữ liệu nằm trong nơi không xoá được từng dòng (event store, backup).
- **Che dữ liệu khi hiển thị**: support thấy `******5678` và chỉ bấm xem đầy đủ khi cần, mỗi lần bấm ghi audit. Che ở server, không gửi giá trị đầy đủ rồi che bằng CSS hay JavaScript. Môi trường dev và staging dùng dữ liệu sinh ra hoặc bản đã che tĩnh (static masking) không đảo ngược được, không chép production.
- **Log là nơi rò nhiều nhất** (cấu trúc log, mask ở encoder: bài Log cho production):
  - Thông báo lỗi constraint của PostgreSQL chứa giá trị: `Key (phone)=(0912345678) already exists`, và với check hay not-null là cả dòng `Failing row contains (...)`. pgjdbc nối phần `Detail` này vào `getMessage()`, Spring giữ nguyên trong `DuplicateKeyException`. Tham số `logServerErrorDetail=false` của pgjdbc bỏ phần này khỏi message, nhưng `getServerErrorMessage().getDetail()` vẫn còn. Log của chính PostgreSQL cũng có dòng `DETAIL`, tắt bằng `log_error_verbosity = terse` (đã chạy với PostgreSQL 17.6, pgjdbc 42.7.7, Spring 7.0.10). Giữ `log_parameter_max_length_on_error = 0` (mặc định, PG13+) để log lỗi không kèm tham số bind, và đừng bật `log_statement = all` trên production vì nó ghi cả giá trị.
  - Nguồn khác: `CommonsRequestLoggingFilter` bật `includePayload`, URL có số điện thoại trong query string (access log, header `Referer`), lỗi validation trả lại giá trị sai, span của [[apm|APM]] chứa câu SQL có literal, SDK analytics và crash report ở app, heap dump (bài Bộ công cụ chẩn đoán JVM).
  - Phòng ở nhiều lớp: không đưa PII vào message ngay từ đầu; mask ở encoder cho mẫu đã biết (số điện thoại, CCCD 12 số, email); quét log định kỳ và cảnh báo khi khớp mẫu; log giữ ngắn và phân quyền xem. Log là dữ liệu cá nhân khi chứa định danh, nên cũng có thời hạn và cũng phải xoá được.
- **Audit log truy cập** (khác [[audit-trail|audit trail]] ghi thay đổi dữ liệu): ai (user thật, không phải tài khoản service), xem hay xuất bản ghi nào, lúc nào, từ đâu, theo ticket nào. Ghi ở tầng ứng dụng vì database chỉ thấy user kết nối chung; `pgaudit` cho truy cập trực tiếp vào database. Ghi vào kho chỉ nối thêm, tài khoản khác với ứng dụng (S3 Object Lock, bài Kiến trúc bảo mật). Audit log chỉ ghi id, không chép lại nội dung hồ sơ. Không ai đọc thì vô dụng: cảnh báo một người xem hàng trăm hồ sơ một giờ, xem hồ sơ không được giao, xuất file lớn.
- **Thời hạn lưu và xoá**:
  - Mỗi loại dữ liệu có thời hạn và lý do; hết hạn thì job xoá hoặc ẩn danh hoá. Có nghĩa vụ giữ theo luật khác (chứng từ kế toán, hồ sơ bệnh án) thì xoá phần không thuộc nghĩa vụ đó và khoá phần còn lại, không phải xoá hết.
  - Yêu cầu xoá phải đi tới mọi bản sao: read replica tự theo; search index, cache, kho phân tích, CRM, bên thứ ba cần event xoá và đối soát. Backup thì thường không sửa từng dòng: giữ backup ngắn hạn, lưu danh sách id đã xoá và chạy lại việc xoá sau mỗi lần khôi phục, hoặc dùng crypto-shredding.
  - Xoá cứng làm vỡ khoá ngoại và báo cáo lịch sử: thay trường cá nhân bằng giá trị trống hay token "đã xoá" và giữ dòng cho thống kê.
- **Bẫy production khác**: chép bảng có PII vào kho mà ai cũng đọc được (bài Kiến trúc dữ liệu); export CSV gửi qua email; bucket S3 public; bên thứ ba tích hợp nhận nhiều hơn cần (gửi cả hồ sơ cho dịch vụ SMS trong khi chỉ cần số); prompt gửi tới LLM bên ngoài chứa dữ liệu khách hàng; [[idor|IDOR]] làm lộ hồ sơ người khác (bài OWASP Top 10 với Java/Spring).
- **Liên quan**: lưu mật khẩu: bài AuthN & AuthZ cơ bản; KMS, envelope encryption: bài Mật mã cho kỹ sư; secret lọt vào log: bài Quản lý secret; RLS và cô lập tenant: bài Kiến trúc multi-tenant.
