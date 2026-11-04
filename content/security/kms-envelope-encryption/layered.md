## Quick

Cơ chế [[envelope-encryption|envelope encryption]] (data key mã hoá dữ liệu, [[kms|KMS]] bọc data key) nằm ở bài Mật mã cho kỹ sư. Bài này về lúc đưa nó vào hệ thống thật: **đếm số lần gọi KMS so với quota, gắn mỗi bản mã với đúng chỗ của nó bằng [[aad|AAD]] (cơ chế ở bài Mật mã cho kỹ sư) và [[encryption-context|encryption context]], và ghi phiên bản khoá vào từng bản mã để xoay khoá, xoá khoá và DR làm được**.

## Interview

Ở quy mô lớn, envelope encryption đặt ra ba câu hỏi thiết kế.

Thứ nhất, gọi KMS bao nhiêu lần. AWS KMS cho mỗi tài khoản mỗi region một quota chung cho `Encrypt`, `Decrypt`, `GenerateDataKey`: mặc định 10.000 request mỗi giây, 20.000 ở Singapore hay Tokyo. Quota này tính cả request mà S3, EBS, RDS gửi thay bạn. Một API đọc 3.000 hồ sơ mỗi giây, mỗi hồ sơ năm trường mã hoá, mỗi trường một lần `Decrypt`, là 15.000 request mỗi giây: vượt quota mặc định, chiếm 75% quota của Singapore (dễ bị KMS từ chối khi S3 cũng gọi cùng lúc), và khoảng 117.000 USD mỗi tháng với giá 0,03 USD mỗi 10.000 request. Cách làm đúng là phân tầng khoá ([[key-hierarchy|key hierarchy]]): khoá KMS bọc một khoá trung gian cho mỗi tenant, khoá trung gian được cache vài phút trong ứng dụng và sinh data key cho từng bản ghi. [[hierarchical-keyring|Hierarchical keyring]] của AWS Encryption SDK làm đúng việc này, và gọi khoá trung gian là [[branch-key|branch key]].

Thứ hai, bản mã gắn với cái gì. [[aes-gcm|AES-GCM]] chỉ chứng minh bản mã không bị sửa, không chứng minh nó thuộc dòng nào. Ai có quyền `UPDATE` chép bản mã CCCD của người này sang dòng người kia thì ứng dụng giải mã bình thường và hiện sai người. Đưa tenant, bảng, cột, khoá chính vào AAD để chép sang chỗ khác là giải mã thất bại.

Thứ ba, vòng đời khoá. Mỗi bản mã mang id và phiên bản của khoá đã bọc nó. Xoay khoá KMS không đổi data key nào; nghi data key bị lộ thì phải mã hoá lại dữ liệu. Xoá khoá của một tenant là [[crypto-shredding|crypto-shredding]], nhưng chỉ đúng khi mọi bản sao của khoá đó, kể cả backup, cũng mất. DR sang region khác cần khoá dùng được ở đó.

Không dùng khi chỉ cần chống mất đĩa hay snapshot: SSE-KMS của S3, mã hoá RDS và EBS đã đủ, rẻ hơn nhiều so với mã hoá từng trường.

## Deep

- **Quota và throttling của AWS KMS** (tài liệu AWS KMS, 11/2026):
  - Các thao tác mã hoá đối xứng dùng chung một quota cho mỗi tài khoản và region: 10.000 request/giây mặc định; 20.000 ở us-east-2, ap-southeast-1, ap-southeast-2, ap-northeast-1, eu-central-1, eu-west-2, eu-south-2; 100.000 ở us-east-1, us-west-2, eu-west-1. Khoá RSA và ECC chỉ 1.000. Gọi khoá ở tài khoản khác thì tính vào quota của tài khoản gọi.
  - Request của dịch vụ AWS thay bạn (S3 SSE-KMS, EBS, RDS) tính vào cùng quota; khoá do AWS sở hữu thì không. Một job đọc hàng triệu object SSE-KMS có thể làm API của bạn bị throttle. S3 Bucket Key giảm số request của SSE-KMS bằng một khoá cấp bucket.
  - Vượt quota thì KMS từ chối request (throttle, lỗi `ThrottlingException`); SDK [[retry-backoff|retry có backoff]], latency tăng trước khi lỗi lộ ra. Theo dõi metric sử dụng quota trong CloudWatch, xin tăng quota trước sự kiện lớn.
  - Giá: 1 USD mỗi khoá mỗi tháng, 0,03 USD mỗi 10.000 request đối xứng, 20.000 request miễn phí mỗi tháng.
