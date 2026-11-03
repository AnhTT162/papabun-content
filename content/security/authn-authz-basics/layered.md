## Quick

[[authentication|Authentication]] (AuthN) trả lời "bạn là ai", [[authorization|authorization]] (AuthZ) trả lời "bạn được làm gì". Xác thực một lần rồi nhớ kết quả bằng [[http-session|session]] (server giữ trạng thái) hoặc token tự chứa như [[jwt|JWT]]; phân quyền thì **kiểm ở server trong mọi request**. Mật khẩu **không mã hoá mà băm bằng hàm chậm có [[salt]]** như [[bcrypt]] hay [[argon2|Argon2id]].

## Interview

**AuthN và AuthZ**: AuthN kiểm bằng chứng danh tính: thứ bạn biết (mật khẩu), thứ bạn có (điện thoại, khoá bảo mật), thứ bạn là (vân tay). Hai loại trở lên là [[mfa|MFA]]. AuthZ chạy sau, mỗi request, ở server. Thiếu xác thực trả `401`, xác thực rồi mà không đủ quyền trả `403`.

**Lưu mật khẩu**: không lưu được bản gốc và không dùng SHA-256 trần. SHA-256 quá nhanh: một luồng CPU tính được khoảng 23 triệu lần mỗi giây, GPU còn nhanh hơn nhiều, nên lộ bảng user là dò được mật khẩu phổ biến. Dùng hàm băm mật khẩu: chậm có chủ đích (bcrypt cost 10 khoảng 50 ms), có salt ngẫu nhiên riêng cho mỗi user để hai người cùng mật khẩu ra hai hash khác nhau và bảng tra sẵn ([[rainbow-table|rainbow table]]) vô dụng. Chọn Argon2id, hoặc bcrypt cost ≥ 10.

**Nhớ đăng nhập**:
- Session: server sinh id ngẫu nhiên, lưu trạng thái ở server, gửi id qua cookie. Thu hồi tức thì bằng cách xoá session. Nhiều instance thì cần kho dùng chung như Redis.
- Token tự chứa (JWT): server ký thông tin vào token, service nào có khoá đều tự kiểm được, không cần tra kho. Giá phải trả: không thu hồi được trước khi hết hạn, nên access token sống ngắn và có refresh token.

**Bẫy hay gặp**: không đổi session id sau đăng nhập ([[session-fixation|session fixation]]); thông báo lỗi khác nhau cho "sai email" và "sai mật khẩu" làm lộ tài khoản tồn tại; không giới hạn số lần đăng nhập sai nên bị [[credential-stuffing|credential stuffing]]; chỉ ẩn nút trên giao diện thay vì kiểm quyền ở API; kiểm role mà quên kiểm quyền trên đúng bản ghi ([[idor|IDOR]]).

## Deep

- **Đo trên JDK 27, Apple M4, spring-security-crypto 7.1.2** (một luồng):
  - SHA-256: khoảng 23 triệu lần/giây.
  - bcrypt cost 10/12/14: 53/210/850 ms. Mỗi bậc cost gấp đôi thời gian. Cost 10 chậm hơn SHA-256 khoảng một triệu lần.
  - `Argon2PasswordEncoder.defaultsForSpringSecurity_v5_8()`: `m=16384,t=2,p=1` (16 MiB), 14 ms. OWASP khuyên Argon2id `m=19 MiB, t=2, p=1`.
  - `Argon2PasswordEncoder` cần BouncyCastle (`bcprov-jdk18on`) trên classpath; thiếu thì lỗi khi chạy, không phải lúc biên dịch.
  - `Pbkdf2PasswordEncoder.defaultsForSpringSecurity_v5_8()`: 28 ms. Chỉ chọn PBKDF2 khi cần chuẩn FIPS.
  - Chọn tham số sao cho một lần kiểm khoảng vài chục tới vài trăm ms. Đây cũng là CPU server: 1.000 lượt đăng nhập/giây với bcrypt cost 12 cần khoảng 200 core.
