## Quick

[[jwt|JWT]] là ba phần `header.payload.signature` encode Base64URL: **ai cũng đọc được payload, chữ ký chỉ chứng minh không bị sửa và do issuer cấp**. Bên nhận phải **ghim thuật toán và khoá phía server** (không tin `alg` trong header), rồi kiểm `iss`, `aud`, `exp`. JWT không thu hồi được trước khi hết hạn, nên [[access-token|access token]] sống ngắn và đi cùng [[refresh-token|refresh token]] thu hồi được.

## Interview

**Cấu trúc**: header (`alg`, `kid`, `typ`), payload là các claim (`sub`, `iss`, `aud`, `exp`, `iat`, `jti` và claim riêng như `roles`), chữ ký trên chuỗi `header.payload`. Đây là [[jws|JWS]]; muốn giấu nội dung thì phải dùng [[jwe|JWE]], hiếm khi cần. Đừng đặt dữ liệu cá nhân vào payload.

**Thuật toán**: `HS256` là [[hmac|HMAC]] với secret chung, ai kiểm được thì cũng ký được, chỉ hợp khi bên cấp và bên kiểm là một. `RS256`, `ES256` là [[digital-signature|chữ ký số]]: issuer giữ khoá riêng, service lấy khoá công khai từ [[jwks|JWKS]] theo `kid`. Nhiều service, nhiều team thì dùng chữ ký.

**Validate**: thư viện chọn verifier theo `alg` trong token là lỗ hổng kinh điển: `alg: none`, hoặc [[algorithm-confusion|algorithm confusion]] khi kẻ tấn công ký `HS256` bằng chính khoá công khai. Ghim thuật toán, kiểm `iss` để biết ai cấp, `aud` để token của service khác không dùng được ở đây, `exp`/`nbf` với độ lệch đồng hồ nhỏ.

**Hết hạn và thu hồi**: access token 5–15 phút, service tự kiểm không gọi ai. Refresh token lưu ở server, đổi lấy access token mới, xoay vòng mỗi lần dùng; dùng lại token cũ là dấu hiệu bị đánh cắp nên huỷ cả chuỗi. Cần thu hồi tức thì (khoá tài khoản, đổi mật khẩu) thì thêm denylist theo `jti` hoặc mốc `iat` theo user, hoặc dùng [[opaque-token|opaque token]] với [[token-introspection|introspection]].

**Nơi lưu ở trình duyệt**: `localStorage` thì [[xss|XSS]] đọc được và gửi đi. An toàn hơn là [[bff|BFF]]: token nằm ở server, trình duyệt chỉ giữ cookie session `HttpOnly`, và khi đó phải chống [[csrf|CSRF]].

**Khi nào không dùng**: một ứng dụng web, một backend thì session đơn giản hơn và thu hồi được ngay.

## Deep

- **Đo trên JDK 27, Nimbus JOSE+JWT 10.10, Spring Security 7.0.5** (lab: scratchpad `code/JwtLab.java`, `code/TypLab.java`):
  - Cùng payload 125 byte, `RS256` khoá 2048 bit (header có `kid`) ra token 546 ký tự (chữ ký 256 byte), `ES256` ra 275 ký tự (chữ ký 64 byte, 86 ký tự Base64URL).
  - Token `HS256` ký bằng PEM khoá công khai (451 byte) qua được verifier chọn theo `alg`. `NimbusJwtDecoder.withPublicKey(...).signatureAlgorithm(RS256)` từ chối: `Signed JWT rejected: Another algorithm expected, or no matching key(s) found`.
  - Token `alg: none` (kết thúc bằng dấu `.`): `SignedJWT.parse` ném `Invalid JWS header: Not a JWS header`, decoder của Spring báo `Unsupported algorithm of none`.
  - Decoder mặc định **không kiểm `aud`**: token `aud=reporting-api` được `payment-api` nhận. Thêm `JwtClaimValidator` cho `aud` (hoặc `spring.security.oauth2.resourceserver.jwt.audiences`) thì ra `The aud claim is not valid`.
  - Độ lệch đồng hồ mặc định 60 giây: token hết hạn 30 giây trước vẫn qua, 90 giây thì `Jwt expired at ...`. **Token không có `exp` vẫn được nhận**: `JwtTimestampValidator` chỉ kiểm khi có claim. Issuer tin được thì thường không sao; muốn chặt thì thêm `new JwtClaimValidator<Instant>("exp", Objects::nonNull)`.
  - `typ`: decoder mặc định chỉ nhận `typ` trống hoặc `JWT`, token `at+jwt` (access token theo RFC 9068) bị từ chối với `the given typ value needs to be one of [JWT]`. `JwtValidators.createAtJwtValidator().audience(...).issuer(...).clientId(...)` thì ngược lại: chỉ nhận `at+jwt`. Kiểm `typ` ngăn dùng ID token hay token loại khác thay access token. IdP phát `at+jwt` thì dùng validator này (hoặc `new JwtTypeValidator("JWT", "at+jwt")`) thay cho mặc định.
