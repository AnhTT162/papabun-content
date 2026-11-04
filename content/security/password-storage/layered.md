## Quick

Lưu mật khẩu là chuẩn bị cho ngày bảng user bị lộ: kẻ tấn công dò offline, không bị rate limit. **Chọn [[argon2|Argon2id]] (m=19 MiB, t=2, p=1) hoặc [[bcrypt]] cost ≥ 10, cho phép nhiều thuật toán cùng lúc để nâng dần, và mọi nhánh đăng nhập phải tốn cùng một thời gian**, kể cả khi email không tồn tại.

## Interview

[[password-hashing|Password hashing]] chống một kịch bản cụ thể: database bị lộ, kẻ tấn công thử mật khẩu offline trên GPU. Một RTX 4090 tính khoảng 22 tỷ SHA-256 mỗi giây, nhưng chỉ khoảng 184.000 bcrypt cost 5, tức chừng 5.750 bcrypt cost 10. [[salt|Salt]] riêng cho mỗi user buộc kẻ tấn công dò từng tài khoản một, và [[work-factor|work factor]] làm mỗi lần thử đắt. Argon2id còn tốn bộ nhớ ([[memory-hard-function|memory-hard]]), nên GPU có hàng nghìn lõi nhưng ít bộ nhớ mỗi lõi không tận dụng được hết.

Cơ chế này không cứu mật khẩu yếu: danh sách 14 triệu mật khẩu phổ biến (cỡ danh sách rockyou) chạy hết trên một tài khoản bcrypt cost 10 trong khoảng 40 phút với một RTX 4090. Vì vậy vẫn phải chặn mật khẩu đã lộ và khuyến khích [[mfa|MFA]].

Ba bẫy hay gặp ở code tự viết. Một: endpoint login trả lời ngay khi không tìm thấy email, còn email có thật thì chờ 50 ms để băm, nên đo thời gian là biết email nào có tài khoản ([[user-enumeration|user enumeration]]). Spring Security `DaoAuthenticationProvider` đã chặn việc này bằng cách băm một mật khẩu giả; code login tự viết thường quên. Hai: hàm băm chậm là CPU và bộ nhớ của chính bạn; 50 lượt Argon2 19 MiB cùng lúc làm heap 512 MB văng `OutOfMemoryError`. Giới hạn số lượt băm đồng thời và [[rate-limiting|rate limit]] trước khi băm. Ba: cùng một mật khẩu tiếng Việt gõ từ hai bàn phím có thể ra hai chuỗi byte khác nhau; [[unicode-normalization|chuẩn hoá]] về dạng NFC trước khi băm.

Nâng thuật toán thì lưu kèm id thuật toán và tham số ([[phc-string-format|PHC string]], tiền tố `{id}` của Spring), băm lại khi user đăng nhập đúng. Hash cũ quá yếu như MD5 thì bọc ngay bằng Argon2id thay vì chờ, và bắt đặt lại mật khẩu với tài khoản không quay lại.

## Deep

- **Toán của kẻ tấn công** (hashcat, công cụ dò hash chạy trên GPU; bản 6.2.6, RTX 4090: MD5 164 GH/s, SHA-256 22 GH/s, bcrypt cost 5 184 kH/s; RTX 5090 bcrypt cost 5 khoảng 305 kH/s):
  - Mỗi bậc cost của bcrypt gấp đôi số vòng: cost 5 là 32 vòng, cost 10 là 1.024 vòng, nên cost 10 chậm hơn cost 5 khoảng 32 lần.
  - Không có salt: một lần dò áp cho cả triệu user cùng lúc và dùng được bảng tra sẵn ([[rainbow-table|rainbow table]]). Có salt: chi phí nhân với số user.
  - Mười GPU thuê theo giờ chia đều được việc dò. Work factor chỉ mua thời gian; thời gian đó dùng để phát hiện vụ lộ, buộc đặt lại mật khẩu và báo user.
