## Quick

Năm việc khác nhau, đừng nhầm: [[encoding|encoding]] (Base64) chỉ đổi cách biểu diễn, ai cũng đảo được; [[cryptographic-hash|hash]] là dấu vân tay một chiều; [[hmac|HMAC]] là hash có khoá để chứng minh không bị sửa; mã hoá giấu nội dung và cần khoá để mở; [[digital-signature|chữ ký số]] chứng minh ai viết. Mặc định an toàn trong Java: **[[aes-gcm|AES-GCM]] với [[nonce]] không bao giờ lặp**, khoá do [[kms|KMS]] giữ theo kiểu [[envelope-encryption|envelope encryption]].

## Interview

**Hash** (SHA-256): cùng đầu vào luôn ra cùng 32 byte, không đảo ngược được, khó tìm hai đầu vào trùng hash. Dùng cho checksum, khử trùng file, đầu vào của chữ ký. MD5 và SHA-1 đã tìm được va chạm, không dùng cho bảo mật. Hash mật khẩu là chuyện riêng (bài AuthN & AuthZ cơ bản).

**HMAC**: hash trộn với khoá bí mật. Ai có khoá mới tính được, nên bên nhận biết message không bị sửa và đến từ bên có khoá, ví dụ webhook.

**[[symmetric-encryption|Mã hoá đối xứng]]**: một khoá cho cả mã hoá lẫn giải mã. AES nhanh, có phần cứng hỗ trợ. Chế độ quan trọng ngang thuật toán: dùng AES-GCM, vừa giấu vừa phát hiện bị sửa. Mỗi lần mã hoá cần một nonce 12 byte không trùng với cùng khoá; lặp nonce là lộ nội dung.

**[[asymmetric-encryption|Mã hoá bất đối xứng]]** (RSA, đường cong elliptic): cặp khoá công khai và khoá riêng. Công khai để mã hoá, chỉ khoá riêng giải được. Chậm và chỉ mã hoá được vài trăm byte, nên thực tế dùng lai: bất đối xứng để trao hoặc bọc khoá, AES để mã hoá dữ liệu, như TLS.

**Chữ ký số**: ngược chiều, khoá riêng ký, khoá công khai kiểm. Chữ ký không giấu nội dung: payload của [[jwt|JWT]] ai cũng đọc được.

**Envelope encryption**: KMS giữ khoá chính trong phần cứng và không bao giờ trả nó ra. Ứng dụng xin một data key, mã hoá dữ liệu tại chỗ, lưu bản data key đã bị khoá chính bọc cạnh dữ liệu.

**Bẫy hay gặp**: coi Base64 là mã hoá; `Cipher.getInstance("AES")` ra chế độ ECB; nonce cố định hoặc tự đếm rồi reset khi restart; khoá nằm trong code hoặc file cấu hình; `Random` cho token; so HMAC bằng `equals`.

## Deep

- **Đã chạy trên JDK 27**:
  - `Cipher.getInstance("AES")` của SunJCE là `AES/ECB/PKCS5Padding`: không IV, hai khối 16 byte giống nhau (`LUONG=25000000;;` hai lần) ra hai khối mã hoá giống hệt nhau. Nhìn ciphertext đã biết chỗ nào lặp. Luôn ghi đủ `AES/GCM/NoPadding`.
  - AES-GCM: 20 byte dữ liệu ra 36 byte (thêm tag 16 byte). Lưu nonce 12 byte cạnh ciphertext; nonce không bí mật.
  - Sửa một bit ciphertext hoặc đổi AAD từ `user:42` sang `user:43` đều ném `AEADBadTagException: Tag mismatch`. [[aad|AAD]] là dữ liệu đi kèm không được mã hoá nhưng được bảo vệ: gắn bản mã với chủ của nó để không chép được ciphertext của người này sang dòng của người khác.
  - Lặp nonce: hai thư mã hoá cùng khoá và nonce, biết thư thứ nhất (`Chuyen 5.000.000 cho tai khoan A`) thì XOR ra nguyên văn thư thứ hai (`Chuyen 9.900.000 cho tai khoan B`). Lặp nonce với GCM còn cho kẻ tấn công giả được tag.
  - Java chỉ chặn trên cùng một object: gọi `doFinal` lần hai ném `IllegalStateException: Must use either different key or  iv for GCM encryption` (nguyên văn, có hai dấu cách), `init` lại cùng IV ném `Cannot reuse iv for GCM encryption`. Tạo `Cipher` mới với cùng khoá và IV thì được chấp nhận. Tránh lặp là việc của bạn.