- **Phân tầng khoá**:
  - Ba tầng thường gặp: khoá KMS (không rời HSM) → khoá trung gian theo tenant hoặc theo khoảng thời gian (lưu ở dạng đã bọc) → data key cho mỗi bản ghi hoặc mỗi lô. Mỗi tầng xoay và thu hồi độc lập.
  - AWS Encryption SDK cho Java 3.x (bản mới nhất 3.0.2, dùng kèm Material Providers Library) có Hierarchical keyring: branch key lưu trong DynamoDB, được khoá KMS bọc; lần đầu dùng một branch key thì gọi KMS một lần, sau đó cache trong thời gian TTL (ví dụ trong tài liệu là 600 giây). Mỗi message vẫn có data key riêng, bọc bằng khoá dẫn xuất từ branch key. (Keyring là thành phần của SDK quyết định data key được bọc và mở bằng gì.) AWS khuyên mỗi tenant một branch key và dùng branch key ID supplier, một hàm đọc tenant từ encryption context để chọn branch key.
  - Bản mã của Hierarchical keyring chỉ giải được bằng Hierarchical keyring. Chọn nó là chọn định dạng.
  - Cache data key (caching CMM; CMM là cryptographic materials manager, lớp lấy và cache khoá cho SDK) là cách cũ hơn: phải đặt tuổi tối đa, có thể giới hạn số message (tới 2³²) và số byte mỗi data key. Mặc định SDK sinh data key mới cho mỗi lần mã hoá; AWS khuyên chỉ cache khi cần để đạt hiệu năng. Java 3.x chỉ hỗ trợ caching CMM với interface master key provider cũ.
  - Cache nghĩa là khoá rõ nằm trong bộ nhớ lâu hơn, và vô hiệu hoá khoá KMS không có tác dụng ngay với các pod đang giữ cache. [[ttl|TTL]] là thời gian tối đa từ lúc thu hồi tới lúc có hiệu lực. CloudTrail và key policy cũng chỉ thấy lần giải khoá trung gian, không thấy từng bản ghi, nên kiểm tenant cho từng lần giải mã là việc của ứng dụng.
- **Định dạng bản mã tự thiết kế**:
  - Lưu `phiên bản định dạng | id khoá và phiên bản | data key đã bọc (hoặc tham chiếu) | nonce | bản mã + tag`. Không có header thì không xoay khoá được, vì không biết bản ghi nào dùng khoá nào.
  - Kích thước: 12 chữ số CCCD mã hoá AES-GCM ra 40 byte ([[nonce]] 12 + 12 + tag 16), chưa kể header và data key. Cột kiểu `bytea`/`VARBINARY`, hoặc Base64 dài thêm một phần ba.
  - Lab: không có AAD, chép bản mã của dòng 1002 sang dòng 1001 thì dòng 1001 hiện CCCD của người 1002; có AAD `customers.national_id:<id>` thì giải mã ném `AEADBadTagException: Tag mismatch` (JDK 27).
  - AAD chỉ chứa giá trị không đổi (tenant, bảng, cột, khoá chính). Dùng trường hay đổi như email làm AAD thì mỗi lần đổi email phải mã hoá lại.
- **Encryption context của KMS**:
  - Là AAD ở tầng bọc data key: gọi `kms:Decrypt` trực tiếp với context sai thì KMS từ chối. So sánh phân biệt hoa thường.
  - AWS Encryption SDK thì khác: context được lưu rõ trong header của message và được xác thực, rồi trả về sau khi giải mã. Message của tenant B chép sang dòng của tenant A vẫn giải mã thành công (branch key ID supplier còn chọn đúng branch key của B từ chính context đó). Ứng dụng phải so `tenant_id` và id bản ghi trong context trả về với dòng đang đọc, hoặc dùng required encryption context CMM để buộc người gọi đưa context mong đợi lúc giải mã.
  - Context được ghi rõ trong CloudTrail, nên không đưa dữ liệu cá nhân vào; dùng id tenant, tên bảng, id bản ghi.
  - Điều kiện `kms:EncryptionContext:tenant_id` trong [[key-policy|key policy]] hoặc IAM policy, so với tag của principal (`${aws:PrincipalTag/tenant_id}`), cho phép một khoá KMS chung mà role của tenant A không giải được data key của tenant B. Điều kiện này chỉ có tác dụng khi mỗi lần giải mã đều gọi KMS. Key policy nói chung và cross-account ở bài Bảo mật trên cloud & IAM.
- **[[key-commitment|Key commitment]]**:
  - AES-GCM không gắn bản mã với một khoá duy nhất: có thể dựng một bản mã giải được bằng hai khoá khác nhau, ra hai nội dung khác nhau. Hệ thống bọc một data key cho nhiều người nhận (nhiều khoá KMS) thì kẻ tấn công có thể làm người nhận A đọc ra `false`, người nhận B đọc ra `true` từ cùng một message.
  - AWS Encryption SDK hỗ trợ giải mã có commitment từ 1.7.x và mặc định `RequireEncryptRequireDecrypt` từ 2.0.x; message lớn thêm khoảng 30 byte. Định dạng tự viết mà có nhiều người nhận thì cần cơ chế tương tự.