- **Chọn thuật toán và tham số** (OWASP Password Storage Cheat Sheet):
  - Argon2id tối thiểu `m=19456 KiB, t=2, p=1`, hoặc các cặp tương đương như `m=47104, t=1` hay `m=12288, t=3`. scrypt `N=2^17, r=8, p=1`. bcrypt cost ≥ 10. PBKDF2-HMAC-SHA256 600.000 vòng, chỉ khi cần FIPS 140 (chuẩn mô-đun mật mã của chính phủ Mỹ).
  - `Argon2PasswordEncoder.defaultsForSpringSecurity_v5_8()` là `m=16384` (16 MiB), thấp hơn mức OWASP. Muốn đúng 19 MiB thì tự dựng `new Argon2PasswordEncoder(16, 32, 1, 19456, 2)` và đăng ký dưới id riêng (ví dụ `argon2id-19m`) trong `DelegatingPasswordEncoder`; hash theo mặc định cũ sẽ được `upgradeEncoding` báo cần nâng.
  - Đo trên máy đích: Argon2id `m=19456, t=2, p=1` mất khoảng 20 ms một lần trên M4 với Spring Security 7.1.2 + BouncyCastle 1.83, bcrypt cost 10 khoảng 57 ms (bài AuthN & AuthZ cơ bản đo được 53 ms ở lần khác). OWASP chỉ đặt trần chung: dưới một giây.
  - Tham số `p` (số lane) không làm Spring nhanh hơn: BouncyCastle tính các lane tuần tự. `Argon2PasswordEncoder.upgradeEncoding` chỉ so `memory` và `iterations` với cấu hình hiện tại, từng cái riêng. Đổi `p` từ 1 lên 4 không làm hash cũ được băm lại (đã chạy: `false`); đổi sang `m=46 MiB, t=1` thì hash `m=19 MiB, t=2` bị coi là cần nâng vì bộ nhớ thấp hơn.
- **Hàm băm chậm là bề mặt DoS** (đo JDK 27, heap 512 MB, 10 lõi):
  - 50 thread cùng chạy Argon2id 19 MiB: 103 trên 200 lượt `OutOfMemoryError`, thông lượng còn 9 lượt/giây. 200 thread: 381 trên 800 lượt lỗi.
  - Thêm `Semaphore` bằng số lõi trước bước băm: 800 lượt đều xong, 156 lượt/giây. Đây là [[bulkhead|bulkhead]] cho bước băm; thread còn lại chờ thay vì cùng xin bộ nhớ.
  - Ước lượng: số lượt băm đồng thời × `m` phải nằm gọn trong heap; số login mỗi giây × thời gian một lượt băm ra số lõi cần. Rate limit theo IP và theo tài khoản đặt trước bước băm (bài Rate limiting), để [[credential-stuffing|credential stuffing]] không đốt CPU.
  - Đặt trần kích thước request và độ dài mật khẩu ở tầng validate. Với Argon2id, 128 ký tự là đủ rộng (NIST yêu cầu cho phép ít nhất 64). Với bcrypt, trần phải tính theo byte UTF-8 (72), vì `BCryptPasswordEncoder.encode` ném lỗi khi dài hơn, và 40 ký tự tiếng Việt có dấu đã có thể vượt 72 byte (bài AuthN & AuthZ cơ bản).
- **Rò rỉ theo thời gian và thông báo** (cơ chế hash giả của `DaoAuthenticationProvider` ở bài AuthN & AuthZ cơ bản; dưới đây là phần còn sót):
  - Hash giả của `DaoAuthenticationProvider` (`userNotFoundEncodedPassword`) được tạo bằng encoder mặc định. Đang chuyển thuật toán thì user còn hash bcrypt cost 10 (57 ms) mà email không tồn tại chỉ tốn một lần Argon2id (20 ms): vẫn lệch đủ để đo. Trong giai đoạn chuyển, chọn tham số để hai thuật toán tốn thời gian gần bằng nhau, hoặc tự tạo hash giả theo thuật toán chậm nhất, và giữ rate limit chặt.
  - Tài khoản bị khoá hoặc disabled: `alwaysPerformAdditionalChecksOnUser` (từ 5.7.23, mặc định `true`) vẫn kiểm mật khẩu rồi mới ném `LockedException`, để thời gian như nhau. Thông báo khoá tài khoản vẫn nói lên rằng email có thật; nhiều hệ thống trả cùng một câu cho mọi lỗi đăng nhập.
  - Enumeration còn lọt qua form đăng ký (email đã được dùng) và quên mật khẩu. Trả cùng một câu (nếu email tồn tại, chúng tôi đã gửi thư), gửi thư ở hàng đợi để thời gian phản hồi không phụ thuộc vào việc có gửi hay không.
  - So sánh hash mật khẩu bằng `equals` không phải lỗ hổng đáng kể: kẻ tấn công chọn được mật khẩu thử, nhưng hash đem so đã qua salt và hàm băm chậm, nên không dò dần từng byte được. Các encoder của Spring vẫn so constant-time (thời gian không phụ thuộc vị trí byte sai đầu tiên). Với chữ ký HMAC của webhook thì khác: kẻ tấn công gửi thẳng giá trị đem so, nên phải dùng `MessageDigest.isEqual` (bài Mật mã cho kỹ sư).