- **Cấu hình resource server đúng trong Spring Boot**: `issuer-uri` (Spring đọc metadata, lấy `jwks_uri`, kiểm `iss`), `audiences`, ghim `jws-algorithms` nếu issuer không chỉ dùng `RS256`. Ánh xạ role, chi tiết filter, cache JWKS: bài Kiến trúc Spring Security; phần ở đây là hành vi đã đo.
- **Các header nguy hiểm**: `jku`, `x5u` (URL để tải khoá) và `jwk` (khoá nhúng trong token) cho kẻ tấn công tự chỉ định khoá. Chỉ lấy khoá từ JWKS cấu hình sẵn. `kid` là chuỗi do client gửi: dùng nó ghép vào SQL hay đường dẫn file là [[injection|injection]].
- **Lỗi ở tầng mật mã của JDK**: CVE-2022-21449 ("psychic signatures") làm JDK 15–18 chấp nhận chữ ký ECDSA toàn số 0 cho mọi nội dung, tức mọi token `ES256` giả đều qua. Sửa ở bản vá 4/2022 (17.0.3, 18.0.1). Ghim thuật toán không cứu được lỗi này; chỉ có cập nhật JDK.
- **Xoay khoá ký**: issuer công bố khoá mới trong JWKS trước, đợi các service cache xong (Nimbus tải lại JWKS khi gặp `kid` lạ, nhưng gateway hay thư viện khác có thể cache cố định vài giờ), rồi mới ký bằng khoá mới; giữ khoá cũ trong JWKS ít nhất bằng thời gian sống tối đa của token. Gỡ khoá cũ ngay là đăng xuất mọi người đang dùng token còn hạn.
- **Refresh token**:
  - [[refresh-token-rotation|Xoay vòng]]: mỗi lần đổi, server cấp refresh token mới và vô hiệu token cũ; các token cùng gốc đăng nhập thuộc một family. Token cũ được dùng lại thì không biết ai là người thật, nên huỷ cả family. RFC 9700 (OAuth 2.0 Security BCP, 1/2025) yêu cầu refresh token của public client (SPA, app di động) phải xoay vòng hoặc gắn với người giữ.
  - Lưu ở server dạng SHA-256 của token (token ngẫu nhiên ≥ 128 bit nên không cần hàm băm chậm như mật khẩu), kèm `family_id`, thiết bị, hạn tuyệt đối (ví dụ 30 ngày) và hạn không hoạt động.
  - Bẫy: app gọi song song nhiều request cùng gặp `401` rồi mỗi request tự refresh, hoặc retry sau timeout khi response đã mất. Server thấy token cũ bị dùng lại và đăng xuất người dùng thật. Client phải refresh một luồng duy nhất ([[single-flight|single-flight]]); server có thể cho khoảng ân hạn vài giây tới vài chục giây với token vừa bị thay, dài hơn `callTimeout` của client (một số IdP gọi là grace period hay reuse interval): trong khoảng đó token cũ vẫn đổi được, cấp thêm token con trong cùng family. Đổi lại là chậm phát hiện trộm và có lúc hai token con cùng sống.
