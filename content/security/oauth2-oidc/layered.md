## Quick

[[oauth2|OAuth 2.0]] là giao thức **ủy quyền**: người dùng cho một ứng dụng gọi API thay mình trong phạm vi [[oauth-scope|scope]], mà không đưa mật khẩu cho ứng dụng đó. [[oidc|OpenID Connect]] thêm lớp **xác thực**: [[id-token|ID token]] cho ứng dụng biết ai vừa đăng nhập. Có người dùng thì dùng [[authorization-code-flow|authorization code]] kèm [[pkce|PKCE]]; service gọi service thì dùng [[client-credentials|client credentials]]. Implicit và password grant đã bị loại.

## Interview

**Bốn vai**: resource owner (người dùng), [[oauth-client|client]] (ứng dụng muốn gọi API), [[authorization-server|authorization server]] (đăng nhập người dùng, cấp token), [[resource-server|resource server]] (API nhận [[access-token|access token]]).

**Authorization code + PKCE**: client chuyển trình duyệt tới `/authorize` với `client_id`, [[redirect-uri|`redirect_uri`]], `scope`, [[oauth-state|`state`]] và `code_challenge`. Authorization server đăng nhập người dùng, hỏi đồng ý, rồi chuyển về `redirect_uri` kèm `code` dùng một lần. Client đổi `code` lấy token ở `/token` qua kênh sau, gửi kèm `code_verifier`. PKCE làm cho ai chặn được `code` cũng không đổi được, vì không có `code_verifier`. `state` chống [[csrf|CSRF]] ở bước quay về.

**Loại client**: [[confidential-client|confidential client]] chạy ở server, giữ được secret. [[public-client|Public client]] (SPA, app di động) không giữ được secret, nên PKCE là bắt buộc. App di động mở trình duyệt hệ thống, không đăng nhập trong WebView. SPA nên có [[bff|BFF]] giữ token ở server (bài JWT chuyên sâu).

**Client credentials**: service xác thực bằng chính nó (secret, hoặc tốt hơn là `private_key_jwt` hay [[mtls|mTLS]]), không có người dùng. Cache token tới gần hết hạn, đừng xin token mỗi request.

**OIDC**: thêm scope `openid`, ID token, endpoint userinfo, [[oidc-discovery|discovery]]. ID token dành cho client: `aud` là `client_id`, phải kiểm `iss`, `aud`, `exp`, `nonce`. Access token dành cho API. Không gửi ID token tới API, client cũng không nên đọc access token.

**Bẫy hay gặp**: `redirect_uri` khớp theo tiền tố hay wildcard nên `code` bị gửi sang trang của kẻ tấn công; không kiểm `state`; secret nhúng trong app di động; coi scope là quyền của người dùng; API chấp nhận token cấp cho client khác vì không kiểm `aud`.

**Cách làm đúng**: dùng thư viện client và authorization server có sẵn, khớp `redirect_uri` chính xác, PKCE cho mọi client theo RFC 9700.

## Deep

- **OAuth không phải đăng nhập**: access token chứng minh "client được phép gọi API", không chứng minh "người dùng đang ở đây với client này". Dùng access token làm bằng chứng đăng nhập thì một app khác lấy được token của người dùng (từ chính authorization server đó) có thể đăng nhập vào app của mình bằng token đó. OIDC sửa bằng ID token có `aud` là client và `nonce` gắn với phiên đăng nhập.
- **PKCE (RFC 7636)**:
  - Client sinh `code_verifier` ngẫu nhiên (43–128 ký tự; 32 byte ngẫu nhiên Base64URL ra 43 ký tự), gửi `code_challenge = BASE64URL(SHA-256(code_verifier))` với `code_challenge_method=S256` ở bước authorize, gửi `code_verifier` ở bước đổi token. Đã chạy với vector của RFC: `dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk` ra `E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM`.
  - Không dùng `plain`: challenge bằng verifier, ai thấy URL authorize là có verifier.
  - Ban đầu cho public client; RFC 9700 (OAuth 2.0 Security BCP, 1/2025) khuyên dùng cho cả confidential client vì nó chặn cả code injection (kẻ tấn công nhét `code` đánh cắp được vào phiên của mình), không chỉ code bị chặn. Authorization server phải từ chối request có `code_verifier` khi lúc authorize không có challenge, để chống hạ cấp.
  - Spring Security 7.0.5 (`DefaultOAuth2AuthorizationRequestResolver`, đã chạy): thêm `code_challenge` S256 cho cả client có secret lẫn public client, thêm `state`, và thêm `nonce` khi scope có `openid`.