- **Đọc chuỗi hash**: `$2a$10$TBXoV2hOjyOiUAI6Now52O4UkeM.NmmkXwSXPLgtByhj.Z688HrCK` gồm thuật toán (`2a`), cost (`10`), 22 ký tự salt rồi tới hash. Salt và tham số nằm ngay trong chuỗi, nên không cần cột salt riêng và đổi cost không làm hash cũ hỏng.
- **bcrypt chỉ đọc 72 byte đầu**. CVE-2025-22228 (sửa ở 6.4.4 và 6.3.8) nói về việc `BCryptPasswordEncoder` chấp nhận mật khẩu dài quá 72 ký tự. Đo trên 7.1.2: `encode` chuỗi dài hơn 72 byte ném `IllegalArgumentException: password cannot be more than 72 bytes`, còn `matches` vẫn cắt: hash của 72 chữ `a` khớp với chuỗi 72 chữ `a` + `xyz`. Tính theo byte UTF-8: 80 ký tự tiếng Việt có dấu đã là 112 byte. Đặt giới hạn độ dài mật khẩu ở tầng validate, hoặc dùng Argon2id.
- **Nâng thuật toán dần**: `PasswordEncoderFactories.createDelegatingPasswordEncoder()` sinh `{bcrypt}$2a$10$...`. Tiền tố `{id}` cho phép bảng user chứa nhiều loại hash cùng lúc. `upgradeEncoding` trả `true` cho hash cũ (`{noop}`, `{sha256}`, bcrypt cost thấp hơn), và khi có bean `UserDetailsPasswordService` thì Spring băm lại bằng thuật toán mới ngay lúc người dùng đăng nhập đúng, vì đó là lúc duy nhất có mật khẩu gốc. Hash không có tiền tố thì `matches` ném `IllegalArgumentException: There is no password encoder mapped for the id "null"`.
- **Pepper**: một secret chung cất ngoài database ([[kms|KMS]], HSM), thường áp bằng HMAC của mật khẩu với pepper trước khi băm. Lộ database mà không lộ pepper thì không dò được. Giá là phải xoay vòng khó; nhiều hệ thống bỏ qua.
- **Chống dò tài khoản bằng thời gian**: user không tồn tại thì không có hash để so, response về nhanh hơn hẳn 50 ms, lộ email nào đã đăng ký. `DaoAuthenticationProvider` của Spring vẫn chạy `matches` với một hash giả khi không tìm thấy user, và mặc định trả cùng `BadCredentialsException`. Màn hình quên mật khẩu cũng phải trả cùng câu "nếu email tồn tại, chúng tôi đã gửi link".
- **Chính sách mật khẩu theo NIST SP 800-63B (bản 4, 2025)**: tối thiểu 15 ký tự nếu mật khẩu là yếu tố duy nhất, 8 nếu đi cùng MFA; cho phép ít nhất 64 ký tự; không bắt trộn chữ hoa, số, ký tự đặc biệt; không bắt đổi định kỳ; phải chặn mật khẩu nằm trong danh sách đã lộ. Spring Security 6.3+ có `CompromisedPasswordChecker`, bản dựng sẵn hỏi Have I Been Pwned theo k-anonymity (chỉ gửi 5 ký tự đầu của SHA-1).
- **Session id**:
  - Tomcat sinh 16 byte ngẫu nhiên (32 ký tự hex) từ `SecureRandom`, đủ để không đoán được. Đừng tự sinh id bằng `Random` hay số tăng dần.
  - Spring Security mặc định chống session fixation bằng `changeSessionId` (đổi id, giữ dữ liệu) khi đăng nhập thành công.
  - Timeout: Spring Boot mặc định `server.servlet.session.timeout=30m` là idle timeout. Ứng dụng nhạy cảm cần thêm absolute timeout (ví dụ 8 giờ) vì servlet container không có sẵn.
  - Nhiều instance: session trong RAM của Tomcat thì cần [[sticky-session|sticky session]] hoặc Spring Session lưu ở Redis/JDBC. Deploy lại instance là mất session nếu chỉ giữ trong RAM.
  - Cờ cookie `HttpOnly`, `Secure`, `SameSite` và CSRF: bài Bảo mật phía trình duyệt.
- **Session hay JWT**: web một ứng dụng thì session đơn giản và thu hồi được ngay. JWT hợp khi nhiều service cần tự kiểm danh tính hoặc token do bên khác cấp (OAuth2). Cấu trúc, thuật toán ký, refresh, thu hồi và nơi lưu: bài JWT chuyên sâu; luồng đăng nhập qua bên thứ ba: bài OAuth2 & OpenID Connect.
- **MFA không ngang nhau**:
  - SMS OTP: bị chiếm qua đổi SIM, và bị lừa nhập vào trang giả.
  - [[totp|TOTP]] (app Authenticator, RFC 6238): mã 6 số đổi mỗi 30 giây, sinh từ [[hmac|HMAC]] của secret chung và thời gian. Không phụ thuộc nhà mạng nhưng vẫn bị lừa nhập vào trang giả.
  - [[passkey|Passkey]] (WebAuthn/FIDO2): khoá riêng nằm trên thiết bị, chữ ký gắn với tên miền thật nên trang giả không dùng được. Đây là loại chống [[phishing]].
  - Push "bấm Duyệt": bị spam tới khi người dùng bấm nhầm; nên bắt nhập số hiện trên màn hình đăng nhập.
- **Giới hạn đăng nhập sai**: khoá cứng tài khoản sau 5 lần cho kẻ xấu cách khoá người khác. Tốt hơn là trễ tăng dần theo tài khoản, rate limit theo IP và thiết bị, CAPTCHA khi bất thường (bài Thiết kế rate limiter có tầng luật đăng nhập).
- **Đặt lại mật khẩu**: token ngẫu nhiên ≥ 128 bit, dùng một lần, hết hạn ngắn (15–60 phút), lưu dạng hash trong database. Đổi mật khẩu xong thì huỷ mọi session và refresh token khác của user.
- **AuthZ**: kiểm ở server, gần dữ liệu, theo nguyên tắc từ chối mặc định. Role chỉ trả lời "loại người dùng nào", còn "đơn hàng 1001 có phải của user này" là kiểm trên bản ghi. RBAC, ABAC, ReBAC và cô lập tenant: bài Mô hình phân quyền; cài đặt trong Spring: bài Kiến trúc Spring Security.