- **Thu hồi access token**: denylist `jti` trong Redis với TTL bằng thời gian còn lại của token (chỉ cần giữ tới `exp`); hoặc lưu mốc `tokens_valid_after` theo user và từ chối token có `iat` nhỏ hơn, hợp cho "đăng xuất mọi thiết bị". Cả hai đưa trạng thái quay lại, mỗi request tra một lần; nếu phải tra mỗi request thì cân nhắc opaque token + introspection (RFC 7662) có cache ngắn. Thay đổi quyền chỉ có hiệu lực khi token mới được cấp.
- **Token bị đánh cắp**: bearer token ai cầm cũng dùng được. [[dpop|DPoP]] (RFC 9449) gắn token với khoá riêng của client, mỗi request kèm bằng chứng ký; mTLS-bound token (RFC 8705) gắn với chứng chỉ client. Đừng đặt JWT vào URL vì URL nằm trong access log và header `Referer`.
- **Lưu ở trình duyệt, xếp từ yếu tới mạnh**:
  - `localStorage`/`sessionStorage`: script nào trên trang cũng đọc được, XSS lấy token mang đi dùng từ máy khác tới khi hết hạn.
  - Access token trong bộ nhớ JavaScript, refresh token trong cookie `HttpOnly; Secure; SameSite=Strict` chỉ gửi tới đường dẫn refresh: XSS không lấy được refresh token, nhưng vẫn gọi API thay người dùng khi trang đang mở.
  - BFF (ở đây là backend riêng của frontend làm OAuth client): server đó giữ token, trình duyệt chỉ có cookie session. Dự thảo OAuth 2.0 for Browser-Based Apps của IETF khuyên mô hình này. Cookie thì quay lại bài toán CSRF và `SameSite` (bài Bảo mật phía trình duyệt).
  - App di động: Keychain (iOS), Keystore (Android), không lưu trong `SharedPreferences` thường.
- **HS256 với secret yếu**: token `HS256` lộ ra là đủ để dò secret offline (thử từng chuỗi, so HMAC). Secret phải ngẫu nhiên ≥ 256 bit; Nimbus `MACSigner` từ chối secret ngắn hơn. EdDSA (`Ed25519`, RFC 8037) là lựa chọn chữ ký ngắn và nhanh nếu mọi bên nhận đều hỗ trợ.
- **Kích thước**: token nằm trong header mỗi request. Tomcat và Spring Boot mặc định giới hạn header 8 KB (`server.max-http-request-header-size`), Nginx mặc định `large_client_header_buffers 4 8k`. Nhét danh sách group, quyền chi tiết vào token là sớm muộn gặp `400`/`431`. Microsoft Entra ID chỉ đưa tối đa 200 group vào JWT, quá thì thay bằng claim báo phải gọi API lấy thêm. Để token mang danh tính và scope thô; quyền chi tiết tra ở service (bài Mô hình phân quyền, sẽ viết).
- **ID token khác access token**: ID token của [[oidc|OIDC]] cho client biết ai đăng nhập, `aud` là client id; access token dành cho API. Gửi ID token tới API là dùng sai, kiểm `aud` và `typ` sẽ chặn (bài OAuth2 & OpenID Connect).
- **Giữa các service**: gateway kiểm token rồi chuyển tiếp nguyên token ([[token-relay|token relay]]) để service tự kiểm, thay vì tin header `X-User-Id` (bài API gateway, BFF & service mesh). Service gọi service bằng danh tính của chính nó dùng client credentials, đừng tái dùng token người dùng cho job chạy nền khi người dùng đã đi.
- **Liên quan**: lưu mật khẩu và session: bài AuthN & AuthZ cơ bản; HMAC và chữ ký: bài Mật mã cho kỹ sư; giữ khoá ký ở đâu và xoay thế nào: bài Quản lý secret.