- **`state` và `nonce`**: `state` gắn lần quay về với phiên trình duyệt đã bắt đầu đăng nhập; thiếu nó, kẻ tấn công gửi link callback chứa `code` của chính họ và nạn nhân bị đăng nhập vào tài khoản kẻ tấn công (login CSRF, bài Bảo mật phía trình duyệt). `nonce` nằm trong ID token, chống phát lại ID token. PKCE đã chặn được phần lớn các tấn công mà `state` nhắm tới, nhưng `state` vẫn cần khi authorization server không hỗ trợ PKCE và để mang trạng thái của ứng dụng.
- **`redirect_uri`**:
  - Đăng ký trước, so khớp chuỗi chính xác (RFC 9700). Cho wildcard `https://*.shop.example.com/*` hay khớp tiền tố là chỉ cần một [[open-redirect|open redirect]] hay một subdomain bị chiếm để `code` (hoặc token) bay sang chỗ khác.
  - Ở bước đổi token, client gửi lại đúng `redirect_uri` và server kiểm nó khớp với lúc authorize.
  - Một client nhiều môi trường: đăng ký từng URI, không mở rộng pattern.
- **App di động (RFC 8252)**: đăng nhập qua trình duyệt hệ thống (`ASWebAuthenticationSession` trên iOS, Custom Tabs trên Android) để app không đọc được mật khẩu và người dùng thấy đúng địa chỉ. WebView nhúng thì app đọc được mọi thứ người dùng gõ, và nhiều [[identity-provider|IdP]] (như Google) chặn. Redirect bằng custom scheme (`shop://callback`) có thể bị app khác đăng ký trùng; universal link / app link có xác minh tên miền thì không. PKCE vẫn là lớp chặn chính.
- **Các grant khác**:
  - Implicit (token trả thẳng trên URL fragment) và resource owner password credentials (client nhận mật khẩu): RFC 9700 nói không dùng; bản dự thảo OAuth 2.1 bỏ hẳn. Password grant còn phá MFA và dạy người dùng gõ mật khẩu vào app lạ.
  - Device authorization grant (RFC 8628): TV, CLI không có trình duyệt hiện mã để người dùng nhập trên điện thoại; client hỏi lại theo `interval`.
  - [[token-exchange|Token exchange]] (RFC 8693): service đổi token của người dùng lấy token mới có `aud` là service phía sau và scope hẹp hơn, thay vì chuyển tiếp nguyên token có phạm vi rộng.
  - [[refresh-token|Refresh token]]: xoay vòng và phát hiện dùng lại, nơi lưu: bài JWT chuyên sâu.
- **Client credentials trong thực tế**:
  - Xác thực client: `client_secret_basic` là secret chung; `private_key_jwt` (RFC 7523) ký một JWT ngắn hạn bằng khoá riêng, authorization server chỉ giữ khoá công khai; mTLS (RFC 8705) dùng chứng chỉ. Với hai cách sau, authorization server không giữ secret của client; khoá riêng ở phía client vẫn phải bảo vệ (bài Quản lý secret).
  - Token cache theo client và scope, xin lại khi còn vài chục giây. Mỗi request xin token là dồn tải lên authorization server, thường dính rate limit. Spring Security có `OAuth2ClientHttpRequestInterceptor` cho `RestClient` (từ 6.4) dùng `OAuth2AuthorizedClientManager` để cache và tự xin lại.
  - Một client cho một service, scope tối thiểu. Job chạy nền thay người dùng thì nên dùng token exchange hay quyền riêng, đừng giữ token người dùng.