- **Chọn nonce**: 12 byte từ `SecureRandom` cho mỗi lần mã hoá. NIST SP 800-38D giới hạn nonce ngẫu nhiên ở 2³² lần mã hoá mỗi khoá; vượt mức đó thì đổi data key, việc envelope encryption làm tự nhiên. Nonce dạng bộ đếm phải bền qua restart và không dùng chung giữa các instance.
- **Không có tag là không biết bị sửa**: AES-CBC hay CTR không kèm MAC thì kẻ tấn công lật bit được, và CBC còn bị padding oracle (server trả lỗi padding khác lỗi khác là đủ để giải mã). Cần CBC vì hệ cũ thì phải encrypt-then-MAC.
- **RSA**:
  - RSA-2048 với OAEP SHA-256 mã hoá tối đa 190 byte; byte thứ 191 ném `IllegalBlockSizeException: Data must not be longer than 190 bytes`.
  - Giải mã RSA-2048 khoảng 1.800 lần/giây một luồng trên M4: không dùng cho dữ liệu khối lớn.
  - `Cipher.getInstance("RSA")` của SunJCE dùng PKCS#1 v1.5 padding, dính tấn công kiểu Bleichenbacher (dấu hiệu: nhận tới 245 byte thay vì 190). Ghi rõ `RSA/ECB/OAEPWithSHA-256AndMGF1Padding` (chữ ECB ở đây chỉ là tên, RSA không chia khối).
  - Bẫy tương thích: chuỗi đó trong SunJCE dùng SHA-256 cho OAEP nhưng **MGF1 với SHA-1** (đã in tham số: `MD: SHA-256, MGF: MGF1SHA-1`). Bên kia dùng SHA-256 cho cả hai (như `RSAES_OAEP_SHA_256` của AWS KMS, nhiều thư viện khác) thì giải mã thất bại. Truyền rõ `new OAEPParameterSpec("SHA-256", "MGF1", MGF1ParameterSpec.SHA256, PSource.PSpecified.DEFAULT)` khi `init`.