- **Xoay khoá**:
  - Xoay tự động của KMS chỉ cho khoá đối xứng do KMS sinh, mặc định mỗi 365 ngày; có thêm xoay theo yêu cầu. Id và ARN không đổi, bản mã cũ vẫn giải được. Lần xoay thứ nhất và thứ hai mỗi lần thêm 1 USD mỗi tháng, từ lần thứ ba không tính thêm.
  - Khoá bất đối xứng, khoá HMAC và khoá trong custom key store không xoay tự động: tạo khoá mới và đổi alias.
  - Xoay khoá KMS chỉ đổi khoá bọc. Data key đã bọc từ trước vẫn như cũ, nên nếu data key rõ có thể đã lộ (dump bộ nhớ, log nhầm) thì phải giải mã và mã hoá lại dữ liệu bằng data key mới. Đổi tầng trung gian (branch key mới) cũng chỉ áp cho bản ghi mới, trừ khi chạy job mã hoá lại.
- **Nhiều region và DR**:
  - Bản mã bọc bằng khoá một region không giải được ở region khác. Sao chép S3 hay snapshot sang region DR phải chỉ định khoá ở region đích, và dịch vụ mã hoá lại khi sao chép.
  - [[multi-region-key|Multi-Region key]] có cùng id và vật liệu khoá ở nhiều region, nên bản mã mà ứng dụng tạo bằng khoá ở region này giải được bằng bản sao khoá ở region kia. Chúng không phải tài nguyên global: key policy, grant, alias, trạng thái bật/tắt ở mỗi region độc lập. AWS khuyên chỉ dùng khi thật sự cần mang bản mã qua region (DR, active-active); không đổi được khoá một region thành multi-Region.
  - Với Hierarchical keyring, bảng branch key trong DynamoDB cũng phải có ở region DR (global table, bảng DynamoDB tự sao chép giữa các region), và khoá KMS bọc nó phải giải được ở đó.
- **Thu hồi và xoá**:
  - Vô hiệu hoá khoá KMS là công tắc khẩn cấp: sau một độ trễ ngắn (trạng thái khoá nhất quán sau), mọi `Decrypt` mới thất bại, trừ data key và branch key còn trong cache. Thời gian chờ xoá 7–30 ngày ở bài Mật mã cho kỹ sư; đặt cảnh báo CloudTrail khi có ai dùng khoá đang chờ xoá, vì đó là dấu hiệu còn dữ liệu cần nó.
  - Crypto-shredding một tenant bằng cách xoá branch key của họ chỉ có hiệu lực khi mọi phiên bản và bản sao của nó cũng hết: mỗi lần xoay branch key thêm một phiên bản, [[pitr|point-in-time recovery]] của DynamoDB giữ tới 35 ngày, global table có bản ở region khác, backup của bảng. Ghi rõ thời hạn đó trong cam kết xoá dữ liệu với khách hàng.
- **Khoá do khách hàng nắm** (enterprise đòi tự quản khoá):
  - Khoá KMS ở tài khoản của khách, cấp quyền cho role của bạn: khách thu hồi được bất kỳ lúc nào, và mọi lỗi phân quyền bên khách làm dịch vụ của bạn hỏng với tenant đó. Thiết kế lỗi rõ ràng theo tenant, không để lan ra tenant khác.
  - Import vật liệu khoá (BYOK, bring your own key) có thể đặt ngày hết hạn; hết hạn là khoá không dùng được. External key store (XKS) giữ khoá trong [[hsm|HSM]] ngoài AWS, nên availability và latency của mọi lần gọi KMS phụ thuộc vào hệ thống của bên giữ khoá.
- **Khoá rõ trong bộ nhớ Java**: xoá `byte[]` bằng `Arrays.fill` sau khi dùng, nhưng `SecretKeySpec` giữ bản sao riêng và GC có thể đã chép mảng đi chỗ khác; Java không bảo đảm xoá sạch được. Giảm rủi ro bằng cách giữ khoá rõ ngắn, không log, không đưa vào heap dump gửi ra ngoài (bài Bộ công cụ chẩn đoán JVM).
- **Tìm kiếm trên trường mã hoá**: [[blind-index|blind index]] (HMAC của giá trị đã chuẩn hoá) ở bài Dữ liệu cá nhân & tuân thủ. AWS Database Encryption SDK cho DynamoDB gọi đó là beacon: HMAC bị cắt ngắn, lưu ở trường riêng, SDK lọc kết quả trùng giả.
- **Ngoài AWS**: GCP Cloud KMS và Azure Key Vault có mô hình tương tự (khoá không rời dịch vụ, bọc data key, quota theo dự án). Vault Transit có endpoint `datakey` trả data key rõ và bản bọc, hợp khi chạy on-premise (bài Quản lý secret).
- **Liên quan**: GenerateDataKey, ReEncrypt, giới hạn 4.096 byte, AAD và nonce: bài Mật mã cho kỹ sư. Key policy, `kms:ViaService`, cross-account: bài Bảo mật trên cloud & IAM. Khoá riêng cho tenant enterprise: bài Kiến trúc multi-tenant. Pepper đặt trong KMS: bài Lưu mật khẩu chuyên sâu.