- **Scope, audience và quyền**: scope là giới hạn mà người dùng (hoặc admin) cho client, ví dụ `orders.read`. Nó không thay phân quyền: người dùng có scope `orders.read` vẫn chỉ đọc được đơn của mình, kiểm ở API (bài Mô hình phân quyền). Token phải có `aud` là API nhận nó; Resource Indicators (RFC 8707) cho client xin token cho đúng API. Hỏi đồng ý cho scope rộng hơn cần là người dùng quen bấm "Cho phép" mà không đọc.
- **ID token, access token, userinfo**:
  - ID token là [[jwt|JWT]] ký bởi IdP; client kiểm chữ ký theo [[jwks|JWKS]], `iss`, `aud` chứa `client_id` (có nhiều aud thì `azp` nên là client), `exp`, `nonce`. Spring Security làm việc này trong `OidcIdTokenValidator`.
  - Claim định danh ổn định là cặp `iss` + `sub`, không phải email: email đổi được, và IdP nhiều tenant có thể cho người dùng tự khai email chưa xác minh. Nối tài khoản theo email mà không kiểm `email_verified` là lỗ hổng chiếm tài khoản.
  - Userinfo trả claim khi ID token không có đủ; gọi bằng access token.
  - Access token với client là chuỗi mờ: IdP có thể đổi định dạng bất kỳ lúc nào.
- **Access token JWT hay opaque**: JWT (RFC 9068) cho API tự kiểm tại chỗ, nhanh và không phụ thuộc IdP mỗi request, nhưng không thu hồi được trước `exp`. [[opaque-token|Opaque token]] buộc API hỏi IdP qua [[token-introspection|introspection]] (RFC 7662), thu hồi có hiệu lực ngay, đổi lại thêm một lần gọi (cache vài chục giây). Client thu hồi refresh token khi đăng xuất qua endpoint revocation (RFC 7009). RFC 9700 khuyên ràng token với người giữ ([[dpop|DPoP]] hoặc mTLS) để token bị đánh cắp không dùng được ở máy khác. Chi tiết: bài JWT chuyên sâu.
- **Discovery**: `/.well-known/openid-configuration` cho `authorization_endpoint`, `token_endpoint`, `jwks_uri`, thuật toán hỗ trợ. Spring Boot chỉ cần `issuer-uri`. Với client (`oauth2Login()` khai `issuer-uri`), Boot gọi discovery lúc khởi động: IdP không trả lời là ứng dụng không lên.
- **Tấn công khi dùng nhiều IdP**: mix-up attack: client dùng chung `redirect_uri` cho nhiều authorization server và một server độc hại lừa client gửi `code` của server thật sang nó. Chống bằng `redirect_uri` riêng mỗi IdP hoặc tham số `iss` trong response (RFC 9207). Pushed Authorization Requests (PAR, RFC 9126): client đẩy tham số authorize qua kênh sau, URL trình duyệt chỉ còn `request_uri`, tham số không bị sửa trên đường đi; FAPI 2.0 cho ngân hàng bắt buộc PAR.
- **Spring Boot 4**: starter đổi tên thành `spring-boot-starter-security-oauth2-client` (tên cũ `spring-boot-starter-oauth2-client` vẫn còn nhưng deprecated). `oauth2Login()` lo toàn bộ luồng authorization code và tạo session; principal là `OidcUser`. Resource server là starter khác (bài Kiến trúc Spring Security).
- **Đăng xuất**: xoá session của client chưa đăng xuất khỏi IdP, người dùng bấm đăng nhập lại là vào luôn. RP-Initiated Logout, back-channel logout và [[sso|SSO]] giữa nhiều ứng dụng: bài SSO doanh nghiệp & SAML.
- **Liên quan**: validate JWT, refresh token, nơi lưu token: bài JWT chuyên sâu; IdP, workload identity, OIDC federation cho CI: bài Kiến trúc bảo mật; token relay ở gateway: bài API gateway, BFF & service mesh.