- **Chữ ký**: ECDSA P-256 ra 69–72 byte (mã hoá DER, đo 2.000 lần), Ed25519 luôn 64 byte. Đổi `amount` 250000 thành 950000 thì `verify` ra `false`. Cùng một thông tin, JWT `HS256` là HMAC với secret chung (ai kiểm được thì cũng ký được), `RS256`/`ES256` là chữ ký (service chỉ cần khoá công khai): bài JWT chuyên sâu.
- **Hash không phải `hashCode`**: `"Aa".hashCode()` và `"BB".hashCode()` cùng là 2112. `hashCode` 32 bit là để chia bucket, không chống ai cả.
- **So sánh bí mật**: `Arrays.equals` hay `String.equals` dừng ở byte khác đầu tiên, thời gian lộ số byte đúng. Dùng `MessageDigest.isEqual` (so trọn, thời gian không phụ thuộc vị trí sai).
- **Ngẫu nhiên**: token, nonce, [[salt]], khoá lấy từ [[csprng|SecureRandom]] (mặc định `NativePRNG` trên Linux và macOS, đọc nguồn của hệ điều hành). `Random` và `Math.random` đoán được từ vài giá trị đã thấy. `UUID.randomUUID()` dùng `SecureRandom` nhưng chỉ 122 bit ngẫu nhiên, đủ cho id, nên dùng 32 byte cho token.
- **Envelope encryption với AWS KMS**:
  - `Encrypt` của KMS chỉ nhận tối đa 4.096 byte, và mỗi lần gọi là một request mạng tính tiền, có quota mỗi giây. Vì vậy không mã hoá dữ liệu trực tiếp bằng KMS.
  - `GenerateDataKey` trả hai bản của một khoá AES-256: bản rõ để mã hoá ngay trong bộ nhớ rồi bỏ đi, và bản đã bọc (`CiphertextBlob`) để lưu cạnh dữ liệu. Đọc lại: gửi bản đã bọc cho `Decrypt`, nhận khoá rõ, giải mã tại chỗ.
  - Quyền giải mã nằm ở key policy và IAM của khoá KMS, có CloudTrail ghi từng lần giải mã: lộ bucket mà không có quyền KMS thì vẫn không đọc được (bài Kiến trúc bảo mật).
  - Xoay khoá chính tự động của AWS KMS (mặc định mỗi năm, cấu hình được) giữ lại vật liệu khoá cũ tới khi xoá khoá, để giải các data key cũ; dữ liệu không phải mã hoá lại. Muốn ngừng phụ thuộc vào một khoá chính (chuyển sang khoá khác) thì gọi `ReEncrypt` để bọc lại các data key, vài chục byte mỗi cái, không đụng tới dữ liệu.
  - Mỗi tenant một khoá: xoá khoá là xoá được dữ liệu ở mọi bản sao và backup ([[crypto-shredding|crypto-shredding]]). Lưu ý: AWS KMS bắt chờ 7–30 ngày trước khi xoá thật, và data key rõ đang cache trong bộ nhớ vẫn dùng được tới khi bị bỏ. Mỗi khoá KMS tính phí hằng tháng và có giới hạn số khoá, nên hệ thống nhiều tenant nhỏ thường giữ một khoá bọc riêng cho mỗi tenant dưới một khoá KMS chung (bài Multi-tenancy).
  - Cache data key giảm số lần gọi KMS nhưng một khoá dùng cho nhiều bản ghi hơn và nằm trong bộ nhớ lâu hơn; AWS Encryption SDK có cache với giới hạn tuổi và số message.
  - Encryption context của KMS đóng vai trò AAD: phải gửi đúng context lúc `Decrypt`, và context được ghi vào CloudTrail.
  - SSE-KMS của S3, mã hoá RDS và EBS dùng đúng cơ chế này. Chúng bảo vệ khi mất đĩa, mất snapshot; ứng dụng có quyền đọc thì vẫn thấy dữ liệu rõ. Dữ liệu cần giấu cả với DBA thì mã hoá ở tầng ứng dụng.
- **Khoá không nằm trong code, image hay git**: lấy từ KMS, Vault, Secrets Manager lúc chạy (bài Quản lý secret).
- **Hậu lượng tử**: máy tính lượng tử đủ lớn sẽ phá RSA và ECC (thuật toán Shor). Với AES và SHA-256, thuật toán Grover chỉ giảm độ mạnh còn khoảng một nửa số bit, nên AES-256 vẫn đủ. Kẻ tấn công có thể lưu traffic hôm nay để giải sau ("harvest now, decrypt later"). JDK 24 thêm ML-KEM (JEP 496) và ML-DSA (JEP 497); trên JDK 27 khoá công khai mã hoá X.509 của ML-KEM-768 là 1.206 byte và ML-DSA-65 là 1.974 byte, so với 91 byte của P-256. TLS của JDK 27 mặc định trao khoá lai `X25519MLKEM768` (bài TLS & HTTPS).
- **Khi khó bảo đảm nonce không lặp** (nhiều máy cùng khoá, không có bộ đếm bền), dùng chế độ chịu lặp nonce như AES-GCM-SIV, hoặc đổi data key thường xuyên. Mỗi message AES-GCM cũng có giới hạn khoảng 64 GiB.
- **Không tự chế thuật toán và giao thức**: dùng thư viện có sẵn (JCA, Tink, AWS Encryption SDK) ở mức API cao nhất có thể. Tink chọn sẵn chế độ, tự sinh nonce và gắn id khoá vào bản mã để xoay khoá.