- **Chuẩn hoá Unicode** (NIST SP 800-63B bản 4: nên chuẩn hoá NFC trước khi băm, đếm mỗi code point là một ký tự, không cắt bớt mật khẩu):
  - Đã chạy: `Mật-khẩu-Phở-2026` dạng NFC dài 17 ký tự (23 byte UTF-8), dạng NFD 23 ký tự (29 byte); bcrypt của NFC không khớp NFD. User đặt mật khẩu trên một thiết bị rồi đăng nhập trên thiết bị khác có thể bị báo sai mật khẩu. Chi tiết NFC/NFD ở bài Thời gian & mã hoá ký tự.
  - Thêm chuẩn hoá vào hệ đã chạy thì hash cũ được băm từ byte chưa chuẩn hoá: thử cả chuỗi gốc lẫn chuỗi NFC, khớp thì băm lại.
- **Vượt 72 byte của bcrypt**: giới hạn và CVE nằm ở bài AuthN & AuthZ cơ bản. Nếu buộc phải nhận mật khẩu dài với bcrypt, OWASP đưa công thức `bcrypt(base64(hmac-sha384(password, pepper)))`. Base64 để tránh byte `0x00`, vì bcrypt gốc coi đó là hết chuỗi. HMAC có khoá để chống [[hash-shucking|hash shucking]]: nếu chỉ băm trước bằng SHA-512 trần, kẻ tấn công thử thẳng các hash SHA-512 đã lộ ở nơi khác.
- **[[pepper|Pepper]]**:
  - Là khoá bí mật chung, cất ngoài database (secret manager, [[hsm|HSM]], [[kms|KMS]]), áp bằng [[hmac|HMAC]] trước hoặc sau bước băm. NIST gọi là lần băm có khoá bổ sung, khoá cất riêng, nên ở vùng có phần cứng bảo vệ.
  - Đổi pepper nghĩa là mọi hash cũ không kiểm được nữa. OWASP nói phải bắt user đặt lại mật khẩu; cách mềm hơn là lưu id phiên bản pepper trong mỗi dòng, giữ pepper cũ để kiểm và băm lại khi user đăng nhập.
  - Pepper là khoá HMAC trong KMS (`GenerateMac`) thì mỗi lượt login là một request KMS, tính vào quota của tài khoản (bài KMS & envelope encryption).
- **Nâng hash cũ**:
  - Lưu thuật toán và tham số cùng hash. bcrypt `$2a$10$...` dài 60 ký tự; Argon2id PHC `$argon2id$v=19$m=19456,t=2,p=1$<salt>$<hash>` cộng tiền tố `{argon2id-19m}` của Spring dài hơn 120 ký tự. Để cột `VARCHAR(255)`.
  - Hash quá yếu (MD5, SHA-1, không salt) thì đừng chờ user đăng nhập: chạy job bọc `argon2id(md5)` ngay, lần đăng nhập sau băm lại bằng mật khẩu gốc (scenario). OWASP lưu ý bọc như vậy có thể dễ dò hơn băm trực tiếp; đã chạy: hash MD5 lộ ở nơi khác thử thẳng vào lớp Argon2id là khớp. Chèn HMAC với pepper giữa hai lớp để chặn việc này.
  - Tài khoản không đăng nhập lâu: OWASP khuyên xoá hash và bắt đặt lại mật khẩu.
- **Token ngẫu nhiên không cần hàm băm chậm**: token đặt lại mật khẩu, API key, refresh token sinh bằng `SecureRandom` 128 bit trở lên thì SHA-256 là đủ, vì không có từ điển nào để dò. Băm nhanh còn cho phép tra theo hash (`WHERE token_hash = ?`), điều bcrypt có salt ngẫu nhiên không làm được. Lưu hash chứ không lưu token rõ.
- **Không mã hoá đảo ngược mật khẩu của user**. Ngoại lệ là credential ứng dụng phải gửi đi nơi khác (mật khẩu SMTP, khoá của đối tác): đó là secret, xem bài Quản lý secret.
- **Băm ở trình duyệt không thay được băm ở server**: hash gửi lên trở thành mật khẩu, lộ hash trong DB là đăng nhập được ngay. Nếu vẫn làm vì lý do khác, server vẫn phải băm chậm có salt giá trị nhận được.
- **Khi bảng user bị lộ**: buộc đặt lại mật khẩu cho tài khoản bị ảnh hưởng (ưu tiên hash cũ, yếu), thu hồi session và refresh token, đổi pepper nếu pepper có thể đã lộ, báo user và cơ quan theo quy định (bài Dữ liệu cá nhân & tuân thủ).
- **Liên quan**: bcrypt cost, 72 byte, `DelegatingPasswordEncoder`, chính sách mật khẩu NIST, `CompromisedPasswordChecker`: bài AuthN & AuthZ cơ bản. PBKDF2 để sinh khoá từ mật khẩu: bài Mật mã cho kỹ sư. Kiến trúc filter và `AuthenticationManager`: bài Kiến trúc Spring Security.
